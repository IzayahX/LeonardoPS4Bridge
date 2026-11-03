#include <Arduino.h>
#include "Crypto.h"
#include "SHA256.h"
#include <avr/pgmspace.h>
#include <avr/wdt.h>
#include <util/atomic.h>
#include "private_crt.h"
#include "hsps.h"
#include "rps_mul.h"
#include "rps_square.h"
#include "Signer.h"

// Product and reduction are separated so squaring can exploit symmetry.
static uint8_t em[256], product[256], work[132], base[128], acc[128], modulus[128], rr[128];
static uint8_t partP[128];
// After Q exponentiation acc holds its final standard-domain result. Nothing
// in CRT recombination modifies acc, so Q needs no separate 128-byte buffer.
static uint8_t* const partQ = acc;
static SHA256 sha;
SignerStats signerStats;
static uint32_t lastService;
extern "C" char __heap_start;
extern "C" void* __brkval;
static uint8_t* canaryStart;

static bool serviceWork() {
  uint32_t now = micros();
  uint32_t gap = now - lastService;
  if (gap > signerStats.maxServiceGapUs) signerStats.maxServiceGapUs = gap;
  lastService = now;
  wdt_reset();
  return signerService();
}

void signerArmStackCanary() {
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    canaryStart = __brkval ? (uint8_t*)__brkval : (uint8_t*)&__heap_start;
    uint8_t* cursor = canaryStart;
    uint8_t* top = (uint8_t*)SP;
    while (cursor < top) *cursor++ = 0xA5;
  }
}

static void measureStack() {
  uint8_t* firstTouched = canaryStart;
  while (firstTouched < (uint8_t*)RAMEND && *firstTouched == 0xA5) ++firstTouched;
  signerStats.stackWatermarkBytes = (uint8_t*)RAMEND - firstTouched + 1;
  signerStats.heapBytes = __brkval ? (uint8_t*)__brkval - (uint8_t*)&__heap_start : 0;
}

static bool pssEncode(const uint8_t digest[32]) {
  // Arithmetic scratch is idle until encoding is complete.
  uint8_t* salt = work;
  uint8_t* h = work + 32;
  uint8_t* block = work + 64;
  // Deterministic benchmark salt: valid PSS encoding, not a production RNG.
  sha.reset(); sha.update(digest, 32); sha.update("AVR-PSS-benchmark", 17); sha.finalize(salt, 32);
  if (!serviceWork()) return false;
  memset(em, 0, 223);
  em[190] = 1;
  memcpy(em + 191, salt, 32);
  sha.reset();
  const uint8_t zeros[8] = {};
  sha.update(zeros, 8); sha.update(digest, 32); sha.update(salt, 32);
  if (!serviceWork()) return false;
  sha.finalize(h, 32);
  if (!serviceWork()) return false;
  for (uint8_t counter = 0; counter < 7; ++counter) {
    uint8_t c[4] = {0, 0, 0, counter};
    sha.reset(); sha.update(h, 32); sha.update(c, 4); sha.finalize(block, 32);
    uint8_t count = counter == 6 ? 31 : 32;
    for (uint8_t i = 0; i < count; ++i) em[(uint16_t)counter * 32 + i] ^= block[i];
    if (!serviceWork()) return false;
  }
  em[0] &= 0x7F;
  memcpy(em + 223, h, 32);
  em[255] = 0xBC;
  return true;
}

static bool ge128(const uint8_t* a, const uint8_t* b) {
  for (int i = 127; i >= 0; --i) {
    if (a[i] != b[i]) return a[i] > b[i];
  }
  return true;
}

static uint8_t subtract128(uint8_t* a, const uint8_t* b) {
  uint16_t borrow = 0;
  for (uint8_t i = 0; i < 128; ++i) {
    uint16_t diff = (uint16_t)a[i] - b[i] - borrow;
    a[i] = diff;
    borrow = diff >> 15;
  }
  return borrow;
}

static void add128(uint8_t* a, const uint8_t* b) {
  uint16_t carry = 0;
  for (uint8_t i = 0; i < 128; ++i) {
    carry += (uint16_t)a[i] + b[i];
    a[i] = carry;
    carry >>= 8;
  }
}

static uint32_t liftInverse32(uint8_t inverse8) {
  uint32_t low = (uint32_t)modulus[0] | ((uint32_t)modulus[1] << 8) |
                 ((uint32_t)modulus[2] << 16) | ((uint32_t)modulus[3] << 24);
  uint32_t inverse = inverse8;
  inverse *= 2UL + low * inverse;
  inverse *= 2UL + low * inverse;
  return inverse;
}

static bool mont(uint8_t* out, const uint8_t* a, const uint8_t* b,
                 uint32_t inverse32) {
  uint32_t begin = micros();
  ++signerStats.montCalls;
  if (a == b) rpsSquare128(product, a);
  else rpsMultiply128(product, a, b);
  hspsMontgomeryReduce128(out, product, modulus, inverse32, work);
  if (!serviceWork()) return false;
  signerStats.montUs += micros() - begin;
  return true;
}

static bool reduceEm() {
  uint32_t begin = micros();
  memset(work, 0, sizeof(work));
  for (uint16_t i = 0; i < 2048; ++i) {
    uint8_t bit = (em[i >> 3] >> (7 - (i & 7))) & 1;
    for (uint8_t j = 0; j < 129; ++j) {
      uint8_t next = work[j] >> 7;
      work[j] = (work[j] << 1) | bit;
      bit = next;
    }
    if (work[128] || ge128(work, modulus)) {
      uint8_t borrow = subtract128(work, modulus);
      work[128] -= borrow;
    }
    if ((i & 15) == 0 && !serviceWork()) return false;
  }
  memcpy(base, work, 128);
  signerStats.reduceUs += micros() - begin;
  return true;
}

static void load128(uint8_t* to, const uint8_t* from) {
  for (uint8_t i = 0; i < 128; ++i) to[i] = pgm_read_byte(from + i);
}

static bool exponentiate(const uint8_t* p, const uint8_t* exp,
                         const uint8_t* r2, uint8_t inverse, uint8_t* result,
                         uint8_t* base5) {
  load128(modulus, p); load128(rr, r2);
  uint32_t inverse32 = liftInverse32(inverse);
  if (!reduceEm() || !mont(base, base, rr, inverse32)) return false;
  memset(acc, 0, 128); acc[0] = 1;
  if (!mont(acc, acc, rr, inverse32)) return false;
  // Conversion constant is dead; keep base^3 in the same buffer.
  if (!mont(rr, base, base, inverse32) || !mont(rr, rr, base, inverse32)) return false;
  // One extra 128-byte scratch slot holds base^5. Its lifetime ends before
  // the corresponding CRT result replaces it.
  if (!mont(base5, rr, base, inverse32) || !mont(base5, base5, base, inverse32)) return false;
  for (uint16_t bit = 0; bit < 1024; ++bit) {
    if (!mont(acc, acc, acc, inverse32)) return false;
    if (pgm_read_byte(exp + (127 - (bit >> 3))) & (1 << (7 - (bit & 7)))) {
      uint16_t next = bit + 1;
      uint16_t afterNext = bit + 2;
      if (afterNext < 1024 &&
          !(pgm_read_byte(exp + (127 - (next >> 3))) & (1 << (7 - (next & 7)))) &&
          (pgm_read_byte(exp + (127 - (afterNext >> 3))) & (1 << (7 - (afterNext & 7))))) {
        if (!mont(acc, acc, acc, inverse32) ||
            !mont(acc, acc, acc, inverse32) ||
            !mont(acc, acc, base5, inverse32)) return false;
        bit += 2;
      } else if (next < 1024 &&
          (pgm_read_byte(exp + (127 - (next >> 3))) & (1 << (7 - (next & 7))))) {
        if (!mont(acc, acc, acc, inverse32) || !mont(acc, acc, rr, inverse32)) return false;
        ++bit;
      } else if (!mont(acc, acc, base, inverse32)) return false;
    }
  }
  memset(rr, 0, 128); rr[0] = 1;
  return mont(result, acc, rr, inverse32);
}

static bool crtSign() {
  uint32_t begin = micros();
  if (!exponentiate(crtP, crtDp, crtR2p, crtInvP, partP, partP)) return false;
  signerStats.pUs = micros() - begin;
  begin = micros();
  // The encoded message is dead once reduceEm() has run for Q.
  if (!exponentiate(crtQ, crtDq, crtR2q, crtInvQ, partQ, em)) return false;
  signerStats.qUs = micros() - begin;
  begin = micros();
  load128(modulus, crtP);
  uint32_t inverse32 = liftInverse32(crtInvP);
  memcpy(rr, partQ, 128);
  if (ge128(rr, modulus)) subtract128(rr, modulus);
  memcpy(base, partP, 128);
  if (subtract128(base, rr)) add128(base, modulus);
  load128(rr, crtR2p);
  if (!mont(base, base, rr, inverse32)) return false;
  load128(rr, crtQinv);
  if (!mont(base, base, rr, inverse32)) return false;
  load128(modulus, crtQ);
  memset(em, 0, 256);
  for (uint8_t i = 0; i < 128; ++i) {
    uint16_t carry = 0;
    for (uint8_t j = 0; j < 128; ++j) {
      uint16_t v = (uint16_t)em[(uint16_t)i+j] + (uint16_t)base[i]*modulus[j] + carry;
      em[(uint16_t)i+j] = v;
      carry = v >> 8;
    }
    uint8_t k = i + 128;
    do {
      uint16_t v = (uint16_t)em[k] + carry;
      em[k++] = v;
      carry = v >> 8;
    } while (carry && k != 0);
    if ((i & 15) == 0 && !serviceWork()) return false;
  }
  uint16_t carry = 0;
  for (uint16_t i = 0; i < 256; ++i) {
    uint16_t v = (uint16_t)em[i] + (i < 128 ? partQ[i] : 0) + carry;
    em[i] = v;
    carry = v >> 8;
  }
  signerStats.combineUs = micros() - begin;
  return serviceWork();
}

uint8_t* signerNonceBuffer() { return em; }

bool signerSign() {
  memset(&signerStats, 0, sizeof(signerStats));
  uint32_t started = micros();
  lastService = started;
  uint8_t digest[32];
  sha.reset();
  for (uint8_t block = 0; block < 4; ++block) {
    sha.update(em + (uint16_t)block * 64, 64);
    if (!serviceWork()) return false;
  }
  sha.finalize(digest, 32);
  if (!serviceWork()) return false;
  if (!pssEncode(digest)) return false;
  uint32_t afterPss = micros();
  signerStats.pssUs = afterPss - started;
  if (!crtSign()) return false;
  uint32_t afterRsa = micros();
  signerStats.rsaUs = afterRsa - afterPss;
  signerStats.totalUs = afterRsa - started;
  measureStack();
  return true;
}

uint8_t signerSignatureByte(uint16_t offset) { return em[255 - offset]; }
