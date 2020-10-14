import gpiozero as gpio

# Sends PWM signal on the MOTOR_X_FORWARD_PIN (value>0) or the MOTOR_X_BACKWARD_PIN (value<0)
# Invalid for our use (should send PWM through MOTOR_X_ENABLE_PIN)

MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27

MOTOR_L_FORWARD_PIN = 22
MOTOR_L_BACKWARD_PIN = 23
MOTOR_L_ENABLE_PIN = 24

right_motor = gpio.Motor(forward=MOTOR_R_FORWARD_PIN, backward=MOTOR_R_BACKWARD_PIN, enable=MOTOR_R_ENABLE_PIN)
left_motor = gpio.Motor(forward=MOTOR_L_FORWARD_PIN, backward=MOTOR_L_BACKWARD_PIN, enable=MOTOR_L_ENABLE_PIN)

while True:
    r_value = float(input("Right motor value: "))
    l_value = float(input("Left motor value: "))
    right_motor.value = r_value
    left_motor.value = l_value

    print("\n")
    cmd = input("Enter a command (blank to do nothing): ")
    if cmd == "stop":
        right_motor.stop()
        left_motor.stop()
    elif cmd == "reverse":
        right_motor.reverse()
        left_motor.reverse()
