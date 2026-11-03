"""Check the single-loop reducer's unrolled quotient and ABI structure."""
from pathlib import Path
import random


def add_product_at(output, product, offset):
    carry = 0
    for index in range(offset, 4):
        value = output[index] + (product & 255) + carry
        output[index] = value & 255
        carry = value >> 8
        product >>= 8
    return output


def quotient_schedule(left, right):
    a = left.to_bytes(4, "little")
    b = right.to_bytes(4, "little")
    output = [0, 0, 0, 0]
    for i, j in ((0, 0), (0, 1), (0, 2), (0, 3),
                 (1, 0), (1, 1), (1, 2),
                 (2, 0), (2, 1), (3, 0)):
        add_product_at(output, a[i] * b[j], i + j)
    return int.from_bytes(output, "little")


def main():
    rng = random.Random(0x53494E47)
    cases = [(0, 0), (1, 1), (0xFFFFFFFF, 0xFFFFFFFF)]
    cases += [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(10000)]
    for left, right in cases:
        assert quotient_schedule(left, right) == (left * right) & 0xFFFFFFFF

    source = Path(__file__).with_name("hsps_avr.S").read_text()
    assert source.count("push r") == source.count("pop  r") == 18
    assert source.count("    cli") == 2
    assert "    clr  r1\n    ret" in source
    function = source.split("hspsMontgomeryReduce128:", 1)[1]
    assert "call " not in function and "rcall " not in function
    print(f"single-loop quotient/ABI schedule PASS: {len(cases)} quotient cases")


if __name__ == "__main__":
    main()
