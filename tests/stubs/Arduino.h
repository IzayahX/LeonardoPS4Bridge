#pragma once
#include <stdint.h>
#include <string.h>
#define __attribute__(x)
#define RAMEND 2559
#define SP 2559
uint32_t millis();
void delay(unsigned);
void cli();
struct UsbDeviceStub { void detach() {} };
extern UsbDeviceStub USBDevice;
