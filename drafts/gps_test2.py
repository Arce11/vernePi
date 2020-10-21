import io
import pynmea2
import serial
import time


print("Starting - PROJECT VERNE")

serial_io = serial.Serial("/dev/serial0", 9600, timeout=2.0)
# serial_io = io.TextIOWrapper(io.BufferedRWPair(serial_port, serial_port))
# serial_io = io.TextIOWrapper(serial_port)

timestamp = time.time()
while 1:
    try:
        time.sleep(3)
        serial_io.flushInput()
        line = serial_io.readline().decode("UTF-8")
        msg = pynmea2.parse(line)
        if msg.sentence_type == "GGA":
            print(repr(msg))
        # new_time = time.time()
        # if (new_time-timestamp) > 0.1:
        #     print(f"Time since last: {new_time - timestamp}")
        # timestamp = new_time


    except serial.SerialException as e:
        print('Device error: {}'.format(e))
        break
    except pynmea2.ParseError as e:
        print('Parse error: {}'.format(e))
        continue
