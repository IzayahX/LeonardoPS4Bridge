"""Verify the 32-bit-column RPS multiplication schedule."""
import random

WORDS = 32
MASK = (1 << 32) - 1


def rps_product(a, b):
    aa = [(a >> (32 * i)) & MASK for i in range(WORDS)]
    bb = [(b >> (32 * i)) & MASK for i in range(WORDS)]
    result = 0
    carry = 0
    for column in range(2 * WORDS - 1):
        first = max(0, column - (WORDS - 1))
        last = min(WORDS - 1, column)
        total = carry + sum(aa[i] * bb[column - i]
                            for i in range(first, last + 1))
        result |= (total & MASK) << (32 * column)
        carry = total >> 32
        assert carry < 1 << 40
    result |= carry << (32 * (2 * WORDS - 1))
    return result


def main():
    rng = random.Random(0x5250534D)
    cases = [(0, 0), (1, 1), ((1 << 1024) - 1, (1 << 1024) - 1)]
    cases.extend((rng.getrandbits(1024), rng.getrandbits(1024)) for _ in range(1000))
    for a, b in cases:
        assert rps_product(a, b) == a * b
        assert rps_product(a, a) == a * a
    print(f"RPS multiplication model PASS: {len(cases)} products plus A==B parity")


if __name__ == "__main__":
    main()
