#include <PS4Arduino.h>
#include <util/atomic.h>

void ps4Begin() { PS4controller.begin(); }

void ps4Update(const uint8_t* report) {
  // Setters also touch the ISR-owned counter byte. Publish one consistent frame.
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    PS4controller.setJoystick(LEFT, X, report[1]);
    PS4controller.setJoystick(LEFT, Y, report[2]);
    PS4controller.setJoystick(RIGHT, X, report[3]);
    PS4controller.setJoystick(RIGHT, Y, report[4]);
    PS4controller.setDpad((dirEnum)((report[5] & 15) + 1));
    PS4controller.setButton(SQUARE, report[5] & 0x10);
    PS4controller.setButton(CROSS, report[5] & 0x20);
    PS4controller.setButton(CIRCLE, report[5] & 0x40);
    PS4controller.setButton(TRIANGLE, report[5] & 0x80);
    PS4controller.setButton(L1, report[6] & 0x01);
    PS4controller.setButton(R1, report[6] & 0x02);
    PS4controller.setButton(L2, report[6] & 0x04);
    PS4controller.setButton(R2, report[6] & 0x08);
    PS4controller.setButton(SHARE, report[6] & 0x10);
    PS4controller.setButton(OPTIONS, report[6] & 0x20);
    PS4controller.setButton(L3, report[6] & 0x40);
    PS4controller.setButton(R3, report[6] & 0x80);
    PS4controller.setButton(PS, report[7] & 0x01);
    PS4controller.setButton(TOUCHPAD, report[7] & 0x02);
    PS4controller.setTrigger(LEFT, report[8]);
    PS4controller.setTrigger(RIGHT, report[9]);
  }
}
