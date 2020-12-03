import trio
import threading
import time
import anyio
import asyncgpio
import gpiozero


async def async_timer():
    counter = 0
    while True:
        print(f"### {counter}s ###")
        counter += 1
        await trio.sleep(1)


async def async_pin_trigger(trigger):
    print(f"Starting pin trigger - Thread: {threading.current_thread().name}")
    trigger_pin = gpiozero.DigitalOutputDevice(trigger, initial_value=False)
    while True:
        await trio.sleep(2)
        trigger_pin.blink(0.1, 0.1, 1)


async def async_pin_listener(pin_to_listen):
    print(f"Starting pin listener - Thread: {threading.current_thread().name}")
    with asyncgpio.Chip(0) as c:
        in_ = c.line(pin_to_listen)
        with in_.monitor(asyncgpio.REQUEST_EVENT_FALLING_EDGE):
            async for event in in_:
                print("asdf")


async def parent():
    GPIO_EVENT_LAUNCHER_PIN = 22
    GPIO_EVENT_LISTENER_PIN = 23
    async with trio.open_nursery() as nursery:
        nursery.start_soon(async_timer)
        nursery.start_soon(async_pin_trigger, GPIO_EVENT_LAUNCHER_PIN)

        pass

trigger_pin = gpiozero.DigitalOutputDevice(22, initial_value=False)


