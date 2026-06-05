import time
import numpy as np
import spibridge
import struct
from arduino.app_utils import App

print(spibridge.config_speed(1000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(512))

def loop():
    # Read JSON list of bytes from Flask
    #spibridge.readBytes(n=5)
    data = spibridge.readBytes(n=24)   # returns Python list
    arr = np.array(data, dtype=np.uint8)
    print(arr)
    print("OK frame")
    time.sleep(0.1)


App.run(user_loop=loop)