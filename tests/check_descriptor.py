"""Validate the staged HID descriptor's advertised size and authentication reports."""
import argparse
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('core', type=Path)
args = p.parse_args()
source = (args.core/'cores/arduino/PS4Arduino/PS4Arduino_USBDesc.cpp').read_text()
body = source.split('const u8 hidDescriptor[] = {', 1)[1].split('};', 1)[0]
body = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
data = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]+)', body))
advertised = int(re.search(r'ps4ReportDescriptorBytes\s*=\s*(\d+)', source)[1])
assert len(data) == advertised == 489, 'Truncated HID report descriptor'
assert 'sizeof(hidDescriptor) == ps4ReportDescriptorBytes' in source
counts = {}
size = count = report = depth = 0
offset = 0
while offset < len(data):
    prefix = data[offset]
    offset += 1
    assert prefix != 0xFE, 'Unexpected long HID item'
    length = (0, 1, 2, 4)[prefix & 3]
    kind, tag = (prefix >> 2) & 3, prefix >> 4
    value = int.from_bytes(data[offset:offset+length], 'little')
    offset += length
    assert offset <= len(data)
    if kind == 1:
        if tag == 7: size = value
        elif tag == 8: report = value
        elif tag == 9: count = value
        assert tag not in (10, 11), 'Add global PUSH/POP support before using it'
    elif kind == 0:
        if tag == 10: depth += 1
        elif tag == 12:
            depth -= 1
            assert depth >= 0
        elif tag in (8, 9, 11):
            counts[tag, report] = counts.get((tag, report), 0) + size*count
assert depth == 0, 'Unclosed HID collection'
for rid, expected in ((0xF0, 64), (0xF1, 64), (0xF2, 16), (0xF3, 8), (0xF4, 64)):
    assert counts[11, rid] == (expected-1)*8
assert counts[8, 1] == 63*8
print('PASS: descriptor length489, balanced collections, input1 and featureF0..F4 sizes')
