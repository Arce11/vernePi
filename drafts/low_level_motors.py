import gpiozero as gpio

MOTOR_R_FORWARD_PIN = 17
MOTOR_R_BACKWARD_PIN = 18
MOTOR_R_ENABLE_PIN = 27

MOTOR_L_FORWARD_PIN = 23
MOTOR_L_BACKWARD_PIN = 24
MOTOR_L_ENABLE_PIN = 22

#Setup pins
Backward_r = gpio.OutputDevice(MOTOR_R_BACKWARD_PIN) # On/Off output
Forward_r = gpio.OutputDevice(MOTOR_R_FORWARD_PIN) #On/Off output
SpeedPWM_r = gpio.PWMOutputDevice(MOTOR_R_ENABLE_PIN) # set up PWM pin

Backward_l = gpio.OutputDevice(MOTOR_L_BACKWARD_PIN) # On/Off output
Forward_l = gpio.OutputDevice(MOTOR_L_FORWARD_PIN) #On/Off output
SpeedPWM_l = gpio.PWMOutputDevice(MOTOR_L_ENABLE_PIN) # set up PWM pin

SpeedPWM_r.frequency = 200
SpeedPWM_l.frequency = 200

CONSTANT = 1


while True:

    directionFlag = input("set motor direction: ")
    if directionFlag == "back": # if user types "back" change direction of motor
        Backward_r.on() # Sets Backward Direction pin on
        Forward_r.off() # Sets Backward Direction pin on

        Backward_l.on() # Sets Backward Direction pin on
        Forward_l.off() # Sets Backward Direction pin on
    else:
        Backward_r.off() # Sets Backward Direction off
        Forward_r.on()   # Sets Backward Direction pin on
        Backward_l.off() # Sets Backward Direction off
        Forward_l.on()   # Sets Backward Direction pin on
    speedFlag_R = float(input("set speed (between 0-1000) R: ")) # Gets a number from the from the user
    speedFlag_L = float(input("set speed (between 0-1000) L: ")) # Gets a number from the from the user

    SpeedPWM_r.value = speedFlag_R/1000 # Sets the duty cycle of the PWM between 0-1
    SpeedPWM_l.value = speedFlag_L/1000 # Sets the duty cycle of the PWM between 0-1