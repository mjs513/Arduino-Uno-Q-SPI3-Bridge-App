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

WRITE_CMD_BYTES  = [0x0A, 0x00, 0x00, 0x00, 0x00]
WRITE_CMD_FLOATS = [0x0B, 0x00, 0x00, 0x00, 0x00]
WRITE_CMD_INTS   = [0x0C, 0x00, 0x00, 0x00, 0x00]
WRITE_CMD_STRUCT = [0x0D, 0x00, 0x00, 0x00, 0x00]
WRITE_CMD_STRUCT_ARRAY = [0x0E,  0x00, 0x00, 0x00, 0x00]
WRITE_CMD_STRUCT_ARRAYFIELDS = [0x0F,  0x00, 0x00, 0x00, 0x00]


def apply_length_to_command(cmd, payload):
    length = len(payload)
    cmd = list(cmd)  # copy
    cmd[3] = length & 0xFF        # LEN_L
    cmd[4] = (length >> 8) & 0xFF # LEN_H
    return cmd


#=======================================
#   Helper function for Stuctures
# =======================================

STRUCT_FORMAT_MAP = {
    "u8":  "B",
    "i8":  "b",
    "u16": "H",
    "i16": "h",
    "u32": "I",
    "i32": "i",
    "f32": "f"
}

def pack_struct(fmt_list, values):
    if len(fmt_list) != len(values):
        raise ValueError("Format and values length mismatch")

    struct_fmt = "<" + "".join(STRUCT_FORMAT_MAP[f] for f in fmt_list)
    return struct.pack(struct_fmt, *values)

def pack_array(type_name, values):
    fmt = STRUCT_FORMAT_MAP[type_name]
    struct_fmt = "<" + fmt * len(values)
    return struct.pack(struct_fmt, *values)


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

# ======================================
#  Write Endpoints
# ======================================
@app.route("/write/bytes", methods=["POST"])
def writeBytes():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        payload = request.json.get("payload")

        if not isinstance(payload, list) or not all(isinstance(b, int) and 0 <= b <= 255 for b in payload):
            return jsonify({"error": "Payload must be a list of integers 0–255"}), 400

        print("WRITE /write/bytes payload:", payload, flush=True)
        # apply data packet length to last 2 bytes
        cmd = apply_length_to_command(WRITE_CMD_BYTES, payload)
        spi.write_bytes(write_command=cmd, payload=bytes(payload))

        return jsonify({"status": "ok", "written": len(payload)})

    except Exception as e:
        print("ERROR in /write/bytes:", e, flush=True)
        return jsonify({"error": str(e)}), 500

# --------------------------------
# Write Floats
# ---------------------------------
@app.route("/write/floats", methods=["POST"])
def writeFloats():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        payload = request.json.get("payload")

        # Validate: list of floats or ints
        if not isinstance(payload, list) or not all(isinstance(x, (int, float)) for x in payload):
            return jsonify({"error": "Payload must be a list of numbers"}), 400

        print("WRITE /write/floats payload:", payload, flush=True)

        # Pack as float32 LE
        raw = b"".join(struct.pack("<f", float(x)) for x in payload)

        # apply data packet length to last 2 bytes
        cmd = apply_length_to_command(WRITE_CMD_FLOATS, raw)
        spi.write_bytes(write_command=cmd, payload=raw)

        return jsonify({"status": "ok", "written": len(payload)})

    except Exception as e:
        print("ERROR in /write/floats:", e, flush=True)
        return jsonify({"error": str(e)}), 500


# ------------------------------------
# Write Ints
# -------------------------------------
@app.route("/write/ints", methods=["POST"])
def writeInts():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        payload = request.json.get("payload")

        # Validate: list of ints
        if not isinstance(payload, list) or not all(isinstance(x, int) for x in payload):
            return jsonify({"error": "Payload must be a list of integers"}), 400

        print("WRITE /write/ints payload:", payload, flush=True)

        # Pack as int32 LE
        raw = b"".join(struct.pack("<i", x) for x in payload)
        # apply data packet length to last 2 bytes
        cmd = apply_length_to_command(WRITE_CMD_INTS, raw)
        spi.write_bytes(write_command=cmd, payload=raw)

        return jsonify({"status": "ok", "written": len(payload)})

    except Exception as e:
        print("ERROR in /write/ints:", e, flush=True)
        return jsonify({"error": str(e)}), 500

#-------------------------------------
# write stuct
# -------------------------------------
@app.route("/write/struct", methods=["POST"])
def writeStruct():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        fmt = request.json.get("format")
        vals = request.json.get("values")

        # Validate format
        if not isinstance(fmt, list) or not all(f in STRUCT_FORMAT_MAP for f in fmt):
            return jsonify({"error": "Invalid format list"}), 400

        # Validate values
        if not isinstance(vals, list) or len(vals) != len(fmt):
            return jsonify({"error": "Values must match format length"}), 400

        print("WRITE /write/struct:", fmt, vals, flush=True)

        # Pack into bytes
        raw = pack_struct(fmt, vals)
        # apply data packet length to last 2 bytes
        cmd = apply_length_to_command(WRITE_CMD_STRUCT, raw)
        # Send via SPI
        spi.write_bytes(write_command=WRITE_CMD_STRUCT, payload=raw)

        return jsonify({
            "status": "ok",
            "written_fields": len(vals),
            "bytes_sent": len(raw)
        })

    except Exception as e:
        print("ERROR in /write/struct:", e, flush=True)
        return jsonify({"error": str(e)}), 500

# --------------------------------------
# Write Structure Arrays
# ---------------------------------------
@app.route("/write/structs", methods=["POST"])
def writeStructs():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        structs = request.json.get("structs")

        if not isinstance(structs, list) or len(structs) == 0:
            return jsonify({"error": "Expected a non-empty list of structs"}), 400

        full_payload = b""

        for idx, s in enumerate(structs):
            fmt = s.get("format")
            vals = s.get("values")

            if not isinstance(fmt, list) or not all(f in STRUCT_FORMAT_MAP for f in fmt):
                return jsonify({"error": f"Invalid format in struct #{idx}"}), 400

            if not isinstance(vals, list) or len(vals) != len(fmt):
                return jsonify({"error": f"Values mismatch in struct #{idx}"}), 400

            packed = pack_struct(fmt, vals)
            full_payload += packed

        # APPLY LENGTH TO COMMAND
        cmd = apply_length_to_command(WRITE_CMD_STRUCT_ARRAY, full_payload)

        # SEND THE UPDATED COMMAND (NOT THE ORIGINAL)
        spi.write_bytes(write_command=cmd, payload=full_payload)

        return jsonify({
            "status": "ok",
            "struct_count": len(structs),
            "bytes_sent": len(full_payload)
        })

    except Exception as e:
        print("ERROR in /write/structs:", e, flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/write/struct_arrayfields", methods=["POST"])
def writeStructArrayFields():
    try:
        if not request.is_json:
            return jsonify({"error": "Expected JSON body"}), 400

        fmt = request.json.get("format")
        vals = request.json.get("values")

        if not isinstance(fmt, dict) or not isinstance(vals, dict):
            return jsonify({"error": "Format and values must be objects"}), 400

        full_payload = b""

        for field_name, field_fmt in fmt.items():
            type_name = field_fmt.get("type")
            count     = field_fmt.get("count")

            if type_name not in STRUCT_FORMAT_MAP:
                return jsonify({"error": f"Invalid type for field {field_name}"}), 400

            if not isinstance(count, int) or count <= 0:
                return jsonify({"error": f"Invalid count for field {field_name}"}), 400

            field_vals = vals.get(field_name)

            if not isinstance(field_vals, list) or len(field_vals) != count:
                return jsonify({"error": f"Field {field_name} must have {count} values"}), 400

            # Pack this array
            full_payload += pack_array(type_name, field_vals)

        # APPLY LENGTH TO COMMAND
        cmd = apply_length_to_command(WRITE_CMD_STRUCT_ARRAYFIELDS, full_payload)

        # SEND UPDATED COMMAND
        spi.write_bytes(write_command=cmd, payload=full_payload)

        return jsonify({
            "status": "ok",
            "bytes_sent": len(full_payload)
        })

    except Exception as e:
        print("ERROR in /write/struct_arrayfields:", e, flush=True)
        return jsonify({"error": str(e)}), 500




# ======================================
#  Config Endpoints
# ======================================

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

    # 4. Dynamically update the bytes and clear out the rest
    for i in range(5):
        if i < len(new_bytes):
            target_array[i] = new_bytes[i]
        else:
            target_array[i] = 0x00  # Clear out old bytes with zeros

    return jsonify({
        "status": "ok", 
        "updated": cmd_type, 
        "full_current_command": target_array
    })

@app.route("/config/writecmd/<cmd_type>", methods=["POST"])
def config_write_command(cmd_type):
    global WRITE_CMD_BYTES, WRITE_CMD_FLOATS, WRITE_CMD_INTS

    # 1. Validate type
    if cmd_type not in ["bytes", "floats", "ints"]:
        return jsonify({"error": "Invalid command type. Choose bytes, floats, or ints."}), 400

    # 2. Extract payload
    new_bytes = request.json.get("command")

    if not isinstance(new_bytes, list) or len(new_bytes) == 0 or len(new_bytes) > 5:
        return jsonify({"error": "Command must be a list containing between 1 and 5 integers."}), 400

    if not all(isinstance(b, int) and 0 <= b <= 255 for b in new_bytes):
        return jsonify({"error": "All values must be integers 0–255."}), 400

    # 3. Select target array
    if cmd_type == "bytes":
        target_array = WRITE_CMD_BYTES
    elif cmd_type == "floats":
        target_array = WRITE_CMD_FLOATS
    elif cmd_type == "ints":
        target_array = WRITE_CMD_INTS

    # 4. Update in-place, pad with zeros
    for i in range(5):
        if i < len(new_bytes):
            target_array[i] = new_bytes[i]
        else:
            target_array[i] = 0x00

    return jsonify({
        "status": "ok",
        "updated": cmd_type,
        "full_current_command": target_array
    })




