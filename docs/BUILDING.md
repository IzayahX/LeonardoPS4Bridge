# Reproducible Windows build

The verified firmware does **not** build against the stock Leonardo core. It requires the pinned PS4Arduino-AVR checkout and this repository's patches, exposed as `experimental:ps4avr:leonardo`.

## Required software

- Git
- Python 3
- Arduino CLI 1.5.1
- Arduino AVR Boards 1.8.6, which supplies AVR GCC 7.3.0
- Python package `cryptography`

Later versions may work but are not the measured configuration.

## Pinned sources

| Dependency | Version/commit |
| --- | --- |
| [PS4Arduino-AVR](https://github.com/Flamethr0wer/PS4Arduino-AVR) | `86723988485d662a75d0f9e93d5524ca738ca6ee` |
| [PS4Arduino](https://github.com/Flamethr0wer/PS4Arduino) | `814e496da57459a20348fe4fa9e2cd63ea50cb89` |
| [USB Host Shield Library 2.0](https://github.com/felis/USB_Host_Shield_2.0) | 1.7.0 |
| Arduino AVR Boards | 1.8.6 |

## 1. Create an isolated Arduino directory

From the repository root, create these directories:

```powershell
New-Item -ItemType Directory -Force `
  toolchain\user\hardware\experimental, `
  toolchain\user\libraries, `
  toolchain\data, `
  toolchain\downloads | Out-Null
```

Create `toolchain/arduino-cli.yaml` using absolute paths on your computer:

```yaml
board_manager:
  additional_urls: []
directories:
  data: C:\absolute\path\to\LeonardoPS4Bridge\toolchain\data
  downloads: C:\absolute\path\to\LeonardoPS4Bridge\toolchain\downloads
  user: C:\absolute\path\to\LeonardoPS4Bridge\toolchain\user
```

Install the pinned AVR tools and Host Shield library:

```powershell
arduino-cli core update-index --config-file toolchain\arduino-cli.yaml
arduino-cli core install arduino:avr@1.8.6 --config-file toolchain\arduino-cli.yaml
arduino-cli lib install "USB Host Shield Library 2.0@1.7.0" `
  --config-file toolchain\arduino-cli.yaml
```

## 2. Install and patch the custom core

```powershell
git clone https://github.com/Flamethr0wer/PS4Arduino-AVR.git `
  toolchain\user\hardware\experimental\ps4avr
git -C toolchain\user\hardware\experimental\ps4avr checkout `
  86723988485d662a75d0f9e93d5524ca738ca6ee

git -C toolchain\user\hardware\experimental\ps4avr apply `
  ..\..\..\..\..\patches\core-auth.patch
git -C toolchain\user\hardware\experimental\ps4avr apply `
  ..\..\..\..\..\patches\integrated-core.patch
git -C toolchain\user\hardware\experimental\ps4avr apply `
  ..\..\..\..\..\patches\no-pointer-capabilities.patch
git -C toolchain\user\hardware\experimental\ps4avr apply `
  ..\..\..\..\..\patches\auth-trace-core.patch
```

Patch order matters because the files are incremental. All four patches were verified to apply sequentially to the pinned commit.

If the relative paths are inconvenient, replace each patch argument with its absolute path.

## 3. Install and patch PS4Arduino

```powershell
git clone https://github.com/Flamethr0wer/PS4Arduino.git `
  toolchain\user\libraries\PS4Arduino
git -C toolchain\user\libraries\PS4Arduino checkout `
  814e496da57459a20348fe4fa9e2cd63ea50cb89
git -C toolchain\user\libraries\PS4Arduino apply `
  ..\..\..\..\patches\touchpad-neutral.patch
```

The library patch keeps neutral touch/motion values and registers the required callbacks. It preserves touchpad-click support while avoiding PS4 keyboard pointer mode.

## 4. Generate local credential headers

Only use credentials you are legally permitted to use. The generator parses the RSA-2048 key, checks CRT consistency, normalizes the serial, verifies the 256-byte certificate signature against the documented public authority, and emits flash-ready arrays.

```powershell
python -m pip install -r tools\requirements.txt
python tools\generate_credentials.py `
  --key C:\private\key.pem `
  --serial C:\private\serial.txt `
  --signature C:\private\sig.bin `
  --output firmware\LeonardoPS4Bridge
```

Expected generated files:

- `firmware/LeonardoPS4Bridge/private_crt.h`
- `firmware/LeonardoPS4Bridge/public_identity.h`

They are ignored by Git. Every resulting HEX embeds credential material and must remain private.

## 5. Run source checks

```powershell
python tests\check_no_secrets.py
python benchmarks\rps_hsps\test_model.py
python benchmarks\rps_hsps\test_rps_mul_model.py
python benchmarks\rps_hsps\test_rps_mul_source.py
python benchmarks\rps_hsps\test_rps_square_model.py
python benchmarks\rps_hsps\test_rps_square_source.py
python benchmarks\rps_hsps\test_singleloop_schedule.py
python tests\test_arithmetic.py
python tests\test_trace_parser.py
```

## 6. Compile

```powershell
arduino-cli compile `
  --config-file toolchain\arduino-cli.yaml `
  --fqbn experimental:ps4avr:leonardo `
  firmware\LeonardoPS4Bridge
```

The verified totals are:

```text
Sketch uses 28462 bytes (99%) of program storage space. Maximum is 28672 bytes.
Global variables use 2019 bytes (78%) of dynamic memory, leaving 541 bytes for local variables.
```

The expected SPI architecture warning occurs because the custom architecture is named `ps4avr` while SPI declares `avr`; the processor is still the ATmega32U4. Treat any other warning or resource change as something to investigate.

## 7. Upload

Identify the Leonardo port while it is connected to Windows:

```powershell
arduino-cli board list --config-file toolchain\arduino-cli.yaml
arduino-cli compile --upload `
  --config-file toolchain\arduino-cli.yaml `
  --fqbn experimental:ps4avr:leonardo `
  --port COM_PORT `
  firmware\LeonardoPS4Bridge
```

Replace `COM_PORT` with the detected port. A Caterina bootloader reset may briefly change the port. Uploading proves only that the image was accepted by the bootloader; continue with [TESTING.md](TESTING.md).

## Secret-safety check before any commit

```powershell
python tests\check_no_secrets.py
git status --short
```

Never add generated headers, credential inputs, `.hex`, `.elf`, `.eep`, `.bin` or linker-map files.
