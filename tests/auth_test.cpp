#include <assert.h>
#include <stdio.h>
#include <vector>
#include <array>
#include <algorithm>
#include <stdint.h>
#include "Arduino.h"

static uint32_t clockMs;
uint32_t millis() { return clockMs; }
void delay(unsigned) {}
void cli() {}
UsbDeviceStub USBDevice;
uint8_t probeHostFlags() { return 3; }
static uint8_t nonce[256], signature[256];
static bool signSuccess = true;
static bool resetDuringSign;
static uint32_t resetDelayMs;
static const uint8_t* f0DuringSign;
static bool f0DuringSignAccepted;
extern "C" bool ps4AuthSet(uint8_t, const uint8_t*, uint8_t);
extern "C" uint8_t ps4AuthGet(uint8_t, uint8_t*);
uint8_t* signerNonceBuffer() { return nonce; }
uint8_t signerSignatureByte(uint16_t n) { return signature[n]; }
bool signerSign() {
  if (resetDuringSign) {
    clockMs += 20000;
    uint8_t status[63]{};
    assert(ps4AuthGet(0xF2, status) == 15 && status[1] == 16);
    clockMs += resetDelayMs - 20000;
    ps4AuthSet(0xF3, nullptr, 0);
  }
  if (f0DuringSign) f0DuringSignAccepted = ps4AuthSet(0xF0, f0DuringSign, 63);
  return signSuccess;
}

#include "Ps4Auth.cpp"

static std::array<uint8_t,63> page(uint8_t id, uint8_t index, uint8_t seed) {
  std::array<uint8_t,63> d{};
  d[0] = id; d[1] = index;
  for (unsigned i = 0; i < (index == 4 ? 32u : 56u); ++i)
    d[3+i] = static_cast<uint8_t>(seed + index + i);
  reportCrc(0xF0, d.data(), 59);
  return d;
}
static void send(const std::array<uint8_t,63>& d) { assert(ps4AuthSet(0xF0, d.data(), 63)); }
static void challenge(uint8_t id, uint8_t seed) {
  for (uint8_t i = 0; i < 5; ++i) send(page(id, i, seed));
}
static void status(uint8_t expected) {
  uint8_t d[63]{};
  assert(ps4AuthGet(0xF2, d) == 15);
  assert(d[1] == expected);
}

int main() {
  assert(sizeof(AuthTrace) == 49);
  clockMs = 1000;
  auto first = page(7, 0, 11);
  send(first);
  send(first); // Exact page zero retransmission must preserve the round.
  assert(trace.duplicateF0 == 1 && state == RECEIVING && nextNoncePage == 1);
  auto skipped = page(7, 2, 11);
  assert(!ps4AuthSet(0xF0, skipped.data(), 63));
  assert(state == RECEIVING && nextNoncePage == 1);
  send(page(7, 1, 11));
  send(page(7, 1, 11));
  assert(trace.duplicateF0 == 2 && nextNoncePage == 2);
  auto conflict = page(7, 1, 12);
  assert(!ps4AuthSet(0xF0, conflict.data(), 63));
  assert(state == IDLE && trace.lastCancelReason == 3);
  clockMs = 2000;
  challenge(8, 22);
  assert(state == PENDING && trace.f0Pages[4] == 1);
  send(page(8, 4, 22));
  assert(state == PENDING && trace.duplicateF0 == 3);
  status(16);
  for (unsigned i = 0; i < 256; ++i) signature[i] = static_cast<uint8_t>(i);
  authTask();
  assert(state == READY && trace.signedOk == 1);
  status(0);
  std::vector<uint8_t> response;
  for (uint8_t p = 0; p < 19; ++p) {
    uint8_t d[63]{};
    assert(ps4AuthGet(0xF1, d) == 63 && d[0] == 8 && d[1] == p);
    uint32_t crc = crc32(0xFFFFFFFFUL, 0xF1);
    for (unsigned i = 0; i < 59; ++i) crc = crc32(crc, d[i]);
    crc = ~crc;
    for (unsigned i = 0; i < 4; ++i) assert(d[59+i] == static_cast<uint8_t>(crc >> (8*i)));
    response.insert(response.end(), d+3, d+59);
    ps4AuthCommit(0xF1);
  }
  assert(response.size() == 1064 && state == IDLE && trace.f1Pages == 19);
  for (unsigned i = 0; i < 256; ++i) assert(response[i] == signature[i]);
  for (unsigned i = 0; i < 808; ++i) assert(response[256+i] == publicIdentity[i]);
  uint8_t out[63]{};
  assert(ps4AuthGet(0xF1, out) == 0);
  clockMs = 3000;
  challenge(9, 33);
  ps4AuthSet(0xF3, nullptr, 0);
  assert(state == IDLE && authCancelled());
  challenge(10, 44);
  resetDuringSign = true;
  resetDelayMs = 31000;
  authTask();
  assert(state == IDLE && trace.signedAborted == 1 && trace.lastCancelReason == 1);
  assert(trace.maxF2BusyAgeDs == 200 && trace.maxF3AgeDs == 310);
  resetDuringSign = false;
  challenge(10, 44);
  auto newer = page(11, 0, 55);
  f0DuringSign = newer.data();
  authTask();
  assert(!f0DuringSignAccepted && state == IDLE && trace.signedAborted == 2);
  assert(trace.f0Busy == 1 && trace.lastCancelReason == 2);
  f0DuringSign = nullptr;
  challenge(10, 44);
  authTask();
  assert(state == READY && trace.signedOk == 2 && trace.f3Resets == 2);
  ps4AuthUsbReset(); authTraceXboxPoll();
  assert(state == IDLE && authCancelled() && trace.lastCancelReason == 4);
  clockMs = 150000;
  for (unsigned i = 0; i < 60; ++i) authTraceTask();
  assert(savedTrace.magic == 0xA74D && savedTrace.version == 4 && savedTrace.usbResets == 1);
  assert(savedTrace.check == traceCheck(reinterpret_cast<const uint8_t*>(&savedTrace)));
  clockMs = 210000;
  ps4AuthUsbReset();
  for (unsigned i = 0; i < 60; ++i) authTraceTask();
  assert(savedTrace.savedSec == 210 && savedTrace.usbResets == 2);
  assert(savedTrace.check == traceCheck(reinterpret_cast<const uint8_t*>(&savedTrace)));
  puts("auth state machine PASS");
}
