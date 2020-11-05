from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
from systems.radiodetection import MickeyMouseDetection
from systems.traction_system import TractionSystem
import smbus
import trio

# ---- A/D CONFIG --------------------------
DEVICE_BUS = 1  # In Raspberry Pi 3+, bus 1 is used
DEVICE_ADDRESS = 0x48  # ADS1015 address (if ADDR = GND -> address 0x48)
ALERT_READY_PIN = 1  # ALERT/READY GPIO pin for ADS1015
# ------------------------------------------
# ---- TRACTION SYSTEM CONFIG --------------
ENABLE_TRACTION = True  # Set to False to ignore all TODO: implement ENABLE_TRACTION toggle
MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27
MOTOR_L_FORWARD_PIN = 23
MOTOR_L_BACKWARD_PIN = 24
MOTOR_L_ENABLE_PIN = 22
# ------------------------------------------


class ControlSystem:
    # ---- OPERATION MODES -----------------
    MODE_IDLE = "IDLE"
    MODE_AUTOMATIC = "AUTOMATIC"
    MODE_MANUAL = "MANUAL"  # TODO: Implement manual control
    MODE_TEST = "TEST"  # TODO: Implement testing modes
    # --------------------------------------
    # ---- SYSTEM STATES -------------------
    # Specific state within one mode
    SYSTEM_AUTO_FOLLOWING = "FOLLOWING"
    SYSTEM_AUTO_REACHED = "REACHED"
    # Missing extra states for undefined modes
    # --------------------------------------
    # ---- TRACTION STATES -----------------
    # Used in AUTOMATIC mode to introduce hysteresis to trajectory changes
    TRACTION_FORWARD = "FORWARD"
    TRACTION_BACKWARD = "BACKWARD"
    TRACTION_TURN_L = "LEFT"
    TRACTION_TURN_R = "RIGHT"
    TRACTION_IDLE = "IDLE"
    TRACTION_TRANSLATOR = {  # Translates from angle signs received from radio system into traction states
        0: TRACTION_FORWARD,
        1: TRACTION_TURN_L,
        -1: TRACTION_TURN_R,
        None: TRACTION_IDLE,
    }
    # --------------------------------------

    def __init__(self, nursery: trio.Nursery):
        self._nursery = nursery  # type: trio.Nursery
        self._operation_mode = ""
        self._system_state = ""

        self._tractor = TractionSystem(  # type: TractionSystem
            forward_r=MOTOR_R_FORWARD_PIN,
            backward_r=MOTOR_R_BACKWARD_PIN,
            enable_r=MOTOR_R_ENABLE_PIN,
            forward_l=MOTOR_L_FORWARD_PIN,
            backward_l=MOTOR_L_BACKWARD_PIN,
            enable_l=MOTOR_L_ENABLE_PIN
        )
        self._tractor.idle()
        self._traction_state = self.TRACTION_IDLE
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        self._adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=0)  # type: ADS1015
        self._radio_system = MickeyMouseDetection(self._adc, self._nursery)
        self._radio_system.subscribe(notification_callbacks=[radio_printer])  # DEBUG ONLY
        self._radio_system.subscribe(notification_callbacks=[self.radio_listener])

    async def initialize_components(self):
        self._nursery.start_soon(self._radio_system.a_run_notification_loop)

    async def radio_listener(self, source, param):
        if self._operation_mode != self.MODE_AUTOMATIC or self._system_state != self.SYSTEM_AUTO_FOLLOWING:
            return
        angle_sign = param.angle_sign
        translated_traction = self.TRACTION_TRANSLATOR[angle_sign]
        confidence = param.confidence

        if self._traction_state == translated_traction or confidence < 1:  # If no change is needed, don't change
            return

        self._traction_state = translated_traction
        if angle_sign is None:
            self._tractor.stop(1)
        elif angle_sign == 0:
            self._tractor.forward(0.8)
        else:
            self._tractor.turn(angle_sign*0.5)

    def _change_mode(self, mode):
        if mode == self.MODE_IDLE:  # Nothing to set up for idle mode (for now at least)
            self._operation_mode = self.MODE_IDLE
        elif mode == self.MODE_AUTOMATIC:
            self._operation_mode = self.MODE_AUTOMATIC
            # TODO: Implement RSSI measurements, and set STATE to REACHED initially (^^^)
            self._system_state = self.SYSTEM_AUTO_FOLLOWING
            self._traction_state = self.TRACTION_IDLE

        else:
            raise ValueError(f"Invalid or unimplemented operation mode: {mode}")


async def radio_printer(source, param):
    # For debugging purposes only
    print(f"New radio system event: ## {param.angle_sign} ##\t## {param.confidence}")


async def main():
    async with trio.open_nursery() as nursery:
        control = ControlSystem(nursery)
        input("Press enter to start...")
        nursery.start_soon(control.initialize_components)


trio.run(main)
