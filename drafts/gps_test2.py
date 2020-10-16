import io
import pynmea2
import serial
import time


print("Starting - PROJECT VERNE")

serial_port = serial.Serial("/dev/serial0", 9600, timeout=5.0)
serial_io = io.TextIOWrapper(io.BufferedRWPair(serial_port, serial_port))

while 1:
    try:
        line = serial_io.readline()
        msg = pynmea2.parse(line)
        #print(msg.sentence_type)
        print(msg.sentence_type)
        print(repr(pynmea2.GGA))
        if msg.sentence_type == pynmea2.GGA:
            print(repr(msg))
            time.sleep(0.5)
    except serial.SerialException as e:
        print('Device error: {}'.format(e))
        break
    except pynmea2.ParseError as e:
        print('Parse error: {}'.format(e))
        continue
