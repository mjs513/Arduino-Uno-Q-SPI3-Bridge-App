import time
from datetime import datetime
import numpy as np
import spibridge
import struct
import schedule
from arduino.app_utils import App

print(spibridge.config_speed(2000000))
print(spibridge.config_mode(0))
print(spibridge.config_bits(8))
print(spibridge.config_bytes_to_read(2048))

def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]   # HH:MM:SS.mmm

def print_header(hdr):
    print("\n=== SPI HEADER ===")
    print(f" raw bytes    : {[f'0x{b:02X}' for b in hdr]}")
    print(f" SOF          : 0x{hdr[0]:02X}")
    print(f" data_type    : 0x{hdr[1]:02X}  ({hdr[1]})")
    print(f" block_size   : {int.from_bytes(hdr[2:4], 'little')} bytes")
    print(f" total_size   : {int.from_bytes(hdr[4:8], 'little')} bytes")
    print(f" block_count  : {hdr[8]}")
    print("===================\n")


def read_header():
    hdr = bytes(spibridge.readBytes(n=9))
    # No data yet or invalid header
    if len(hdr) != 9 or hdr[0] != 0xAA:
        return 0xFF, 0, 0, 0

    data_type = hdr[1]
    block_size = int.from_bytes(hdr[2:4], "little")
    total_size = int.from_bytes(hdr[4:8], "little")
    block_count = hdr[8]
    
    #print_header(hdr)
    return data_type, block_size, total_size, block_count

def read_frame():
    data_type, block_size, total_size, block_count = read_header()

    # No valid frame yet
    if data_type == 0xFF:
        return 0xFF, b""
    
    blocks = []
    remaining = total_size

    for i in range(block_count):
        chunk = min(block_size, remaining)
        block = spibridge.readBytes(n=chunk)
        blocks.append(bytes(block))
        remaining -= chunk

    raw = b"".join(blocks)

    if len(raw) != total_size:
        raise ValueError(f"Size mismatch: expected {total_size}, got {len(raw)}")

    return data_type, raw

def read_lidar():
    spibridge.config_command("bytes", [0x1A])
    time.sleep(0.001)

    # Send the 5‑byte command
    spibridge.readBytes(n=5)

    data_type, raw = read_frame()
    if data_type == 0xFF:
        return  # skip, no data yet
    
    if data_type == 0x1A:
        ints = struct.unpack("<1444i", raw)
        arr = np.array(ints, dtype=np.int32)
        lidar = {
            "angle":   arr[0:361],
            "flag":    arr[361:722],
            "quality": arr[722:1083],
            "range":   arr[1083:1444],
        }

        print(f"{ts()} LIDAR:")
        print(f"{'i':>3} | {'angle':>6} | {'flag':>4} | {'qual':>5} | {'range':>6}")
        print("-" * 34)
        for i in range(10):
            print(f"{i:3d} | {lidar['angle'][i]:6d} | {lidar['flag'][i]:4d} | "
                  f"{lidar['quality'][i]:5d} | {lidar['range'][i]:6d}")
        print("---------------------------------------------------")

def read_imu():
    spibridge.config_command("bytes", [0x2A])
    time.sleep(0.001)

    # Send the 5‑byte command
    spibridge.readBytes(n=5)
    
    data_type, raw = read_frame()
    if data_type == 0xFF:
        return  # skip, no data yet
        
    if data_type == 0x2A:
        imu = struct.unpack("<9f", raw)
        print(f"{ts()} IMU:", imu)

def read_gps():
    spibridge.config_command("bytes", [0x3A])
    time.sleep(0.001)

    # Send the 5‑byte command
    spibridge.readBytes(n=5)

    data_type, raw = read_frame()

    if data_type == 0xFF:
        return  # skip, no data yet
       
    if data_type == 0x3A:
        lat, lon, alt = struct.unpack("<ddfxxxx", raw) 
        print(f"{ts()} GPS:", lat, lon, alt)


schedule.every(0.25).seconds.do(read_lidar)
schedule.every(0.01).seconds.do(read_imu)
schedule.every(1).seconds.do(read_gps)

def loop():
    schedule.run_pending()
    time.sleep(0.001)   # idle

App.run(user_loop=loop)