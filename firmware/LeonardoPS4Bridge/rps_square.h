#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Computes the exact 2048-bit little-endian square. Buffers must not overlap.
void rpsSquare128(uint8_t product[256], const uint8_t input[128]);

#ifdef __cplusplus
}
#endif
