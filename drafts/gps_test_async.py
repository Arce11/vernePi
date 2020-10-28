import trio
import serial
import pynmea2
import io
import time


async def aprint_loop():
    counter = 0
    while True:
        print(f"###### {counter} ######")
        counter += 1
        await trio.sleep(1)


async def agps_loop(async_io):
    while True:
        try:
            line = await async_io.readline()
            t_start = time.time()
            msg = pynmea2.parse(line.decode("UTF-8"))
            print(f"Time: {time.time()-t_start}")
            #print(repr(msg))
        except serial.SerialException as e:
            print(f'Device error: {e}')
        except pynmea2.ParseError as e:
            print(f'Format error: {e}')


async def parent():
    async with trio.open_nursery() as nursery:
        serial_port = serial.Serial("/dev/serial0", 9600, timeout=5.0)
        serial_io = io.TextIOWrapper(io.BufferedRWPair(serial_port, serial_port))
        a_serial = trio.wrap_file(serial_port)

        print("Starting print loop")
        nursery.start_soon(aprint_loop)
        print("Starting GPS async serial loop")
        a_serial.flushInput()
        nursery.start_soon(agps_loop, a_serial)
    print("This should never be reached...")

print("Starting - PROJECT VERNE")
trio.run(parent)
