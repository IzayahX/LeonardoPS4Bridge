"""Linked-disassembly cycle accounting for the single-loop HSPS reducer."""


def main():
    low_convolution = 107 * sum(range(1, 32)) - 31
    high_convolution = low_convolution
    low_columns = (32 * 25 + 626 + low_convolution + 32 * 52 + 512 +
                   128 + 32 * 95 + 32 * 7 + 287)
    high_columns = 31 * 25 + high_convolution + 31 * 20 + 31 * 16 + 31 * 7 + 278
    final_normalization = 25 + 16 + 1289 + 8 + 1417 + 2 + 904
    call_and_frame = 137
    total = low_columns + high_columns + final_normalization + call_and_frame
    assert low_convolution == high_convolution == 53041
    assert low_columns == 60322
    assert high_columns == 55427
    assert final_normalization == 3661
    assert total == 119547
    print({
        "low_columns_cycles": low_columns,
        "high_columns_cycles": high_columns,
        "final_normalization_cycles": final_normalization,
        "call_and_frame_cycles": call_and_frame,
        "complete_reduction_cycles_without_async_interrupts": total,
        "milliseconds_at_16mhz": total / 16000,
        "internal_calls": 0,
        "stack_bytes_including_return_address": 35,
    })


if __name__ == "__main__":
    main()
