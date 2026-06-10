// Source: https://forum.arduino.cc/t/how-to-install-python-packages-on-the-arduino-q/1434480/7
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define num_vals 180
#define spiBlock 1024

SPIPeripheralClass<spiBlock> spi;
uint8_t buffer[5];

void floats_to_bytes(const float* src, size_t float_count, uint8_t* dst) {
  if (!src || !dst || float_count == 0) return;
  memcpy(dst, src, float_count * sizeof(float));
}


float sensorValues[num_vals];
long randNumber;

void get_sensor_data() {
  for (uint8_t i = 0; i < num_vals; i++) {
    randNumber = random(300);
    sensorValues[i] = float(randNumber) / 10.0;
  }
}

void setup() {
  Serial.begin();
  delay(2000);
  Serial.println("Begin SPI3 Test....");
  randomSeed(analogRead(42));
  spi.begin();
}


void loop() {
  uint8_t bytes[spiBlock];
  //memset(bytes, 0, 1024);
  
  // 1. Read command
  spi.depopulate(*buffer, 5);  

  get_sensor_data();
  floats_to_bytes(sensorValues, num_vals, bytes);
  spi.populate(bytes, spiBlock);

  // 3. Signal ready
  spi.ready();
  delayMicroseconds(5);
}

