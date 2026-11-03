"""Count private exponent operations without printing key-derived bytes."""
import re
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: window_counts.py PATH_TO_LOCAL_PRIVATE_CRT_HEADER")
header = Path(sys.argv[1])
source = header.read_text()

for name in ("crtDp", "crtDq"):
    match = re.search(r"const uint8_t " + name + r"\[128\].*?=\s*\{(.*?)\};", source, re.S)
    if not match:
        raise ValueError("missing exponent")
    raw = bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", match.group(1)))
    bits = "".join(f"{byte:08b}" for byte in raw[::-1])
    old = 0
    i = 0
    while i < 1024:
        if bits[i] == "1" and i + 1 < 1024 and bits[i+1] == "1":
            old += 1
            i += 2
        elif bits[i] == "1":
            old += 1
            i += 1
        else:
            i += 1
    for pattern in ("101", "111"):
        i = new_mult = 0
        while i < 1024:
            if bits[i:i+3] == pattern:
                new_mult += 1
                i += 3
            elif bits[i:i+2] == "11":
                new_mult += 1
                i += 2
            elif bits[i] == "1":
                new_mult += 1
                i += 1
            else:
                i += 1
        print(f"{name} {pattern}: old multiplications={old}, proposed={new_mult}, saved={old-new_mult-2} after setup")
