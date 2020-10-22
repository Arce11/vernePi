from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
import smbus

I2C_BUS = 1
DEVICE_I2C_ADDRESS = 0x48
ALERT_READY_SIGNAL = 16

ready_signal = DigitalInputDevice(ALERT_READY_SIGNAL, pull_up=True)
i2c_bus = smbus.SMBus(1)
adc = ADS1015(i2c_bus, DEVICE_I2C_ADDRESS, ready_signal)

f" Old config: {adc.read_config()} \n"

while True:
    phase_diff_voltage = adc.read_single_shot_debug(0, 6.144, 490)
    f" {phase_diff_voltage} V \n"
