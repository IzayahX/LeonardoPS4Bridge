"""Verify the published two-pass RPS square schedule used by rps_square.cpp."""
import random

WORDS = 32
MASK = (1 << 32) - 1


def rps_square(value):
    words = [(value >> (32 * i)) & MASK for i in range(WORDS)]
    cross = [0] * (2 * WORDS)
    carry = 0
    for column in range(2 * WORDS - 1):
        first = max(0, column - (WORDS - 1))
        last = (column - 1) // 2
        total = carry + sum(words[i] * words[column - i]
                            for i in range(first, last + 1))
        cross[column] = total & MASK
        carry = total >> 32
    assert carry == 0

    result = 0
    carry = 0
    for i in range(WORDS):
        chunk = words[i] * words[i] + 2 * (
            cross[2 * i] | (cross[2 * i + 1] << 32)) + carry
        result |= (chunk & ((1 << 64) - 1)) << (64 * i)
        carry = chunk >> 64
    assert carry == 0
    return result


def main():
    rng = random.Random(0x52505353)
    cases = [0, 1, (1 << 1024) - 1]
    cases.extend(rng.getrandbits(1024) for _ in range(1000))
    for value in cases:
        assert rps_square(value) == value * value
    print(f"Two-pass RPS square model PASS: {len(cases)} credential-free vectors")


if __name__ == "__main__":
    main()
