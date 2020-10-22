from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
import smbus
import time
import statistics

I2C_BUS = 1
DEVICE_I2C_ADDRESS = 0x48
ALERT_READY_SIGNAL = 16

ready_signal = DigitalInputDevice(ALERT_READY_SIGNAL, pull_up=True)
i2c_bus = smbus.SMBus(1)
adc = ADS1015(i2c_bus, DEVICE_I2C_ADDRESS, ready_signal)

fifo = [0] * 10
print(f" Old config: {adc.read_config()} \n")

counter = 0
while True:
    phase_diff_voltage = adc.read_single_shot_debug(0, 6.144, 490)
    fifo[1:10] = fifo[0:9]
    fifo[0] = phase_diff_voltage
    avg = statistics.mean(fifo)
    counter += 1
    if counter % 10 == 0:
        print(f"Actual: {phase_diff_voltage} V \t Media: {avg} V")
    time.sleep(0.05)
