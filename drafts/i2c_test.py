import smbus

DEVICE_BUS = 1
DEVICE_ADDR = 0x48
bus = smbus.SMBus(DEVICE_BUS)
bus.write_byte_data(DEVICE_ADDR, 0x48, 0x01)