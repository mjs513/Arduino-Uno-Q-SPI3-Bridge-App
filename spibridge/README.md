# SPI Bridge  (DRAFT)

See: https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568

# Technical Description
```

+-------------------------------------------------------------+
|                     UNO Q Firmware (spibridge)              |
|  - receives commands                                        |
|  - reads sensor / buffer                                    |
|  - returns structured frame                                 |
|  - sketch.ino/main.py                                       |
+-------------------------------------------------------------+
	 |
	 |
+-----------------------+
|    Custom Brick       |
+-----------+-----------+
      |
			|
+-------------------------------------------------------------+
|                        User Application                     |
|                  (main.py / App.run(loop))                  |
+-------------------------------+-----------------------------+
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

