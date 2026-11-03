"""Check the counter-only F4 console trace decoder without hardware."""
import contextlib
import io
import json
import struct
import sys
import types
import zlib

import probe_control


values = ([0xA74D, 3] + [1] * 5 + [5, 8000, 1, 19, 2200]
          + [0, 0, 0, 1, 1, 1, 0, 2, 1, 1, 64, 18, 0]
          + [1, 75, 75, 83, 84, 150, 58, 70, 0])
raw = struct.pack('<HB5B5H13B9H', *values)
raw = raw[:-2] + struct.pack('<H', zlib.crc32(raw[:-2]) & 0xFFFF)
body = bytes((0xF4, 2, 1)) + raw + bytes(8)
assert len(body) == 60
report = body + struct.pack('<I', zlib.crc32(body))


class FakeDevice:
    def open_path(self, path):
        assert path == b'\x01'

    def get_feature_report(self, report_id, length):
        assert (report_id, length) == (0xF4, 64)
        return report

    def close(self):
        pass


sys.modules['hid'] = types.SimpleNamespace(
    enumerate=lambda vid, pid: [{'path': b'\x01'}], device=FakeDevice)
sys.argv = ['probe_control.py', '--path', 'hex:01', '--diagnostics']
out = io.StringIO()
with contextlib.redirect_stdout(out):
    probe_control.main()
result = json.loads(out.getvalue())
assert result['source'] == 'EEPROM snapshot'
assert result['f0_setups'] == 5 and result['f0_pages'] == [1] * 5
assert result['f2_busy'] == 8000 and result['f1_pages'] == 19
assert result['last_f1_page'] == 18 and result['saved_sec'] == 150
assert result['duplicate_f0'] == 2 and result['usb_resets'] == 1
assert result['xbox_polls_during_signing'] == 2200
assert (result['min_abort_duration_sec'], result['max_abort_duration_sec']) == (58, 70)

old_values = ([0xA74D, 2] + [1] * 5 + [5, 64]
              + [0, 0, 123, 1, 19, 0, 2, 1, 1, 0]
              + [18, 0] + [1, 80, 81, 150, 60, 55, 60, 0])
old_raw = struct.pack('<HB5BHB10H2B8H', *old_values)
old_raw = old_raw[:-2] + struct.pack('<H', zlib.crc32(old_raw[:-2]) & 0xFFFF)
old_body = bytes((0xF4, 2, 1)) + old_raw + bytes(8)
report = old_body + struct.pack('<I', zlib.crc32(old_body))
out = io.StringIO()
with contextlib.redirect_stdout(out):
    probe_control.main()
old_result = json.loads(out.getvalue())
assert old_result['trace_version'] == 2
assert old_result['f0_setups'] == 5 and old_result['last_f0_transfer_length'] == 64
assert old_result['f2_busy'] == 123 and old_result['f1_pages'] == 19
assert old_result['last_abort_duration_sec'] == 60

v4_values = values.copy()
v4_values[1] = 4
v4_values[-3:] = [287, 760, 0]
v4_raw = struct.pack('<HB5B5H13B9H', *v4_values)
v4_raw = v4_raw[:-2] + struct.pack('<H', zlib.crc32(v4_raw[:-2]) & 0xFFFF)
v4_body = bytes((0xF4, 2, 1)) + v4_raw + bytes(8)
report = v4_body + struct.pack('<I', zlib.crc32(v4_body))
out = io.StringIO()
with contextlib.redirect_stdout(out):
    probe_control.main()
v4_result = json.loads(out.getvalue())
assert v4_result['trace_version'] == 4
assert v4_result['max_f2_busy_age_deciseconds'] == 287
assert v4_result['max_f3_age_deciseconds'] == 760
assert 'min_abort_duration_sec' not in v4_result
print('F4 parser v2/v3/v4 PASS')
