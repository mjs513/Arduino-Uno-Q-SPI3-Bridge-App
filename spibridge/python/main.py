import time
import os
import numpy as np
import spibridge
import schedule
from arduino.app_utils import App

# -------------------------
# SPI CONFIG
# -------------------------
print(spibridge.config_speed(2000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(2048))


def get_cpu_temp():
    """
    Obtains the current value of the CPU temperature.
    :returns: Current value of the CPU temperature if successful, zero value otherwise.
    :rtype: float
    """
    # Initialize the result.
    result = 0.0
    # The first line in this file holds the CPU temperature as an integer times 1000.
    # Read the first line and remove the newline character at the end of the string.
    if os.path.isfile('/sys/class/thermal/thermal_zone0/temp'):
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            line = f.readline().strip()
        # Test if the string is an integer as expected.
        if line.isdigit():
            # Convert the string with the CPU temperature to a float in degrees Celsius.
            result = float(line) / 1000
    
    # Give the result back to the caller.

    return result

def read_temp():
    """This function is called repeatedly by the App framework."""
    # You can replace this with any code you want your App to run repeatedly.
    #print('Current CPU temperature is {:.2f} degrees Celsius.'.format(get_cpu_temp()))
    print('\t {:.2f} degrees Farhrenheit.'.format(get_cpu_temp()*1.8 + 32))


def send_bytes():  
    # -------------------------
    # WRITE INTS
    # -------------------------
    spibridge.writeBytes([0xAA, 0xBB, 0xCC, 0xDD])
    time.sleep(0.01)

def send_ints():  
    # -------------------------
    # WRITE INTS
    # -------------------------
    spibridge.writeInts([1, -5, 2048])
    time.sleep(0.01)

def send_floats():
    # -------------------------
    # WRITE FLOATS
    # -------------------------
    spibridge.writeFloats([1.0, 2.5, -3.75])
    time.sleep(0.01)

def send_struct():
    # -------------------------
    # WRITE STRUCT WITH ARRAYS
    # -------------------------
    spibridge.writeStructArrayFields(
        {
            "x": {"type": "f32", "count": 2},
            "y": {"type": "i32", "count": 2},
            "z": {"type": "u8",  "count": 2}
        },
        {
            "x": [2.14, 3.14],
            "y": [1, 2],
            "z": [0x2F, 0x10]
        }
    )
    time.sleep(0.01) 


schedule.every(1).seconds.do(read_temp)
schedule.every(0.01).seconds.do(send_ints)
#schedule.every(0.5).seconds.do(send_bytes)
schedule.every(0.25).seconds.do(send_floats)
schedule.every(0.5).seconds.do(send_struct)


def loop():
    schedule.run_pending()
    
    data = spibridge.readBytes(n=5)

    time.sleep(0.005)


# Run the loop continuously
App.run(user_loop=loop)
