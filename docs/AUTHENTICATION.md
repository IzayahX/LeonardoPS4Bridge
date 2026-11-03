# Authentication protocol implementation

This describes the feature-report behavior implemented by the project. It is an interoperability record, not official Sony protocol documentation.

## Reports

All authentication traffic uses HID feature reports on endpoint zero. The report ID is included in CRC calculation but is handled separately by the sketch-facing callbacks.

| Report | Direction | Purpose | Full length |
| --- | --- | --- | ---: |
| F0 | PS4 to device | Challenge page | 64 bytes |
| F1 | Device to PS4 | Response page | 64 bytes |
| F2 | Device to PS4 | Busy/ready status | 16 bytes |
| F3 | PS4 to device | Reset authentication round | 8 bytes |
| F4 | Development | Credential-free diagnostics/boot request | 64 bytes |

CRC-32 uses reflected polynomial `0xEDB88320`, initial value `0xFFFFFFFF`, final complement, and little-endian CRC bytes.

## F0 challenge collection

The F0 body after the report ID is:

```text
byte 0      nonce/sequence identifier
byte 1      page index 0..4
byte 2      zero
bytes 3..58 payload
bytes 59..62 CRC-32
```

Pages 0-3 contribute 56 bytes. Page 4 contributes 32 bytes, producing the exact 256-byte RSA challenge.

The firmware checks total control-transfer length, report shape, CRC, page order and nonce ID. Exact retransmissions of already accepted pages are acknowledged without restarting. A conflicting nonzero page cancels the partial round. A new page zero starts a new epoch. F0 is stalled while the shared challenge/arithmetic buffer is live in the signer.

## Signing

After page 4, the state changes from `PENDING` to `SIGNING` in the main loop, outside the USB ISR. The signer:

1. hashes all 256 challenge bytes with SHA-256;
2. forms a 2048-bit EMSA-PSS encoded message using MGF1-SHA-256 and a 32-byte salt;
3. reduces that message modulo both 1,024-bit CRT primes;
4. exponentiates using `dP` and `dQ` in the Montgomery domain;
5. converts both residues to normal form;
6. applies `h = (sP - sQ) * qInv mod p`; and
7. forms the normal 2,048-bit signature `sQ + q*h`.

The present firmware derives its salt deterministically from the challenge digest and a fixed label. This produces a valid 32-byte PSS salt and makes tests reproducible, but it is variable-time, unblinded research code and is not claimed to resist physical side-channel or fault attacks.

## F2 status

The F2 body echoes the nonce ID and reports:

- `0x10` while the response is unavailable;
- `0x00` only after a complete, uncancelled signature is ready.

Nine zero bytes and CRC-32 complete the 15-byte body; the USB core prepends the F2 report ID.

## F1 response

The response is:

| Offset | Length | Content |
| ---: | ---: | --- |
| 0 | 256 | Fresh RSA-PSS signature over the challenge |
| 256 | 16 | Controller serial |
| 272 | 256 | Certified RSA modulus |
| 528 | 256 | Certified RSA exponent, big-endian and padded |
| 784 | 256 | Authority signature over serial + modulus + exponent |
| 1040 | 24 | Zero padding |

Nineteen F1 reports carry 56 response bytes each. The final report contains the last 56 bytes, so no special short transfer is required. Every page echoes the nonce ID and includes its page number and CRC.

The USB core calls `ps4AuthCommit(F1)` only after queueing the complete report. This transaction boundary matters: advancing during response construction caused page loss/repetition during earlier integration work.

## F3, resets and stale work

F3 increments the epoch, marks the current operation cancelled, clears page indices and returns to `IDLE`. A native USB reset does the same. Arithmetic checks cancellation at service points and never publishes the result if the epoch changed.

The firmware intentionally does not continue and cache a signature across F3 because it cannot assume that the next authentication round uses the same challenge.

## Diagnostics

F4 exposes only counters, coarse timestamps and state flags. It never stores challenge bytes, signatures, key material or certificate bytes. The parser is `firmware/LeonardoPS4Bridge/probe_control.py`.

Useful counters include F0 pages/setups, malformed and duplicate pages, F2 busy/ready, F1 committed pages, F3 and USB resets, signer starts/completions/aborts, Xbox polls during signing and the last committed page.

## Evidence boundary

The following are separately established:

- local RSA-PSS correctness;
- certificate signature correctness;
- private/public-key match;
- exact 1,064-byte response construction;
- all nineteen F1 pages delivered on Windows;
- complete F1 responses requested by a physical PS4.

None alone proves that the console accepts an identity. Only continued physical gameplay beyond the unauthenticated timeout establishes that outcome.

