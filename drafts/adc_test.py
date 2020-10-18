from gpiozero import DigitalInputDevice
import smbus

class ADS1015:
    # I2C interface provided by the ADS1015 (registers predefined by the datasheet)
    CONVERSION_REGISTER = 0x00  # Result of the last conversion
    CONFIG_REGISTER = 0x01      # ADS1015 operating modes and query the status of the device
    LO_THRES_REGISTER = 0x02    # Low threshold (comparator mode)
    HI_THRES_REGISTER = 0x03    # High threshold (comparator mode)

    def __init__(self, bus, address):
        self.BUS = bus                  # SMBus object (import smbus). I2C bus connected to the device
        self.PGA = voltage_range        # abs(voltage to read) <= abs(voltage_range)
        self.DEVICE_ADDRESS = address   # ADS1015 address, which depends of the value of the ADDR pin

    def read_channel(self):
        conf = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self.CONFIG_REGISTER, 2)
        print("Antigua configuracion:", conf)

DEVICE_BUS = 1
ALERT_READY_PIN = 16


bus = smbus.SMBus(DEVICE_BUS)
adc = ADS1015(bus, 0, 3, 0x48)
adc.read_channel()


# Calculate the 2's complement of a number
def twos_comp(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

# alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up = True)
# bus = smbus.SMBus(1)

# conf = bus.read_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, 2)
# print("Antigua configuracion:", conf)

# nuevo_valor = [0xC1, 0x48]
# bus.write_i2c_block_data(DEVICE_ADDRESS, HI_THRES_REGISTER, [0xFF, 0xFF])
# bus.write_i2c_block_data(DEVICE_ADDRESS, LO_THRES_REGISTER, [0x00, 0x00])
# bus.write_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, nuevo_valor)
# alert_ready.wait_for_active()
# val = bus.read_i2c_block_data(DEVICE_ADDRESS, CONVERSION_REGISTER, 2)
# conf = bus.read_i2c_block_data(DEVICE_ADDRESS, CONFIG_REGISTER, 2)
# print("Nueva configuracion: ", conf)
# print("Valor leido [bytes]:", val)
# print((val[0]<<4)|(val[1]>>4))
# print(twos_comp((val[0]<<4)|(val[1]>>4), 12))
# pendiente = (2*6.144)/pow(2,12)
# print(pendiente*twos_comp((val[0]<<4)|(val[1]>>4), 12))
