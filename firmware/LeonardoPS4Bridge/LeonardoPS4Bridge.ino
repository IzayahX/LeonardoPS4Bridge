// Experimental credential-required Xbox-to-PS4 bridge.
// Build with the supplied core patches. Keep credential headers and binaries local.
#include <SPI.h>
#include <XBOXONE.h>
#include <avr/wdt.h>
#include "Signer.h"

USB usbHost;
XBOXONE xbox(&usbHost);
static bool hostReady;
static uint32_t lastSigningInputMs;

uint8_t probeHostFlags() {
  return (hostReady ? 1 : 0) | (xbox.XboxOneConnected ? 2 : 0);
}

void authTask();
void authTraceTask();
void authTraceXboxPoll();
bool authCancelled();
void probeBootTask();
void ps4Begin();
void xboxUpdate(XBOXONE& controller);

bool signerService() {
  probeBootTask();
  if (authCancelled()) return false;
  uint32_t now = millis();
  if (now - lastSigningInputMs >= 40) {
    lastSigningInputMs = now;
    if (hostReady) usbHost.Task();
    if (hostReady) authTraceXboxPoll();
    xboxUpdate(xbox);
  }
  return !authCancelled();
}

void setup() {
  // USB is the PS4 HID interface; no Serial or Serial1 is used.
  ps4Begin();
  hostReady = usbHost.Init() == 0;
  signerArmStackCanary();
  wdt_enable(WDTO_8S);
}

void loop() {
  probeBootTask();
  wdt_reset();
  if (hostReady) usbHost.Task();
  xboxUpdate(xbox);
  authTask();
  authTraceTask();
}
