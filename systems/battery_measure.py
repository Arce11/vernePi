from systems.event_source import AsyncEventSource, BaseEventArgs
from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
import smbus
import trio


class BatteryMeasure(AsyncEventSource):
    """
    Simple module to perform battery voltage measurements and transform them onto battery levels
    """
    BATTERY_EVENT = "BATTERY_EVENT"
    _MAX_BATTERY_VOLTAGE = 3.9
    _MIN_BATTERY_VOLTAGE = 3.1
    _SPAN_BATTERY_VOLTAGE = _MAX_BATTERY_VOLTAGE - _MIN_BATTERY_VOLTAGE

    def __init__(self, nursery, adc: ADS1015, channel: int, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._CHANNEL = channel
        self._data = data if data is not None else {'battery': None}
        self._adc = adc  # type: ADS1015
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        while self._running:
            await trio.sleep(1)
            bat_voltage = self._adc.read_single_shot(channel=self._CHANNEL)
            battery_percent = max(0, min((bat_voltage - self._MIN_BATTERY_VOLTAGE)/self._SPAN_BATTERY_VOLTAGE * 100, 100))
            self._data['battery'] = battery_percent
            await self.raise_event(BatteryEventArgs(self.BATTERY_EVENT, self._data.copy()))

    def stop_notification_loop(self):
        self._running = False

class BatteryEventArgs(BaseEventArgs):
    def __init__(self, event_type, data_dict: dict):
        super().__init__(event_type)
        self.data = data_dict  # type: dict


class DummyBatteryMeasure(AsyncEventSource):
    def __init__(self, nursery, adc: ADS1015, channel: int, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._data = data if data is not None else {'battery': None}
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        while self._running:
            await trio.sleep(1)
            self._data['battery'] = 100
            await self.raise_event(BatteryEventArgs(BatteryMeasure.BATTERY_EVENT, self._data.copy()))

    def stop_notification_loop(self):
        self._running = False


if __name__ == "__main__":
    DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
    DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
    ALERT_READY_PIN = 26  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015

    COUNTER = 0

    async def process_data(source, param: BatteryEventArgs):
        print(f"Battery level: {param.data['battery']}%")


    async def parent():
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=0)

        async with trio.open_nursery() as nursery:
            battery_system = BatteryMeasure(nursery, adc, channel=2, notification_callbacks=[process_data])
            nursery.start_soon(battery_system.a_run_notification_loop)

    trio.run(parent)