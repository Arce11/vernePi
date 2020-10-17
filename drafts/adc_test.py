from gpiozero import DigitalInputDevice
import smbus

DEVICE_BUS = 1
DEVICE_ADDRESS = 0x48

CONVERSION_REGISTER = 0X00
CONFIG_REGISTER = 0X01
LO_THRES_REGISTER = 0X02
HI_THRES_REGISTER = 0X03

ALERT_READY_PIN = 16

alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up = True)
bus = smbus.SMBus(1)

conf = bus.read_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, 2)
print("Antigua configuracion:", conf)

nuevo_valor = [0xC1, 0x48]
bus.write_i2c_block_data(DEVICE_ADDRESS, HI_THRES_REGISTER, [0xFF, 0xFF])
bus.write_i2c_block_data(DEVICE_ADDRESS, LO_THRES_REGISTER, [0x00, 0x00])
bus.write_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, nuevo_valor)
alert_ready.wait_for_active()
val = bus.read_i2c_block_data(DEVICE_ADDRESS, CONVERSION_REGISTER, 2)
conf = bus.read_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, 2)
print("Nueva configuracion: ", conf)
print("Valor leido [bytes]:", val)

