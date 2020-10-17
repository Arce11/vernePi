from gpiozero import DigitalInputDevice
import smbus


DEVICE_BUS = 1
DEVICE_ADDRESS = 0x48
ALERT_READY_PIN = 40

alert_ready = DigitalInputDevice(4ALERT_READY_PIN, pull_up = True)
bus = smbus.SMBus(1)
