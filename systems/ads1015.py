from gpiozero import DigitalInputDevice
import smbus


def twos_comp(val, bits):
    # Calculates the 2's complement of a number
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val


def get_channel(i):
    # Retrieves the code of the single-ended channel used in the multiplexer
    switcher = {
        0: 4,
        1: 5,
        2: 6,
        3: 7
    }
    return switcher.get(i)


def get_pga(i):
    # Retrieves the code of the PGA used during the conversion
    switcher = {
        6.144: 0,
        4.096: 1,
        2.048: 2,
        1.024: 3,
        0.512: 4,
        0.256: 5
    }
    return switcher.get(i)


class ADS1015:
    # I2C interface provided by the ADS1015 (registers predefined by the datasheet):
    CONVERSION_REGISTER = 0x00  # Result of the last conversion
    CONFIG_REGISTER = 0x01      # ADS1015 operating modes and query the status of the device
    LO_THRES_REGISTER = 0x02    # Low threshold (comparator mode)
    HI_THRES_REGISTER = 0x03    # High threshold (comparator mode)

    def __init__(self, bus, address, ready):
        self.BUS = bus                  # SMBus object (import smbus). The I2C bus connected to the device
        self.DEVICE_ADDRESS = address   # ADS1015 address, which depends of the value of the ADDR pin
        self.READY_PIN = ready          # DigitalInputDevice (from gpiozero). Conversion ready signal

    def read_config(self):
        config = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self.CONFIG_REGISTER, 2)
        return config

    def read_channel_single_shot(self, channel, voltage_reference):
        # In order to deactivate the comparator mode and use the ADDR/READY as a conversion ready signal,
        # the most-significant bit (MSb) of the HI_THRES_REGISTER is set to 1, and the MSb of the
        # LO_THRES_REGISTER is set to 0
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self.HI_THRES_REGISTER, [0xFF, 0xFF])
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self.LO_THRES_REGISTER, [0x00, 0x00])
        # Configuration of CONFIG_REGISTER to perform a "single-shot" conversion
        #   (1) OS[15] = 1, in order to start a single conversion
        #   (2) MUX[14:12] = value dependent of the channel to read
        #   (3) PGA[11:9] = value dependent of the voltage reference
        #   (4) MODE[8] = 1, single-shot mode
        #   (5) DR[7:5] = data rate output, irrelevant in single-shot mode
        #   (6) COMP_MODE[4] = irrelevant when using the ADDR/READY pin as a conversion ready signal
        #   (7) COMP_POL[3] = 1, polarity of the conversion ready signal
        #   (8) COMP_LAT[2] = irrelevant when using the ADDR/READY pin as a conversion ready signal
        #   (9) COMP_QUE[1:0] = any value other than 11 when using ADDR/READY as a conversion ready signal
        mux_code = get_channel(channel)
        pga_code = get_pga(voltage_reference)
        config_first_byte = (1 << 7)|(mux_code << 4)|(pga_code << 1)|1
        config_second_byte = 0x08   # fixed value following the aforementioned rules
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self.CONFIG_REGISTER,
                                          [config_first_byte, config_second_byte]) # starting single-shot conversion
        self.READY_PIN.wait_for_active()
        self.READY_PIN.wait_for_inactive()
        # The script is stopped until the ADDR/READY pin is set to 1 (the conversion has ended and the
        # analog value can then be read using teh CONFIG_REGISTER). The analog value is represented by a
        # two's complement format left-adjusted 12-bit word within 16-bit data (2 bytes)
        reg = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self.CONVERSION_REGISTER, 2)
        # Data processing:
        #   (1) Convert the 2 bytes into a 12-bit word data: the most-significant byte (MSB) is the MSB of
        #       12-bit conversion, and the 4 MSbs of the least-significant byte (LSB), the 4 least-significant
        #       bits (LSbs).
        #   (2) Perform the two's complement operation (twos_comp function).
        #   (3) Obtain the real voltage using the calibration function:
        #           voltage = code*(2*full scale/number of codes)
        code = twos_comp((reg[0] << 4)|(reg[1] >> 4), 12)
        input_voltage = code*2*voltage_reference/pow(2,12)
        return input_voltage