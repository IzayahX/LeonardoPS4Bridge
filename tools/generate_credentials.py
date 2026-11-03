"""Validate owner-supplied DS4 credentials and generate local firmware headers.

Generated files and firmware binaries contain credential material. Never commit them.
"""
import argparse
import math
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def array(name, raw, comment=None):
    lines = ([comment] if comment else []) + [f"const uint8_t {name}[{len(raw)}] PROGMEM = {{"]
    lines += ["  " + ", ".join(f"0x{byte:02x}" for byte in raw[start:start + 16]) + ","
              for start in range(0, len(raw), 16)]
    return lines + ["};"]


def write_private(path, numbers):
    p, q = numbers.p, numbers.q
    values = {
        "crtP": p, "crtQ": q,
        "crtDp": numbers.dmp1, "crtDq": numbers.dmq1,
        "crtQinv": numbers.iqmp,
        "crtR2p": pow(2, 2048, p), "crtR2q": pow(2, 2048, q),
    }
    lines = ["#pragma once", "#include <avr/pgmspace.h>",
             "// CONFIDENTIAL: private CRT factors; keep this file and all binaries local."]
    for name, value in values.items():
        lines += array(name, value.to_bytes(128, "little"))
    lines += [f"const uint8_t crtInvP = {-pow(p & 255, -1, 256) % 256};",
              f"const uint8_t crtInvQ = {-pow(q & 255, -1, 256) % 256};"]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_public(path, identity):
    lines = ["#pragma once", "#include <avr/pgmspace.h>"]
    lines += array("publicIdentity", identity,
                   "// CONFIDENTIAL: certified controller identity; keep this file and binaries local.")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--serial", required=True, type=Path)
    parser.add_argument("--signature", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    key = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey) or key.key_size != 2048:
        raise SystemExit("Expected an unencrypted RSA-2048 private key")
    numbers = key.private_numbers()
    if (numbers.p.bit_length() != 1024 or numbers.q.bit_length() != 1024 or
            numbers.p * numbers.q != numbers.public_numbers.n or
            numbers.public_numbers.e * numbers.d % math.lcm(numbers.p - 1, numbers.q - 1) != 1):
        raise SystemExit("Private key failed CRT consistency checks")

    serial_text = args.serial.read_text(encoding="ascii").strip()
    if len(serial_text) not in (16, 32):
        raise SystemExit("Serial must contain 16 or 32 hexadecimal characters")
    try:
        serial = bytes.fromhex(serial_text).rjust(16, b"\0")
    except ValueError as error:
        raise SystemExit("Serial must contain only hexadecimal characters") from error
    certificate_signature = args.signature.read_bytes()
    if len(certificate_signature) != 256:
        raise SystemExit("Certificate signature must be exactly 256 bytes")

    public = numbers.public_numbers
    certificate_message = serial + public.n.to_bytes(256, "big") + public.e.to_bytes(256, "big")
    authority = serialization.load_pem_public_key(
        Path(__file__).with_name("ds4_public_authority.pem").read_bytes())
    try:
        authority.verify(certificate_signature, certificate_message, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    except InvalidSignature as error:
        raise SystemExit("Certificate signature is not accepted by the documented public authority") from error

    identity = certificate_message + certificate_signature + bytes(24)
    assert len(identity) == 808
    args.output.mkdir(parents=True, exist_ok=True)
    write_private(args.output / "private_crt.h", numbers)
    write_public(args.output / "public_identity.h", identity)
    print("Credentials validated; generated two local-only headers (no values printed)")


if __name__ == "__main__":
    main()
