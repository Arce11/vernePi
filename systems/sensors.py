from systems.event_source import AsyncEventSource, BaseEventArgs
from sense_hat import SenseHat
import trio


class SenseHatWrapper(AsyncEventSource):
    """
    Simple wrapper around sense hat sensor checks
    """
    SENSOR_EVENT = "SENSOR_EVENT"

    def __init__(self, nursery, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        try:
            self.sense_hat = SenseHat()
        except:
            print("ERROR INITIALIZING SENSE HAT")
            raise
        self._data = data if data is not None else {'temperature': None, 'pressure': None, 'humidity': None}
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        while self._running:
            await trio.sleep(1)
            self._data["temperature"] = self.sense_hat.get_temperature()
            await trio.sleep(0)
            self._data["pressure"] = self.sense_hat.get_pressure()
            await trio.sleep(0)
            self._data["humidity"] = self.sense_hat.get_humidity() * 81/121  # TODO: Check humidity correction
            await self.raise_event(SensorEventArgs(self.SENSOR_EVENT, self._data.copy()))

    def stop_notification_loop(self):
        self._running = False


class SensorEventArgs(BaseEventArgs):
    def __init__(self, event_type, data_dict: dict):
        super().__init__(event_type)
        self.data = data_dict  # type: dict


class DummySenseHatWrapper(AsyncEventSource):
    def __init__(self, nursery, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._data = data if data is not None else {'temperature': None, 'pressure': None, 'humidity': None}
        self._running = False

    async def a_run_notification_loop(self):
        if self._running:
            return
        self._running = True
        while self._running:
            await trio.sleep(1)
            await self.raise_event(SensorEventArgs(SenseHatWrapper.SENSOR_EVENT, self._data.copy()))

    def stop_notification_loop(self):
        self._running = False


# Test Suite: Minimal working example
if __name__ == "__main__":
    # Simple async timer to run "in parallel" to all GPS shenanigans
    data = {}

    async def async_timer():
        counter = 0
        while True:
            print(f"### {counter}s ### Main data dict is also updated: {data}")
            counter += 1
            await trio.sleep(1)

    async def event_listener(source, param):
        print(f"New Sensor event. New reported data dict: {param.data}")

    async def error_listener(source, param):
        print(f"New Error: {param}")

    async def parent():
        async with trio.open_nursery() as nursery:
            sensors = SenseHatWrapper(nursery, data=data)
            sensors.subscribe(notification_callbacks=[event_listener], error_callbacks=[error_listener])
            nursery.start_soon(sensors.a_run_notification_loop)
            nursery.start_soon(async_timer)

    trio.run(parent)
