#include <Arduino.h>
#include <avr/pgmspace.h>
#include <avr/eeprom.h>
#include <util/atomic.h>
#include <avr/wdt.h>
#include "public_identity.h"
#include "Signer.h"

enum AuthState : uint8_t { IDLE, RECEIVING, PENDING, SIGNING, READY };
static volatile uint8_t nonceId, nextNoncePage, nextResponsePage, state;
static volatile uint16_t epoch;
static uint16_t signingEpoch;
static volatile bool cancelled;
static volatile uint16_t completed, abandoned;
static volatile bool bootRequested;
static volatile bool signerBusy;
uint8_t probeHostFlags();

// Counter-only trace: no nonce, signature, certificate, or key bytes are stored.
struct AuthTrace {
  uint16_t magic;
  uint8_t version, f0Pages[5];
  uint16_t f0Setups, f2Busy, f2Ready, f1Pages, xboxPolls;
  uint8_t f0Bad, f0Busy, f1Early, f3Resets, signerStarts;
  uint8_t signedOk, signedAborted, duplicateF0, usbResets;
  uint8_t lastCancelReason, lastF0Length, lastF1Page, stateAtSave;
  uint16_t firstF0Sec, lastF0Sec, f0CompleteSec, readySec;
  uint16_t lastF1Sec, savedSec, maxF2BusyAgeDs, maxF3AgeDs, check;
} __attribute__((packed));
static_assert(sizeof(AuthTrace) == 49, "Trace layout changed");
static AuthTrace trace = {0xA74D, 4};
static AuthTrace snapshot;
static AuthTrace EEMEM savedTrace;
static uint8_t persistPos;
static bool persistStarted;
static uint32_t lastSnapshotMs;
static uint32_t signStartedMs;

static uint32_t crc32(uint32_t crc, uint8_t value) {
  crc ^= value;
  for (uint8_t bit = 0; bit < 8; ++bit)
    crc = (crc >> 1) ^ ((crc & 1) ? 0xEDB88320UL : 0);
  return crc;
}

static uint16_t traceCheck(const uint8_t* bytes) {
  uint32_t crc = 0xFFFFFFFFUL;
  for (uint8_t i = 0; i < sizeof(AuthTrace) - 2; ++i) crc = crc32(crc, bytes[i]);
  return (uint16_t)~crc;
}

void authTraceTask() {
  uint32_t now = millis();
  if (now >= 150000UL &&
      (!persistStarted || (persistPos >= sizeof(snapshot) && now - lastSnapshotMs >= 60000UL))) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      memcpy(&snapshot, &trace, sizeof(snapshot));
      snapshot.stateAtSave = state;
    }
    snapshot.savedSec = now / 1000UL;
    snapshot.check = traceCheck((const uint8_t*)&snapshot);
    persistStarted = true;
    persistPos = 0;
    lastSnapshotMs = now;
    eeprom_update_byte((uint8_t*)&savedTrace.magic, 0); // invalidate old snapshot
  }
  if (!persistStarted || persistPos >= sizeof(snapshot)) return;
  // Write the magic last, one EEPROM byte per loop to keep USB/host service active.
  uint8_t index = persistPos < sizeof(snapshot) - 2 ? persistPos + 2 :
                  persistPos - (sizeof(snapshot) - 2);
  eeprom_update_byte((uint8_t*)&savedTrace + index,
                     *((const uint8_t*)&snapshot + index));
  ++persistPos;
}

extern "C" void ps4AuthSeenF0(uint8_t length, bool validShape) {
  ++trace.f0Setups;
  trace.lastF0Length = length;
  if (!validShape) ++trace.f0Bad;
}

extern "C" void ps4AuthUsbReset() {
  ++trace.usbResets;
  trace.lastCancelReason = 4;
  ++epoch;
  cancelled = true;
  state = IDLE;
  nextNoncePage = nextResponsePage = 0;
}
void authTraceXboxPoll() { ++trace.xboxPolls; }

static void reportCrc(uint8_t id, uint8_t* data, uint8_t count) {
  uint32_t crc = crc32(0xFFFFFFFFUL, id);
  for (uint8_t i = 0; i < count; ++i) crc = crc32(crc, data[i]);
  crc = ~crc;
  for (uint8_t i = 0; i < 4; ++i) data[count + i] = crc >> (8 * i);
}

// Called only from the USB ISR. A new round may arrive during arithmetic.
extern "C" bool ps4AuthSet(uint8_t reportId, const uint8_t* data, uint8_t length) {
  if (reportId == 0xF4) {
    if (length != 63 || memcmp(data, "LEOBOOT!", 8)) return false;
    for (uint8_t i = 8; i < 59; ++i) if (data[i]) return false;
    uint32_t crc = crc32(0xFFFFFFFFUL, 0xF4);
    for (uint8_t i = 0; i < 59; ++i) crc = crc32(crc, data[i]);
    crc = ~crc;
    for (uint8_t i = 0; i < 4; ++i)
      if (data[59 + i] != (uint8_t)(crc >> (8 * i))) return false;
    bootRequested = true;
    cancelled = true;
    return true;
  }
  if (reportId == 0xF3) {
    ++trace.f3Resets;
    if (state == SIGNING || state == READY) {
      uint16_t age = (millis() - signStartedMs) / 100UL;
      if (age > trace.maxF3AgeDs) trace.maxF3AgeDs = age;
    }
    trace.lastCancelReason = 1;
    ++epoch;
    cancelled = true;
    state = IDLE;
    nextNoncePage = nextResponsePage = 0;
    return true;
  }
  if (reportId != 0xF0) return false;
  if (length != 63 || data[1] > 4 || data[2] != 0) {
    ++trace.f0Bad;
    return false;
  }
  uint32_t crc = crc32(0xFFFFFFFFUL, 0xF0);
  for (uint8_t i = 0; i < 59; ++i) crc = crc32(crc, data[i]);
  crc = ~crc;
  for (uint8_t i = 0; i < 4; ++i)
    if (data[59 + i] != (uint8_t)(crc >> (8 * i))) {
      ++trace.f0Bad;
      return false;
    }
  // em is both nonce input and arithmetic/output workspace. A new nonce must
  // never overwrite it before the active signer has completely unwound.
  if (signerBusy) {
    ++trace.f0Busy;
    trace.lastCancelReason = 2;
    ++epoch;
    cancelled = true;
    state = IDLE;
    return false; // STALL: host must start again with page zero after unwind.
  }
  uint8_t page = data[1];
  uint8_t count = page == 4 ? 32 : 56;
  // Before signing, em still holds every accepted challenge page. An exact
  // retransmission can be acknowledged without restarting the nonce.
  if (data[0] == nonceId && (state == RECEIVING || state == PENDING) &&
      page < nextNoncePage) {
    if (!memcmp(signerNonceBuffer() + (uint16_t)page * 56, data + 3, count)) {
      ++trace.duplicateF0;
      return true;
    }
    if (page != 0) {
      ++trace.f0Bad;
      trace.lastCancelReason = 3;
      ++epoch;
      cancelled = true;
      state = IDLE;
      nextNoncePage = nextResponsePage = 0;
      return false;
    }
  }
  if (page == 0) {
    uint16_t now = millis() / 1000UL;
    if (!trace.f0Pages[0]) trace.firstF0Sec = now;
    trace.lastF0Sec = now;
    ++epoch;
    cancelled = true;
    nonceId = data[0];
    nextNoncePage = nextResponsePage = 0;
    state = RECEIVING;
  }
  if (state != RECEIVING || data[0] != nonceId || page != nextNoncePage) {
    ++trace.f0Bad;
    return false;
  }
  memcpy(signerNonceBuffer() + (uint16_t)page * 56, data + 3, count);
  ++trace.f0Pages[page];
  if (++nextNoncePage == 5) {
    state = PENDING;
    trace.f0CompleteSec = millis() / 1000UL;
  }
  return true;
}

void probeBootTask() {
  if (!bootRequested) return;
  delay(50); // Let the SET_REPORT status packet reach the PC before detaching.
  USBDevice.detach();
  cli();
  wdt_reset();
  wdt_enable(WDTO_120MS);
  // Caterina.c checks 0x0800 for 0x7777 after a watchdog reset. New LUFA
  // Caterina variants use RAMEND-1. No calls/returns after either RAM write.
  *(volatile uint16_t*)0x0800 = 0x7777;
  *(volatile uint16_t*)(RAMEND - 1) = 0x7777;
  for (;;) {}
}

extern "C" uint8_t ps4AuthGet(uint8_t reportId, uint8_t* data) {
  if (reportId == 0xF2) {
    if (state == READY) ++trace.f2Ready; else ++trace.f2Busy;
    if (state == SIGNING) {
      uint16_t age = (millis() - signStartedMs) / 100UL;
      if (age > trace.maxF2BusyAgeDs) trace.maxF2BusyAgeDs = age;
    }
    data[0] = nonceId;
    data[1] = state == READY ? 0 : 16;
    memset(data + 2, 0, 9);
    reportCrc(0xF2, data, 11);
    return 15;
  }
  if (reportId == 0xF4) {
    memset(data, 0, 63);
    eeprom_read_block(data + 2, &savedTrace, sizeof(AuthTrace));
    const uint8_t* stored = data + 2;
    bool persisted = stored[0] == 0x4D && stored[1] == 0xA7 && stored[2] == 4 &&
                     (uint16_t)(stored[47] | ((uint16_t)stored[48] << 8)) == traceCheck(stored);
    if (!persisted) memcpy(data + 2, &trace, sizeof(AuthTrace));
    data[0] = 2; data[1] = persisted;
    data[51] = state;
    data[52] = probeHostFlags();
    data[53] = signerBusy;
    reportCrc(0xF4, data, 59);
    return 63;
  }
  if (reportId != 0xF1) return 0;
  if (state != READY || nextResponsePage >= 19) {
    ++trace.f1Early;
    return 0;
  }
  data[0] = nonceId; data[1] = nextResponsePage; data[2] = 0;
  for (uint8_t i = 0; i < 56; ++i) {
    uint16_t offset = (uint16_t)nextResponsePage * 56 + i;
    data[3 + i] = offset < 256 ? signerSignatureByte(offset) :
        pgm_read_byte(publicIdentity + offset - 256);
  }
  reportCrc(0xF1, data, 59);
  return 63;
}

// Commit only after the core has queued every byte successfully. This does not
// assert that the host/application accepted the authentication response.
extern "C" void ps4AuthCommit(uint8_t reportId) {
  if (reportId == 0xF1 && state == READY && nextResponsePage < 19) {
    ++trace.f1Pages;
    trace.lastF1Page = nextResponsePage;
    trace.lastF1Sec = millis() / 1000UL;
    if (++nextResponsePage == 19) state = IDLE;
  }
}

bool authCancelled() {
  bool result;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    result = cancelled || epoch != signingEpoch;
  }
  return result;
}

void authTask() {
  bool begin = false;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    if (state == PENDING) {
      signingEpoch = epoch;
      cancelled = false;
      signerBusy = true;
      state = SIGNING;
      ++trace.signerStarts;
      signStartedMs = millis();
      begin = true;
    }
  }
  if (!begin) return;
  bool success = signerSign();
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    signerBusy = false;
    if (success && !cancelled && epoch == signingEpoch && state == SIGNING) {
      state = READY;
      ++completed;
      ++trace.signedOk;
      trace.readySec = millis() / 1000UL;
    } else {
      ++abandoned;
      ++trace.signedAborted;
      if (state == SIGNING) state = IDLE;
    }
  }
}
