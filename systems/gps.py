import trio
import serial
import pynmea2
import io
from systems.event_source import AsyncEventSource


class GPS(AsyncEventSource):
    """
    TBD: Implement "event" calls on data update, or rely on polling?
    """
    def __init__(self, port, nursery, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        if port is None:
            raise ValueError('port cannot be None')
        try:
            self._connection = serial.Serial(port, 9600, timeout=5.0)
            self._a_connection = trio.wrap_file(self._connection)
        except serial.SerialException:
            print("ERROR initializing GPS module")
            raise

        self.coordinates = None  # None when no location fix is available
        self.visible_satellites = {}  # Empty when no satellites are visible
        self._is_running = False
        self._is_notifying = False

    def _receive_data(self, do_update=True):
        """
        Receives one NMEA sentence. If do_update is True, the stored data is updated.
        :return: Raw byte array, with the encoded message
        """
        pass

    async def _a_receive_data(self, do_update=True):
        """
        Receives one NMEA sentence. If do_update is True, the stored data is updated. Asynchronous.
        :return: Raw byte array, with the encoded message
        """
        pass

    async def _a_flush_input(self):
        """
        Flushes UART input buffer, and reads until the next EOL, so that the next received
        NMEA sentence is guaranteed to be complete. Asynchronous.
        """
        self._connection.flushInput()
        await self._a_connection.readline()

    def check_connection(self):
        """
        Synchronous check for connection health. Flushes UART input buffer.
        :return: True if connection with the GPS module is healthy, False otherwise
        """
        self._connection.flushInput()

        pass

    async def a_run_update_loop(self):
        """
        Runs an infinite update loop on the stored data. Asynchronous.
        """
        pass

    async def a_run_notify_loop(self, period):
        """
        Runs an loop periodically sending an update notification to the passed. Asynchronous.
        """
        pass

    def stop_update_loop(self):
        """
        Stops the update loop on the stored data. If it is not running, it does nothing.
        """
        self._is_running = False

    def stop_notify_loop(self):
        """
        Stops the notification loop. If it is not running, it does nothing.
        """
        self._is_notifying = False

