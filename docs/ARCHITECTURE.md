# Architecture

## Hardware data paths

```text
Xbox controller
  USB-C
    |
MAX3421E USB Host Shield
  SPI over Leonardo ICSP pins
    |
ATmega32U4 main loop                 ATmega32U4 native USB peripheral
  USB Host Shield task                endpoint-zero feature reports
  Xbox report parser                  interrupt input reports
  Xbox -> PS4 translation             PS4 console
  authentication task
  RSA signer
```

The MAX3421E supplies the USB host controller missing from the Leonardo. The ATmega32U4 native USB peripheral remains free to act as the PS4-side device. This makes simultaneous Xbox hosting and PS4 device emulation possible with one microcontroller.

## Firmware modules

| Module | Responsibility |
| --- | --- |
| `LeonardoPS4Bridge.ino` | Initializes both USB roles, runs the cooperative loop and services Xbox input during signing |
| `XboxInput.cpp` | Reads XBOXONE values and builds a compact ten-byte translated report |
| `Ps4Device.cpp` | Atomically publishes translated controls through PS4Arduino setters |
| `Ps4Auth.cpp` | F0/F1/F2/F3 state machine, CRC, cancellation epochs and F4 diagnostics |
| `Signer.cpp` | SHA-256, PSS, CRT exponentiation, recombination, timing and stack instrumentation |
| `rps_mul_avr.S` | 1,024x1,024-bit product using single-frame reverse product scanning |
| `rps_square_avr.S` | Symmetry-aware 1,024-bit square |
| `hsps_avr.S` | 2,048-to-1,024-bit Montgomery reduction |
| `mont_avr.S` | Retained fused FIOS helpers used by regression/instruction tests |
| Core patches | Authentication feature reports, descriptor fixes, transactional F1 commit and USB-reset notification |

## Execution model

The main loop repeatedly:

1. handles an optional authenticated bootloader request;
2. resets the watchdog;
3. services the MAX3421E host stack;
4. publishes the latest Xbox controls;
5. starts a pending signature outside the USB ISR; and
6. advances the one-byte-at-a-time EEPROM trace writer.

Native USB control and input transfers continue through interrupts. Arithmetic never disables interrupts for a complete modular operation. `signerService()` runs after each complete square/multiply/reduction combination, approximately every 12-15 ms in the measured kernels, to reset the watchdog and poll the Xbox host.

## Authentication concurrency

The F0 callback runs from the USB ISR, while signing runs in the main loop. A monotonically increasing epoch protects against stale results:

- beginning a round records `signingEpoch`;
- F3, USB reset or incompatible F0 increments `epoch` and sets `cancelled`;
- the signer checks cancellation at service points; and
- READY is published only if epoch, state and cancellation still match after signing.

The 256-byte `em` buffer is both challenge storage and RSA encoded-message/signature workspace. Because F0 cannot overwrite it while signing, the core stalls a new challenge until the current signer unwinds.

## Memory ownership

Static arithmetic buffers in `Signer.cpp` are intentionally fixed and heap-free:

| Buffer | Bytes | Main uses |
| --- | ---: | --- |
| `em` | 256 | F0 challenge, PSS encoded message, final signature |
| `product` | 256 | Full RPS product before HSPS reduction |
| `work` | 132 | PSS scratch, reduction scratch, bit-serial initial reduction |
| `base`, `acc`, `modulus`, `rr` | 4 x 128 | Montgomery operands, accumulator and constants |
| `partP` | 128 | P-branch CRT result and temporary `base^5` |
| `partQ` | alias | Points to `acc` after Q exponentiation |

Key factors, CRT exponents, `qInv`, `R^2 mod p/q`, serial and certificate data remain in flash through generated PROGMEM headers.

The final link uses 2,019 bytes of static SRAM, leaving 541 bytes before stack. Estimated signer plus USB-ISR overlap is 266 bytes, leaving an estimated 275-byte margin. That margin has not been confirmed with a physical high-water mark.

## Input translation

Axes are scaled from signed 16-bit Xbox values to unsigned PS4 bytes. Y axes are inverted. Ten-bit triggers are rounded into 0-255 values. Opposite D-pad directions cancel, and valid diagonals map to the standard eight-way hat values.

All PS4Arduino setters run inside one atomic block so the USB ISR never observes a partially updated report.

## Patched USB core boundary

The stock PS4Arduino-derived core is patched to:

- advertise the complete 489-byte HID descriptor;
- route F0/F3/F4 SET_REPORT data to the sketch;
- obtain dynamic F1/F2/F4 GET_REPORT bodies from the sketch;
- prepend exactly one report ID;
- commit F1 page advancement only after the complete control response queues;
- notify the sketch on a USB bus reset; and
- avoid advertising pointer capabilities that forced the PS4 keyboard into touch mode.

The library patch keeps touch and motion values neutral while retaining touchpad-click support.

