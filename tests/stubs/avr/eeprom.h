#pragma once
#include <stdint.h>
#include <string.h>
#define EEMEM
inline void eeprom_update_byte(uint8_t* p, uint8_t b) { *p = b; }
inline void eeprom_read_block(void* to, const void* from, size_t n) { memcpy(to, from, n); }
