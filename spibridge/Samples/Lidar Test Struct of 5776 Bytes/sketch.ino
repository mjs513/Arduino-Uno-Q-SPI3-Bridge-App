#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define spiBlock 2048
SPIPeripheralClass<spiBlock> spi;

uint8_t buffer[18];   // Python sends 18 bytes

struct {
  int angle[361];
  int flag[361];
  int quality[361];
  int range[361];
} lidar;

void fillTestData() {
  for (int i = 0; i < 361; i++) {
    lidar.angle[i]   = i;          // 0..360
    lidar.flag[i]    = (i % 2);    // 0,1,0,1...
    lidar.quality[i] = i * 10;     // 0,10,20,...
    lidar.range[i]   = 1000 + i;   // 1000..1361
  }
}

const size_t TOTAL = sizeof(lidar);      // 5776
uint8_t* ptr = (uint8_t*)&lidar;

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  fillTestData();

  Serial.println("LIDAR test struct ready");
  Serial.print("Struct size = ");
  Serial.println(sizeof(lidar));   // Should print 5776erial.begin(115200);
  delay(2000);

  spi.begin();

  Serial.println("Lidar SPI test ready");
}

void loop() {
  // 1. Read command (match Python's command size)
  spi.depopulate(*buffer, 5);

// ptr = (uint8_t*)&lidar;
// TOTAL = sizeof(lidar);  // 5776
// spiBlock = 2048

  // --- Block 1: first 2048 bytes ---
  spi.populate(ptr, 2048);
  spi.ready();
  
  // --- Block 2: next 2048 bytes ---
  spi.populate(ptr + 2048, 2048);
  spi.ready();

  
  // --- Block 3: remaining bytes ---
  spi.populate(ptr + 4096, TOTAL - 4096);   // 5776 - 4096 = 1680
  spi.ready();
  delayMicroseconds(5);
}
