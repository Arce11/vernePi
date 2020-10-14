import serial  # import serial package
import time


def parse_line(line):
    parts = line.split(",")
    if parts[0] != "$GPGGA":  # Only GPGGA messages are of interest (for now). Check: http://aprs.gids.nl/nmea/
        return

    print("---- NEW MEASUREMENT ----")
    print(f"Raw data: {line}")
    print(f"Time: {parts[1][0:1]}:{parts[1][2:3]}:{parts[1][4:]}")
    fix = parts[6] != "0"
    if not fix:
        print("NO LOCATION FIX")
    else:
        print(f"Latitude: {parts[2]} {parts[3]} \tLongitude: {parts[4]} {parts[5]}")
    print(f"Satellites in view: {parts[7]}")
    print("---- END OF MEASUREMENT ----")
    print("\n\n")
    time.sleep(1)


print("Starting - PROJECT VERNE")
ser = serial.Serial("/dev/serial0")  # Open port with baud rate
raw_data = None

while True:
    try:
        raw_data = ser.readline()
        decoded_data = raw_data.decode(encoding="UTF-8")
        parse_line(decoded_data)
    except UnicodeDecodeError:  # I KNOW there is an error. And I want to find that sh*t
        print(raw_data)
        raise

