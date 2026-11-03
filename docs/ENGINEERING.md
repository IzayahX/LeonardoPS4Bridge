# Engineering progression

This document records how the project moved from a working eight-minute controller prototype to a complete authentication implementation and a 37.422-second physical RSA signer.

## 1. Establishing the bridge

The starting hardware was an Arduino Leonardo connected to a USB Host Shield 2.0 over the Leonardo's SPI/ICSP pins. The library's `XBOXONE` example proved that a wired Xbox Series X controller enumerated and produced buttons, sticks and triggers.

PS4Arduino supplied the initial PS4-style USB input interface. The firmware translated Xbox values into PS4 report fields and physically verified:

- home-screen navigation;
- game input;
- D-pad and face buttons;
- analog sticks and triggers;
- PS4 on-screen keyboard operation; and
- Xbox Share as the PS4 touchpad click.

The keyboard initially remained in a touch-pointer mode. Advertising neutral touch/motion capabilities and keeping neutral touch coordinates fixed restored ordinary D-pad keyboard navigation without removing the touchpad button.

The first controller build stopped at exactly eight minutes. Reconnecting only the Xbox controller did not recover it; reconnecting the Leonardo did. That separated Xbox-host input failure from the PS4's unauthenticated-controller limit.

## 2. Completing the authentication protocol

The original PS4Arduino core described the F0-F3 feature reports but did not forward a challenge to sketch code or serve dynamic F1/F2 responses. The core patches added sketch callbacks while preserving endpoint-zero control-transfer behavior.

The state machine was implemented in `Ps4Auth.cpp`:

```text
IDLE -> RECEIVING -> PENDING -> SIGNING -> READY -> IDLE
```

Important correctness rules were added after trace-driven debugging:

- accept only the expected F0 page and nonce ID;
- verify CRC-32 before copying challenge bytes;
- acknowledge exact duplicate pages without restarting a partial challenge;
- reject conflicting or out-of-order pages;
- never overwrite the challenge/work buffer while the signer is active;
- cancel stale work on F3 or USB reset;
- report F2 busy until a complete response exists;
- advance F1 only after the USB core successfully queues that page; and
- never reuse a signature for a different challenge.

The F4 diagnostic report records counters and timestamps, not challenge, signature or identity bytes. A compact snapshot is written one EEPROM byte per main-loop iteration after 150 seconds and refreshed each minute. This made blind PS4 tests diagnosable after moving the Leonardo back to Windows.

## 3. First standalone signer: correctness before speed

The isolated benchmark implemented:

- SHA-256 over the 256-byte console challenge;
- MGF1-SHA-256;
- EMSA-PSS with a 32-byte salt;
- RSA-2048 signing through two 1,024-bit CRT branches; and
- Garner recombination into the 256-byte signature.

The physical Leonardo produced a signature verified by Python. Measurements were:

| Part | Time |
| --- | ---: |
| SHA-256 and PSS | 166.868 ms |
| CRT RSA | 209.164 s |
| Total | 209.330 s |

This proved mathematical correctness and identified the real problem: almost all time was in modular exponentiation, specifically Montgomery operations.

## 4. FIOS optimization

The next implementation fused multiplication and Montgomery reduction in an AVR-oriented finely integrated operand-scanning loop. It used fixed 8-bit limbs, flash-resident key material and Montgomery constants, no heap, and cooperative service points.

Fixed-key exponent scheduling added `base^3` and `base^5`, recognizing `11` and `101` patterns in the two private CRT exponents. This reduced the complete schedule to 2,651 Montgomery calls without allocating a large window table.

Incremental assembly tuning reduced the physical signer to approximately 71.45 seconds. It was a major improvement, but small loop changes had reached diminishing returns and remained far above the observed console polling window.

## 5. Why the arithmetic architecture changed

Published AVR work suggested that standalone products and specialized squaring could be materially faster than treating every operation as a single generic fused loop:

- Liu and Grossschädl, [New Speed Records for Montgomery Modular Multiplication on 8-bit AVR Microcontrollers](https://eprint.iacr.org/2013/882)
- Großschädl et al., [Reverse Product Scanning Multiplication and Squaring on 8-bit AVR](https://orbilu.uni.lu/handle/10993/19568)

Published simulator timings were treated as leads, not as Leonardo measurements. The project required a complete product plus reduction, ABI costs, final normalization, physical timing and integrated memory fit before accepting an approach.

The replacement kept the caller-facing `mont(out, a, b, inverse)` boundary but split its internals:

```text
a, b --RPS multiply/square--> 2,048-bit product
product --HSPS reduction----> 1,024-bit Montgomery result
```

This separation makes a symmetric square cheaper while sharing one reducer between square and multiply.

## 6. Credential-free kernel gates

Every arithmetic candidate had to pass host big-integer comparison, boundary vectors, chained operations, alias tests, source-level control-flow guards, static cycle accounting and a physical Leonardo benchmark.

The HSPS reducer physically measured 120,892.8 cycles. The complete RPS square plus HSPS reduction measured 186,336 cycles.

The first multiplication attempt failed. Its upper 31 product columns incorrectly executed 32 blocks each. The kernel ran 1,520 blocks instead of the required 1,024, read past operand A and reported an invalid 289,672-cycle result. A high-level model had not emulated the assembly pointers, so it missed the error.

The fix changed the upper-half count, and a source guard now asserts exactly 1,024 blocks and checks stack/alias constraints. The corrected physical multiply plus reduction passed its vectors at a mean 235,929.6 cycles.

## 7. Integrated signer

The separated kernels were integrated behind the existing `mont()` boundary. The signer uses:

- 2,048 specialized modular squares;
- 603 general Montgomery operations;
- bit-serial initial reduction of the 2,048-bit encoded message modulo each CRT prime;
- two fixed 1,024-bit exponent schedules;
- two Montgomery operations for `qInv`-based CRT preparation; and
- bytewise 1,024x1,024 multiplication plus addition for Garner recombination.

The first integration selected an older local PS4 AVR core. RSA finished in roughly 37 seconds, but F1 page zero repeated because that core lacked the transactional `ps4AuthCommit()` hook. The EEPROM trace recorded ready status with zero committed pages, proving that the failure was transport integration rather than arithmetic.

Rebuilding against the pinned core fixed the page advancement. Two physical Windows rounds each reached ready in 37.422 seconds. Both signatures, certificates, certified-key matches and all nineteen response pages passed.

## 8. Memory and responsiveness

The final build leaves only 210 bytes of application flash. Static SRAM leaves 541 bytes before stack use. Non-LTO stack files plus explicit assembly frames estimate a 266-byte signer/USB-ISR overlap and 275 bytes of remaining margin; a physical high-water mark is still unavailable.

Large exponentiation tables were rejected because they would remain live alongside the 256-byte product, 128-byte modulus and arithmetic scratch. The implemented three-power schedule provides useful call reduction within the memory budget.

Native USB interrupts remain enabled. After every complete Montgomery operation, `signerService()` resets the watchdog and services MAX3421E/Xbox work. The measured Windows validation gap was at most 16 ms. The test observed changing report counters, but not changing button values during the final two rounds, so it does not claim that every control transition survives signing.

## 9. Console result and current conclusion

The fastest build completed eight signatures during a twelve-minute PS4 run. The console requested seven complete F1 responses and still stopped accepting controller input at about eight minutes.

That evidence rules out the previously suspected signing-time and response-paging blockers for that run. The remaining leading explanation is that the tested identity was not accepted by that console. The console does not expose whether this is revocation, a trust-store mismatch or another identity-specific policy.

The project therefore demonstrates a working controller bridge, a complete PS4 authentication exchange and a 37.422-second standalone AVR signer. It does not demonstrate accepted authentication with the tested credentials.

## Approaches deliberately not retained

- Reconnecting every eight minutes: not authentication and not acceptable.
- Hardcoding a signature: impossible because the console supplies fresh challenges.
- Descriptor/VID/PID spoofing alone: sufficient for temporary input, not authentication.
- Large width-4/5 exponent tables: insufficient SRAM alongside live arithmetic buffers.
- Published fully unrolled Karatsuba routines: incompatible with the available flash budget.
- The first specialized square: slower than the then-current fused kernel.
- Continuing a signature after a conflicting F0 or F3: risks serving an obsolete response.
- Reporting F2 ready early: invalid because all 1,064 response bytes must already be stable.

## References and how they were used

- [USB Host Shield Library 2.0](https://github.com/felis/USB_Host_Shield_2.0): MAX3421E host stack and `XBOXONE` parser. This project adds translation and PS4-side behavior; it does not replace the Xbox USB driver.
- [PS4Arduino-AVR](https://github.com/Flamethr0wer/PS4Arduino-AVR) and [PS4Arduino](https://github.com/Flamethr0wer/PS4Arduino): starting PS4-style USB device core, descriptor and controller report setters. The repository patches endpoint-zero authentication routing, report commitment, capabilities and neutral touch behavior.
- [GP2040-CE PS4 driver](https://github.com/OpenStickCommunity/GP2040-CE/blob/main/src/drivers/ps4/PS4Driver.cpp): cross-check for authentication report layout, paging, status and CRC behavior. Its RP2040 implementation was not copied as an AVR arithmetic implementation.
- [RFC 8017](https://www.rfc-editor.org/rfc/rfc8017): EMSA-PSS encoding and RSA terminology.
- [Liu and Grossschädl, AVR Montgomery multiplication](https://eprint.iacr.org/2013/882): HFIPS/HSPS design reference and published comparison point. Published simulator cycles were not presented as Leonardo measurements.
- [Reverse Product Scanning on AVR](https://orbilu.uni.lu/handle/10993/19568): product and square architecture used as the lead for the credential-free RPS kernels.
- [Karatsuba multiplication for AVR](https://eprint.iacr.org/2014/592): evaluated as an alternative but not integrated because the available fully unrolled code and scratch requirements did not fit the complete firmware budget.

