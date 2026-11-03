# Benchmarks and measured evidence

Physical timings were captured on an Arduino Leonardo at 16 MHz. Published AVR simulator results and Windows host timings were used only as design guidance and are not labeled as Leonardo measurements.

## Complete signing progression

| Implementation | Physical time | Relative to 209.330 s |
| --- | ---: | ---: |
| Initial CRT implementation | 209.330 s | 1.00x |
| Optimized 8-bit FIOS | 71.45 s | 2.93x |
| RPS product/square + HSPS reduction | **37.422 s** | **5.59x** |

The early prototype was informally rounded to approximately 220 seconds. Its instrumented successor measured:

```text
SHA-256/PSS: 0.166868 s
CRT RSA:   209.163592 s
Total:     209.330460 s
```

This showed that optimizing certificate construction, descriptors or SHA could not materially change the outcome.

## Complete modular operations

| Operation | Static/physical status | Cycles | Time at 16 MHz |
| --- | --- | ---: | ---: |
| HSPS Montgomery reduction | physical mean | 120,892.8 | 7.556 ms |
| RPS square + HSPS reduction | physical mean | 186,336.0 | 11.646 ms |
| RPS multiply + HSPS reduction | physical mean | 235,929.6 | 14.746 ms |

The measured complete operation includes reduction and final result handling, not only raw multiplication.

The current fixed-key schedule performs 2,048 squares and 603 other Montgomery operations. A hardware-calibrated model predicted about 39.21 seconds before integration. The physical integrated result was faster at 37.422 seconds, demonstrating why the model remained a gate rather than a claimed result.

## Integrated Windows validation

| Metric | Round 1 | Round 2 |
| --- | ---: | ---: |
| Last F0 to F2 ready | 37.422 s | 37.422 s |
| Full USB exchange | 37.469 s | 37.453 s |
| F2 polls | 3,151 | 3,141 |
| Input reports | 9,367 | 9,366 |
| Maximum observed F2/input gap | 16 ms | 16 ms |
| RSA-PSS verification | PASS | PASS |
| Certificate/key match | PASS | PASS |
| F1 pages | 19 | 19 |

The input counters advanced, but no button/stick value changes were recorded in these final rounds; this evidence establishes report continuity, not control-change continuity.

## Resource usage

```text
Flash:        28,462 / 28,672 bytes (210 bytes free)
Static SRAM:   2,019 /  2,560 bytes (541 bytes before stack)
Estimated signer + USB ISR stack overlap: 266 bytes
Estimated remaining margin: 275 bytes
Heap use: 0 bytes by design
```

The stack figures are derived from non-LTO stack-use files and explicit assembly frames. They are not a physical high-water measurement.

## PS4 timing evidence

An earlier timing build observed its latest F2-busy poll at 42.0 seconds into signing and an F3 at 72.0 seconds. These were maxima across rounds, not an official or exact deadline.

The final twelve-minute test recorded a 34-second final challenge-to-ready interval using coarse whole-second firmware timestamps. It delivered seven complete response sets before the eight-minute input cutoff. Therefore the tested failure is no longer explained by a signer that misses the observed polling period.

## Correctness coverage

Credential-free tests cover:

- 85 product/square and five reduction-boundary model cases;
- 1,003 general RPS products plus square parity;
- 1,003 specialized-square vectors;
- 10,003 HSPS quotient/ABI cases;
- exact 1,024-block multiplication source structure;
- instruction-level FIOS regression cases;
- zero, one, modulus-minus-one, maximum-carry and random values;
- chained Montgomery-domain operations; and
- supported result aliasing.

The physical kernel benchmarks embedded independent expected vectors and repeated them five times. The integrated validator used fresh challenges and a trusted host cryptographic implementation.

## Interpretation limits

- Physical timing does not prove console acceptance.
- Static cycle counts do not replace physical timing.
- Static SRAM subtraction does not prove stack safety.
- A valid certificate signature does not prove an identity remains accepted by a PS4.
- A complete F1 transfer proves delivery, not the console's internal trust decision.

