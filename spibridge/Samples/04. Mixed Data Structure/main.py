import time
import numpy as np
import spibridge
import struct
from arduino.app_utils import App

print(spibridge.config_speed(1000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(2048))

def loop():
    # -------------------------
    # READ FLOATS (0x0C)
    # -------------------------
    # Get Read Type for processing in Arduino Sketch
    spibridge.readBytes(n=5)
    data = spibridge.readBytes(n=1024)

    # Byte length is caluculated from the struct
    # ints = 4 bytes, floats are 4 bytes
    raw = bytes(data[:28])  # exact struct size

    fmt = "<Iff4i"
    timestamp, temp, hum, r0, r1, r2, r3 = struct.unpack(fmt, raw)

    print("\n=== SENSOR FRAME ===")
    print(f"{'timestamp':<12}: {timestamp}")
    print(f"{'temp (°C)':<12}: {temp:.2f}")
    print(f"{'hum (%)':<12}: {hum:.2f}")
    print(f"{'r0':<12}: {r0}")
    print(f"{'r1':<12}: {r1}")
    print(f"{'r2':<12}: {r2}")
    print(f"{'r3':<12}: {r3}")
    print("====================\n")

    time.sleep(0.005)


App.run(user_loop=loop)