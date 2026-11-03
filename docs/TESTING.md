# Verification and physical test procedure

Testing is intentionally staged so a compile is never confused with cryptographic or console acceptance.

## Gate 1: credential-safe source checks

From the repository root:

```powershell
python tests/check_no_secrets.py
python benchmarks/rps_hsps/test_model.py
python benchmarks/rps_hsps/test_rps_mul_model.py
python benchmarks/rps_hsps/test_rps_mul_source.py
python benchmarks/rps_hsps/test_rps_square_model.py
python benchmarks/rps_hsps/test_rps_square_source.py
python benchmarks/rps_hsps/test_singleloop_schedule.py
python tests/test_arithmetic.py
python tests/test_trace_parser.py
```

The arithmetic tests cover boundaries, random products, reduction, `A == B`, result aliasing, fixed exponent schedules, ABI preservation, stack limits and source control-flow assumptions. They do not emulate every AVR instruction in the RPS/HSPS kernels; the physical benchmark remains necessary when modifying assembly.

## Gate 2: build

Generate local credential headers and compile with the pinned `experimental:ps4avr:leonardo` core. Confirm the expected current totals:

```text
Flash:       28,462 / 28,672 bytes
Static SRAM:  2,019 /  2,560 bytes
```

Unexpected growth is important because only 210 bytes of application flash remain. A successful compile does not prove stack safety or PS4 acceptance.

## Gate 3: Windows authentication validation

Before a PS4 test, use a host validator to send two fresh random challenges through the Leonardo authentication HID interface. For each round require:

- five F0 pages accepted;
- F2 remains responsive and changes from busy to ready;
- the nonce ID is echoed in F1 and F2;
- exactly nineteen sequential F1 pages;
- a 1,064-byte response after reassembly;
- RSA-PSS/SHA-256 signature verification;
- authority certificate signature verification;
- certified public key matches the local private key; and
- no signer abort, malformed page or early F1 count.

The recorded reference rounds reached ready in 37.422 seconds and completed in 37.469/37.453 seconds. Maximum observed input/F2 gap was 16 ms.

Exercise Xbox buttons and sticks during this test. The reference final rounds observed continuous input report counters but no changing control values, so control-change continuity should be explicitly repeated after signer changes.

## Gate 4: PS4 test

1. Keep the Xbox controller attached to the Host Shield.
2. Connect only the Leonardo native USB cable to the PS4.
3. Verify home-screen movement and button input within the first minute.
4. Launch a game and test sticks, D-pad, face buttons, triggers, Options, PS and touchpad click.
5. Check controls at 1, 8, 12 and 20 minutes without reconnecting either device.
6. Leave the Leonardo connected for at least one additional minute after the event of interest so the EEPROM trace refresh can complete.
7. Move only the Leonardo cable back to Windows; do not flash first.
8. Read F4 diagnostics using the exact authentication HID path:

```powershell
python firmware\LeonardoPS4Bridge\probe_control.py --path hex:EXACT_PATH --diagnostics
```

## Interpreting a trace

Authentication transport completed when all of the following hold:

- each challenge has five F0 pages;
- `signatures_ready` increases;
- F2 ready is nonzero;
- F1 pages increase in groups of nineteen;
- the last F1 page is 18;
- malformed/early counts remain zero; and
- signer aborts are explained by F3 or USB reset rather than arithmetic failure.

Console acceptance is established only if controls remain usable beyond eight minutes, preferably through a 20-minute observed session and a repeated authentication round.

## Current physical PS4 result

The November 2 twelve-minute trace recorded eight complete challenges, eight completed signatures, seven F2-ready replies and 133 F1 pages, but input stopped around eight minutes. The final challenge-to-ready interval was 34 seconds by coarse firmware timestamps. This proves signing and response transport completed; it does not prove identity acceptance.

