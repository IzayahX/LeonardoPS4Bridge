#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Fixed 128-byte little-endian rows. t and a must not overlap.
// Computes t[0..127] += a[0..127] * scalar, returning the high carry byte.
uint8_t avr_mac128(uint8_t* t, const uint8_t* a, uint8_t scalar);

// Same row calculation, then discards result byte zero and shifts bytes 1..127
// into t[0..126]. Leaves t[127] and higher untouched; returns the carry byte.
// For Montgomery reduction the discarded result byte must be zero.
uint8_t avr_mac_shift128(uint8_t* t, const uint8_t* a, uint8_t scalar);

// One fused Montgomery outer row, radix 256, with 128-byte a and modulus.
// t is a 130-byte little-endian accumulator; t[129] must be zero on entry.
// Computes (t + a*scalar + u*modulus)/256, where u makes the low byte zero.
// m0inv is -modulus[0]^-1 modulo 256. Writes t[0..129], clearing t[129].
// t must not overlap either input. a and modulus may overlap each other.
void avr_fios128(uint8_t* t, const uint8_t* a, const uint8_t* modulus,
                 uint8_t scalar, uint8_t m0inv);

// Identical contract; four limbs per loop iteration, then three tail limbs.
void avr_fios128_unrolled4(uint8_t* t, const uint8_t* a, const uint8_t* modulus,
                          uint8_t scalar, uint8_t m0inv);

void avr_fios128_unrolled8(uint8_t* t, const uint8_t* a, const uint8_t* modulus,
                          uint8_t scalar, uint8_t m0inv);

#ifdef __cplusplus
}
#endif
