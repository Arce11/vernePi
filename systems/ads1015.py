from gpiozero import DigitalInputDevice
import smbus
import time


class ADS1015:
    # I2C interface provided by the ADS1015 (registers predefined by the datasheet):
    _CONVERSION_REGISTER = 0x00  # Result of the last conversion
    _CONFIG_REGISTER = 0x01  # ADS1015 operating modes and query the status of the device
    _LO_THRES_REGISTER = 0x02  # Low threshold (comparator mode)
    _HI_THRES_REGISTER = 0x03  # High threshold (comparator mode)
    _DEFAULT_CHANNEL = 0
    _DEFAULT_DATA_RATE = 128

    def __init__(self, i2c_bus, address, ready):
        self.BUS = i2c_bus  # SMBus object (import smbus). The I2C bus connected to the device
        self.DEVICE_ADDRESS = address  # ADS1015 address, which depends of the value of the ADDR pin
        self.READY_PIN = ready  # DigitalInputDevice (from gpiozero). Conversion ready signal

    @staticmethod
    def _twos_comp(val, bits):
        # Calculates the 2's complement of a number
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val

    @staticmethod
    def _get_pga(i):
        # Retrieves the code of the PGA used during the conversion
        switcher = {
            6.144: 0,
            4.096: 1,
            2.048: 2,  # default value
            1.024: 3,
            0.512: 4,
            0.256: 5
        }
        return switcher.get(i)

    @staticmethod
    def _get_channel(i):
        # Retrieves the code of the single-ended channel used in the multiplexer
        switcher = {
            0: 4,
            1: 5,
            2: 6,
            3: 7
        }
        return switcher.get(i)

    @staticmethod
    def _get_data_rate(i):
        # Retrieves the code of the desired data rate output
        switcher = {
            128: 0,
            250: 1,
            490: 2,
            920: 3,
            1600: 4,  # default value
            2400: 5,
            3300: 6
        }
        return switcher.get(i)

    def _data_processing(self, reg_value, voltage_reference):
        # Data processing:
        #   (1) Convert the 2 bytes into a 12-bit word data: the most-significant byte (MSB) is the MSB of
        #       12-bit conversion, and the 4 MSbs of the least-significant byte (LSB), the 4 least-significant
        #       bits (LSbs).
        #   (2) Perform the two's complement operation (twos_comp function).
        #   (3) Obtain the real voltage using the calibration function:
        #           voltage = code*(2*full scale/number of codes)
        code = self._twos_comp((reg_value[0] << 4) | (reg_value[1] >> 4), 12)
        input_voltage = code * 2 * voltage_reference / pow(2, 12)
        return input_voltage

    def wait_ack(self):
        self.READY_PIN.wait_for_active()
        self.READY_PIN.wait_for_inactive()

    def read_config(self):
        # Reads the ADS1015 configuration register
        config = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self._CONFIG_REGISTER, 2)
        return config

    def configure_adc(self, channel, voltage_reference, data_rate):
        self._DEFAULT_CHANNEL = channel
        self._DEFAULT_DATA_RATE = data_rate
        # In order to deactivate the comparator mode and use the ADDR/READY as a conversion ready signal,
        # the most-significant bit (MSb) of the HI_THRES_REGISTER is set to 1, and the MSb of the
        # LO_THRES_REGISTER is set to 0
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._HI_THRES_REGISTER, [0xFF, 0xFF])
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._LO_THRES_REGISTER, [0x00, 0x00])
        # Configuration of CONFIG_REGISTER to perform a continuous conversion
        #   (1) OS[15] = 0, no effect
        #   (2) MUX[14:12] = value dependent of the channel to read
        #   (3) PGA[11:9] = value dependent of the voltage reference
        #   (4) MODE[8] = 0, in order to activate the continuous-conversion mode
        #   (5) DR[7:5] = data rate output (in samples per second)
        #   (6) COMP_MODE[4] = irrelevant when using the ADDR/READY pin as a conversion ready signal
        #   (7) COMP_POL[3] = 1, polarity of the conversion ready signal
        #   (8) COMP_LAT[2] = irrelevant when using the ADDR/READY pin as a conversion ready signal
        #   (9) COMP_QUE[1:0] = any value other than 11 when using ADDR/READY as a conversion ready signal
        mux_code = self._get_channel(channel)
        pga_code = self._get_pga(voltage_reference)
        data_rate_code = self._get_data_rate(data_rate)
        config_first_byte = (0 << 7) | (mux_code << 4) | (pga_code << 1) | 0
        config_second_byte = (data_rate_code << 5) | (0 << 4) | (1 << 3) | 0
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._CONFIG_REGISTER,
                                      [config_first_byte, config_second_byte])  # starting single-shot conversion

    def read_continuous(self, channel, voltage_reference, data_rate):
        # Reads the conversion stored in the conversion register
        if channel == self._DEFAULT_CHANNEL:
            # The analog value is represented by a two's complement format left-adjusted 12-bit word within
            # 16-bit data (2 bytes)
            reg = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self._CONVERSION_REGISTER, 2)
            return self._data_processing(reg, voltage_reference)
        else:
            self.configure_adc(channel, voltage_reference, data_rate)
            self.wait_ack()
            self.read_continuous(channel, voltage_reference, data_rate)

    def read_single_shot(self, channel, voltage_reference):
        if channel == self._DEFAULT_CHANNEL:
            reg = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self._CONVERSION_REGISTER, 2)
        else:
            self._configure_single(channel, voltage_reference)
            self.wait_ack()
            reg = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self._CONVERSION_REGISTER, 2)
            self.configure_adc(self._DEFAULT_CHANNEL, voltage_reference, self._DEFAULT_DATA_RATE)

    def _configure_single(self, channel, voltage_reference):
        # Aimed for private use by the class method read_single_shot
        # Comparator mode is deactivated
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._HI_THRES_REGISTER, [0xFF, 0xFF])
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._LO_THRES_REGISTER, [0x00, 0x00])
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
        mux_code = self._get_channel(channel)
        pga_code = self._get_pga(voltage_reference)
        config_first_byte = (1 << 7) | (mux_code << 4) | (pga_code << 1) | 1
        config_second_byte = 0x08  # fixed value following the aforementioned rules
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._CONFIG_REGISTER,
                                      [config_first_byte, config_second_byte])  # starting single-shot conversion

    def read_single_shot_debug(self, channel, voltage_reference, data_rate):
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._HI_THRES_REGISTER, [0xFF, 0xFF])
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._LO_THRES_REGISTER, [0x00, 0x00])
        mux_code = self._get_channel(channel)
        pga_code = self._get_pga(voltage_reference)
        data_rate_code = self._get_data_rate(data_rate)
        config_first_byte = (1 << 7) | (mux_code << 4) | (pga_code << 1) | 1
        config_second_byte = (data_rate_code << 5) | (0 << 4) | (1 << 3) | 0
        self.BUS.write_i2c_block_data(self.DEVICE_ADDRESS, self._CONFIG_REGISTER,
                                      [config_first_byte, config_second_byte])  # starting single-shot conversion
        self.wait_ack()
        reg = self.BUS.read_i2c_block_data(self.DEVICE_ADDRESS, self._CONVERSION_REGISTER, 2)
        return self._data_processing(reg, voltage_reference)


if __name__ == "__main__":
    DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
    DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
    #   (ver dirección en RaspPi con sudo i2cdetect -y <DEVICE_BUS>)
    ALERT_READY_PIN = 16  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015

    time_inicio = time.time()
    alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
    bus = smbus.SMBus(DEVICE_BUS)
    adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready)
    time_final = time.time()
    print(adc.read_channel_single_shot(0, 6.144))
    print(time_final - time_inicio)
