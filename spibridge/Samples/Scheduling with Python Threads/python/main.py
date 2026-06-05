import time
import threading
import numpy as np
import spibridge
from arduino.app_utils import App

def periodic(interval, func):
    def loop():
        while True:
            time.sleep(interval)
            func()
    t = threading.Thread(target=loop, daemon=True)
    t.start()

def job_ints():
    np.array(spibridge.readInts(n=18), dtype=np.int32)
    # Get Integer daya
    ints = np.array(spibridge.readInts(n=18), dtype=np.int32)
    print("INTS:", ints)

def job_floats():
    # Get Read Type for processing in Arduino Sketch
    np.array(spibridge.readFloats(n=18), dtype=np.float32)
    # Get Integer daya
    floats_out = np.array(spibridge.readFloats(n=18), dtype=np.float32)
    print("FLOATS:", floats_out)

def setup():
    spibridge.config_speed(1000000)
    spibridge.config_mode(0)
    spibridge.config_bits(8)
    spibridge.config_bytes_to_read(1024)

    periodic(1.0, job_ints)
    periodic(2.5, job_floats)

def loop():
    time.sleep(0.05)

if __name__ == "__main__":
    setup()
    App.run(user_loop=loop)
