#ifndef SPI_PERIPHERAL_H
#define SPI_PERIPHERAL_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/init.h>
#include <zephyr/drivers/spi.h>

#ifdef CONFIG_BOARD_ARDUINO_UNO_Q

#define SPI_PERIPHERAL_NODE DT_COMPAT_GET_ANY_STATUS_OKAY(zephyr_spi_slave)

template <int SPI_MAX_MESSAGE>
class SPIPeripheralClass {
public:
    SPIPeripheralClass() {
        spi_cfg.frequency = 2000000;
        spi_cfg.operation = SPI_WORD_SET(8) | SPI_OP_MODE_SLAVE;
        rx.buf = rxmsg;
        rx.len = SPI_MAX_MESSAGE;
        rx_bufs.buffers = &rx;
        rx_bufs.count = 1;
        tx.buf = txmsg;
        tx.len = SPI_MAX_MESSAGE;
        tx_bufs.buffers = &tx;
        tx_bufs.count = 1;

    }

    int begin() {
        int ret = device_init(spi_peripheral);
        return ret;
    }

    int depopulate(uint8_t &buf, size_t len) {     
        int ret = spi_transceive(spi_peripheral, &spi_cfg, &tx_bufs, &rx_bufs);
        uint8_t* rx_bytes = static_cast<uint8_t*>(rx_bufs.buffers[0].buf);
      
        //memcpy(buf, rx_bytes, len);
        buf = rx_bytes[0];
        return ret;
    }

    int read(uint8_t *buf, size_t len) {     
        int ret = spi_transceive(spi_peripheral, &spi_cfg, &tx_bufs, &rx_bufs);
        uint8_t* rx_bytes = static_cast<uint8_t*>(rx_bufs.buffers[0].buf);
      
        memcpy(buf, rx_bytes, len);
        //buf = rx_bytes[0];
        return ret;
    }

    void* populate(uint8_t* buf, size_t len) {
        return memcpy(tx.buf, buf, len);
      }

    int ready() {
          return spi_transceive(spi_peripheral, &spi_cfg, &tx_bufs, &rx_bufs);
      }

private:

    const struct device *const spi_peripheral = DEVICE_DT_GET(DT_BUS(SPI_PERIPHERAL_NODE));
    struct spi_config spi_cfg;

    uint8_t rxmsg[SPI_MAX_MESSAGE];
    struct spi_buf rx ;
    struct spi_buf_set rx_bufs;

    uint8_t txmsg[SPI_MAX_MESSAGE];
    struct spi_buf tx ;
    struct spi_buf_set tx_bufs;
};

#endif
#endif //SPI_PERIPHERAL_H