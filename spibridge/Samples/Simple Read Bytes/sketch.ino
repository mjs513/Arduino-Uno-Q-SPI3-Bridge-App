#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define spiBlock 512
SPIPeripheralClass<spiBlock> spi;

uint8_t buffer[18];   // Python sends 18 bytes

uint8_t testBlock[spiBlock];

void setup() {
  Serial.begin(115200);
  delay(2000);

  spi.begin();

  // Fill test block with predictable data
  for (int i = 0; i < spiBlock; i++) {
    testBlock[i] = i & 0xFF;   // 0,1,2,3,...255,0,1,2...
  }

  Serial.println("512-byte SPI test ready");
}

void loop() {
  // 1. Read command (Python sends 18 bytes)
  spi.depopulate(*buffer, 5);

  Serial.print("CMD = ");
  Serial.println(buffer[0], HEX);

  // 2. Send 512 bytes
  spi.populate(testBlock, spiBlock);

  // 3. Signal ready
  spi.ready();
  delayMicroseconds(5);
}
