from systems.ads1015 import ADS1015
from gpiozero import DigitalInputDevice
from systems.radiodetection import MickeyMouseDetection
from systems.traction_system import TractionSystem
import smbus
import trio

# ---- A/D CONFIG --------------------------
DEVICE_BUS = 1  # En RaspPi 3+, el bus I2C utilizado es el bus 1
DEVICE_ADDRESS = 0x48  # Dirección usada por el integrado ADS1015 (si ADDR = GND => dirección 0x48)
ALERT_READY_PIN = 1  # Pin al que está conectado el pin ALERT/READY del integrado ADS1015
# ------------------------------------------
# ---- TRACTION SYSTEM CONFIG --------------
MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27
MOTOR_L_FORWARD_PIN = 23
MOTOR_L_BACKWARD_PIN = 24
MOTOR_L_ENABLE_PIN = 22
# ------------------------------------------
# ---- TRACTION CALIBRATION ----------------

TURN_CONF_THRESHOLD = 0.7
STRAIGHT_CONF_THRESHOLD = 0.7
# ------------------------------------------

class ControlSystem:
    def __init__(self, nursery: trio.Nursery):
        self._nursery = nursery  # type: trio.Nursery
        self._tractor = TractionSystem(  # type: TractionSystem
            forward_r=MOTOR_R_FORWARD_PIN,
            backward_r=MOTOR_R_BACKWARD_PIN,
            enable_r=MOTOR_R_ENABLE_PIN,
            forward_l=MOTOR_L_FORWARD_PIN,
            backward_l=MOTOR_L_BACKWARD_PIN,
            enable_l=MOTOR_L_ENABLE_PIN
        )
        alert_ready = DigitalInputDevice(ALERT_READY_PIN, pull_up=True)
        bus = smbus.SMBus(DEVICE_BUS)
        self._adc = ADS1015(bus, DEVICE_ADDRESS, alert_ready, channel=0)  # type: ADS1015
        self._radio_system = MickeyMouseDetection(self._adc, self._nursery)
        self._radio_system.subscribe(notification_callbacks=[self.radio_printer])  # DEBUG ONLY
        self._radio_system.subscribe(notification_callbacks=[self.radio_listener])


    async def initialize_components(self):
        self._nursery.start_soon(self._radio_system.a_run_notification_loop)

    async def radio_listener(self, source, param):
        angle_sign = param.angle_sign
        confidence = param.confidence

        if angle_sign is None:
            self._tractor.stop(1)
        elif angle_sign == 0:
            self._tractor.forward(0.8)
        else:
            self._tractor.turn(angle_sign*0.5)

    async def radio_printer(self, source, param):
        print(f"New radio system event: ## {param.angle_sign} ##\t## {param.confidence}")


async def main():
    async with trio.open_nursery() as nursery:
        control = ControlSystem(nursery)
        input("Press enter to start...")
        nursery.start_soon(control.initialize_components)


trio.run(main)