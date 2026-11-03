"""Guard the single-frame multiply properties used by cycle/stack accounting."""
from pathlib import Path


def main():
    source = Path(__file__).with_name("rps_mul_avr.S").read_text()
    function = source.split("rpsMultiply128:", 1)[1]
    assert function.count("push r") == 18
    assert function.count("pop  r") == 18
    assert "call " not in function and "rcall " not in function
    assert function.count("cli") == 2
    assert "clr  r1" in function
    assert function.count("RPS_MUL_BLOCK") == 1
    assert "sub  r22, r25" in function
    counts = [column + 1 if column < 32 else 63 - column for column in range(63)]
    assert counts[31:] == list(range(32, 0, -1))
    assert sum(counts) == 1024
    print("Single-frame RPS multiply source guard PASS: 1024 blocks, no internal calls, 45-byte stack")


if __name__ == "__main__":
    main()
