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
