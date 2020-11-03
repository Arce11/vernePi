from systems.event_source import AsyncEventSource
from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
from systems.event_source import BaseEventArgs
import smbus
import trio


class MickeyMouseDetection(AsyncEventSource):
    TURN_DIRECTION_EVENT = "TURN_DIRECTION_EVENT"
    # --- Needs calibration ---
    _VOLTAGE_CENTER = 1.17  # Ideal "straigth ahead" value
    _VOLTAGE_R_OFFSET = 0.15  # Margin to one side of _VOLTAGE_CENTER before deciding to turn right
    _VOLTAGE_L_OFFSET = 0.15  # Margin to the other side of _VOLTAGE_CENTER before deciding to turn left
    # -------------------------
    _MAX_EXPECTED_VOLTAGE = 1.7
    _VOLTAGE_REFERENCE = 1.8
    _CONFIDENCE_NORMALIZATION_FACTOR = 1

    _FIFO_STACK_LENGTH = 5

    def __init__(self, adc: ADS1015, nursery: trio.Nursery, notification_callbacks=None, error_callbacks=None):
        """
        :param ADS1015 adc: initialized A/D converter
        :param nursery: Trio nursery
        :param notification_callbacks: list of async functions to be notified of the event
        :param error_callbacks: list of async functions to be called when an error happens
        """
        self._adc_polling_rate = 50
        self._adc_polling_period = 1/self._adc_polling_rate
        self._adc = adc  # type: ADS1015
        self._is_running = False
        self._fifo_stack = [0]*self._FIFO_STACK_LENGTH
        super().__init__(nursery, notification_callbacks, error_callbacks)

    async def a_run_notification_loop(self):
        if self._is_running:
            return
        self._is_running = True
        counter = 1
        while self._is_running:
            await trio.sleep(self._adc_polling_period)
            voltage = self._adc.read_continuous()
            self._fifo_stack[1:len(self._fifo_stack)] = self._fifo_stack[0:len(self._fifo_stack)-1]
            self._fifo_stack[0] = voltage
            if counter % self._FIFO_STACK_LENGTH == 0:
                average_voltage = sum(self._fifo_stack)/len(self._fifo_stack)
                angle = self.get_angle_sign(average_voltage)
                if angle == 0:  # Higher confidence the lower the deviation from the ideal center
                    confidence = 1 - abs(average_voltage - self._VOLTAGE_CENTER)/self._CONFIDENCE_NORMALIZATION_FACTOR
                else:  # Higher confidence the higher the deviation from the ideal center
                    confidence = abs(average_voltage - self._VOLTAGE_CENTER)/self._CONFIDENCE_NORMALIZATION_FACTOR
                await self.raise_event(BeaconDirectionEventArgs(self.TURN_DIRECTION_EVENT, angle, confidence))
            counter += 1


    def stop_notification_loop(self):
        self._is_running = False

    def get_angle_sign(self, voltage):
        """
        Representation of whether the beacon is detected counter-clockwise (+1), clockwise (-1) or straight ahead (0)
        Returns None if no proper beacon signal is detected
        :return: +1, 0 or -1
        """
        # Assumption: 90deg phase line placed after LEFT antenna
        # Therefore: Voltage > _VOLTAGE_CENTER  ->  Need to turn "left" (counter-clockwise)
       #  return voltage
        if voltage > self._MAX_EXPECTED_VOLTAGE:  # Very close to reference voltage -> no beacon detected
            return None

        if voltage < self._VOLTAGE_CENTER - self._VOLTAGE_R_OFFSET:  # Need to turn right (clockwise)
            return -1
        elif voltage > self._VOLTAGE_CENTER + self._VOLTAGE_L_OFFSET:  # Need to turn left (c-clockwise(
            return +1
        else:
            return 0


class BeaconDirectionEventArgs(BaseEventArgs):
    def __init__(self, event_type: str, angle_sign: float, confidence: float):
        """
        :param event_type: event identifier
        :param angle_sign: +1, -1, 0 or None
        :param confidence: Ideally, between 0 and 1
        """
        super().__init__(event_type)
        self.angle_sign = angle_sign  # type: float
        self.confidence = confidence  # type: float


if __name__ == "__main__":
    DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
    DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
    ALERT_READY_PIN = 1  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015

    COUNTER = 0

    async def process_data(source, param):
        print(f"## {param.angle_sign} ##\t## {param.confidence}")


    async def parent():
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=1)

        async with trio.open_nursery() as nursery:
            radio_system = MickeyMouseDetection(adc, nursery)
            radio_system.subscribe(notification_callbacks=[process_data])
            nursery.start_soon(radio_system.a_run_notification_loop)

    trio.run(parent)