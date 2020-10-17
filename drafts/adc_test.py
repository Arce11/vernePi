from gpiozero import DigitalInputDevice
import smbus


DEVICE_BUS = 1
DEVICE_ADDRESS = 0x48
CONFIG_REGISTER = 0X01
ALERT_READY_PIN = 40

alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up = True)
bus = smbus.SMBus(1)

val = bus.read_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, 2)
print("Old CONFIG:", val)