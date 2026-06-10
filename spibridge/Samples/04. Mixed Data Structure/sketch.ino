#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define spiBlock 1024
SPIPeripheralClass<spiBlock> spi;

uint8_t buffer[18];   // Python sends 18 bytes

struct __attribute__((packed)) SensorPacket {
    uint32_t timestamp;
    float temperature;
    float humidity;
    int32_t readings[4];
};

SensorPacket pkt;

void fillPacket() {
    pkt.timestamp = millis();
    pkt.temperature = 23.5f;
    pkt.humidity = 48.2f;
    pkt.readings[0] = 100;
    pkt.readings[1] = 200;
    pkt.readings[2] = 300;
    pkt.readings[3] = 400;
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  spi.begin();
  fillPacket();
  Serial.println("Mixed SPI test ready");
}

void loop() {
  fillPacket();

  // 1. Read command (match Python's command size)
  spi.depopulate(*buffer, 5);

  uint8_t* bytes = (uint8_t*)&pkt;
  size_t len = sizeof(SensorPacket);

  spi.populate(bytes, len);
  spi.ready();

  spi.ready();
  delayMicroseconds(5);
}
