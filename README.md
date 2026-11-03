# LeonardoPS4Bridge

An experimental, standalone Xbox Series X controller to PlayStation 4 bridge built with an Arduino Leonardo and USB Host Shield 2.0.

The Leonardo simultaneously hosts the wired Xbox controller through the shield's MAX3421E and appears to the PS4 as a PS4-style USB controller. It translates controls, supports the PS4 home screen, games and on-screen keyboard, maps Xbox Share to the touchpad click, implements the PS4 F0/F1/F2/F3 authentication exchange, and performs RSA-2048 PSS/SHA-256 signing entirely on the 16 MHz ATmega32U4.

> This is credential-required research firmware. It contains no controller credentials or compiled firmware. Continuous authenticated play requires a legitimate, console-accepted credential set obtained from hardware you own. The public source has not completed a 20-minute PS4 test with an accepted identity.

## What was accomplished

- Xbox Series X USB input through USB Host Shield Library 2.0
- PS4-compatible USB enumeration and input reports through a patched PS4Arduino core
- Working sticks, triggers, D-pad, face/shoulder buttons, PS, Options and Share
- Touchpad-click emulation without forcing the PS4 keyboard into pointer mode
- Complete five-page F0 challenge collection with CRC, sequence and duplicate handling
- F2 busy/ready reporting while the signer runs
- Complete nineteen-page F1 authentication response delivery
- RSA-2048 PSS/SHA-256 signing using CRT on an ATmega32U4
- Cooperative watchdog, Xbox polling and native USB service during signing
- Credential-free diagnostics persisted to EEPROM for retrieval after a PS4 test
- A physical signing-time reduction from approximately 220 seconds to **37.422 seconds**

## Results

| Milestone | Physical Leonardo signing time | Main change |
| --- | ---: | --- |
| Early prototype | approximately 220 s | Correct but minimally optimized CRT signer |
| First instrumented benchmark | 209.330 s | Separated PSS and RSA timing |
| Optimized FIOS | 71.45 s | Fused 8-bit Montgomery arithmetic and fixed-key scheduling |
| Current RPS + HSPS | **37.422 s** | Specialized product/square kernels plus separated Montgomery reduction |

The current integrated build uses **28,462 / 28,672 bytes of flash** and **2,019 / 2,560 bytes of static SRAM**. Two physical Windows validation rounds produced valid signatures, matched the certified public key, reconstructed all nineteen response pages, and observed a maximum 16 ms gap between F2/input reports.

The 37.422-second result is a **5.59x speedup** over the first instrumented 209.330-second benchmark and about **5.88x faster** than the rounded early prototype.

## How the speedup was achieved

The original bottleneck was not SHA-256 or USB. The first instrumented run spent 166.868 ms in SHA-256/PSS and 209.164 seconds in CRT RSA. Montgomery modular arithmetic accounted for almost all RSA time.

The final design combines several techniques:

1. **Chinese Remainder Theorem:** one RSA-2048 private operation becomes two 1,024-bit exponentiations modulo `p` and `q`, followed by Garner recombination.
2. **Fixed-key exponent schedule:** the private CRT exponents stay in flash and a small `{base, base^3, base^5}` schedule reduces general multiplications without an SRAM-heavy window table.
3. **RPS product scanning:** separate AVR assembly kernels form 2,048-bit products. Squaring uses operand symmetry; general multiplication uses a single 63-column frame.
4. **HSPS Montgomery reduction:** a separate 1,024-bit reducer converts each 2,048-bit product back into the Montgomery domain.
5. **Memory lifetime reuse:** buffers are reused between PSS encoding, the two CRT branches and recombination. The Q result aliases the accumulator after exponentiation.
6. **Cooperative servicing:** native USB interrupts remain enabled, and the firmware services the watchdog and Xbox host after each complete modular operation.
7. **Measured integration:** candidates were first checked with Python big integers, source guards and static cycle accounting, then benchmarked as complete modular operations on the physical Leonardo before integration.

Physical arithmetic measurements at 16 MHz:

| Complete operation | Cycles | Time |
| --- | ---: | ---: |
| HSPS reduction | 120,892.8 | 7.558 ms |
| RPS square + HSPS reduction | 186,336 | 11.646 ms |
| RPS multiply + HSPS reduction | 235,929.6 | 14.746 ms |

The complete signer performs 2,048 modular squares and 603 other Montgomery operations, then pays the remaining cost for message reduction, PSS encoding, CRT recombination and cooperative servicing.

The development was not a straight line. A specialized square initially lost to the fused kernel. Small assembly changes produced only low-single-digit improvements. The first physical RPS multiplication attempt executed 1,520 blocks instead of 1,024, read beyond an operand and failed every vector. Fixing the upper-column loop, adding an exact block-count source guard, and rerunning boundary/alias tests produced the verified 235,929.6-cycle operation. A later integrated test used the wrong local USB core and repeatedly returned F1 page zero; the persisted trace isolated that transport failure from the RSA result. Rebuilding against the pinned core restored transactional F1 page advancement.

The full engineering progression, including discarded approaches, is documented in [docs/ENGINEERING.md](docs/ENGINEERING.md).

## Authentication flow

```text
PS4                         Leonardo
 |-- SET_REPORT F0 page 0 ---->|
 |-- SET_REPORT F0 page 1 ---->|
 |-- SET_REPORT F0 page 2 ---->|
 |-- SET_REPORT F0 page 3 ---->|
 |-- SET_REPORT F0 page 4 ---->|  256-byte challenge complete
 |<-- GET_REPORT F2: busy ------|  RSA-PSS signing
 |<-- GET_REPORT F2: ready -----|  response ready
 |<-- GET_REPORT F1 pages 0..18-|  1,064 response bytes
 |-- GET_REPORT F3/reset ------>|  next authentication round
```

F0 pages 0-3 carry 56 challenge bytes each; page 4 carries 32. F2 returns status `0x10` while signing and `0x00` when ready. F1 returns the following response in nineteen 56-byte pages:

```text
RSA-PSS signature (256)
serial (16)
RSA modulus (256)
RSA exponent padded to 256 bytes (256)
authority certificate signature (256)
zero padding (24)
= 1,064 bytes
```

Each report includes the console-provided nonce identifier and a reflected CRC-32. F1 advances only after the USB core successfully queues the complete report, preventing a failed transfer from silently skipping a page. See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md).

## What the PS4 test proved

The bridge physically worked on the PS4 home screen, on-screen keyboard and in games. The fastest build was then left connected for twelve minutes. Controls became intermittent and stopped around eight minutes.

The saved trace recorded:

- 40 valid F0 transfers: eight complete five-page challenges
- 264 F2-busy and seven F2-ready responses
- 133 committed F1 pages: exactly seven complete nineteen-page responses
- eight completed signatures and zero signer aborts
- zero malformed F0 pages and zero F1-before-ready requests
- 5,682 Xbox polls while signing
- the final challenge completed at 641 s and became ready at 675 s

This moved the blocker. Signing speed and F1 delivery were no longer the observed failures. The console received complete responses but still enforced the eight-minute timeout, so the tested credential identity was not accepted. Local signature verification cannot prove console acceptance, and this repository does not claim otherwise.

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

No computer is needed during gameplay. The Leonardo's native USB cable connects to the PS4; the Xbox controller connects to the Host Shield.

## Control mapping

| Xbox | PS4 |
| --- | --- |
| A / B / X / Y | Cross / Circle / Square / Triangle |
| LB / RB | L1 / R1 |
| LT / RT | L2 / R2, including analog values |
| View / Menu | Share / Options |
| Left/right stick click | L3 / R3 |
| Xbox button | PS button |
| Xbox Share button | Touchpad click |
| D-pad and both sticks | Corresponding PS4 controls |

## Repository map

- `firmware/LeonardoPS4Bridge/` - integrated controller, authentication and signer firmware
- `benchmarks/rps_hsps/` - credential-free arithmetic models, vectors and source guards
- `patches/` - the PS4Arduino core and library changes required by the bridge
- `tests/` - state-machine, descriptor, arithmetic and trace-parser checks
- `tools/generate_credentials.py` - validates owner-supplied credentials and generates ignored local headers
- [docs/ENGINEERING.md](docs/ENGINEERING.md) - optimization journey and design decisions
- [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) - report formats and state machine
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - module, memory and execution architecture
- [docs/BUILDING.md](docs/BUILDING.md) - pinned dependencies and exact build procedure
- [docs/TESTING.md](docs/TESTING.md) - offline, Windows and PS4 validation gates
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - common build, input and authentication failures
- [docs/BENCHMARKS.md](docs/BENCHMARKS.md) - physical timing and resource measurements

## Quick build outline

The verified build uses Arduino CLI 1.5.1, Arduino AVR Boards 1.8.6 / AVR GCC 7.3.0, USB Host Shield Library 2.0 1.7.0, and a patched custom core named **`experimental:ps4avr:leonardo`**. It does not use the stock `arduino:avr:leonardo` core.

Generate the two ignored headers from credentials you are legally permitted to use:

```powershell
python -m pip install -r tools/requirements.txt
python tools/generate_credentials.py `
  --key C:\private\key.pem `
  --serial C:\private\serial.txt `
  --signature C:\private\sig.bin `
  --output firmware\LeonardoPS4Bridge
```

The generator validates RSA structure and the certificate signature without printing credential values. Follow [docs/BUILDING.md](docs/BUILDING.md) to install the pinned core/library commits, apply patches and compile.

## Security and publication policy

- Never commit `private_crt.h`, `public_identity.h`, credential inputs or firmware binaries.
- Every compiled firmware image embeds private credential material.
- This repository does not provide or extract PlayStation credentials.
- Do not open an issue asking for keys.
- Challenge, signature and identity bytes are intentionally absent from diagnostic traces.

See [SECURITY.md](SECURITY.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Status

This is a research prototype, not a supported commercial adapter. The accurate status is:

> **Controller translation works, the complete authentication exchange works, and the physical signer finishes in 37.422 seconds. Continuous authenticated gameplay remains blocked by credential acceptance.**

The next decisive validation is a screen-observed 20-minute PS4 session using a legitimately sourced, console-accepted identity.
