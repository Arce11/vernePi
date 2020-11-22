from systems.ads1015 import ADS1015
from systems.traction_system import TractionSystem
from gpiozero import DigitalInputDevice
import smbus
import time
import statistics

I2C_BUS = 1 
DEVICE_I2C_ADDRESS = 0x48
ALERT_READY_SIGNAL = 16

ready_signal = DigitalInputDevice(ALERT_READY_SIGNAL, pull_up=True)
i2c_bus = smbus.SMBus(1)
adc = ADS1015(i2c_bus, DEVICE_I2C_ADDRESS, ready_signal)

fifo = [0] * 10
print(f" Old config: {adc.read_config()} \n")

counter = 0
current_state = 'straight'
threshold = {
    'left' : 0.5,
    'straight' : 0.1,
    'right' : 0.5
}
straight_voltage = 0.9

MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27
MOTOR_L_FORWARD_PIN = 23
MOTOR_L_BACKWARD_PIN = 24
MOTOR_L_ENABLE_PIN = 22

tractor = TractionSystem( forward_r=MOTOR_R_FORWARD_PIN, backward_r=MOTOR_R_BACKWARD_PIN,
                          enable_r=MOTOR_R_ENABLE_PIN, forward_l=MOTOR_L_FORWARD_PIN,
                          backward_l=MOTOR_L_BACKWARD_PIN, enable_l=MOTOR_L_ENABLE_PIN)

while True:
    phase_diff_voltage = adc.read_single_shot_debug(0, 6.144, 490)
    fifo[1:10] = fifo[0:9]
    fifo[0] = phase_diff_voltage
    avg = statistics.mean(fifo)
    counter += 1
    error = avg - straight_voltage
    if current_state == 'left':
        if error < -threshold['left']:
            current_state = 'left'
        else:
            current_state = 'straight'
    elif current_state == 'right':
        if error > threshold['right']:
            current_state = 'right'
        else:
            current_state = 'straight'
    elif current_state == 'straight':
        if error < -threshold['straight']:
            current_state = 'left'
        elif error > threshold['straight']:
            current_state = 'right'

    if current_state == 'straight':
        print('Hacia adelante')
        tractor.forward(0.25)
    elif current_state == 'left':
        print('Hacia la izquierda')
        tractor.turn(0.25)
    elif current_state == 'right':
        print('Hacia la derecha')
        tractor.turn(-0.25)

    if counter % 10 == 0:
        print(f"Actual: {phase_diff_voltage} V \t Media: {avg} V")
    time.sleep(0.05)
