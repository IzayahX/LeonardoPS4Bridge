#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Reduces a 2048-bit little-endian product T to T*R^-1 mod modulus, where
// R=2^1024, modulus is odd, and 0 <= T < modulus*R. Output may alias product.
// scratch is 132 bytes and must not overlap product, modulus, or output.
void hspsMontgomeryReduce128(uint8_t* output, const uint8_t product[256],
                             const uint8_t modulus[128], uint32_t inverse32,
                             uint8_t scratch[132]);

#ifdef __cplusplus
}
#endif
