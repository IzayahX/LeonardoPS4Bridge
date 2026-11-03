#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Computes the exact 2048-bit little-endian product. Buffers must not overlap.
void rpsMultiply128(uint8_t product[256], const uint8_t a[128],
                    const uint8_t b[128]);

#ifdef __cplusplus
}
#endif
