import time
import numpy as np
import spibridge
from arduino.app_utils import App

print(spibridge.config_speed(1000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(1024))

last_int_time = 0
last_float_time = 0

INT_INTERVAL = 1.0
FLOAT_INTERVAL = 2.0

def loop():

    global last_int_time, last_float_time

    now = time.time()

    if now - last_int_time >= INT_INTERVAL:
        # -------------------------
        # READ INTS (0x0C)
        # -------------------------
        # Get Read Type for processing in Arduino Sketch
        np.array(spibridge.readInts(n=18), dtype=np.int32)
        # Get Integer daya
        ints = np.array(spibridge.readInts(n=18), dtype=np.int32)
        print("INTS:", ints)
        last_int_time = now
        
    if now - last_float_time >= FLOAT_INTERVAL:
        # -------------------------
        # READ FLOATS (0x0B)
        # -------------------------
        # Get Read Type for processing in Arduino Sketch
        np.array(spibridge.readFloats(n=18), dtype=np.float32)
        # Get Integer daya
        floats_out = np.array(spibridge.readFloats(n=18), dtype=np.float32)
        print("FLOATS:", floats_out)
        last_float_time = now

    time.sleep(0.01)


App.run(user_loop=loop)
