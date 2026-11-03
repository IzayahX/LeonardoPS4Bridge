"""Static cycle accounting for the linked single-frame square and reducer."""


def main():
    square_prologue = 66
    cross_blocks = 107 * 496 - 61
    cross_columns = 48 + 31 * 75 + 30 * 77 + 55
    word_63 = 8
    diagonal_setup = 12
    diagonal_words = 31 * 220 + 219
    square_epilogue = 48
    square_call = 4
    square = (square_prologue + cross_blocks + cross_columns + word_63 +
              diagonal_setup + diagonal_words + square_epilogue + square_call)
    multiply_prologue = 70
    multiply_blocks = 107 * 1024 - 63
    multiply_columns = 32 * 66 + 30 * 64 + 63
    multiply_word_63 = 8
    multiply_epilogue = 48
    multiply_call = 4
    multiply = (multiply_prologue + multiply_blocks + multiply_columns +
                multiply_word_63 + multiply_epilogue + multiply_call)
    reduction = 119547
    complete = square + reduction
    complete_multiply = multiply + reduction
    assert cross_blocks == 53011
    assert cross_columns == 4738
    assert square == 64926
    assert multiply_blocks == 109505
    assert multiply_columns == 4095
    assert multiply == 113730
    assert complete == 184473
    assert complete_multiply == 233277
    assert complete < 195000
    assert complete_multiply < 240000
    print({
        "rps_square_cycles_without_async_interrupts": square,
        "single_frame_hsps_cycles_without_async_interrupts": reduction,
        "complete_modular_square_cycles_without_async_interrupts": complete,
        "rps_multiply_cycles_without_async_interrupts": multiply,
        "complete_modular_multiply_cycles_without_async_interrupts": complete_multiply,
        "milliseconds_at_16mhz": complete / 16000,
        "multiply_milliseconds_at_16mhz": complete_multiply / 16000,
        "cycle_gate": 195000,
        "margin_cycles": 195000 - complete,
        "multiply_cycle_gate": 240000,
        "multiply_margin_cycles": 240000 - complete_multiply,
        "rps_square_internal_calls": 0,
        "rps_square_stack_bytes_including_return_address": 46,
        "rps_multiply_internal_calls": 0,
        "rps_multiply_stack_bytes_including_return_address": 45,
    })


if __name__ == "__main__":
    main()
