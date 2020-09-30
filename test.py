import gpiozero as gpio

print("Hello world!!!!!!!!")
pwm_out = gpio.PWMLED(18, initial_value=0, frequency=100)

while True:
    duty = float(input("Duty cycle: "))
    pwm_out.value = duty

