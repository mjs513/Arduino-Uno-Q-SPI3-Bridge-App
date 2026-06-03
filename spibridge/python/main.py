import time

import requests
import spibridge
from arduino.app_utils import App


result = spibridge.config_speed(2000000)
print(result)

result = spibridge.config_mode(0)
print(result)

result = spibridge.config_bits(8)
print(result)

result = spibridge.config_bytes_to_read(1024)  // had to multiples of 2^n
print(result)

def loop():
    #data = spibridge.readFloats()
    #print("Read data Floats:")
    #print(data)

    data = spibridge.readBytes()
    print("Read data Bytes:")
    print(data)

    data = spibridge.readInts()
    print("Read data Ints:")
    print(data)
    time.sleep(1)


App.run(user_loop=loop)
