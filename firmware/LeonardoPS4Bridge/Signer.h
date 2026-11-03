#pragma once
#include <stdint.h>

struct SignerStats {
  uint32_t pssUs, rsaUs, totalUs, montUs, reduceUs;
  uint32_t pUs, qUs, combineUs, montCalls, maxServiceGapUs;
  uint16_t stackWatermarkBytes, heapBytes;
};

extern SignerStats signerStats;
void signerArmStackCanary();
uint8_t* signerNonceBuffer();
bool signerSign();
uint8_t signerSignatureByte(uint16_t bigEndianOffset);
// Main-context callback: services Xbox, returns false to unwind cancellation.
bool signerService();
