# LeonardoPS4Bridge

An experimental, standalone Xbox Series X controller to PlayStation 4 bridge built on an Arduino Leonardo and USB Host Shield 2.0.

The project demonstrates working Xbox USB host input, PS4-style USB reports, controller translation, touchpad-click emulation, the PS4 F0/F1/F2 authentication exchange, and RSA-2048 PSS/SHA-256 signing entirely on a 16 MHz ATmega32U4.

> This is credential-required research firmware. It does not include controller credentials, keys, or compiled firmware. Continuous authenticated PS4 play requires a legitimate credential set from hardware you own. The public source has not yet completed a 20-minute PS4 test with a console-accepted credential identity.

## Results

| Milestone | Physical Leonardo signing time |
| --- | ---: |
| Early prototype | approximately 220 s |
| First instrumented benchmark | 209.33 s |
| Optimized FIOS implementation | 71.45 s |
| Current separated RPS + HSPS implementation | **37.42 s** |

The current integrated build used 28,462 of 28,672 bytes of flash and 2,019 of 2,560 bytes of static SRAM. Two Windows validation rounds produced valid RSA-PSS signatures, matching certified identities, all 19 response pages, and a maximum observed USB/input service gap of 16 ms.

On a real PS4, the bridge enumerated and worked in the home screen, on-screen keyboard, and games. A 12-minute trace recorded complete challenges, completed signatures, F2-ready responses, and seven complete 19-page F1 responses. Controls still stopped at about eight minutes with the tested credential identity, which means that identity was not accepted by the console. This is not evidence that arbitrary or shared credentials work.

## Hardware

```text
Xbox Series X controller --USB-C--> USB Host Shield 2.0
                                           |
                                      SPI / ICSP
                                           |
                                    Arduino Leonardo
                                           |
                                      native USB
                                           |
                                          PS4
```

No PC is used during gameplay. The Leonardo hosts the Xbox controller through the MAX3421E and appears to the PS4 as the USB controller device.

## Repository layout

- `firmware/LeonardoPS4Bridge/` — integrated bridge and AVR RSA implementation
- `benchmarks/rps_hsps/` — credential-free arithmetic models and tests
- `patches/` — required PS4Arduino core/device changes
- `tests/` — host-side protocol, descriptor, arithmetic, and trace tests
- `tools/generate_credentials.py` — validates owner-supplied credentials and generates ignored local headers
- `docs/` — architecture, benchmarks, build, and console-test details

## Build

The measured build used Arduino CLI 1.5.1, Arduino AVR Boards 1.8.6, AVR GCC 7.3.0, USB Host Shield Library 2.0 1.7.0, and the pinned PS4Arduino repositories listed in [docs/BUILDING.md](docs/BUILDING.md).

Generate the two ignored headers from credentials that you are legally permitted to use:

```powershell
python -m pip install -r tools/requirements.txt
python tools/generate_credentials.py `
  --key C:\private\key.pem `
  --serial C:\private\serial.txt `
  --signature C:\private\sig.bin `
  --output firmware\LeonardoPS4Bridge
```

The generator validates RSA structure and the certificate signature without printing credential values. See [docs/BUILDING.md](docs/BUILDING.md) for dependency patching and compilation.

## Security and publication policy

- Never commit `private_crt.h`, `public_identity.h`, credential files, or firmware binaries.
- Every compiled firmware image contains the private credential material.
- This repository does not provide, extract, sell, or help obtain PlayStation credentials.
- Do not open an issue asking for keys.

See [SECURITY.md](SECURITY.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Status

This is a research prototype, not a supported commercial adapter. The next decisive test is a screen-observed 20-minute PS4 session with a legitimately sourced, console-accepted identity. Until that passes, the correct claim is **working bridge and complete authentication implementation, credential acceptance unresolved**.

