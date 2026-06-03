# Source: https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568/18
import spidev
import struct

class SPIBridge:
    def __init__(self, bus=0, device=0, max_speed_hz=5000000, mode=0, bits_per_word=8):
        self.bus = bus
        self.device = device
        self.max_speed_hz = max_speed_hz
        self.mode = mode
        self.bits_per_word = bits_per_word
        self.spi = None

    # -----------------------------
    # Initialization
    # -----------------------------
    def init_spi(self):
        spi = spidev.SpiDev()
        spi.open(self.bus, self.device)
        spi.max_speed_hz = self.max_speed_hz
        spi.mode = self.mode
        spi.bits_per_word = self.bits_per_word
        self.spi = spi
        return spi

    # -----------------------------
    # Reconfiguration
    # -----------------------------
    def set_speed(self, hz):
        self.max_speed_hz = hz
        if self.spi:
            self.spi.max_speed_hz = hz

    def set_mode(self, mode):
        self.mode = mode
        if self.spi:
            self.spi.mode = mode

    def set_bits(self, bits):
        self.bits_per_word = bits
        if self.spi:
            self.spi.bits_per_word = bits

    # -----------------------------
    # Core read functions
    # -----------------------------
    def read_bytes(self, read_command, bytes_to_read=1024):
        if self.spi is None:
            raise RuntimeError("SPI not initialized. Call init_spi() first.")

        data = self.spi.xfer2(read_command + [0x00] * bytes_to_read)
        return bytes(data)


    # -----------------------------
    # Cleanup
    # -----------------------------
    def close(self):
        if self.spi:
            self.spi.close()
            self.spi = None