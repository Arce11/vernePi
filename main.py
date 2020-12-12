# External dependencies
import smbus
import trio
from gpiozero import DigitalInputDevice
from systems.traction_system import TractionSystem
from systems.battery_measure import BatteryEventArgs
from systems.current_measure import CurrentEventArgs
from systems.gps import LocationEventArgs, VisibleSatellitesEventArgs
from systems.server import ServerErrorArgs
from systems.commands import CommandSystem, CommandEventArgs
from systems.receptor import ReceptorEventArgs


# ---- DEBUG CONFIG -----------------------
DEBUG_ADC = True
DEBUG_RADIOSYSTEM = True
DEBUG_SENSORS = True
DEBUG_BATTERY = True
DEBUG_CURRENT = True
DEBUG_GPS = True
DEBUG_TRANSCEIVER = True
DEBUG_SERVER = False
# ------------------------------------------
# ---- SERVER CONFIG -----------------------
ROVER_ID = 'verne'
SERVER_ADDRESS = '192.168.137.1'
SERVER_PORT = 80
COMMAND_PORT = 8000
# ------------------------------------------
# ---- A/D CONFIG --------------------------
DEVICE_BUS = 1  # In Raspberry Pi 3+, bus 1 is used
DEVICE_ADDRESS = 0x48  # ADS1015 address (if ADDR = GND -> address 0x48)
ALERT_READY_PIN = 26  # ALERT/READY GPIO pin for ADS1015
RADIO_CHANNEL = 0
BATTERY_CHANNEL = 3
CURRENT_CHANNEL = 1
# ------------------------------------------
# ---- TRACTION SYSTEM CONFIG --------------
DRIVER_ENABLE_PIN = 12
MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27
MOTOR_L_FORWARD_PIN = 5
MOTOR_L_BACKWARD_PIN = 6
MOTOR_L_ENABLE_PIN = 13
# ------------------------------------------
# ---- SENSE HAT PINS (FIXED) --------------
# 5V, 3V3, GND
# SDA (GPIO 2)
# SCL (GPIO 3)
# ID_SD (GPIO 0)
# ID_SC (GPIO 1)
# GPIO 8
# GPIO 23
# GPIO 24
# GPIO 25
# ------------------------------------------
# ---------- GPS PINS (FIXED) --------------
# 3V3/5V, GND
# TXD (GPIO 14)
# RXD (GPIO 15)
# GPS_PORT = "/dev/serial0"  # Raspberry Pi 4
GPS_PORT = "/dev/ttyS0"  # Raspberry Pi 3
# ------------------------------------------
# ---- TX/RX PINS (SPI0) -------------------
# SPI0 MOSI (GPIO 10)
# SPI0 MISO (GPIO 9)
# SPI0 SCLK (GPIO 11)
# SPI0 CE1 (GPIO 7)
# SPI0 CE0 (GPIO 8) ---- ??????
CE_PIN = 7  # SPI CE 1
RX_INTERRUPTION_PIN = 16
TX_DEVICE = 1

# ------------------------------------------

# --------- DEBUG IMPORTS ------------------
if DEBUG_ADC:
    from systems.ads1015 import DummyADS1015 as ADS1015
else:
    from systems.ads1015 import ADS1015
if DEBUG_RADIOSYSTEM:
    from systems.radiodetection import DummyRadioDetection as RadioDetection
else:
    from systems.radiodetection import RadioDetection
if DEBUG_SENSORS:
    from systems.sensors import DummySenseHatWrapper as SenseHatWrapper
else:
    from systems.sensors import SenseHatWrapper
if DEBUG_GPS:
    from systems.gps import DummyGPS as GPS
else:
    from systems.gps import GPS
if DEBUG_TRANSCEIVER:
    from systems.receptor import DummyReceptorSystem as ReceptorSystem
else:
    from systems.receptor import ReceptorSystem
if DEBUG_BATTERY:
    from systems.battery_measure import DummyBatteryMeasure as BatteryMeasure
else:
    from systems.battery_measure import BatteryMeasure
if DEBUG_CURRENT:
    from systems.current_measure import DummyCurrentMeasure as CurrentMeasure
else:
    from systems.current_measure import CurrentMeasure
if DEBUG_SERVER:
    from systems.server import DummyServer as Server
else:
    from systems.server import Server
# ------------------------------------------


class ControlSystem:
    # ---- OPERATION MODES -----------------
    MODE_IDLE = "IDLE"
    MODE_AUTOMATIC = "AUTOMATIC"
    MODE_MANUAL = "MANUAL"
    MODE_BATTERY_SAVER = "BATTERY_SAVER"
    MODE_CURRENT_PROTECTION = "CURRENT_PROTECTION"
    # --------------------------------------
    # ---- SYSTEM STATES -------------------
    # Specific state within one mode
    SYSTEM_AUTO_FOLLOWING = "FOLLOWING"
    SYSTEM_AUTO_REACHED = "REACHED"
    SYSTEM_AUTO_NOTFOUND = "NOT_FOUND"
    # Missing extra states for undefined modes
    # --------------------------------------
    # ---- RADIO RSSI THRESHOLDS -----------
    RSSI_STOP_THRESHOLD = -79
    RSSI_FOLLOW_THRESHOLD = -85
    RSSI_GIVEUP_THRESHOLD = -105
    # --------------------------------------
    # ---- BATTERY & CURRENT THRESHOLDS ----
    BATTERY_SAVER_THRESHOLD = 10 # %
    CURRENT_PROTECTION_THRESHOLD = 1.4  # A, max motor current
    # --------------------------------------
    # ---- TRACTION TRANSLATION ------------
    # Used in AUTOMATIC mode to transform angle values into traction states
    TRACTION_TRANSLATOR = {  # Translates from angle signs received from radio system into traction states
        0: TractionSystem.FORWARD_STATE,
        1: TractionSystem.TURN_LEFT_STATE,
        -1: TractionSystem.TURN_RIGHT_STATE,
        None: TractionSystem.IDLE_STATE,
    }
    # --------------------------------------

    def __init__(self, nursery: trio.Nursery):
        self._nursery = nursery  # type: trio.Nursery
        self._operation_mode = None
        self._system_state = None
        self._sensor_data = {
            'temperature': None,
            'pressure': None,
            'humidity': None,
            'num_satellites': None,
            'latitude': None,
            'longitude': None,
            'altitude': None,
            'message': None,
            'rssi': None,
            'session_state': None,
            'session_substate': None,
            'battery': None,
            'motor_current': None
        }

        # Traction system ----------------
        self._tractor = TractionSystem(  # type: TractionSystem
            forward_r=MOTOR_R_FORWARD_PIN,
            backward_r=MOTOR_R_BACKWARD_PIN,
            enable_r=MOTOR_R_ENABLE_PIN,
            forward_l=MOTOR_L_FORWARD_PIN,
            backward_l=MOTOR_L_BACKWARD_PIN,
            enable_l=MOTOR_L_ENABLE_PIN,
            enable_global=DRIVER_ENABLE_PIN
        )

        # ADC -----------------------------
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        self._adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=RADIO_CHANNEL)  # type: ADS1015

        # Radio System -------------------
        self._radio_system = RadioDetection(self._adc, self._nursery, notification_callbacks=[self.radio_listener])
        # self._radio_system.subscribe(notification_callbacks=[radio_printer])  # DEBUG ONLY

        # SenseHat ------------------------
        self._sensors = SenseHatWrapper(nursery, data=self._sensor_data)

        # GPS -----------------------------
        # Lat/long/alt data is updated automatically, the satellite list is not used for now
        self._gps = GPS(GPS_PORT, nursery, data=self._sensor_data)

        # Transceiver --------------------
        self._transceiver = ReceptorSystem(RX_INTERRUPTION_PIN, TX_DEVICE, nursery,
                                           notification_callbacks=[self.transceiver_listener], data=self._sensor_data)

        # Battery & current measurements -----------
        self._battery = BatteryMeasure(nursery, self._adc, BATTERY_CHANNEL, data=self._sensor_data)
        self._battery.subscribe(notification_callbacks=[self.battery_listener])
        self._current_meas = CurrentMeasure(nursery, self._adc, CURRENT_CHANNEL, data=self._sensor_data)
        self._current_meas.subscribe(notification_callbacks=[self.current_listener])

        # Server -------------------------
        self._server = Server(SERVER_ADDRESS, SERVER_PORT, self._sensor_data, ROVER_ID, nursery,
                              error_callbacks=[self.server_error])

        # Command system -----------------
        self._commands = CommandSystem(COMMAND_PORT, nursery, notification_callbacks=[self.command_listener])

        # --------------- Start in idle mode ------------
        self._change_mode(self.MODE_IDLE)


    async def initialize_components(self):
        self._nursery.start_soon(self._radio_system.a_run_notification_loop)
        self._nursery.start_soon(self._gps.a_run_notification_loop)
        self._nursery.start_soon(self._sensors.a_run_notification_loop)
        self._nursery.start_soon(self._battery.a_run_notification_loop)
        self._nursery.start_soon(self._current_meas.a_run_notification_loop)
        self._nursery.start_soon(self._transceiver.a_run_notification_loop)
        self._nursery.start_soon(self._server.initialize_session, True)
        self._nursery.start_soon(self._commands.run)
        self._tractor.toggle_enable(True)

        self._nursery.start_soon(self.visualize_data_values)  # DEBUG
        self._change_mode(self.MODE_AUTOMATIC)

    async def radio_listener(self, source, param):
        if self._operation_mode != self.MODE_AUTOMATIC or self._system_state != self.SYSTEM_AUTO_FOLLOWING:
            return
        angle_sign = param.angle_sign
        translated_traction = self.TRACTION_TRANSLATOR[angle_sign]
        is_confident = param.is_confident

        if self._tractor.state == translated_traction or not is_confident:  # If no change is needed, don't change
            return

        if angle_sign is None:
            self._tractor.stop(1)
        elif angle_sign == 0:
            self._tractor.forward(1)
        else:
            self._tractor.turn(angle_sign*0.8)

    async def battery_listener(self, source, param: BatteryEventArgs):
        if param.data['battery'] < self.BATTERY_SAVER_THRESHOLD and self._operation_mode != self.MODE_BATTERY_SAVER:
            self._change_mode(self.MODE_BATTERY_SAVER)

    async def current_listener(self, source, param: CurrentEventArgs):
        if param.data['motor_current'] > self.CURRENT_PROTECTION_THRESHOLD and self._operation_mode != self.MODE_CURRENT_PROTECTION:
            previous_mode = self._operation_mode
            self._change_mode(self.MODE_CURRENT_PROTECTION)
            self._nursery.start_soon(schedule, self._change_mode, 3, previous_mode)

    async def transceiver_listener(self, source, param: ReceptorEventArgs):
        if self._operation_mode != self.MODE_AUTOMATIC:
            return
        rssi = param.data['rssi']
        if rssi < self.RSSI_GIVEUP_THRESHOLD:
            self._change_state(self.SYSTEM_AUTO_NOTFOUND)
            self._tractor.idle()
        elif rssi < self.RSSI_FOLLOW_THRESHOLD:
            self._change_state(self.SYSTEM_AUTO_FOLLOWING)
        elif rssi > self.RSSI_STOP_THRESHOLD \
                or (rssi > self.RSSI_FOLLOW_THRESHOLD and self._system_state == self.SYSTEM_AUTO_NOTFOUND):
            self._change_state(self.SYSTEM_AUTO_REACHED)
            self._tractor.idle()

    async def command_listener(self, source, param: CommandEventArgs):
        command_data = param.data
        print(f"Received command: {command_data}")
        if not "command" in command_data:
            print("!!!! INVALID COMMAND")
            return
        if command_data['command'] == CommandSystem.DIRECTION_COMMAND:
            if self._operation_mode != self.MODE_MANUAL:
                return
            if "param" not in command_data:
                print("!!!! INVALID COMMAND")
                return
            if command_data["param"] == CommandSystem.DIRECTION_STOP:
                self._tractor.stop(1)
            elif command_data["param"] == CommandSystem.DIRECTION_LEFT:
                self._tractor.turn(0.8)
            elif command_data["param"] == CommandSystem.DIRECTION_RIGHT:
                self._tractor.turn(-0.8)
            elif command_data["param"] == CommandSystem.DIRECTION_FORWARDS:
                self._tractor.forward(1)
            elif command_data["param"] == CommandSystem.DIRECTION_BACKWARDS:
                self._tractor.backward(1)
            else:
                print("!!!! INVALID DIRECTION")
            print(f"NEW MANUAL DIRECTION SET: {self._tractor.state}")

        elif command_data['command'] == CommandSystem.MODE_COMMAND:
            if "param" not in command_data:
                print("!!!! INVALID COMMAND")
                return
            self._change_mode(command_data["param"])

        elif command_data['command'] == CommandSystem.SESSION_COMMAND:
            self._nursery.start_soon(self._server.initialize_session, True)
        else:
            print("!!!! UNKNOWN COMMAND")


    async def server_error(self, source, param: ServerErrorArgs):
        error_code = param.event_type
        was_running = param.is_server_running
        if error_code == Server.CONNECTION_ERROR:
            print("!!!! DETECTED SERVER CONNECTION ERROR")
            if was_running:  # If it was already running, try to reconnect
                self._nursery.start_soon(self._server.a_run_update_loop)
            else:  # If it was not running (disconnected from the start) try to initialize again
                self._nursery.start_soon(self._server.initialize_session)
        elif error_code == Server.SESSION_REGISTER_ERROR:
            # This should never happen. If it does, this will probably not fix it, but will at least print the error
            print("!!!! DETECTED SERVER REGISTRATION ERROR")
            self._nursery.start_soon(self._server.initialize_session)
        elif error_code == Server.SESSION_UPDATE_ERROR:
            # This does not even interrupt the update loop.
            print("!!!! DETECTED SERVER UPDATE ERROR")
        else:
            print(f"!!!! DETECTED UNKNOWN SERVER ERROR: {error_code}. WasRunning: {was_running}")


    def _change_mode(self, mode):
        if self._operation_mode == self.MODE_BATTERY_SAVER:
            print("Could not change mode - Currently in battery saver")
            return
        if mode == self.MODE_IDLE:  # Nothing to set up for idle mode (for now at least)
            self._operation_mode = self.MODE_IDLE
            self._change_state(None)
            self._tractor.idle()
            self._tractor.toggle_enable(False)
        elif mode == self.MODE_AUTOMATIC:
            self._operation_mode = self.MODE_AUTOMATIC
            self._change_state(self.SYSTEM_AUTO_NOTFOUND)
            self._tractor.idle()
            self._tractor.toggle_enable(True)
        elif mode == self.MODE_MANUAL:
            self._operation_mode = self.MODE_MANUAL
            self._change_state(None)
            self._tractor.idle()
            self._tractor.toggle_enable(True)
        elif mode == self.MODE_CURRENT_PROTECTION:
            self._operation_mode = self.MODE_CURRENT_PROTECTION
            self._change_state(None)
            self._tractor.idle()
            self._tractor.toggle_enable(False)
        elif mode == self.MODE_BATTERY_SAVER:
            self._operation_mode = self.MODE_MANUAL
            self._change_state(None)
            self._tractor.idle()
            self._tractor.toggle_enable(False)

        else:
            print(f"!!!! Invalid or unimplemented operation mode: {mode}")

        print(f"### NEW MODE: {self._operation_mode}")
        self._sensor_data['session_state'] = self._operation_mode

    def _change_state(self, new_state):
        self._system_state = new_state
        self._sensor_data['session_substate'] = new_state

    async def visualize_data_values(self):
        """
        Periodically shows the sensor data values.
        ONLY FOR DEBUGGING
        """
        counter = 0
        while True:
            print(f"### {counter}s ###  Data: {self._sensor_data}")
            counter += 1
            await trio.sleep(1)


async def schedule(function, scheduled_time, *args, **kwargs):
    await trio.sleep(scheduled_time)
    function(*args, **kwargs)


async def radio_printer(source, param):
    # For debugging purposes only
    print(f"New radio system event: ## {param.angle_sign} ##\t## {param.is_confident}")


async def main():
    async with trio.open_nursery() as nursery:
        control = ControlSystem(nursery)
        input("Press enter to start...")
        nursery.start_soon(control.initialize_components)


trio.run(main)
