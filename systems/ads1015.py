import time
import smbus
from gpiozero import DigitalInputDevice


class ADS1015:
    # I2C interface provided by the ADS1015 (registers predefined by the datasheet):
    _CONVERSION_REGISTER = 0x00  # Result of the last conversion
    _CONFIG_REGISTER = 0x01  # ADS1015 operating modes and query the status of the device
    _LO_THRES_REGISTER = 0x02  # Low threshold (comparator mode)
    _HI_THRES_REGISTER = 0x03  # High threshold (comparator mode)

    def __init__(self, i2c_bus: smbus.SMBus, address: int, ready: DigitalInputDevice,
                 channel: int = 0, sample_rate: int = 3300, voltage_ref: float = 6.144):
        self._bus = i2c_bus  # SMBus object (import smbus). The I2C bus connected to the device
        self._device_address = address  # ADS1015 address, which depends of the value of the ADDR pin
        self._ready_pin = ready  # DigitalInputDevice (from gpiozero). Conversion ready signal
        self._default_channel = channel
        self._default_sample_rate = sample_rate
        self._default_voltage_ref = voltage_ref

        self._disable_comparator()
        self.configure_defaults(self._default_channel, self._default_voltage_ref, self._default_sample_rate)

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

    @staticmethod
    def _data_processing(reg_value, voltage_reference):
        # Data processing:
        #   (1) Convert the 2 bytes into a 12-bit word data: the most-significant byte (MSB) is the MSB of
        #       12-bit conversion, and the 4 MSbs of the least-significant byte (LSB), the 4 least-significant
        #       bits (LSbs).
        #   (2) Perform the two's complement operation (twos_comp function).
        #   (3) Obtain the real voltage using the calibration function:
        #           voltage = code*(2*full scale/number of codes)
        code = ADS1015._twos_comp((reg_value[0] << 4) | (reg_value[1] >> 4), 12)
        input_voltage = code * 2 * voltage_reference / pow(2, 12)
        return input_voltage

    def _wait_ack(self):
        """
        Waits for the READY/ALERT pin signal.
        WARNING: it often does NOT work due to timing issues (READY pulse getting skipped...?)
        To mitigate this, timeouts are included.
        This works about as well as calling time.sleep(1/self._default_sample_rate) instead of self._wait_ack()

        :return:
        """
        self._ready_pin.wait_for_active(1/self._default_sample_rate)
        self._ready_pin.wait_for_inactive(0.5/self._default_sample_rate)

    def _read_config(self):
        # Reads the ADS1015 configuration register
        config = self._bus.read_i2c_block_data(self._device_address, self._CONFIG_REGISTER, 2)
        return config

    def _disable_comparator(self):
        # In order to deactivate the comparator mode and use the ADDR/READY as a conversion ready signal,
        # the most-significant bit (MSb) of the HI_THRES_REGISTER is set to 1, and the MSb of the
        # LO_THRES_REGISTER is set to 0
        self._bus.write_i2c_block_data(self._device_address, self._HI_THRES_REGISTER, [0xFF, 0xFF])
        self._bus.write_i2c_block_data(self._device_address, self._LO_THRES_REGISTER, [0x00, 0x00])

    def configure_defaults(self, channel: int, voltage_reference: float, sample_rate: int):
        self._default_channel = channel
        self._default_sample_rate = sample_rate
        self._default_voltage_ref = voltage_reference
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
        mux_code = ADS1015._get_channel(channel)
        pga_code = ADS1015._get_pga(voltage_reference)
        data_rate_code = ADS1015._get_data_rate(sample_rate)
        config_first_byte = (0 << 7) | (mux_code << 4) | (pga_code << 1) | 0
        config_second_byte = (data_rate_code << 5) | (0 << 4) | (1 << 3) | 0
        self._bus.write_i2c_block_data(self._device_address, self._CONFIG_REGISTER,
                                       [config_first_byte, config_second_byte])  # starting continuous?-shot conversion

    def read_continuous(self):
        # Reads the conversion stored in the conversion register (last conversion value)
        # The analog value is represented by a two's complement format left-adjusted 12-bit word within
        # 16-bit data (2 bytes)
        reg = self._bus.read_i2c_block_data(self._device_address, self._CONVERSION_REGISTER, 2)
        return self._data_processing(reg, self._default_voltage_ref)

    def read_single_shot(self, channel: int = None, voltage_reference: float = None, sample_rate: int = None):
        channel = channel if channel is not None else self._default_channel
        voltage_reference = voltage_reference if voltage_reference is not None else self._default_voltage_ref
        sample_rate = sample_rate if sample_rate is not None else self._default_sample_rate
        if all([channel == self._default_channel, voltage_reference == self._default_voltage_ref,
                sample_rate == self._default_sample_rate]):
            reg = self._bus.read_i2c_block_data(self._device_address, self._CONVERSION_REGISTER, 2)
        else:
            old_channel = self._default_channel
            old_voltage = self._default_voltage_ref
            old_sample_rate = self._default_sample_rate
            self.configure_defaults(channel, voltage_reference, sample_rate)
            self._wait_ack()
            #time.sleep(1/sample_rate)
            reg = self._bus.read_i2c_block_data(self._device_address, self._CONVERSION_REGISTER, 2)
            self.configure_defaults(old_channel, old_voltage, old_sample_rate)
        return ADS1015._data_processing(reg, voltage_reference)


class DummyADS1015:
    def __init__(self, *args, **kwargs):
        pass

    def configure_defaults(self, *args, **kwargs):
        pass

    def read_continuous(self, *args, **kwargs):
        return 1

    def read_single_shot(self, *args, **kwargs):
        return 1


if __name__ == "__main__":
    DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
    DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
    #   (ver dirección en RaspPi con sudo i2cdetect -y <DEVICE_BUS>)
    ALERT_READY_PIN = 26  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015
    alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
    bus = smbus.SMBus(DEVICE_BUS)
    adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=0)

    counter = 1
    while True:
        if counter % 10 == 0:
            time_start = time.time()
            meas = adc.read_single_shot(1)
            time_end = time.time()
            token = "## SS ##"
        else:
            time_start = time.time()
            meas = adc.read_continuous()
            time_end = time.time()
            token = "C"

        # print(f"{token} Tiempo: {time_end - time_start}s \t - \t Medida: {meas}")
        print(f"{token}: {meas}")
        time.sleep(0.1)
        counter += 1
