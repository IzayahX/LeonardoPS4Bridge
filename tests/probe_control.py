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
            if len(data) != 64 or data[0] != 0xF4 or data[1] not in (1, 2):
                raise ValueError("Incorrect diagnostic format")
            if struct.unpack("<I", data[-4:])[0] != zlib.crc32(data[:-4]):
                raise ValueError("Diagnostic CRC failed")
            if data[1] == 2:
                raw = data[3:52]
                magic, version = struct.unpack_from("<HB", raw)
                if magic != 0xA74D or version not in (2, 3, 4):
                    raise ValueError("Incorrect trace header")
                if data[2] and struct.unpack_from("<H", raw, 47)[0] != (zlib.crc32(raw[:-2]) & 0xFFFF):
                    raise ValueError("Saved trace checksum failed")
                if version == 2:
                    old = struct.unpack("<HB5BHB10H2B8H", raw)
                    result = dict(source="EEPROM snapshot" if data[2] else "live RAM",
                                  trace_version=2, f0_pages=list(old[2:7]),
                                  f0_setups=old[7], last_f0_transfer_length=old[8],
                                  f0_bad=old[9], f0_during_signing=old[10],
                                  f2_busy=old[11], f2_ready=old[12],
                                  f1_pages=old[13], f1_before_ready=old[14],
                                  f3_resets=old[15], signer_starts=old[16],
                                  signatures_ready=old[17], signatures_aborted=old[18],
                                  last_f1_page=old[19], state_at_save=old[20],
                                  first_f0_sec=old[21], ready_sec=old[22],
                                  last_f1_sec=old[23], saved_sec=old[24],
                                  last_abort_duration_sec=old[25],
                                  min_abort_duration_sec=old[26],
                                  max_abort_duration_sec=old[27],
                                  current_state=data[52],
                                  host_initialized=bool(data[53] & 1),
                                  xbox_connected=bool(data[53] & 2),
                                  signer_busy=bool(data[54]))
                else:
                    values = struct.unpack("<HB5B5H13B9H", raw)
                    result = dict(source="EEPROM snapshot" if data[2] else "live RAM",
                              trace_version=version,
                              f0_pages=list(values[2:7]),
                              f0_setups=values[7], f2_busy=values[8],
                              f2_ready=values[9], f1_pages=values[10],
                              xbox_polls_during_signing=values[11],
                              f0_bad=values[12], f0_during_signing=values[13],
                              f1_before_ready=values[14], f3_resets=values[15],
                              signer_starts=values[16], signatures_ready=values[17],
                              signatures_aborted=values[18], duplicate_f0=values[19],
                              usb_resets=values[20], last_cancel_reason=values[21],
                              last_f0_transfer_length=values[22], last_f1_page=values[23],
                              state_at_save=values[24], first_f0_sec=values[25],
                              last_f0_sec=values[26], f0_complete_sec=values[27],
                              ready_sec=values[28], last_f1_sec=values[29],
                              saved_sec=values[30],
                              current_state=data[52],
                              host_initialized=bool(data[53] & 1),
                              xbox_connected=bool(data[53] & 2),
                              signer_busy=bool(data[54]))
                    if version == 3:
                        result.update(min_abort_duration_sec=values[31],
                                      max_abort_duration_sec=values[32])
                    else:
                        result.update(max_f2_busy_age_deciseconds=values[31],
                                      max_f3_age_deciseconds=values[32])
            else:
                fields = ["pss_us", "rsa_us", "total_us", "mont_us", "reduce_us", "p_us",
                          "q_us", "combine_us", "mont_calls", "max_service_gap_us",
                          "stack_watermark_bytes", "heap_bytes"]
                result = dict(zip(fields, struct.unpack("<10I2H", data[5:49])))
                completed, abandoned, epoch = struct.unpack("<3H", data[49:55])
                result.update(state=data[2], cancelled=bool(data[3]), completed=completed,
                              abandoned=abandoned, epoch=epoch,
                              host_initialized=bool(data[55] & 1), xbox_connected=bool(data[55] & 2),
                              signer_busy=bool(data[56]))
            result["real_PS4_acceptance"] = "NOT ESTABLISHED BY DIAGNOSTICS ALONE"
            print(json.dumps(result, indent=2))
    finally:
        device.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"result": "FAIL", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
