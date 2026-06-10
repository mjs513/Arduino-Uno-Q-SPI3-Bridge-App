#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "SPIPeripheral.h"
#include "Arduino_RouterBridge.h"

#define spiBlock 2048
SPIPeripheralClass<spiBlock> spi;

uint8_t buffer[5];   // Python sends 18 bytes
/* Thread: Define stack size and scheduling priority used by each thread */
#define STACKSIZE 1024
#define spibridge_priority 7

struct {
  int angle[361];
  int flag[361];
  int quality[361];
  int range[361];
} lidar;

void fillTestData() {
  for (int i = 0; i < 361; i++) {
    lidar.angle[i]   = i;          // 0..360
    lidar.flag[i]    = (i % 2);    // 0,1,0,1...
    lidar.quality[i] = i * 10;     // 0,10,20,...
    lidar.range[i]   = 1000 + i;   // 1000..1361
  }
}

const size_t TOTAL = sizeof(lidar);      // 5776
uint8_t* ptr = (uint8_t*)&lidar;

//Thread:  Thread to be executed
void spibridge(void)
{
    // Thread:  Code before while() loop executes once when thread starts
    Serial.println("Hello spibridge Started\n");
 
    // Thread: Make sure you put your repeating code in the while() loop
    while (1) {
      // 1. Read command (match Python's command size)
      spi.depopulate(*buffer, 5);

      if(buffer[0] == 0x0A) {
        // --- Block 1: first 2048 bytes ---
        spi.populate(ptr, 2048);
        spi.ready();
        
        // --- Block 2: next 2048 bytes ---
        spi.populate(ptr + 2048, 2048);
        spi.ready();
      
        // --- Block 3: remaining bytes ---
        spi.populate(ptr + 4096, TOTAL - 4096);   // 5776 - 4096 = 1680
        spi.ready();
        //delayMicroseconds(25);
        buffer[0] == 0x00;
      }
      k_yield();
    }
    delay(1);
}

/*************************************************************************************
* Parameters:
*    name – Symbolic name for the thread (also becomes the thread ID variable).
*    stack_size – Size of the thread stack in bytes.
*    entry_function – Function pointer to the thread entry function (void func(void *, void *, void *)).
*    p1, p2, p3 – Parameters passed to the entry function.
*    priority – Thread priority (lower number = higher priority in Zephyr).
*    options – Thread options.
*    delay – Start delay in milliseconds (K_NO_WAIT for immediate start).
************************************************************************************/
K_THREAD_DEFINE(spibridge_id, STACKSIZE, spibridge, NULL, NULL, NULL, spibridge_priority, 0, 0);

void setup() {
  Serial.begin(115200);
  delay(5000);
  
  fillTestData();
  
  Serial.println("LIDAR test struct ready");
  Serial.print("Struct size = ");
  Serial.println(sizeof(lidar));   // Should print 5776erial.begin(115200);
  
  spi.begin();
  
  k_tid_t our_tid = k_sched_current_thread_query();
  int main_pri = k_thread_priority_get(our_tid);
  Serial.print("main TID: ");
  Serial.print((uint32_t)our_tid, HEX);
  Serial.print(" pri: ");
  Serial.println(main_pri);
  printk("main TID:%x pri:%d\n", (uint32_t)our_tid, main_pri);
  k_thread_priority_set(our_tid, spibridge_priority+1);
  main_pri = k_thread_priority_get(our_tid);
  Serial.print("\tupdated pri: ");
  Serial.println(main_pri);
  printk("main TID:%x pri:%d\n", (uint32_t)our_tid, main_pri);
  
  Serial.println("Lidar SPI test ready");
}

void loop() {

  delay(1);  // keep loop alive
}
