#include <XBOXONE.h>

void ps4Update(const uint8_t* report);

static uint8_t axisByte(int16_t value, bool invert) {
  int32_t scaled = invert ? -(int32_t)value : (int32_t)value;
  if (scaled > 32767) scaled = 32767;
  return (scaled + 32768) >> 8;
}

static uint8_t triggerByte(uint16_t value) {
  if (value > 1023) value = 1023;
  return ((uint32_t)value * 255 + 511) / 1023;
}

static uint8_t hat(bool up, bool right, bool down, bool left) {
  if (up && down) up = down = false;
  if (left && right) left = right = false;
  if (up) return right ? 1 : left ? 7 : 0;
  if (down) return right ? 3 : left ? 5 : 4;
  if (right) return 2;
  if (left) return 6;
  return 8;
}

void xboxUpdate(XBOXONE& controller) {
  uint8_t report[10] = {0x01, 128, 128, 128, 128, 8, 0, 0, 0, 0};
  if (controller.XboxOneConnected) {
    report[1] = axisByte(controller.getAnalogHat(LeftHatX), false);
    report[2] = axisByte(controller.getAnalogHat(LeftHatY), true);
    report[3] = axisByte(controller.getAnalogHat(RightHatX), false);
    report[4] = axisByte(controller.getAnalogHat(RightHatY), true);
    report[5] = hat(controller.getButtonPress(UP), controller.getButtonPress(RIGHT),
                    controller.getButtonPress(DOWN), controller.getButtonPress(LEFT));
    if (controller.getButtonPress(X)) report[5] |= 0x10;
    if (controller.getButtonPress(A)) report[5] |= 0x20;
    if (controller.getButtonPress(B)) report[5] |= 0x40;
    if (controller.getButtonPress(Y)) report[5] |= 0x80;
    uint16_t left = controller.getButtonPress(L2), right = controller.getButtonPress(R2);
    if (controller.getButtonPress(LB)) report[6] |= 0x01;
    if (controller.getButtonPress(RB)) report[6] |= 0x02;
    if (left) report[6] |= 0x04;
    if (right) report[6] |= 0x08;
    if (controller.getButtonPress(BACK)) report[6] |= 0x10;
    if (controller.getButtonPress(START)) report[6] |= 0x20;
    if (controller.getButtonPress(L3)) report[6] |= 0x40;
    if (controller.getButtonPress(R3)) report[6] |= 0x80;
    if (controller.getButtonPress(XBOX)) report[7] |= 0x01;
    if (controller.getButtonPress(SHARE)) report[7] |= 0x02;
    report[8] = triggerByte(left);
    report[9] = triggerByte(right);
  }
  ps4Update(report);
}
