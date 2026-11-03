"""Guard the single-frame assembly properties used by cycle/stack accounting."""
from pathlib import Path


def main():
    source = Path(__file__).with_name("rps_square_avr.S").read_text()
    function = source.split("rpsSquare128:", 1)[1]
    assert function.count("push r") == 18
    assert function.count("pop  r") == 18
    assert "call " not in function and "rcall " not in function
    assert function.count("cli") == 2
    assert "clr  r1" in function
    assert function.count("RPS_SQUARE_BLOCK") == 1
    assert function.count("RPS_SQUARE_GROUP") == 4
    assert function.count("DOUBLE_CROSS_ADD") == 8
    print("Single-frame RPS square source guard PASS: no internal calls, 46-byte stack")


if __name__ == "__main__":
    main()
