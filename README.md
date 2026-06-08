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
+-------------------------------------------------------------+
|                     UNO Q Firmware (spibridge)              |
|  - receives commands                                        |
|  - reads sensor / buffer                                    |
|  - returns structured frame                                 |
|  - sketch.ino/main.py                                       |
+-------------------------------------------------------------+
	 |
	 v
+-------------------------------------------------------------+
|                        User Application                     |
|                  (sketch.ino / loop                         |
+-------------------------------+-----------------------------+
                                |
                                v
+-------------------------------------------------------------+
|                        User Application                     |
|                  (main.py / App.run(loop))                  |
+-------------------------------+-----------------------------+
                                |
                                v
                   +-----------------------+
                   |    Custom Brick       |
                   +-----------+-----------+
                               |
                               |
                               v
+-------------------------------------------------------------+
|                     Python Client (__init__.py)             |
|  - config_speed()                                           |
|  - readBytes()                                              |
|  - readInts()                                               |
|  - readFloats()                                             |
+-------------------------------+-----------------------------+
                                |
                                |  ** HTTP POST/GET **
                                v
+-------------------------------------------------------------+
|                     Flask Server (app.py)                   |
|  - /config/* endpoints                                      |
|  - /read/* endpoints                                        |
|  - calls spihelper                                          |
+-------------------------------+-----------------------------+
                                |
                                |  ** SPI Command (5 bytes) **
                                v
+-------------------------------------------------------------+
|                     SPI Helper (spihelper.py)               |
|  - open spidev                                              |
|  - set mode/speed/bits                                      |
|  - send command                                             |
|  - read header + payload                                    |
|  - parse into arrays                                        |
+-------------------------------+-----------------------------+
```


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

Perfect for SPI development where you frequently adjust parsing logic.  You run watcher its best to load/run the app using the command line versus using AppLab

## **Operation**

### **MCU Side**

The MCU responds to the read command:

```
0x0B 00 00 00 00
```

and returns **1024 bytes** per transaction or what you have specified.  

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

### **POST `/config/config_command`**
Sets the command byte for data type requested

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

### **config_command(cmd_type, command)**
**Description:**  
Updates the 5‑byte SPI read command used by the bridge for a specific data type.

**Arguments:**
```
cmd_type — string, one of "bytes", "floats", or "ints".
```
command — list of 5 integers (0–255), e.g. [0x0B, 0, 0, 0, 0].

**Returns:**

```json
{"status": "ok", "cmd_type": "<cmd_type>", "command": [<byte0>, <byte1>, <byte2>, <byte3>, <byte4>]}
```
**Use when:**
You need to change the SPI read command dynamically without editing the Flask server code.
Each command defines how the MCU responds to read requests for different data formats.

**Example**
```python
# Update the read command for float32 data
spibridge.config_command("floats", [0x0B, 0, 0, 0, 0])
---
```
## **Summary Table**

| Command                               | Purpose                            | Return Type     |
| :------------------------------------ | :--------------------------------- | :-------------- |
| ``readBytes(n)``                      | Read raw bytes as ``uint8`` list   | ``list[int]``   |
| ``readFloats(n)``                     | Read float32 values from SPI       | ``list[float]`` |
| ``readInts(n)``                       | Read int32 values from SPI         | ``list[int]``   |
| ``config_speed(hz)``                  | Set SPI clock speed                | ``dict`` (JSON) |
| ``config_mode(mode)``                 | Set SPI mode (0–3)                 | ``dict`` (JSON) |
| ``config_bits(bits)``                 | Set bits per word                  | ``dict`` (JSON) |
| ``config_bytes_to_read(n)``           | Set SPI read size                  | ``dict`` (JSON) |
| ``config_command(cmd_type, command)`` | Set SPI read command for data type | ``dict`` (JSON) |

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

```text
├── Lidar Test Struct of 5776 Bytes
├── Mixed Data Structure
├── Multiple Data Type Reads
├── Reading Scheduled Data
├── Scheduling with Python Threads
├── Simple Read Bytes
└── Single Data Type Read
```
NOTES
- Max useful bus speed for transferring a lot of data between MCU and MPU seems to be 1Mhz if transferring more than one data type.
- Max number of bytes that you can use seems to be around 2048.
- Remember to change the block size in both the sketch and in python main.py
---

# Appendix: Technical Description
Detailed analysis of the app.py flask interface.

# app.py
In short, this code is an API endpoint that reads raw byte data from a hardware sensor or device via the SPI (Serial Peripheral Interface) bus, ensures it's in the correct format, converts it into a NumPy numerical array, slices it based on a dynamic parameter, and returns it as a JSON response.

---

### Line-by-Line Breakdown

```python
@app.route("/read/bytes")

```

* **What it does:** This is a Flask decorator. It registers the function immediately below it as a route/endpoint.
* **Details:** When a client (like a frontend app or a `curl` request) makes an HTTP GET request to `http://your-server-ip/read/bytes`, Flask will trigger the `readBytes()` function.

```python
def readBytes():

```

* **What it does:** Defines the Python function that handles the logic for the `/read/bytes` endpoint.

```python
    data = spi.read_bytes(read_command=READ_CMD_BYTES, bytes_to_read=BYTES_TO_READ)

```

* **What it does:** Communicates with a hardware peripheral over the SPI bus to read raw data.
* **Details:** It calls a method on an `spi` object (likely from a library like `spidev` or a custom hardware wrapper). It sends a specific command (`READ_CMD_BYTES`) to tell the device *what* to do, and specifies exactly how many bytes to expect back (`BYTES_TO_READ`). The resulting raw data is stored in the `data` variable.

```python
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)

```

* **What it does:** Validates and sanitizes the data type.
* **Details:** Some SPI libraries return data as a standard Python `list` of integers (e.g., `[255, 0, 128]`) instead of actual bytes. This checks if `data` is **not** already a `bytes` or `bytearray` object. If it isn't, `bytes(data)` converts that list of integers into a proper byte string to ensure compatibility with the next step.

```python
    arr = np.frombuffer(data, dtype=np.uint8)

```

* **What it does:** Converts the raw binary data into a NumPy array of 8-bit unsigned integers.
* **Details:** `np.frombuffer` interprets a buffer of data (our bytes) as a 1-dimensional array without copying the data in memory, making it highly efficient. `dtype=np.uint8` specifies that every single byte represents an integer ranging from 0 to 255.

```python
    n = get_n_param(len(arr))

```

* **What it does:** Calculates a dynamic slicing index based on the total number of elements.
* **Details:** It takes the total length of the array (`len(arr)`) and passes it to a helper function named `get_n_param()`. This function likely determines how many of the data points are actually valid or required, returning an integer `n`.

```python
    return jsonify(arr[:n].tolist())

```

* **What it does:** Prepares the data, converts it to JSON, and sends it back to the client.
* **Details:** * `arr[:n]`: Slices the NumPy array, keeping only the elements from the beginning up to index `n`.
* `.tolist()`: NumPy arrays cannot be directly serialized into JSON. This converts the NumPy array back into a standard Python list of numbers.
* `jsonify(...)`: A Flask helper function that turns that Python list into a properly formatted JSON response (e.g., `[23, 45, 89]`) with the correct HTTP `Content-Type: application/json` header.
---

The core difference here is that instead of reading simple 1-byte integers ($\text{uint8}$), this code is reading **32-bit floating-point numbers** (decimal numbers). Because a float requires 4 bytes of memory, the code has to group the incoming raw bytes into blocks of 4 and decode them using Python's `struct` library.

---

### Line-by-Line Breakdown

```python
@app.route("/read/floats")

```

* **What it does:** Registers this function as a Flask route.
* **Details:** When a client hits the `/read/floats` URL, Flask executes the `readFloats()` function.

```python
def readFloats():

```

* **What it does:** Defines the function handling the float-reading logic.

```python
    data = spi.read_bytes(read_command=READ_CMD_FLOATS, bytes_to_read=BYTES_TO_READ)

```

* **What it does:** Pulls raw data from the SPI hardware.
* **Details:** It sends a float-specific command (`READ_CMD_FLOATS`) to the peripheral and requests a predetermined number of bytes (`BYTES_TO_READ`).

```python
    raw_bytes = bytes(data[:BYTES_TO_READ])

```

* **What it does:** Slices the incoming data to the expected limit and forces it into a `bytes` object.
* **Details:** It ensures that even if the SPI read accidentally returned extra data, it strictly cuts it off at `BYTES_TO_READ`. Converting it via `bytes(...)` ensures it is a formal byte string, which is required for the unpacking step coming up.

```python
    count = len(raw_bytes) // 4

```

* **What it does:** Calculates exactly how many floating-point numbers are in the byte stream.
* **Details:** In standard computing (IEEE 754 format), a single-precision float is **4 bytes** (32 bits) long. The floor division operator (`//`) divides the total number of bytes by 4 to figure out how many distinct float values are hidden in that binary block.

```python
    floats = struct.unpack("<" + str(count) + "f", raw_bytes)

```

* **What it does:** Decodes the raw binary data into actual Python float numbers.
* **Details:** This uses Python’s `struct` module to translate binary into numbers. The string `"<" + str(count) + "f"` dynamically builds a **format string**.
* `<` means **Little-Endian** (the byte order commonly used by microcontrollers like Raspberry Pi or Arduino, where the least significant byte comes first).
* `f` stands for **float**.
* If `count` is 10, the format string becomes `"<10f"`, telling Python: *"Interpret these bytes as 10 little-endian floats."* * The result (`floats`) is returned as a Python tuple of decimal numbers.

```python
    n = get_n_param(len(floats))

```

* **What it does:** Determines the dynamic slicing cutoff.
* **Details:** It checks how many total floats were successfully unpacked (`len(floats)`) and passes that total to `get_n_param()` to find out how many elements the client actually needs.

```python
    return jsonify(list(floats[:n]))
```

* **What it does:** Slices the tuple, converts it to a standard list, and sends it back as JSON.
* **Details:** `floats[:n]` keeps only the first `n` decoded numbers. Because `struct.unpack` returns a read-only `tuple`, `list(...)` converts it into a standard mutable list so that Flask's `jsonify()` can seamlessly serialize it into a JSON array response.

---
Unlike the previous two routes which were reading data from the hardware, this route is a **POST** endpoint designed to **write** or change a setting—specifically, the clock speed (frequency in Hertz) of the SPI communication bus.

---

### Line-by-Line Breakdown

```python
@app.route("/config/speed", methods=["POST"])

```

* **What it does:** Registers the function as a Flask route, but restricts it exclusively to HTTP **POST** requests.
* **Details:** POST requests are used when a client wants to send data to the server to update a state or configuration. If a client tries to access `/config/speed` using a regular GET request (like typing it into a browser), Flask will automatically block it and return a `405 Method Not Allowed` error.

```python
def config_speed():

```

* **What it does:** Defines the function that handles the SPI speed configuration logic.

```python
    hz = int(request.json.get("hz"))

```

* **What it does:** Extracts the desired frequency from the incoming JSON payload and converts it into an integer.
* **Details:** * `request.json`: Flask looks at the body of the incoming HTTP request and parses it as JSON.
* `.get("hz")`: It searches the JSON data for a key named `"hz"` (e.g., if the client sent `{"hz": 1000000}`).
* `int(...)`: It forces the value into a standard Python integer. This is a safety measure to ensure that if the client accidentally sent the speed as a string (like `"1000000"`), it gets properly converted to a number so the hardware library can understand it.

```python
    spi.set_speed(hz)

```

* **What it does:** Physically changes the clock speed of the SPI hardware bus.
* **Details:** It calls a method on the `spi` object, passing the integer frequency (`hz`). This directly changes how fast the master device (e.g., your Raspberry Pi) toggles the SCLK (Serial Clock) line when talking to the peripheral. Higher numbers mean faster data transfers, up to the maximum limit supported by your hardware.

```python
    return jsonify({"status": "ok", "speed": hz})
```

* **What it does:** Sends a confirmation response back to the client in JSON format.
* **Details:** It wraps a Python dictionary into a JSON object. Returning `{"status": "ok", "speed": 1000000}` lets the client know that the operation was successful and echoes back the exact speed that was successfully applied.

---
First, let's address your critical question: **Is it correct to change all 5 bytes this way?**

**No, there is a subtle but breaking bug in how this code handles updating the bytes.** Because of the validation check (`len(new_bytes) > 5`), the code allows the user to send a list that is shorter than 5 bytes (e.g., a list of 2 bytes: `[0x01, 0x02]`).

However, in **Step 4**, the loop *only* overwrites the first 2 positions of `target_array`. The remaining 3 bytes of the old command will linger in the array untouched. If your hardware expects a specific packet length or padding, leaving old, stale bytes at the end of the array will cause corrupted commands to be sent to your SPI device.

To fix this, if a user sends fewer than 5 bytes, you should explicitly overwrite or clear out the remaining positions (e.g., padding them with `0x00`), or simply assign the new list directly if the hardware doesn't strictly require a fixed 5-byte array.

---

This route is a **POST** endpoint designed to **write** or change a setting—specifically, the READ COMMAND for Bytes, Float or Ints.

### Line-by-Line Breakdown

Here is exactly what the code is doing, section by section.

```python
@app.route("/config/cmd/<cmd_type>", methods=["POST"])

```

* **What it does:** Registers a dynamic POST endpoint.
* **Details:** The `<cmd_type>` part is a **URL variable**. This means a client can send a POST request to `/config/cmd/bytes`, `/config/cmd/floats`, or `/config/cmd/ints`, and Flask will pass whatever string is in that position into the function as the `cmd_type` argument.

```python
def config_command(cmd_type):
    global READ_CMD_BYTES, READ_CMD_FLOATS, READ_CMD_INTS

```

* **What it does:** Defines the function and declares global scope access.
* **Details:** The `global` keyword tells Python that when we modify `READ_CMD_BYTES`, `READ_CMD_FLOATS`, or `READ_CMD_INTS` inside this function, we want to alter the actual global variables defined at the top of the entire script, rather than creating temporary, local variables.

```python
    # 1. Validate the command type
    if cmd_type not in ["bytes", "floats", "ints"]:
        return jsonify({"error": "Invalid command type. Choose bytes, floats, or ints."}), 400

```

* **What it does:** Acts as a gatekeeper for the URL variable.
* **Details:** It ensures the user typed a valid endpoint. If someone hits `/config/cmd/strings`, it catches it immediately, stops execution, and sends back a `400 Bad Request` error.

```python
    # 2. Extract the new bytes list from the JSON payload
    new_bytes = request.json.get("command")

```

* **What it does:** Extracts the payload data.
* **Details:** It looks inside the incoming JSON body for a key named `"command"` (e.g., `{"command": [10, 20, 30]}`).

```python
    if not isinstance(new_bytes, list) or len(new_bytes) == 0 or len(new_bytes) > 5:
        return jsonify({"error": "Command must be a list containing between 1 and 5 integers."}), 400

```

* **What it does:** Validates the structure and length of the incoming data.
* **Details:** It throws a `400` error if the payload isn't a list, if it's completely empty, or if it contains more than 5 elements.

```python
    # Validate that every item in the list is a valid byte (0-255)
    if not all(isinstance(b, int) and 0 <= b <= 255 for b in new_bytes):
        return jsonify({"error": "All values in the list must be integers between 0 and 255."}), 400

```

* **What it does:** Sanitizes the actual values inside the list.
* **Details:** A byte can only hold a value from 0 to 255. This uses a Python list comprehension coupled with `all()` to verify that every single item provided is both an integer *and* fits within valid 8-bit byte boundaries. If a user tries to send `256` or `-1`, it rejects it.

```python
    # 3. Select the target global array to update
    if cmd_type == "bytes":
        target_array = READ_CMD_BYTES
    elif cmd_type == "floats":
        target_array = READ_CMD_FLOATS
    elif cmd_type == "ints":
        target_array = READ_CMD_INTS

```

* **What it does:** Maps the URL text to the actual physical variable in memory.
* **Details:** Depending on what the user typed in the URL, Python creates a reference pointer called `target_array` that points directly to one of the three global lists/arrays.

```python
    # 4. Dynamically update the bytes
    for i, byte_value in enumerate(new_bytes):
        target_array[i] = byte_value

```

* **What it does:** Overwrites the elements in the target global array.
* **Details:** `enumerate(new_bytes)` loops through the user's data, providing both the index (`i`) and the value (`byte_value`). It modifies `target_array` in-place. *(As noted above, if `new_bytes` only has 2 items, only indices `0` and `1` get updated; indices `2`, `3`, and `4` retain whatever garbage data was previously stored there).*

```python
    return jsonify({
        "status": "ok", 
        "updated": cmd_type, 
        "full_current_command": target_array
    })

```

* **What it does:** Responds back to the user with a confirmation payload showing the updated state of the entire array.

---

