// Source: https://forum.arduino.cc/t/how-to-install-python-packages-on-the-arduino-q/1434480/7
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define num_vals 180

SPIPeripheralClass<1024> spi;

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
  randomSeed(analogRead(A0));

  for (uint8_t i = 0; i < num_vals; i++) {
    randNumber = random(300);
    sensorValues[i] = float(randNumber) / 10.0;
  }
}

void get_sensor_data_ints() {
  randomSeed(analogRead(A0));

  for (uint8_t i = 0; i < num_vals; i++) {
    randNumber = random(300);
    sensorValuesInts[i] = (randNumber);
  }
}

void setup() {
  Monitor.begin();
  delay(2000);
  Monitor.println("Begin SPI3 Test....");
  spi.begin();
}

void loop() {
  uint8_t bytes[num_vals * sizeof(float)];

  // Convert float array → bytes
  //To send floats
  //get_sensor_data();
  //floats_to_bytes(sensorValues, num_vals, bytes);
  //spi.populate(bytes, num_vals * sizeof(float));
  //spi.ready();

  // To send integers
  get_sensor_data_ints();
  bytes[num_vals * sizeof(int32_t)];
  ints_to_bytes(sensorValuesInts, num_vals, bytes);
  spi.populate(bytes, num_vals * sizeof(int32_t));
  spi.ready();
}
