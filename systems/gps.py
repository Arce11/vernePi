import trio
import serial
import pynmea2
from typing import List, Union
from systems.event_source import AsyncEventSource, BaseEventArgs


class GPS(AsyncEventSource):
    """
    GPS module. Compatible with an event-based architecture (listeners are subscribed to GPS updates/errors),
    as well as with a polling-based architecture (latest GPS values are periodically checked externally).
    """
    LOCATION_EVENT = "LOCATION_EVENT"
    SATELLITE_LIST_EVENT = "SATELLITE_LIST_EVENT"

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

        self.location = None  # type: Union[pynmea2.GGA, None]
        self.visible_satellites = []  # type: List[SatelliteMeasurement]

        self._new_satellites = []  # New list of satellites being constructed (multiple NMEA sentences are required)
        self._is_running = False

    async def _a_receive_data(self, do_update=True):
        """
        Receives one NMEA sentence. If do_update is True, the stored data is updated. Asynchronous.
        """
        try:
            line = (await self._a_connection.readline()).decode("UTF-8")
            if do_update:
                await self._parse_line(line)
        except serial.SerialException as e:
            await self.raise_error(e)
        except UnicodeDecodeError as e:
            await self.raise_error(e)

    async def _a_flush_input(self):
        """
        Flushes UART input buffer, and reads until the next EOL, so that the next received
        NMEA sentence is guaranteed to be complete. Asynchronous.
        """
        try:
            self._connection.flushInput()
            await self._a_connection.readline()
        except serial.SerialException as e:
            await self.raise_error(e)

    async def _parse_line(self, line):
        try:
            msg = pynmea2.parse(line)
            if msg.sentence_type == "GGA":
                self.location = msg
                if self.location is not None:
                    await self.raise_event(LocationEventArgs(GPS.LOCATION_EVENT, self.location))

            elif msg.sentence_type == "GSV":
                await self._parse_gsv(msg)

        except pynmea2.ParseError as e:
            await self.raise_error(e)

    async def _parse_gsv(self, msg):
        try:
            total_msg = int(msg.num_messages)
            current_msg = int(msg.msg_num)
            if current_msg == 1:
                self._new_satellites = []
            if msg.sv_prn_num_1 != "":
                self._new_satellites.append(
                    SatelliteMeasurement(svid=msg.sv_prn_num_1,
                                         elevation_deg=msg.elevation_deg_1,
                                         azimuth=msg.azimuth_1,
                                         snr=msg.snr_1)
                )

                if msg.sv_prn_num_2 != "":
                    self._new_satellites.append(
                        SatelliteMeasurement(svid=msg.sv_prn_num_2,
                                             elevation_deg=msg.elevation_deg_2,
                                             azimuth=msg.azimuth_2,
                                             snr=msg.snr_2)
                    )

                    if msg.sv_prn_num_3 != "":
                        self._new_satellites.append(
                            SatelliteMeasurement(svid=msg.sv_prn_num_3,
                                                 elevation_deg=msg.elevation_deg_3,
                                                 azimuth=msg.azimuth_3,
                                                 snr=msg.snr_3)
                        )

                        if msg.sv_prn_num_4 != "":
                            self._new_satellites.append(
                                SatelliteMeasurement(svid=msg.sv_prn_num_4,
                                                     elevation_deg=msg.elevation_deg_4,
                                                     azimuth=msg.azimuth_4,
                                                     snr=msg.snr_4)
                            )

            if current_msg == total_msg:
                self.visible_satellites = self._new_satellites
                self._new_satellites = []
                await self.raise_event(VisibleSatellitesEventArgs(GPS.SATELLITE_LIST_EVENT, self.visible_satellites))

        except ValueError as e:
            await self.raise_error(e)

    def check_connection(self):
        """
        Synchronous check for connection health. Flushes UART input buffer.
        :return: True if connection with the GPS module is healthy, False otherwise
        """
        try:
            self._connection.flushInput()
            line = self._connection.readline()
            return len(line) > 0
        except serial.SerialException:
            return False

    async def a_run_update_loop(self):
        """
        Runs an infinite update loop on the stored data. Asynchronous.
        """
        self._new_satellites = []
        self._is_running = True
        await self._a_flush_input()
        while self._is_running:
            await self._a_receive_data()

    def stop_update_loop(self):
        """
        Stops the update loop on the stored data. If it is not running, it does nothing.
        """
        self._is_running = False


class SatelliteMeasurement:
    def __init__(self, svid: str, elevation_deg: str, azimuth: str, snr: str):
        # svid: Space Vehicle ID
        # Some fields may be empty
        self.svid = svid  # type: str
        self.elevation_deg = elevation_deg  # type: str
        self.azimuth = azimuth  # type: str
        self.snr = snr  # type: str


class LocationEventArgs(BaseEventArgs):
    def __init__(self, event_type: str, location: pynmea2.GGA):
        super().__init__(event_type)
        self.location = location  # type: pynmea2.GGA


class VisibleSatellitesEventArgs(BaseEventArgs):
    def __init__(self, event_type: str, satellite_list: List[SatelliteMeasurement]):
        super().__init__(event_type)
        self.satellite_list = satellite_list  # type: List[SatelliteMeasurement]


# Test Suite: Minimal working example
if __name__ == "__main__":
    # Simple async timer to run "in parallel" to all GPS shenanigans
    async def async_timer():
        counter = 0
        while True:
            print(f"### {counter}s ###")
            counter += 1
            await trio.sleep(1)

    async def event_listener(source, param):
        if type(param) is LocationEventArgs:
            print(f"New Location: {repr(param.location)}")
        elif type(param) is VisibleSatellitesEventArgs:
            print(f"New satellite list (length {len(param.satellite_list)}): {param.satellite_list}")

    async def error_listener(source, param):
        print(f"New Error: {param}")

    async def parent():
        async with trio.open_nursery() as nursery:
            gps = GPS("/dev/serial0", nursery)
            gps.subscribe(notification_callbacks=[event_listener], error_callbacks=[error_listener])
            nursery.start_soon(gps.a_run_update_loop)
            nursery.start_soon(async_timer)

    trio.run(parent)
