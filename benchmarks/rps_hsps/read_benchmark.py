"""Read repeated, credential-free HFIPS timings from a Leonardo."""
import argparse
import json
import statistics
import time

import serial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20:
        parser.error("rounds must be between 1 and 20")
    results = []
    with serial.Serial(args.port, 115200, timeout=15) as device:
        time.sleep(1)
        device.reset_input_buffer()
        for _ in range(args.rounds):
            device.write(b"R")
            raw = device.readline()
            if not raw:
                raise RuntimeError("benchmark response timed out")
            row = json.loads(raw)
            if (row.get("hfips_correct") is not True or row.get("hsps_correct") is not True
                    or row.get("hsps_vectors_correct") is not True
                    or row.get("rps_square_correct") is not True
                    or row.get("rps_hsps_square_correct") is not True
                    or row.get("rps_multiply_correct") is not True
                    or row.get("rps_hsps_multiply_correct") is not True
                    or row.get("rps_multiply_vectors_correct") is not True
                    or row.get("rps_multiply_alias_a") is not True
                    or row.get("rps_multiply_alias_b") is not True
                    or row.get("rps_multiply_square_parity") is not True):
                raise RuntimeError("arithmetic result failed its expected vector")
            if row.get("hsps_vector_count") != 8:
                raise RuntimeError("unexpected HSPS vector count")
            if row.get("rps_multiply_vector_count") != 6:
                raise RuntimeError("unexpected RPS multiply vector count")
            if not all(isinstance(row.get(field), int) for field in
                       ("hfips_microseconds", "hsps_reduction_microseconds",
                        "hsps_timer1_cycles", "rps_hsps_square_microseconds",
                        "rps_hsps_square_timer1_cycles", "rps_hsps_multiply_microseconds",
                        "rps_hsps_multiply_timer1_cycles")):
                raise RuntimeError("invalid timing report")
            results.append(row)
    print(json.dumps({
        "device": "physical Arduino Leonardo",
        "synthetic_vectors": True,
        "rounds": results,
        "mean_hfips_microseconds": statistics.mean(
            x["hfips_microseconds"] for x in results),
        "mean_hsps_reduction_microseconds": statistics.mean(
            x["hsps_reduction_microseconds"] for x in results),
        "mean_hsps_timer1_cycles": statistics.mean(
            x["hsps_timer1_cycles"] for x in results),
        "mean_rps_hsps_square_microseconds": statistics.mean(
            x["rps_hsps_square_microseconds"] for x in results),
        "mean_rps_hsps_square_timer1_cycles": statistics.mean(
            x["rps_hsps_square_timer1_cycles"] for x in results),
        "mean_rps_hsps_multiply_microseconds": statistics.mean(
            x["rps_hsps_multiply_microseconds"] for x in results),
        "mean_rps_hsps_multiply_timer1_cycles": statistics.mean(
            x["rps_hsps_multiply_timer1_cycles"] for x in results),
    }, indent=2))


if __name__ == "__main__":
    main()
