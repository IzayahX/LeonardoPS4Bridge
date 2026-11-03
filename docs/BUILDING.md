# Building

## Pinned toolchain

- Arduino CLI 1.5.1
- Arduino AVR Boards 1.8.6 / AVR GCC 7.3.0
- USB Host Shield Library 2.0 1.7.0
- PS4Arduino-AVR commit `86723988485d662a75d0f9e93d5524ca738ca6ee`
- PS4Arduino commit `814e496da57459a20348fe4fa9e2cd63ea50cb89`

Apply the core patches to PS4Arduino-AVR in this order:

```text
patches/core-auth.patch
patches/integrated-core.patch
patches/no-pointer-capabilities.patch
patches/auth-trace-core.patch
```

Apply `patches/touchpad-neutral.patch` to PS4Arduino.

## Local credential headers

Install `cryptography` and run `tools/generate_credentials.py` as shown in the README. The output directory must be `firmware/LeonardoPS4Bridge/`; the generated files are:

- `private_crt.h` — private CRT factors and Montgomery constants
- `public_identity.h` — certified identity and signature used in the F1 response

Both are ignored. Do not upload a compiled HEX: the compiler embeds both headers.

## Compile

Compile `firmware/LeonardoPS4Bridge/LeonardoPS4Bridge.ino` for `arduino:avr:leonardo` with link-time optimization enabled by the Arduino AVR core. A successful compile is not proof that a PS4 accepts the identity.

Run the host checks before flashing:

```powershell
python tests/check_no_secrets.py
python benchmarks/rps_hsps/test_model.py
python benchmarks/rps_hsps/test_rps_mul_model.py
python benchmarks/rps_hsps/test_rps_square_model.py
python tests/test_trace_parser.py
```

