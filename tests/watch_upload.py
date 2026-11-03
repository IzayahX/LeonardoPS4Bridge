"""Wait for a physical Leonardo RESET (or F4 boot request), then flash locally."""
import argparse
import subprocess
import time
from pathlib import Path
from serial.tools import list_ports

p = argparse.ArgumentParser()
p.add_argument('hex', type=Path)
p.add_argument('--wait', type=float, default=300)
p.add_argument('--tools', type=Path, default=Path('work/arduino-data/packages/arduino/tools/avrdude/8.0.0-arduino1'))
args = p.parse_args()
if not args.hex.is_file() or 'with_bootloader' in args.hex.name or not 0 < args.wait <= 600:
    raise SystemExit('Supply application-only HEX and a wait of 1..600 seconds')
print('Waiting for Leonardo RESET / Caterina bootloader', flush=True)
deadline = time.monotonic() + args.wait
while time.monotonic() < deadline:
    found = [x for x in list_ports.comports()
             if x.vid in (0x2341, 0x2A03) and x.pid in (0x0036, 0x0037)]
    if len(found) == 1:
        code = subprocess.call([
            str(args.tools/'bin/avrdude.exe'), '-C'+str(args.tools/'etc/avrdude.conf'),
            '-patmega32u4', '-cavr109', '-P'+found[0].device, '-b57600', '-D',
            '-Uflash:w:'+str(args.hex.resolve())+':i'])
        raise SystemExit(code)
    time.sleep(0.05)
raise SystemExit('No bootloader detected before deadline; run again and press RESET')
