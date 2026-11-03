# Benchmarks

All headline timings below are physical Arduino Leonardo measurements at 16 MHz. Host models and static cycle counts were used as development gates, not reported as hardware results.

| Implementation | Complete RSA-PSS signature |
| --- | ---: |
| Initial CRT prototype | 209.330 s |
| Optimized FIOS | 71.45 s |
| RPS multiplication/squaring + HSPS reduction | 37.422 s |

The early development result was commonly rounded to approximately 220 seconds. The instrumented first benchmark separated 166.868 ms of SHA-256/PSS work from 209.164 s of CRT RSA work.

For the current integrated build:

- Flash: 28,462 / 28,672 bytes
- Static SRAM: 2,019 / 2,560 bytes
- Estimated stack/ISR margin: 275 bytes; this is an estimate, not a formal proof
- Maximum observed USB/input service gap in two Windows validation rounds: 16 ms
- Cryptographic result: two fresh signatures verified against the certified public key
- Authentication response: all 19 pages reconstructed to exactly 1,064 bytes

The final 37.422-second result is a 5.59x improvement over the first instrumented 209.330-second benchmark.

The PS4 was observed polling F2 busy through roughly 42 seconds in an earlier trace. That made the current signer fast enough to deliver F2 ready and full F1 responses, but a tested credential identity was rejected and the eight-minute timeout remained.

