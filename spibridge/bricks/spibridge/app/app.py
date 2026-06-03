# See: https://flask.palletsprojects.com/en/stable/quickstart/#a-minimal-application
import struct

import spihelper
from flask import Flask, request, jsonify

app = Flask(__name__)

spi = spihelper.SPIBridge()
spi.init_spi()

BYTES_TO_READ = 1024

# -----------------------------
# READ: BYTES
# -----------------------------
@app.route("/read/bytes")
def readBytes():
    read_cmd = [0x0B, 0, 0, 0, 0]
    data = spi.read_bytes(read_command=read_cmd, bytes_to_read=BYTES_TO_READ)

    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        lines.append(chunk.hex(" "))

    return {"hex": "\n".join(lines)}

# -----------------------------
# READ: FLOATS
# -----------------------------
@app.route("/read/floats")
def readFloats():
    # Source: https://forum.arduino.cc/t/how-to-install-python-packages-on-the-arduino-q/1434480/7
    read_cmd = [0x0B, 0x00, 0x00, 0x00, 0x00]
    data = spi.read_bytes(read_command=read_cmd, bytes_to_read=BYTES_TO_READ)
    raw_bytes = bytes(data[:1024])

    count = len(raw_bytes) // 4
    fmt = "<" + str(count) + "f"

    floats = struct.unpack(fmt, raw_bytes)
    formatted_data = ", ".join(f"{v:.4f}" for v in floats)

    return formatted_data

# -----------------------------
# READ: INTEGERS
# -----------------------------
@app.route("/read/ints")
def readInts():
    read_cmd = [0x0B, 0, 0, 0, 0]

    # Read 1024 bytes from SPI
    data = spi.read_bytes(read_command=read_cmd, bytes_to_read=BYTES_TO_READ)

    # Use ALL returned bytes (Arduino starts payload at index 0)
    raw_bytes = data

    # Only decode full int32 values
    count = len(raw_bytes) // 4
    raw_bytes = raw_bytes[:count * 4]

    # Little-endian int32
    fmt = "<" + str(count) + "i"
    ints = struct.unpack(fmt, raw_bytes)

    # Return as comma-separated text
    #return ", ".join(str(v) for v in ints)
    return {"hex": " ".join(lines)}


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








