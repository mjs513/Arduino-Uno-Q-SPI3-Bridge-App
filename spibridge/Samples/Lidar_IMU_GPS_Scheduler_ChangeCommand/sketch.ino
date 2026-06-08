#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define spiBlock 2048
SPIPeripheralClass<spiBlock> spi;

// Data types
enum DataType : uint8_t {
    DATA_LIDAR = 0x1A,
    DATA_IMU   = 0x2A,
    DATA_GPS   = 0x3A,
};

uint8_t buffer[5];   // Python sends 18 bytes
/* Thread: Define stack size and scheduling priority used by each thread */
#define STACKSIZE 1024
#define spibridge_priority 7

// Stuctures for Lidar, IMU and GPS
struct {
  int angle[361];
  int flag[361];
  int quality[361];
  int range[361];
} lidar;

struct IMUData {
    float ax, ay, az;
    float gx, gy, gz;
    float mx, my, mz;
} imu;

struct GPSData {
    double lat, lon;
    float alt;
} gps;

//Fill data for Lidar IMU and GPS
void fillTestData() {
  for (int i = 0; i < 361; i++) {
    lidar.angle[i]   = i;          // 0..360
    lidar.flag[i]    = (i % 2);    // 0,1,0,1...
    lidar.quality[i] = i * 10;     // 0,10,20,...
    lidar.range[i]   = 1000 + i;   // 1000..1361
  }
}

void fillIMUTestData() {
    imu.ax = 0.01f;   // m/s^2
    imu.ay = -0.02f;
    imu.az = 9.81f;   // gravity

    imu.gx = 0.001f;  // rad/s
    imu.gy = 0.002f;
    imu.gz = 0.003f;

    imu.mx = 30.5f;   // microtesla
    imu.my = -12.7f;
    imu.mz = 45.2f;
}

void fillGPSTestData() {
    gps.lat = 40.7580;     // Times Square latitude
    gps.lon = -73.9855;    // Times Square longitude
    gps.alt = 15.2f;       // meters
}

// Lidar, IMU and GPS pointers to send data
const size_t TOTAL_LIDAR = sizeof(lidar);      // 5776
uint8_t* ptr = (uint8_t*)&lidar;

// send data frame
void sendFrame(uint8_t data_type, uint8_t* payload, uint32_t total_size)
{
    const uint16_t BLOCK_SIZE = 2048;
    uint8_t block_count = (total_size + BLOCK_SIZE - 1) / BLOCK_SIZE;

    // ---- Build header (9 bytes) ----
    uint8_t header[9];
    header[0] = 0xAA;               // SOF
    header[1] = data_type;          // e.g. 0x01 = LIDAR

    // block_size (uint16 LE)
    header[2] = BLOCK_SIZE & 0xFF;
    header[3] = (BLOCK_SIZE >> 8) & 0xFF;

    // total_size (uint32 LE)
    header[4] = total_size & 0xFF;
    header[5] = (total_size >> 8) & 0xFF;
    header[6] = (total_size >> 16) & 0xFF;
    header[7] = (total_size >> 24) & 0xFF;

    header[8] = block_count;

    // ---- Send header ----
    spi.populate(header, sizeof(header));
    spi.ready();

    // ---- Send blocks ----
    uint32_t offset = 0;
    for (uint8_t i = 0; i < block_count; i++) {
        uint32_t remaining = total_size - offset;
        uint16_t chunk = remaining > BLOCK_SIZE ? BLOCK_SIZE : remaining;

        spi.populate(payload + offset, chunk);
        spi.ready();

        offset += chunk;
    }
}

//Thread:  Thread to be executed
void spibridge(void)
{
    Serial.println("Hello spibridge Started\n");

    while (1) {
        spi.depopulate(*buffer,5);
        //Serial.print(buffer[0]); Serial.print(", "); 
        //Serial.print(buffer[1]); Serial.print(", "); 
        //Serial.println(buffer[2]);
        // Only process if command byte is correct
        //if (buffer[0] == 0x0A) {
            switch (buffer[0]) {
                case 0x1A:   // LIDAR request
                    sendFrame(DATA_LIDAR, (uint8_t*)&lidar, sizeof(lidar));
                    break;
                case 0x2A:   // IMU request
                    sendFrame(DATA_IMU, (uint8_t*)&imu, sizeof(imu));
                    break;
                case 0x3A:   // GPS request
                    sendFrame(DATA_GPS, (uint8_t*)&gps, sizeof(gps));
                    break;
                default:
                    break;
            }
        //}

        // Reset ALL command bytes
        memset(buffer, 0, sizeof(buffer));

        k_yield();
    }

    delay(1);
}


/*************************************************************************************
* Parameters:
*    name – Symbolic name for the thread (also becomes the thread ID variable).
*    stack_size – Size of the thread stack in bytes.
*    entry_function – Function pointer to the thread entry function (void func(void *, void *, void *)).
*    p1, p2, p3 – Parameters passed to the entry function.
*    priority – Thread priority (lower number = higher priority in Zephyr).
*    options – Thread options.
*    delay – Start delay in milliseconds (K_NO_WAIT for immediate start).
************************************************************************************/
K_THREAD_DEFINE(spibridge_id, STACKSIZE, spibridge, NULL, NULL, NULL, spibridge_priority, 0, 0);

void setup() {
  Serial.begin(115200);
  delay(5000);
  
  fillTestData();
  fillIMUTestData();
  fillGPSTestData();
  
  Serial.println("LIDAR test struct ready");
  Serial.print("Struct size = ");
  Serial.println(sizeof(lidar));   // Should print 5776erial.begin(115200);
  
  spi.begin();

  Serial.println("Lidar SPI test ready");
}

void loop() {

  delay(1);  // keep loop alive
}
