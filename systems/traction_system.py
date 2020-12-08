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

    @property
    def is_braking(self):
        """
        Returns :data:`True` if the motor is currently braking
        :data:`False` otherwise.
        """
        return self.backward_device.value ==0 and self.forward_device.value ==0

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
        Stops motor action, turning off the enable (PWM) signal. Must be done
        before turning off power to the driver.
        """
        self.value = 0


class TractionSystem:
    """
    :type forward_r: int or str
    :param forward_r:
        The GPIO pin that the forward input of the right motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type backward_r: int or str
    :param backward_r:
        The GPIO pin that the backward input of the right motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type enable_r: int or str
    :param forward_r:
        The GPIO pin that the enable input of the right motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type forward_l: int or str
    :param forward_l:
        The GPIO pin that the forward input of the left motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type backward_l: int or str
    :param backward_l:
        The GPIO pin that the backward input of the left motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type enable_l: int or str
    :param enable_l:
        The GPIO pin that the enable input of the left motor driver chip is
        connected to. See :ref:`pin-numbering` for valid pin numbers. If this
        is :data:`None` a :exc:`GPIOPinMissing` will be raised.

    :type enable_global: int or str
    :param enable_global:
        GPIO pin that controlls power supply to the traction driver. If this is
        :data:`None` a :exc:`GPIOPinMissing` will be raised.
    """
    # Scale multipliers to compensate motor thrusts. All <=1
    _R_FORWARD_SCALE = 0.69    # Scale to right-motor PWM when going forwards
    _R_BACKWARD_SCALE = 0.69   # Scale to right-motor PWM when going backwards
    _R_RIGHT_SCALE = 1      # Scale to right-motor PWM when turning right
    _R_LEFT_SCALE = 1       # Scale to right-motor PWM when turning left (1 should be fine)
    _L_FORWARD_SCALE = 1
    _L_BACKWARD_SCALE = 1
    _L_RIGHT_SCALE = 1      # (1 should be fine)
    _L_LEFT_SCALE = 1
    FORWARD_STATE = "FORWARD"
    BACKWARD_STATE = "BACKWARD"
    TURN_LEFT_STATE = "TURN_LEFT"
    TURN_RIGHT_STATE = "TURN_RIGHT"
    STOPPED_STATE = "STOPPED"
    IDLE_STATE = "IDLE"
    UNKNOWN_STATE = "UNKNOWN"

    def __init__(self, forward_r=None, backward_r=None, enable_r=None, forward_l=None, backward_l=None, enable_l=None,
                 enable_global=None):
        required = [forward_r, backward_r, enable_r, forward_l, backward_l, enable_l, enable_global]
        if not all(p is not None for p in required):
            raise GPIOPinMissing(
                'enable, forward and backward pins must be provided for both motors'
            )

        self._right_motor = Motor(
            forward=forward_r,
            backward=backward_r,
            enable=enable_r
        )
        self._left_motor = Motor(
            forward=forward_l,
            backward=backward_l,
            enable=enable_l
        )
        self._enable = DigitalOutputDevice(enable_global)
        self._enable.off()

    @property
    def is_active(self):
        """
        Returns :data:`True` if any motor is currently running and
        :data:`False` otherwise.
        """
        return self._right_motor.value != 0 or self._left_motor.value

    @property
    def is_enabled(self):
        """
        Returns :data:`True` if the global enable pin is active, and
        :data:`False` otherwise
        """
        return self._enable.value == 1

    @property
    def state(self):
        """
        Returns the current state of the traction system. Possible values:
            "FORWARD" if both motors are going forwards
            "BACKWARD" if both motors are going backwards
            "TURN_LEFT" if the right motor goes forward and the left one does not
            "TURN_RIGHT" if the left motor goes forward and the right one does not
            "STOPPED" if both motors are stopped
            "IDLE" if both motors are idle (disconnected)
            "UNKNOWN" if any other (should not happen)
        """
        if self._right_motor.value > 0 and self._left_motor.value > 0:
            return self.FORWARD_STATE
        elif self._right_motor.value < 0 and self._left_motor.value < 0:
            return self.BACKWARD_STATE
        elif self._right_motor.value > 0 and self._left_motor.value <= 0:
            return self.TURN_LEFT_STATE
        elif self._right_motor.value <= 0 and self._left_motor.value > 0:
            return self.TURN_RIGHT_STATE
        elif self._right_motor.is_braking and self._left_motor.is_braking:
            return self.STOPPED_STATE
        elif not self._right_motor.is_active and not self._left_motor.is_active:
            return self.IDLE_STATE
        else:
            return self.UNKNOWN_STATE

    def toggle_enable(self, value: bool):
        self._enable.value = 1 if value else 0
        if self.is_enabled:
            print("DRIVER ENABLED")
        else:
            print("DRIVER DISABLED")

    def forward(self, speed=1):
        """
        Drive the system forwards.

        :param float speed:
            The speed at which the system should move. Can be any value between
            0 (stopped) and the default 1 (maximum speed).
        """
        if not 0 <= speed <= 1:
            raise ValueError('forward speed must be between 0 and 1')

        self._right_motor.forward(speed * self._R_FORWARD_SCALE)
        self._left_motor.forward(speed * self._L_FORWARD_SCALE)

    def backward(self, speed=1):
        """
        Drive the system backwards.

        :param float speed:
            The speed at which the system should move. Can be any value between
            0 (stopped) and the default 1 (maximum speed).
        """
        if not 0 <= speed <= 1:
            raise ValueError('backward speed must be between 0 and 1')

        self._right_motor.backward(speed*self._R_BACKWARD_SCALE)
        self._left_motor.backward(speed*self._L_BACKWARD_SCALE)

    def stop(self, brake_force=1):
        """
        Engages system brakes, symmetrically on both motors.
        :param float brake_force:
            The intensity of the brakes (PWM duty). Can be any value between 0
            (no brakes) and the default 1 (full breaks).
        """
        if not 0 <= brake_force <= 1:
            raise ValueError('brake force must be between 0 and 1')
        self._right_motor.stop(brake_force)
        self._left_motor.stop(brake_force)

    def idle(self):
        """
        Stops system action, turning off the enable (PWM) signals. Must be done
        before turning off power to the driver.
        """
        self._right_motor.idle()
        self._left_motor.idle()

    def turn(self, direction):
        """
        Starts turning motion, with one motor forwards and the other backwards
        :param float direction:
            Between 0 and 1 for a counter-clockwise turn, and between -1 and 0
            for a clockwise one. +-1 sets the turning speed to the maximum
        """
        if not -1 <= direction <= 1:
            raise ValueError('direction')

        if direction < 0:  # Clockwise (right turn)
            self._left_motor.forward(-direction * self._L_RIGHT_SCALE)
            self._right_motor.backward(-direction * self._R_RIGHT_SCALE)
        else:  # Counter-clockwise (left turn)
            self._left_motor.backward(direction * self._L_LEFT_SCALE)
            self._right_motor.forward(direction * self._R_LEFT_SCALE)


# Simple unit test for the traction system
if __name__ == "__main__":
    MOTOR_R_FORWARD_PIN = 17
    MOTOR_R_BACKWARD_PIN = 18
    MOTOR_R_ENABLE_PIN = 27
    MOTOR_L_FORWARD_PIN = 5
    MOTOR_L_BACKWARD_PIN = 6
    MOTOR_L_ENABLE_PIN = 13

    tractor = TractionSystem(
        forward_r=MOTOR_R_FORWARD_PIN,
        backward_r=MOTOR_R_BACKWARD_PIN,
        enable_r=MOTOR_R_ENABLE_PIN,
        forward_l=MOTOR_L_FORWARD_PIN,
        backward_l=MOTOR_L_BACKWARD_PIN,
        enable_l=MOTOR_L_ENABLE_PIN
    )
    control = DigitalOutputDevice(12).on()

    while True:
        action = input("Set action: ").upper()
        if action == "F":
            tractor.forward(float(input("Value: ")))
        elif action == "B":
            tractor.backward(float(input("Value: ")))
        elif action == "S":
            tractor.stop(float(input("Value: ")))
        elif action == "I":
            tractor.idle()
        elif action == "T":
            tractor.turn(float(input("Value: ")))
        else:
            print(f"Current state: {tractor.state}")

        print("\n")
