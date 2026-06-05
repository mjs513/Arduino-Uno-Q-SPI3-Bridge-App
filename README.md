---

# **SPI Bridge — App Lab Brick (Proof of Concept)**  
### *A minimal SPI → Docker → HTTP → App Lab data bridge for the Arduino UNO Q*

---

## **Introduction**

This project is a Proof of Concept demonstrating **SPI communication between the STM32U585 MCU and the Qualcomm QRB2210 MPU** on the Arduino UNO Q using a custom App Lab brick.

The goal is to show that it is possible to:

- Read raw bytes from the UNO Q’s **SPI3 hardware interface**  
- Process and decode the data inside a **dedicated Docker container**  
- Expose the results through a **simple Flask HTTP API**  
- Access the data from an **App Lab Python module** (`__init__.py`)  

This brick is intentionally minimal and designed for experimentation, debugging, and learning how to build App Lab bricks that interact with Linux hardware.

It totally based on the **custom-brick-with-container app** developed by @ptillisch (Arduino Team): https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568/17 and the full discussion on developing the spidev brick: https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568

---

## **Architecture**

```
+--------------------------------------------------------------+
|                       Arduino UNO Q                          |
+--------------------------------------------------------------+

   +----------------------+                    +----------------------+
   |   STM32U585 (MCU)   |                    |   QRB2210 (MPU)      |
   |----------------------|                    |----------------------|
   | - Generates payload  |   SPI3 (spidev0.0) | - Linux spidev       |
   | - Packs bytes/floats | <----------------> | - Docker container   |
   | - Responds to 0x0B   |                    | - Flask HTTP server  |
   +----------------------+                    +----------------------+
                                                        |
                                                        | HTTP (localhost:5000)
                                                        v
                                            +------------------------------+
                                            |   App Lab Python Brick       |
                                            |------------------------------|
                                            | - readBytes()                |
                                            | - readFloats()               |
                                            | - readInts()                 |
                                            | - config_speed/mode/bits     |
                                            +------------------------------+
                                                        |
                                                        v
                                            +------------------------------+
                                            |      App Lab Application     |
                                            +------------------------------+
```

---

## Prerequisites
Before running this App Lab brick, the following components must be properly configured on the Arduino UNO Q. These steps ensure that the Docker container can access the SPI hardware and that the App Lab environment can communicate with the brick.

**SPI Device Access** (udev Rules Required)
The UNO Q’s Linux environment restricts write access to:

```
/dev/spidev0.0
```
The Docker container runs as the arduino user, which does not have permission to open this device by default.
To fix this, install a udev rule that assigns all /dev/spidev* devices to the gpiod group — a group the arduino user already belongs to.

Install the rule on the UNO Q (not inside the container):

```
echo \
'# See: https://github.com/doceme/py-spidev/blob/v3.8/99-local-spi-example-udev.rules#L31
KERNEL=="spidev*", GROUP="gpiod", MODE="0660"' \
| \
  sudo \
    tee \
      "/etc/udev/rules.d/60-spi.rules" \
&& \
sudo \
  udevadm control \
    --reload-rules \
&& \
sudo \
  udevadm trigger
```  

Verify:

```
ls -l /dev/spidev0.0
```
Expected:

```
crw-rw---- 1 root gpiod ...
```
Without this rule, the brick will fail with PermissionError or return empty data.

## Automatic Rebuilds with docker compose watch
This brick supports rapid development through automatic container rebuilds.
The develop.watch section in brick_compose.yaml instructs Docker to monitor key files and rebuild the container whenever they change.

This eliminates the need to manually run docker compose build or restart App Lab.

**How It Works**
The brick_compose.yaml includes:

```yaml
develop:
  watch:
    - action: rebuild
      path: ./app
    - action: rebuild
      path: brick_compose.yaml
    - action: rebuild
      path: Dockerfile
    - action: restart
      path: __init__.py
```
Whenever any of these files change:

1. Docker automatically rebuilds the image
2. Restarts the container
3. App Lab immediately uses the updated code

**Starting the Watcher**
Start the app and then run this on the UNO Q (not inside the container):

```text
docker compose --file ~/ArduinoApps/spibridge/.cache/app-compose.yaml watch
```
You will see output like:

```Code
[+] Watching for changes...
  spi3bridge Rebuilding because app/app.py changed
  spi3bridge Recreating
  spi3bridge Starting
 ```

Append & to the command:
```
docker compose --file ~/ArduinoApps/spibridge/.cache/app-compose.yaml watch --no-up &
```
The & control operator causes the process to run as a background job. This is useful in the case where the command creates a persistent process because it allows you to continue working from the shell while the process is running asynchronously

What Triggers a Rebuild
- Editing app.py
- Editing spihelper.py
- Editing __init__.py
- Editing the Dockerfile
- Editing brick_compose.yaml

**Why This Matters**
- No manual rebuilds
- No restarting App Lab
- Faster debugging

Perfect for SPI development where you frequently adjust parsing logic

## **Operation**

### **MCU Side**

The MCU responds to the read command:

```
0x0B 00 00 00 00
```

and returns **1024 bytes** per transaction.  
The MCU may send:

- Raw bytes  
- Packed float32 values  
- Packed int32 values  
- Custom binary payloads  

This POC does not enforce a protocol — it simply reads whatever the MCU sends.

---

### **MPU Side (Docker Container)**

The Docker container:

- Maps `/dev/spidev0.0` into the container  
- Uses `spidev` to perform SPI transfers  
- Runs a Flask server exposing multiple endpoints  
- Converts raw bytes into floats or ints when requested  
- Allows runtime reconfiguration of SPI parameters  

The core SPI logic lives in **`spihelper.py`**, which wraps:

- `init_spi()`  
- `read_bytes()`  
- `set_speed()`  
- `set_mode()`  
- `set_bits()`  

---

## **MCU Payload Protocol (Recommended)**

To make the SPI data self‑describing and robust, this README defines a simple, extensible protocol that fits your existing brick perfectly.

### **Frame Layout (1024 bytes total)**

```
+---------+----------+---------------------------+
| Offset  | Size     | Description               |
+---------+----------+---------------------------+
| 0       | 1 byte   | Signature (0xA5)          |
| 1       | 1 byte   | Payload type              |
| 2       | 2 bytes  | Payload length (LE)       |
| 4       | N bytes  | Payload data              |
| 4+N     | ...      | Zero padding up to 1024   |
+---------+----------+---------------------------+
```

### **Payload Type Values**

| Value | Meaning             |
|-------|----------------------|
| 0x01  | Raw bytes            |
| 0x02  | Float32 array        |
| 0x03  | Int32 array          |
| 0x04  | Custom / user‑defined|

### **Why this protocol?**

- Works with your existing `/read/floats` and `/read/ints` endpoints  
- Self‑describing  
- Easy to extend  
- Fixed frame size simplifies SPI transactions  
- Zero‑copy decoding on the MPU  

---

## **HTTP API Endpoints**

### **GET `/read/bytes`**  
Reads 1024 bytes and returns them as formatted hex lines.

### **GET `/read/floats`**  
Reads 1024 bytes and decodes them as **little‑endian float32** values.

### **GET `/read/ints`**  
Reads 1024 bytes and decodes them as **little‑endian int32** values.

### **POST `/config/speed`**  
Sets SPI clock speed (Hz).

### **POST `/config/mode`**  
Sets SPI mode (0–3).

### **POST `/config/bits`**  
Sets bits per word (usually 8).

---

## **App Lab Python API (Command Reference)**  
*(Updated for JSON list returns + `n` parameter support)*

This section documents all Python‑level commands exposed by the SPI Bridge brick.  
These functions communicate with the Docker‑hosted Flask server running on the UNO Q.

Each command corresponds directly to an endpoint in `app.py`.

---

## **Read Commands**

---

### **`readBytes(n=None)`**
**Description:**  
Reads raw bytes from the MCU via SPI and returns them as a list of unsigned 8‑bit integers.

**Arguments:**  
- `n` *(optional)* — number of byte values to return.  
  - If omitted, returns all bytes read (default: 1024).

**Returns:**  
`list[int]` — each element is a `uint8` (0–255).

**Use when:**  
You want direct access to the raw SPI byte stream for debugging, framing, or protocol parsing.

---

### **`readFloats(n=None)`**
**Description:**  
Reads 1024 bytes from SPI and interprets them as **little‑endian float32** values.

**Arguments:**  
- `n` *(optional)* — number of float values to return.  
  - If omitted, returns all decoded floats (default: 256 floats from 1024 bytes).

**Returns:**  
`list[float]` — Python floats decoded from the SPI buffer.

**Use when:**  
The MCU is sending float32 sensor data, structured arrays, or telemetry.

---

### **`readInts(n=None)`**
**Description:**  
Reads 1024 bytes from SPI and interprets them as **little‑endian int32** values.

**Arguments:**  
- `n` *(optional)* — number of int32 values to return.  
  - If omitted, returns all decoded ints (default: 256 ints from 1024 bytes).

**Returns:**  
`list[int]` — signed 32‑bit integers.

**Use when:**  
The MCU is sending counters, timestamps, fixed‑point values, or packed integer data.

---

## **Configuration Commands**

---

### **`config_speed(hz)`**
**Description:**  
Sets the SPI clock speed (in Hz).

**Arguments:**  
- `hz` — integer, e.g. `1000000` for 1 MHz.

**Returns:**  
```json
{"status": "ok", "speed": <hz>}
```

**Use when:**  
You need to match the MCU’s SPI clock or debug timing issues.

---

### **`config_mode(mode)`**
**Description:**  
Sets the SPI mode (0–3).

**Arguments:**  
- `mode` — integer (0, 1, 2, or 3).

**Returns:**  
```json
{"status": "ok", "mode": <mode>}
```

**Use when:**  
The MCU requires a specific CPOL/CPHA configuration.

---

### **`config_bits(bits)`**
**Description:**  
Sets the number of bits per SPI word (usually 8).

**Arguments:**  
- `bits` — integer, typically `8`.

**Returns:**  
```json
{"status": "ok", "bits": <bits>}
```

**Use when:**  
You need non‑standard SPI word sizes or are debugging protocol alignment.

---

### **`config_bytes_to_read(n)`**
**Description:**  
Sets how many bytes the SPI bridge reads per transaction.

**Arguments:**  
- `n` — integer, must be a power‑of‑two multiple (e.g., 256, 512, 1024).

**Returns:**  
```json
{"status": "ok", "bytes": <n>}
```

**Use when:**  
You want to adjust the SPI payload size for your MCU protocol.

---

## **Summary Table**

| Command                | Purpose                                   | Return Type        |
|------------------------|--------------------------------------------|--------------------|
| `readBytes(n)`         | Read raw bytes as `uint8` list             | `list[int]`        |
| `readFloats(n)`        | Read float32 values from SPI               | `list[float]`      |
| `readInts(n)`          | Read int32 values from SPI                 | `list[int]`        |
| `config_speed(hz)`     | Set SPI clock speed                        | `dict` (JSON)      |
| `config_mode(mode)`    | Set SPI mode (0–3)                         | `dict` (JSON)      |
| `config_bits(bits)`    | Set bits per word                          | `dict` (JSON)      |
| `config_bytes_to_read(n)` | Set SPI read size                      | `dict` (JSON)      |

---

The App Lab code communicates with the Docker container using the hostname:

```
http://spi3bridge:5000
```

This is automatically provided by Docker Compose service discovery.

---

## **Files Overview**

### **`app.py`**  
Flask server implementing all HTTP endpoints and SPI read logic.

### **`spihelper.py`**  
Thin wrapper around `spidev` providing:

- Initialization  
- Reconfiguration  
- Raw byte reads  

### **`__init__.py`**  
The App Lab Python module that:

- Calls the Flask API  
- Provides `readBytes()`, `readFloats()`, `readInts()`  
- Provides SPI configuration helpers  

### **`Dockerfile`**  
Builds a minimal Python 3.13 container with Flask + spidev + requests + jsonify.

### **`brick_compose.yaml`**  
Defines the Docker service, device mapping, port exposure, and file‑watch rebuild rules.

### **`brick_config.yaml`**  
Registers the brick with App Lab.

---

## **Demonstration Data**

This POC does not assume any specific MCU payload.  
It simply reads whatever the MCU sends.

Typical use cases:

- Sensor data  
- Float arrays  
- Int32 streams  
- Binary packets  
- Custom protocols  

The goal is to validate the **communication path**, not the data format.

---

## **Validated Features**

- SPI3 access from inside a Docker container  
- 1024‑byte transfers using `spidev` 
- Float and integer decoding  
- Hex dump formatting  
- Runtime SPI reconfiguration  
- Clean App Lab Python API  
- Automatic container rebuild via `docker compose watch`  

---

## **Known Limitations**

- No synchronization or framing  
- No CRC or integrity checks  
- No error handling for malformed payloads  

These can be improved in future iterations.

---

## **Debugging**
**Running out of Room**

If you get "You don't have enough free space in /var/cache/apt/archives/." error, apparently because I am running out of the space allocated by Docker. So I would first run a docker system prune command:
```
docker system prune --force && docker compose -f ~/ArduinoApps/spibridge/.cache/app-compose.yaml build --with-dependencies 
```
**Debugging container errors**
```
docker compose --file ~/ArduinoApps/spibridge/.cache/app-compose.yaml logs
```

## **Educational Purpose**

This project is not intended to be a production‑ready SPI driver.  
Its purpose is to demonstrate:

- How to build a custom App Lab brick  
- How to run a hardware‑accessing service inside Docker  
- How to expose Linux‑side functionality to App Lab  
- How to debug SPI communication on the UNO Q  

---

## **License**

MIT License

---

## **References**
- [**Compose File Reference**](https://docs.docker.com/reference/compose-file/)
- [**Docker Compose Quickstart**](https://docs.docker.com/compose/gettingstarted/)
- [**Networking overview**](https://docs.docker.com/engine/network/)
- [**Flask Quick Start**](https://flask.palletsprojects.com/en/stable/quickstart/)
- [**Flask App Routing**](https://www.geeksforgeeks.org/python/flask-app-routing/)

**Arduino Brick Development**

- [**Custom Bricks**](https://github.com/arduino/docs-content/blob/app-lab-custom-bricks-documentation/content/software/app-lab/5.bricks/3.custom-bricks/custom-bricks.md)
- [**Arduino® App Lab 0.7: Custom Bricks are here!**](https://blog.arduino.cc/2026/04/29/arduino-app-lab-0-7-custom-bricks-are-here/)

## **Test case example**
1. This case just sends data from the MCU to the MPU. Does not use the read_command option for just sending data to the MPU
---
**sketch.ino**
```c++
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
```
## **SPIPeripheral.h** (this is mandatory for all sketches using SPI3 right now)

```c++
#ifndef SPI_PERIPHERAL_H
#define SPI_PERIPHERAL_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/drivers/spi.h>

#ifdef CONFIG_BOARD_ARDUINO_UNO_Q

#define SPI_PERIPHERAL_NODE DT_COMPAT_GET_ANY_STATUS_OKAY(zephyr_spi_slave)

template <int SPI_MAX_MESSAGE>
class SPIPeripheralClass {
public:
    SPIPeripheralClass() {
        spi_cfg.frequency = 1000000;
        spi_cfg.operation = SPI_WORD_SET(8) | SPI_OP_MODE_SLAVE;
        rx.buf = rxmsg;
        rx.len = SPI_MAX_MESSAGE;
        rx_bufs.buffers = &rx;
        rx_bufs.count = 1;
        tx.buf = txmsg;
        tx.len = SPI_MAX_MESSAGE;
        tx_bufs.buffers = &tx;
        tx_bufs.count = 1;

    }
    int begin() {
        int ret = device_init(spi_peripheral);
        return ret;
    }

    void depopulate(uint8_t &buf, size_t len) {
        spi_transceive(spi_peripheral, &spi_cfg, &tx_bufs, &rx_bufs);
        uint8_t* rx_bytes = static_cast<uint8_t*>(rx_bufs.buffers[0].buf);
        buf = rx_bytes[0];
    }

    void* populate(uint8_t* buf, size_t len) {
        return memcpy(tx.buf, buf, len);
    }

    int ready() {
        return spi_transceive(spi_peripheral, &spi_cfg, &tx_bufs, &rx_bufs);
    }
private:

    const struct device *const spi_peripheral = DEVICE_DT_GET(DT_BUS(SPI_PERIPHERAL_NODE));
    struct spi_config spi_cfg;

    uint8_t rxmsg[SPI_MAX_MESSAGE];
    struct spi_buf rx ;
    struct spi_buf_set rx_bufs;

    uint8_t txmsg[SPI_MAX_MESSAGE];
    struct spi_buf tx ;
    struct spi_buf_set tx_bufs;
};

#endif
#endif //SPI_PERIPHERAL_H
## **main.py**
```python
import time
import numpy as np
import spibridge
from arduino.app_utils import App

print(spibridge.config_speed(1000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(1024))

def loop():
    # -------------------------
    # READ FLOATS (0x0B)
    # -------------------------
    # Get Read Type for processing in Arduino Sketch
    #np.array(spibridge.readFloats(n=18), dtype=np.float32)
    # Get Integer daya
    floats_out = np.array(spibridge.readFloats(n=18), dtype=np.float32)
    print("FLOATS:", floats_out)

    print("---------------------------------------------------")
    time.sleep(0.01)
App.run(user_loop=loop)
```

2, List of other examples in samples directory of repo
- Read on multiple data types
- Simple scheduling of reading of Integers and Floats
---
