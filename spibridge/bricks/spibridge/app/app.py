# See: https://flask.palletsprojects.com/en/stable/quickstart/#a-minimal-application
import struct
import numpy as np
import spihelper
from flask import Flask, request, jsonify

app = Flask(__name__)

spi = spihelper.SPIBridge()
spi.init_spi()

BYTES_TO_READ = 1024
READ_CMD_INTS = [0x0C, 0x00, 0x00, 0x00, 0x00]
READ_CMD_BYTES = [0x0A, 0x00,0x000, 0x00, 0x00]
READ_CMD_FLOATS = [0x0B, 0x00, 0x00,0x000, 0x00]


# ----------------------------------------------
#
# Helper function to get n-values from bytes,
# floats or ints.  N will be different for each
# 1. for Bytes it will by the number of bytes to return
# 2. for Ints and Floats it will be the number of
#     ints or floats to return
#
# ------------------------------------------------
def get_n_param(default):
    try:
        n = int(request.args.get("n", default))
        return max(0, n)
    except:
        return default

# -----------------------------
# READ: BYTES
# -----------------------------
@app.route("/read/bytes")
def readBytes():
    data = spi.read_bytes(read_command=READ_CMD_BYTES, bytes_to_read=BYTES_TO_READ)

    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)

    arr = np.frombuffer(data, dtype=np.uint8)
    n = get_n_param(len(arr))
    return jsonify(arr[:n].tolist())


    
# -----------------------------
# READ: FLOATS
# -----------------------------
@app.route("/read/floats")
def readFloats():
    data = spi.read_bytes(read_command=READ_CMD_FLOATS, bytes_to_read=BYTES_TO_READ)

    raw_bytes = bytes(data[:BYTES_TO_READ])
    count = len(raw_bytes) // 4

    floats = struct.unpack("<" + str(count) + "f", raw_bytes)
    n = get_n_param(len(floats))
    return jsonify(list(floats[:n]))



# -----------------------------
# READ: INTEGERS
# -----------------------------
@app.route("/read/ints")
def readInts():
    data = spi.read_bytes(read_command=READ_CMD_INTS, bytes_to_read=BYTES_TO_READ)

    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)

    count = len(data) // 4
    raw_bytes = data[:count * 4]

    arr = np.frombuffer(raw_bytes, dtype='<i4')
    n = get_n_param(len(arr))
    return jsonify(arr[:n].tolist())

@app.route("/config/speed", methods=["POST"])
def config_speed():
    hz = int(request.json.get("hz"))
    spi.set_speed(hz)
    return jsonify({"status": "ok", "speed": hz})

@app.route("/config/mode", methods=["POST"])
def config_mode():
    mode = int(request.json.get("mode"))
    spi.set_mode(mode)
    return jsonify({"status": "ok", "mode": mode})

@app.route("/config/bits", methods=["POST"])
def config_bits():
    bits = int(request.json.get("bits"))
    spi.set_bits(bits)
    return jsonify({"status": "ok", "bits": bits})


@app.route("/config/bytes", methods=["POST"])
def config_bytes():
    global BYTES_TO_READ
    BYTES_TO_READ = int(request.json.get("bytes"))
    return jsonify({"status": "ok", "bytes": BYTES_TO_READ})

@app.route("/config/cmd/<cmd_type>", methods=["POST"])
def config_command(cmd_type):
    global READ_CMD_BYTES, READ_CMD_FLOATS, READ_CMD_INTS
    
    # 1. Validate the command type
    if cmd_type not in ["bytes", "floats", "ints"]:
        return jsonify({"error": "Invalid command type. Choose bytes, floats, or ints."}), 400
        
    # 2. Extract the new bytes list from the JSON payload
    new_bytes = request.json.get("command")
    
    if not isinstance(new_bytes, list) or len(new_bytes) == 0 or len(new_bytes) > 5:
        return jsonify({"error": "Command must be a list containing between 1 and 5 integers."}), 400

    # Validate that every item in the list is a valid byte (0-255)
    if not all(isinstance(b, int) and 0 <= b <= 255 for b in new_bytes):
        return jsonify({"error": "All values in the list must be integers between 0 and 255."}), 400

    # 3. Select the target global array to update
    if cmd_type == "bytes":
        target_array = READ_CMD_BYTES
    elif cmd_type == "floats":
        target_array = READ_CMD_FLOATS
    elif cmd_type == "ints":
        target_array = READ_CMD_INTS

    # 4. Dynamically update the bytes
    # This loops through whatever you sent (1 to 5 bytes) and updates those specific positions
    for i, byte_value in enumerate(new_bytes):
        target_array[i] = byte_value

    return jsonify({
        "status": "ok", 
        "updated": cmd_type, 
        "full_current_command": target_array
    })





