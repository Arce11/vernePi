from collections import OrderedDict

from gpiozero import SourceMixin, CompositeDevice, GPIOPinMissing, PWMOutputDevice, DigitalOutputDevice, \
    OutputDeviceBadValue


class Motor(SourceMixin, CompositeDevice):
    """
    Extends :class:`CompositeDevice` and represents a generic motor
    connected to a bi-directional motor driver circuit (i.e. an `H-bridge`).

    Inspired from gpiozero's Motor implementation

    The following code will make the motor turn "forwards"::

        from gpiozero import Motor

        motor = Motor(17, 18)
        motor.forward()

    :type forward: int or str
    :param forward:
        The GPIO pin that the forward input of the motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIODeviceError` will be raised.

    :type backward: int or str
    :param backward:
        The GPIO pin that the backward input of the motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIODeviceError` will be raised.

    :type enable: int or str
    :param enable:
        The GPIO PWM pin that enables the motor. See :ref:`pin-numbering` for
        valid pin numbers. If this is :data:`None` a :exc:`GPIODeviceError`
        will be raised.

    :type pin_factory: Factory or None
    :param pin_factory:
        See :doc:`api_pins` for more information (this is an advanced feature
        which most users can ignore).
    """

    def __init__(self, forward=None, backward=None, enable=None, pin_factory=None):
        if not all(p is not None for p in [forward, backward, enable]):
            raise GPIOPinMissing(
                'enable, forward and backward pins must be provided'
            )
        devices = OrderedDict((
            ('forward_device', DigitalOutputDevice(forward, initial_value=False)),
            ('backward_device', DigitalOutputDevice(backward, initial_value=False)),
            ('enable_device', PWMOutputDevice(enable, frequency=100))
        ))
        super(Motor, self).__init__(_order=devices.keys(), **devices)

    @property
    def value(self):
        """
        Represents the speed of the motor as a floating point value between -1
        (full speed backward) and 1 (full speed forward), with 0 representing
        stopped.
        """
        if self.forward_device.value and not self.backward_device.value:
            return self.enable_device.value
        elif not self.forward_device.value and self.backward_device.value:
            return -self.enable_device.value
        else:
            return 0

    @value.setter
    def value(self, value):
        if not -1 <= value <= 1:
            raise OutputDeviceBadValue("Motor value must be between -1 and 1")
        if value > 0:
            try:
                self.forward(value)
            except ValueError as e:
                raise OutputDeviceBadValue(e)
        elif value < 0:
            try:
                self.backward(-value)
            except ValueError as e:
                raise OutputDeviceBadValue(e)
        else:
            self.stop()

    @property
    def is_active(self):
        """
        Returns :data:`True` if the motor is currently running and
        :data:`False` otherwise.
        """
        return self.value != 0

    def forward(self, speed=1):
        """
        Drive the motor forwards.

        :param float speed:
            The speed at which the motor should turn. Can be any value between
            0 (stopped) and the default 1 (maximum speed).
        """
        if not 0 <= speed <= 1:
            raise ValueError('forward speed must be between 0 and 1')

        self.backward_device.off()
        self.forward_device.on()
        self.enable_device.value = speed

    def backward(self, speed=1):
        """
        Drive the motor backwards.

        :param float speed:
            The speed at which the motor should turn. Can be any value between
            0 (stopped) and the default 1 (maximum speed).
        """
        if not 0 <= speed <= 1:
            raise ValueError('backward speed must be between 0 and 1')

        self.backward_device.on()
        self.forward_device.off()
        self.enable_device.value = speed

    def reverse(self):
        """
        Reverse the current direction of the motor. If the motor is currently
        idle this does nothing. Otherwise, the motor's direction will be
        reversed at the current speed.
        """
        self.value = -self.value

    def stop(self, brake_force=1):
        """
        Engages motor brakes.
        :param float brake_force:
            The intensity of the brakes (PWM duty). Can be any value between 0
            (no brakes) and the default 1 (full breaks).
        """
        if not 0 <= brake_force <= 1:
            raise ValueError('brake force must be between 0 and 1')
        self.forward_device.off()
        self.backward_device.off()
        self.enable_device.value = brake_force

    def idle(self):
        """
        Stops motor action, turning off the enable (PWM) signal.
        """
        self.value = 0


# Simple unit test for the traction system
if __name__ == "__main__":
    MOTOR_R_FORWARD_PIN = 17
    MOTOR_R_BACKWARD_PIN = 18
    MOTOR_R_ENABLE_PIN = 27
    MOTOR_L_FORWARD_PIN = 23
    MOTOR_L_BACKWARD_PIN = 24
    MOTOR_L_ENABLE_PIN = 22

    motor_r = Motor(
        forward=MOTOR_R_FORWARD_PIN,
        backward=MOTOR_R_BACKWARD_PIN,
        enable=MOTOR_R_ENABLE_PIN
    )

    while True:
        action = input("Set action: ")
        if action == "F":
            motor_r.forward(float(input("Value: ")))
        elif action == "B":
            motor_r.backward(float(input("Value: ")))
        elif action == "S":
            motor_r.stop(float(input("Value: ")))
        elif action == "R":
            motor_r.reverse()
        elif action == "V":
            print(f"Current value: {motor_r.value}")
        else:
            motor_r.value = float(input("Value: "))

        print("\n")
