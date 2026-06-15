#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#include "LibPrintf.h"

#define spiBlock 2048
SPIPeripheralClass<spiBlock> spi;

// Write command opcodes (first byte of 5-byte command header)
#define WRITE_CMD_BYTES              0x0A
#define WRITE_CMD_FLOATS             0x0B
#define WRITE_CMD_INTS               0x0C
#define WRITE_CMD_STRUCT             0x0D
#define WRITE_CMD_STRUCT_ARRAY       0x0E
#define WRITE_CMD_STRUCT_ARRAYFIELDS 0x0F

#define X_COUNT 2
#define Y_COUNT 2
#define Z_COUNT 2

typedef struct {
    float   x[X_COUNT];    // f32
    int32_t y[Y_COUNT];    // i32
    uint8_t z[Z_COUNT];    // u8
} StructArrayFieldsPacket;


uint8_t rx[spiBlock];   // example size
int     rx_len = spiBlock;    // actual bytes received

void processSpiFrame(uint8_t* rx, int rx_len) {
    if (rx_len < 5) return;  // need at least command header

    uint8_t cmd0 = rx[0];
    uint8_t lenL = rx[3];
    uint8_t lenH = rx[4];
    
    uint16_t payload_len = (uint16_t)lenL | ((uint16_t)lenH << 8);
    uint8_t* payload = rx + 5;

    //Serial.print(cmd0); Serial.print(", "); Serial.println(payload_len);
    switch (cmd0) {
        case WRITE_CMD_BYTES:
            handleWriteBytes(payload, payload_len);
            break;

        case WRITE_CMD_FLOATS:
            Serial.println("WRITE FLOATS:");
            handleWriteFloats(payload, payload_len);
            break;

        case WRITE_CMD_INTS:
            Serial.println("WRITE INTS:");
            handleWriteInts(payload, payload_len);
            break;

        case WRITE_CMD_STRUCT:
            Serial.println("WRITE STRUCT:");
            handleWriteStruct(payload, payload_len);
            break;

        case WRITE_CMD_STRUCT_ARRAY:
            Serial.println("WRITE STRUCT_ARRAY:");
            handleWriteStructArray(payload, payload_len);
            break;

        case WRITE_CMD_STRUCT_ARRAYFIELDS:
            Serial.println("WRITE STRUCT_ARRAYFIELDS:");
            handleWriteStructArrayFields(payload, payload_len);
            break;

        default:
            // unknown command
            break;
    }
}

void handleWriteBytes(uint8_t* p, int len) {
    // raw bytes
    Serial.println("WRITE BYTES:");
    for (int i = 0; i < len; i++) {
        Serial.print(p[i], HEX);
        Serial.print(" ");
    }
    Serial.println();
}

void handleWriteFloats(uint8_t* p, int len) {
    int count = len / 4;
    float* f = (float*)p;

    for (int i = 0; i < count; i++) {
        Serial.print("f[");
        Serial.print(i);
        Serial.print("] = ");
        Serial.println(f[i], 6);
    }
}

void handleWriteInts(uint8_t* p, int len) {
    int count = len / 4;
    int32_t* v = (int32_t*)p;

    for (int i = 0; i < count; i++) {
        Serial.print("i[");
        Serial.print(i);
        Serial.print("] = ");
        Serial.println(v[i]);
    }
}

void handleWriteStruct(uint8_t* p, int len) {
    if (len < 1 + 4 + 4) return;

    uint8_t  a = p[0];
    int32_t  b = *(int32_t*)(p + 1);
    float    c = *(float*)(p + 5);

    Serial.print("a = ");
    Serial.println(a);

    Serial.print("b = ");
    Serial.println(b);

    Serial.print("c = ");
    Serial.println(c, 6);
}

void handleWriteStructArray(uint8_t* p, int len) {
    if (len < 2) return;

    uint8_t* cur = p;
    uint16_t count = *(uint16_t*)cur;
    cur += 2;
    int remaining = len - 2;

    Serial.print("struct count = ");
    Serial.println(count);

    for (int i = 0; i < count && remaining >= 2; i++) {
        uint16_t slen = *(uint16_t*)cur;
        cur += 2;
        remaining -= 2;

        if (remaining < slen) break;

        uint8_t* sdata = cur;
        cur += slen;
        remaining -= slen;

        Serial.print("struct #");
        Serial.print(i);
        Serial.print(" len = ");
        Serial.println(slen);

        // For now, just dump raw bytes
        for (int j = 0; j < slen; j++) {
            Serial.print(sdata[j], HEX);
            Serial.print(" ");
        }
        Serial.println();
    }
}

void handleWriteStructArrayFields(uint8_t* p, int len) {
    int expected = X_COUNT*4 + Y_COUNT*4 + Z_COUNT*1;
    if (len < expected) return;

    StructArrayFieldsPacket pkt;

    // x: float32
    memcpy(pkt.x, p, X_COUNT * sizeof(float));

    // y: int32
    memcpy(pkt.y, p + X_COUNT*4, Y_COUNT * sizeof(int32_t));

    // z: u8
    memcpy(pkt.z, p + X_COUNT*4 + Y_COUNT*4, Z_COUNT * sizeof(uint8_t));

    // Debug print
    Serial.println("StructArrayFieldsPacket:");

    Serial.println("x:");
    for (int i = 0; i < X_COUNT; i++) {
        Serial.print("  x[");
        Serial.print(i);
        Serial.print("] = ");
        Serial.println(pkt.x[i], 6);
    }

    Serial.println("y:");
    for (int i = 0; i < Y_COUNT; i++) {
        Serial.print("  y[");
        Serial.print(i);
        Serial.print("] = ");
        Serial.println(pkt.y[i]);
    }

    Serial.println("z:");
    for (int i = 0; i < Z_COUNT; i++) {
        Serial.print("  z[");
        Serial.print(i);
        Serial.print("] = 0x");
        Serial.println(pkt.z[i], HEX);
    }
}


//#define DEBUG

void setup() {
  Serial.begin(115200);
  delay(5000);

  spi.begin();

}

void loop() {
    uint8_t buffer[spiBlock];
    uint8_t tx_buf[5];
  
    spi.depopulate(*tx_buf, 5);
    tx_buf[1] = 1;
    spi.populate(tx_buf, 2048);
    spi.ready();
  
    // 1. Read SPI frame into rx[]
    //spi.depopulate(*buffer, 5);
    int byte_count = spi.read(buffer, sizeof(buffer));
    spi.ready();

    delayMicroseconds(5);

    #if defined(DEBUG)
      Serial.print(icount); Serial.print(", "); Serial.println(byte_count);
      Serial.print("CMD = ");
      Serial.println(rx[0], HEX);
      for (uint8_t i = 0; i < 8; i++) {
          Serial.print(buffer[i]);
          Serial.print(", ");
      }
      Serial.println();
    #endif
  
    if(byte_count > 0) {
      processSpiFrame(buffer, rx_len); 
    }

    delayMicroseconds(25);
}

