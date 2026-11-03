"""Read prototype F4 diagnostics or request Caterina without a CDC serial port.

Use ../OptimizedRsaBenchmark/hid_validate.py --list to obtain the exact HID path.
python probe_control.py --path hex:... --diagnostics
python probe_control.py --path hex:... --bootloader
Requires hidapi. Never accesses credentials or logs authentication payloads.
"""
import argparse
import json
import struct
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--diagnostics", action="store_true")
    action.add_argument("--bootloader", action="store_true")
    args = parser.parse_args()
    if not args.path.startswith("hex:"):
        parser.error("Use the exact hex:... path returned by hid_validate.py --list")
    path = bytes.fromhex(args.path[4:])
    import hid
    matches = [entry for entry in hid.enumerate(0x1532, 0x0401) if entry["path"] == path]
    if len(matches) != 1:
        raise ValueError("Exact HID path must match one prototype interface")
    device = hid.device()
    try:
        device.open_path(path)
        if args.bootloader:
            body = b"\xF4LEOBOOT!" + bytes(51)
            packet = body + struct.pack("<I", zlib.crc32(body))
            if device.send_feature_report(packet) != 64:
                raise ValueError("Incomplete bootloader request")
            print(json.dumps({"Caterina_request": "SENT", "bootloader_enumeration": "CHECK REQUIRED"}))
        else:
            data = bytes(device.get_feature_report(0xF4, 64))
            if len(data) != 64 or data[0] != 0xF4 or data[1] != 1:
                raise ValueError("Incorrect diagnostic format")
            if struct.unpack("<I", data[-4:])[0] != zlib.crc32(data[:-4]):
                raise ValueError("Diagnostic CRC failed")
            fields = ["pss_us", "rsa_us", "total_us", "mont_us", "reduce_us", "p_us",
                      "q_us", "combine_us", "mont_calls", "max_service_gap_us",
                      "stack_watermark_bytes", "heap_bytes"]
            result = dict(zip(fields, struct.unpack("<10I2H", data[5:49])))
            completed, abandoned, epoch = struct.unpack("<3H", data[49:55])
            result.update(state=data[2], cancelled=bool(data[3]), completed=completed,
                          abandoned=abandoned, epoch=epoch,
                          host_initialized=bool(data[55] & 1), xbox_connected=bool(data[55] & 2),
                          signer_busy=bool(data[56]), real_PS4_acceptance="NOT TESTED")
            print(json.dumps(result, indent=2))
    finally:
        device.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"result": "FAIL", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
