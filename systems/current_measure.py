from systems.event_source import AsyncEventSource, BaseEventArgs
from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
import smbus
import trio


class CurrentMeasure(AsyncEventSource):
    """
    Simple module to perform battery voltage measurements and transform them onto battery levels
    """
    CURRENT_EVENT = "CURRENT_EVENT"
    _SENSITIVITY = 0.187  # V/A
    _ZERO_SENSOR_VOLTAGE = 2.5  # Output voltage at zero-current

    def __init__(self, nursery, adc: ADS1015, channel: int, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._CHANNEL = channel
        self._data = data if data is not None else {'motor_current': None}
        self._adc = adc  # type: ADS1015
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        fifo_stack = [0,0,0,0]
        while self._running:
            await trio.sleep(0.5)
            fifo_stack[1:len(fifo_stack)] = fifo_stack[0:(len(fifo_stack)-1)]
            fifo_stack[0] = self._adc.read_single_shot(channel=self._CHANNEL)
            mean_voltage = sum(fifo_stack)/len(fifo_stack)
            self._data['motor_current'] = (mean_voltage - self._ZERO_SENSOR_VOLTAGE) * self._SENSITIVITY
            await self.raise_event(CurrentEventArgs(self.CURRENT_EVENT, self._data))

    def stop_notification_loop(self):
        self._running = False

class CurrentEventArgs(BaseEventArgs):
    def __init__(self, event_type, data: dict):
        super().__init__(event_type)
        self.data = data  # type: dict


class DummyCurrentMeasure(AsyncEventSource):
    def __init__(self, nursery, adc: ADS1015, channel: int, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._data = data if data is not None else {'motor_current': 0}
        #self._reported_data = [0,0,0,1,1.2,1.3,1.5,1.5,1.5,1.5,1.5,1.5,1.5,0,0,0]
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        # counter = 0
        while self._running:
            await trio.sleep(1)
            #self._data['motor_current'] = self._reported_data[counter % len(self._reported_data)]
            await self.raise_event(CurrentEventArgs(CurrentMeasure.CURRENT_EVENT, self._data))
            # counter += 1

    def stop_notification_loop(self):
        self._running = False


if __name__ == "__main__":
    DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
    DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
    ALERT_READY_PIN = 26  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015

    COUNTER = 0

    async def process_data(source, param: CurrentEventArgs):
        print(f"Current: {param.data}%")


    async def parent():
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=0)

        async with trio.open_nursery() as nursery:
            current_system = CurrentMeasure(nursery, adc, channel=2, notification_callbacks=[process_data])
            nursery.start_soon(current_system.a_run_notification_loop)

    trio.run(parent)