"""Generate deterministic, credential-free 1024-bit Montgomery vectors."""
from pathlib import Path
import random

SIZE = 128
R = 1 << 1024


def bytes_le(value, size=SIZE):
    return value.to_bytes(size, "little")


def declaration(name, data):
    rows = [", ".join(f"0x{x:02X}" for x in data[i:i + 16])
            for i in range(0, len(data), 16)]
    return f"const uint8_t {name}[{len(data)}] PROGMEM = {{\n  " + ",\n  ".join(rows) + "\n};\n"


def redc_case(product, modulus):
    assert modulus & 1 and 0 <= product < modulus * R
    inverse = (-pow(modulus & 0xFFFFFFFF, -1, 1 << 32)) & 0xFFFFFFFF
    expected = product * pow(R, -1, modulus) % modulus
    return bytes_le(modulus), product.to_bytes(2 * SIZE, "little"), bytes_le(expected), inverse


modulus_bytes = bytearray((i * 73 + 19) & 255 for i in range(SIZE))
modulus_bytes[0] |= 1
modulus_bytes[-1] |= 0x80
modulus = int.from_bytes(modulus_bytes, "little")
a = int.from_bytes(bytes((i * 59 + 7) & 255 for i in range(SIZE)), "little") % modulus
b = int.from_bytes(bytes((i * 37 + 11) & 255 for i in range(SIZE)), "little") % modulus
inverse32 = (-pow(modulus & 0xFFFFFFFF, -1, 1 << 32)) & 0xFFFFFFFF
expected = a * b * pow(R, -1, modulus) % modulus
square = a * a
square_expected = square * pow(R, -1, modulus) % modulus

rng = random.Random(0x48535053)
redc_cases = [redc_case(product, modulus) for product in
              (0, 1, modulus - 1, modulus, modulus * R - 1, (modulus - 1) ** 2)]
for _ in range(2):
    case_modulus = rng.getrandbits(1024) | 1 | (1 << 1023)
    redc_cases.append(redc_case(rng.randrange(case_modulus * R), case_modulus))
mul_pairs = [(0, modulus - 1), (1, 1), (modulus - 1, modulus - 1), (a, b)]
mul_pairs.extend((rng.randrange(modulus), rng.randrange(modulus)) for _ in range(2))
mul_products = [left * right for left, right in mul_pairs]
mul_expecteds = [value * pow(R, -1, modulus) % modulus for value in mul_products]
product = a * b

header = "#pragma once\n#include <avr/pgmspace.h>\n#include <stdint.h>\n\n"
header += declaration("vectorModulus", bytes_le(modulus))
header += declaration("vectorA", bytes_le(a))
header += declaration("vectorB", bytes_le(b))
header += declaration("vectorProduct", bytes_le(product, 2 * SIZE))
header += declaration("vectorExpected", bytes_le(expected))
header += declaration("vectorSquareProduct", bytes_le(square, 2 * SIZE))
header += declaration("vectorSquareExpected", bytes_le(square_expected))
header += f"const uint32_t vectorInverse32 = 0x{inverse32:08X}UL;\n"
header += f"const uint8_t redcVectorCount = {len(redc_cases)};\n"
header += declaration("redcModuli", b"".join(case[0] for case in redc_cases))
header += declaration("redcProducts", b"".join(case[1] for case in redc_cases))
header += declaration("redcExpecteds", b"".join(case[2] for case in redc_cases))
header += "const uint32_t redcInverses[] PROGMEM = {\n  " + ", ".join(
    f"0x{case[3]:08X}UL" for case in redc_cases) + "\n};\n"
header += f"const uint8_t multiplyVectorCount = {len(mul_pairs)};\n"
header += declaration("multiplyAs", b"".join(bytes_le(left) for left, _ in mul_pairs))
header += declaration("multiplyBs", b"".join(bytes_le(right) for _, right in mul_pairs))
header += declaration("multiplyProducts", b"".join(bytes_le(value, 2 * SIZE) for value in mul_products))
header += declaration("multiplyExpecteds", b"".join(bytes_le(value) for value in mul_expecteds))
Path(__file__).with_name("synthetic_vectors.h").write_text(header)
