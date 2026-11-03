"""Check the radix-2^32 FIPS dataflow against Python big integers."""
import random

WORDS = 32
RADIX = 1 << 32
R = RADIX ** WORDS


def words(value, count=WORDS):
    return [(value >> (32 * i)) & 0xFFFFFFFF for i in range(count)]


def model(a, b, modulus):
    aa, bb, mm = words(a), words(b), words(modulus)
    inverse = (-pow(mm[0], -1, RADIX)) & 0xFFFFFFFF
    q = []
    accumulator = 0
    result = []
    for column in range(WORDS):
        accumulator += sum(aa[i] * bb[column - i] for i in range(column + 1))
        accumulator += sum(q[i] * mm[column - i] for i in range(column))
        quotient = (accumulator * inverse) & 0xFFFFFFFF
        q.append(quotient)
        accumulator += quotient * mm[0]
        assert accumulator & 0xFFFFFFFF == 0
        accumulator >>= 32
    for column in range(WORDS, 2 * WORDS - 1):
        first = column - WORDS + 1
        accumulator += sum(aa[i] * bb[column - i]
                           for i in range(first, WORDS))
        accumulator += sum(q[i] * mm[column - i]
                           for i in range(first, WORDS))
        result.append(accumulator & 0xFFFFFFFF)
        accumulator >>= 32
    result.append(accumulator & 0xFFFFFFFF)
    accumulator >>= 32
    assert accumulator in (0, 1)
    value = sum(x << (32 * i) for i, x in enumerate(result)) + accumulator * R
    if value >= modulus:
        value -= modulus
    return value


def reduction_model(product, modulus):
    tt, mm = words(product, 2 * WORDS), words(modulus)
    inverse = (-pow(mm[0], -1, RADIX)) & 0xFFFFFFFF
    q = []
    accumulator = 0
    result = []
    for column in range(WORDS):
        accumulator += tt[column]
        accumulator += sum(q[i] * mm[column - i] for i in range(column))
        assert accumulator < 1 << 72
        quotient = (accumulator * inverse) & 0xFFFFFFFF
        q.append(quotient)
        accumulator += quotient * mm[0]
        assert accumulator < 1 << 72
        assert accumulator & 0xFFFFFFFF == 0
        accumulator >>= 32
    for column in range(WORDS, 2 * WORDS - 1):
        first = column - WORDS + 1
        accumulator += tt[column]
        accumulator += sum(q[i] * mm[column - i] for i in range(first, WORDS))
        assert accumulator < 1 << 72
        result.append(accumulator & 0xFFFFFFFF)
        accumulator >>= 32
    accumulator += tt[-1]
    assert accumulator < 1 << 72
    result.append(accumulator & 0xFFFFFFFF)
    accumulator >>= 32
    assert accumulator in (0, 1)
    value = sum(x << (32 * i) for i, x in enumerate(result)) + accumulator * R
    assert value < 2 * modulus
    if value >= modulus:
        value -= modulus
    return value


def main():
    rng = random.Random(0x48464950)
    cases = []
    for _ in range(80):
        modulus = rng.getrandbits(1024) | 1 | (1 << 1023)
        a, b = rng.randrange(modulus), rng.randrange(modulus)
        cases.append((a, b, modulus))
    modulus = (1 << 1024) - 109
    cases.extend((a, b, modulus) for a, b in (
        (0, 0), (0, modulus - 1), (1, 1),
        (modulus - 1, modulus - 1), (modulus - 1, 1)))
    for a, b, modulus in cases:
        expected = a * b * pow(R, -1, modulus) % modulus
        assert model(a, b, modulus) == expected
        assert model(a, a, modulus) == a * a * pow(R, -1, modulus) % modulus
        assert reduction_model(a * b, modulus) == expected
        assert reduction_model(a * a, modulus) == a * a * pow(R, -1, modulus) % modulus
    boundary_modulus = (1 << 1024) - 109
    for product in (0, 1, boundary_modulus - 1, boundary_modulus,
                    boundary_modulus * R - 1):
        assert reduction_model(product, boundary_modulus) == (
            product * pow(R, -1, boundary_modulus) % boundary_modulus)
    print(f"HFIPS and separated HSPS models PASS: {len(cases)} products/squares plus 5 REDC boundaries")


if __name__ == "__main__":
    main()
