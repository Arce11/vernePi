import trio, serial, pynmea2, io


async def aprint_loop():
    counter = 0
    while True:
        print(f"###### {counter} ######")
        counter += 1
        await trio.sleep(0.002)


async def agps_loop(async_io):
    while True:
        try:
            line = await async_io.readline()
            msg = pynmea2.parse(line)
            print(repr(msg))
        except serial.SerialException as e:
            print(f'Device error: {e}')
        except pynmea2.ParseError as e:
            print(f'Device error: {e}')


async def parent():
    async with trio.open_nursery() as nursery:
        serial_port = serial.Serial("/dev/serial0", 9600, timeout=5.0)
        serial_io = io.TextIOWrapper(io.BufferedRWPair(serial_port, serial_port))
        serial_async_io = trio.wrap_file(serial_io)

        print("Starting print loop")
        nursery.start_soon(aprint_loop)
        print("Starting GPS async serial loop")
        nursery.start_soon(agps_loop, serial_async_io)
    print("This should never be reached...")

print("Starting - PROJECT VERNE")
trio.run(parent)
