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

# **Write Commands**

These commands send structured or unstructured data **from Python → MCU** through the SPI Bridge.  
All write endpoints automatically:

- validate JSON input  
- pack values into binary  
- apply the **length prefix** to the last 2 bytes of the write command  
- transmit via `spi.write_bytes()`  

---

## **`writeBytes(data)`**
**Description:**  
Sends a list of raw byte values (0–255) to the MCU.

**Arguments:**  
- `data` — list of integers (`0–255`)

**Returns:**  
```json
{"status": "ok", "written": <len(data)>}
```

**Use when:**  
You need to send arbitrary byte sequences, command frames, or protocol packets.

**Example:**
```python
spibridge.writeBytes([0xA5, 0x5A, 0x01, 0x00])
```

---

## **`writeFloats(data)`**
**Description:**  
Sends a list of float32 values encoded as **little‑endian IEEE‑754**.

**Arguments:**  
- `data` — list of floats or ints

**Returns:**  
```json
{"status": "ok", "written": <len(data)>}
```

**Use when:**  
Sending calibration values, PID gains, or float‑based telemetry.

**Example:**
```python
spibridge.writeFloats([1.0, 3.14, -2.5])
```

---

## **`writeInts(data)`**
**Description:**  
Sends a list of int32 values encoded as **little‑endian signed 32‑bit integers**.

**Arguments:**  
- `data` — list of Python integers

**Returns:**  
```json
{"status": "ok", "written": <len(data)>}
```

**Use when:**  
Sending counters, timestamps, fixed‑point values, or integer‑based structures.

**Example:**
```python
spibridge.writeInts([100, -1, 2048])
```

---

# **Structured Write Commands**

These commands let you send **binary‑packed structs** and **arrays of structs** using a declarative JSON format.

Your Flask server uses:

- `STRUCT_FORMAT_MAP`  
- `pack_struct(fmt, vals)`  
- `pack_array(type, values)`  

to convert JSON → binary.

---

## **`writeStruct(format, values)`**
**Description:**  
Packs a **single struct** using a list of field types and values, then sends it to the MCU.

**Arguments:**  
- `format` — list of type codes (must exist in `STRUCT_FORMAT_MAP`)  
- `values` — list of values matching the format length  

**Returns:**  
```json
{
  "status": "ok",
  "written_fields": <count>,
  "bytes_sent": <payload_size>
}
```

**Use when:**  
You need to send a single structured packet (e.g., a config struct, pose struct, sensor struct).

**Example:**
```python
spibridge.writeStruct(
    format=["u16", "f32", "i32"],
    values=[42, 3.14, -100]
)
```

---

## **`writeStructs(structs)`**
**Description:**  
Sends an **array of structs**, each with its own `format` and `values`.  
All structs are packed sequentially into one binary payload.

**Arguments:**  
- `structs` — list of objects, each containing:  
  - `format`: list of type codes  
  - `values`: list of values  

**Returns:**  
```json
{
  "status": "ok",
  "struct_count": <n>,
  "bytes_sent": <payload_size>
}
```

**Use when:**  
You need to send a batch of structs — e.g., multiple sensor readings, multiple control frames, or a table of configuration entries.

**Example:**
```python
spibridge.writeStructs([
    {"format": ["u8", "u8"], "values": [1, 2]},
    {"format": ["f32", "f32"], "values": [3.14, 2.71]},
    {"format": ["i32"], "values": [-42]}
])
```

---

## **`writeStructArrayFields(format, values)`**
**Description:**  
Sends a **struct-of-arrays** layout:  
Each field has:

- a type (`u8`, `i32`, `f32`, etc.)  
- a count  
- an array of values  

The server packs each array sequentially.

**Arguments:**  
- `format` — dict describing each field’s type + count  
- `values` — dict containing arrays for each field  

**Returns:**  
```json
{
  "status": "ok",
  "bytes_sent": <payload_size>
}
```

**Use when:**  
You want to send **parallel arrays** instead of array‑of‑structs.  
Useful for bulk sensor data, vector fields, or large numeric arrays.

**Example:**
```python
spibridge.writeStructArrayFields(
    format={
        "x": {"type": "f32", "count": 3},
        "y": {"type": "f32", "count": 3},
        "id": {"type": "u16", "count": 3}
    },
    values={
        "x": [1.0, 2.0, 3.0],
        "y": [4.0, 5.0, 6.0],
        "id": [10, 11, 12]
    }
)
```

---

# **Write Command Summary Table**

| Command                                   | Purpose                                  | Input Type                     | Return Type     |
|-------------------------------------------|-------------------------------------------|--------------------------------|-----------------|
| `writeBytes(data)`                        | Send raw bytes                            | `list[int]`                    | `dict` (JSON)   |
| `writeInts(data)`                         | Send int32 values (LE)                    | `list[int]`                    | `dict` (JSON)   |
| `writeFloats(data)`                       | Send float32 values (LE)                  | `list[float]`                  | `dict` (JSON)   |
| `writeStruct(format, values)`             | Send one packed struct                    | `list[str]`, `list[*]`         | `dict` (JSON)   |
| `writeStructs(structs)`                   | Send array of packed structs              | `list[{format, values}]`       | `dict` (JSON)   |
| `writeStructArrayFields(fmt, vals)`       | Send struct‑of‑arrays payload             | `dict`, `dict`                 | `dict` (JSON)   |
| `config_write_command(type, command)`     | Set write opcode for data type            | `list[int]` (1–5 bytes)        | `dict` (JSON)   |

---

Absolutely, Michael — here is a **clean, visual, README‑ready diagram** that explains **how struct packing works** in your SPI Bridge. It’s designed to match the tone and formatting of the rest of your documentation and to be immediately understandable to anyone reading the API reference.

No images needed — this is a pure ASCII diagram that renders perfectly on GitHub.

---

# **📦 How Struct Packing Works**

The SPI Bridge converts JSON‑described structs into a **binary payload** using your `STRUCT_FORMAT_MAP` and the helper functions `pack_struct()` and `pack_array()`.

Below is a visual explanation of how a struct is transformed from:

- JSON →  
- typed fields →  
- binary layout →  
- final SPI payload

---

## **1. Input JSON (Python → Flask)**

```json
{
  "format": ["u16", "f32", "i32"],
  "values": [42, 3.14, -100]
}
```

---

## **2. Format Resolution**

Each format token maps to a binary type:

| Token | Meaning            | Size | Encoding |
|------|--------------------|------|----------|
| `u16` | Unsigned 16‑bit    | 2 B  | Little‑endian |
| `f32` | Float32            | 4 B  | IEEE‑754 LE |
| `i32` | Signed 32‑bit int  | 4 B  | Little‑endian |

---

## **3. Field‑by‑Field Packing**

```
┌───────────────┬───────────────┬────────────────┐
│   u16 (42)     │   f32 (3.14)   │   i32 (-100)   │
├───────────────┼───────────────┼────────────────┤
│ 2 bytes        │ 4 bytes        │ 4 bytes        │
└───────────────┴───────────────┴────────────────┘
```

### **Binary Breakdown**

```
u16 42      →  2A 00
f32 3.14    →  C3 F5 48 40
i32 -100    →  9C FF FF FF
```

---

## **4. Final Packed Struct Payload**

```
2A 00 | C3 F5 48 40 | 9C FF FF FF
```

Or as a continuous byte stream:

```
2A 00 C3 F5 48 40 9C FF FF FF
```

Total size: **10 bytes**

---

## **5. SPI Write Command Assembly**

Before sending, the bridge updates the last 2 bytes of the write command with the payload length:

```
WRITE_CMD_STRUCT = [0x0E, 0x00, 0x00, 0x00, 0x00]

apply_length_to_command(..., payload=10 bytes)
→ last two bytes become: 0x0A 0x00
```

### **Final SPI Transaction**

```
Write Command: 0E 00 00 0A 00
Payload:       2A 00 C3 F5 48 40 9C FF FF FF
```

---

# **📘 Full Diagram (Combined)**

```
JSON Input
──────────
{
  "format": ["u16", "f32", "i32"],
  "values": [42, 3.14, -100]
}

        │
        ▼

Format Resolution
─────────────────
u16 → 2 bytes LE
f32 → 4 bytes LE
i32 → 4 bytes LE

        │
        ▼

Binary Packing
──────────────
42      → 2A 00
3.14    → C3 F5 48 40
-100    → 9C FF FF FF

        │
        ▼

Final Payload (10 bytes)
────────────────────────
2A 00 C3 F5 48 40 9C FF FF FF

        │
        ▼

Write Command Length Patch
──────────────────────────
WRITE_CMD_STRUCT = 0E 00 00 00 00
Length = 10 bytes → 0A 00

Final Command = 0E 00 00 0A 00

        │
        ▼

SPI Transaction
───────────────
CMD:     0E 00 00 0A 00
PAYLOAD: 2A 00 C3 F5 48 40 9C FF FF FF
```

---

Here you go, Michael — **two clean, GitHub‑ready diagrams** that visually explain:

1. **writeStructs** → *array‑of‑structs*  
2. **writeStructArrayFields** → *struct‑of‑arrays*

Both diagrams match the style of the earlier struct‑packing diagram so they drop directly into your README without friction.

---

# **📦 Diagram: `writeStructs` (Array‑of‑Structs)**  
### *Multiple structs, each with their own format + values, packed sequentially*

This mode is **AoS (Array‑of‑Structs)**:

```
struct[0] → packed
struct[1] → packed
struct[2] → packed
...
```

---

## **1. Input JSON**

```json
{
  "structs": [
    { "format": ["u8", "u8"], "values": [1, 2] },
    { "format": ["f32", "f32"], "values": [3.14, 2.71] },
    { "format": ["i32"], "values": [-42] }
  ]
}
```

---

## **2. Per‑Struct Packing**

### **Struct #0**
```
Format: [u8, u8]
Values: [1, 2]

u8 1 → 01
u8 2 → 02

Packed: 01 02
```

### **Struct #1**
```
Format: [f32, f32]
Values: [3.14, 2.71]

3.14 → C3 F5 48 40
2.71 → 8F C2 2D 40

Packed: C3 F5 48 40 8F C2 2D 40
```

### **Struct #2**
```
Format: [i32]
Values: [-42]

-42 → D6 FF FF FF

Packed: D6 FF FF FF
```

---

## **3. Final Payload (Concatenated)**

```
01 02
C3 F5 48 40 8F C2 2D 40
D6 FF FF FF
```

As a continuous stream:

```
01 02 C3 F5 48 40 8F C2 2D 40 D6 FF FF FF
```

Total size: **2 + 8 + 4 = 14 bytes**

---

## **4. SPI Transaction**

```
WRITE_CMD_STRUCT_ARRAY = [0x0E, 00, 00, 00, 00]

Length = 14 bytes → 0E 00

Final Command: 0E 00 00 0E 00
Payload:       01 02 C3 F5 48 40 8F C2 2D 40 D6 FF FF FF
```

---

# **📦 Diagram: `writeStructArrayFields` (Struct‑of‑Arrays)**  
### *Each field is an array; all arrays are packed in field order*

This mode is **SoA (Struct‑of‑Arrays)**:

```
x[] → packed
y[] → packed
id[] → packed
```

---

## **1. Input JSON**

```json
{
  "format": {
    "x":  { "type": "f32", "count": 3 },
    "y":  { "type": "f32", "count": 3 },
    "id": { "type": "u16", "count": 3 }
  },
  "values": {
    "x":  [1.0, 2.0, 3.0],
    "y":  [4.0, 5.0, 6.0],
    "id": [10, 11, 12]
  }
}
```

---

## **2. Field‑by‑Field Packing**

### **Field: x (3 × f32)**

```
1.0 → 00 00 80 3F
2.0 → 00 00 00 40
3.0 → 00 00 40 40

Packed x[]:
00 00 80 3F 00 00 00 40 00 00 40 40
```

### **Field: y (3 × f32)**

```
4.0 → 00 00 80 40
5.0 → 00 00 A0 40
6.0 → 00 00 C0 40

Packed y[]:
00 00 80 40 00 00 A0 40 00 00 C0 40
```

### **Field: id (3 × u16)**

```
10 → 0A 00
11 → 0B 00
12 → 0C 00

Packed id[]:
0A 00 0B 00 0C 00
```

---

## **3. Final Payload (Concatenated)**

```
x[]  → 00 00 80 3F 00 00 00 40 00 00 40 40
y[]  → 00 00 80 40 00 00 A0 40 00 00 C0 40
id[] → 0A 00 0B 00 0C 00
```

As a continuous stream:

```
00 00 80 3F 00 00 00 40 00 00 40 40
00 00 80 40 00 00 A0 40 00 00 C0 40
0A 00 0B 00 0C 00
```

Total size: **12 + 12 + 6 = 30 bytes**

---

## **4. SPI Transaction**

```
WRITE_CMD_STRUCT_ARRAYFIELDS = [0x0F, 00, 00, 00, 00]

Length = 30 bytes → 1E 00

Final Command: 0F 00 00 1E 00
Payload:       <30‑byte concatenated array>
```

---

# **📘 Summary: AoS vs SoA**

```
Array‑of‑Structs (writeStructs)
───────────────────────────────
[ {fmt, vals}, {fmt, vals}, ... ]

struct0: [fields...] → packed
struct1: [fields...] → packed
struct2: [fields...] → packed
...
Concatenate all structs


Struct‑of‑Arrays (writeStructArrayFields)
─────────────────────────────────────────
{
  x: [x0, x1, x2...],
  y: [y0, y1, y2...],
  id: [id0, id1, id2...]
}

Pack x[] → Pack y[] → Pack id[]
Concatenate all arrays
```

---

