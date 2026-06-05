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

void ints_to_bytes(const int32_t* values, size_t count, uint8_t* out_bytes) {
    const uint8_t* src = reinterpret_cast<const uint8_t*>(values);
    memcpy(out_bytes, src, count * sizeof(int32_t));
}


float sensorValues[num_vals];
int sensorValuesInts[num_vals];
long randNumber;

void get_sensor_data() {
  for (uint8_t i = 0; i < num_vals; i++) {
    randNumber = random(300);
    sensorValues[i] = float(randNumber) / 10.0;
  }
}

void get_sensor_data_ints() {
  for (uint8_t i = 0; i < num_vals; i++) {
    randNumber = random(300);
    sensorValuesInts[i] = (randNumber);
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

  // Debug print
  //for(uint8_t i = 0; i < 5; i++) {
  //  Serial.print(buffer[i], HEX); Serial.print(", ");
  //}
  Serial.println();

  if(buffer[0] == 0x0C) {
    get_sensor_data_ints();
    ints_to_bytes(sensorValuesInts, num_vals, bytes);
    spi.populate(bytes, spiBlock);
  }
  
  if(buffer[0] == 0x0B) {
    get_sensor_data();
    floats_to_bytes(sensorValues, num_vals, bytes);
    spi.populate(bytes, spiBlock);
  }

  // 3. Signal ready
  spi.ready();
  delayMicroseconds(5);
}

