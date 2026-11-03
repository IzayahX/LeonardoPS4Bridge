"""Verify the proposed exponent schedule with local credentials; print no secrets."""
import hashlib
import re
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_window_signature.py PATH_TO_LOCAL_PRIVATE_CRT_HEADER")
source = Path(sys.argv[1]).read_text()
sys.path.insert(0, str(Path(__file__).parent))
from test_arithmetic import window_power  # noqa: E402


def component(name):
    match = re.search(r"const uint8_t " + name + r"\[128\].*?=\s*\{(.*?)\};", source, re.S)
    if not match:
        raise ValueError("missing component")
    return int.from_bytes(bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", match.group(1))), "little")


p, q = component("crtP"), component("crtQ")
dp, dq, qinv = component("crtDp"), component("crtDq"), component("crtQinv")
n, e = p * q, 65537
assert (q * qinv) % p == 1
public = rsa.RSAPublicNumbers(e, n).public_key()

for _ in range(2):
    challenge = secrets.token_bytes(256)
    digest = hashlib.sha256(challenge).digest()
    salt = hashlib.sha256(digest + b"AVR-PSS-benchmark").digest()
    h = hashlib.sha256(bytes(8) + digest + salt).digest()
    db = bytearray(bytes(190) + b"\x01" + salt)
    mask = b"".join(hashlib.sha256(h + i.to_bytes(4, "big")).digest() for i in range(7))
    for i in range(223):
        db[i] ^= mask[i]
    db[0] &= 0x7f
    em = int.from_bytes(db + h + b"\xbc", "big")
    sp = window_power(em % p, dp, p, 3)
    sq = window_power(em % q, dq, q, 3)
    signature = (sq + q * (((sp - sq) * qinv) % p)).to_bytes(256, "big")
    assert pow(int.from_bytes(signature, "big"), e, n) == em
    public.verify(signature, challenge, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                       salt_length=32), hashes.SHA256())

print("two fresh RSA-PSS/SHA-256 model signatures PASS")
