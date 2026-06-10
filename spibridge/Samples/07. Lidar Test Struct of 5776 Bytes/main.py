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
    # Get Integer data in 3 blocks
    # Read first block
    block1 = spibridge.readBytes(n=2048)
    time.sleep(0.003)

    block2 = spibridge.readBytes(n=2048)
    time.sleep(0.003)

    # Read second block
    block3 = spibridge.readBytes(n=1680)
    time.sleep(0.003)

    # Combine
    raw = bytes(block1 + block2 + block3)
    
    if len(raw) != 5776:
        print("ERROR: got", len(raw), "bytes")
        return
    
    ints = struct.unpack("<1444i", raw)

    # Convert to numpy
    arr = np.array(ints, dtype=np.int32)
    
    # Slice into lidar struct
    lidar = {
        "angle":   arr[0:361],
        "flag":    arr[361:722],
        "quality": arr[722:1083],
        "range":   arr[1083:1444],
    }

    print(f"{'i':>3} | {'angle':>6} | {'flag':>4} | {'qual':>5} | {'range':>6}")
    print("-" * 34)
    for i in range(361):
        print(f"{i:3d} | {lidar['angle'][i]:6d} | {lidar['flag'][i]:4d} | "
              f"{lidar['quality'][i]:5d} | {lidar['range'][i]:6d}")
    print("---------------------------------------------------")
    time.sleep(0.025)


App.run(user_loop=loop)