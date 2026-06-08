# SPI Bridge  (DRAFT)

See: https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568

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

