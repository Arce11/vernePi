from systems.event_source import AsyncEventSource, BaseEventArgs
from systems.pycc1101 import TICC1101
from gpiozero import DigitalInputDevice
import trio

'''
    Pinout Connection:
    Raspberry Pi (SPI bus 0)    CC1101
    ----------------------------------------------
    GND                         GND
    D1(3.3V)                    VCC
    D19(MOSI)                   SI (Master Output/Slave Input)
    D21(MISO)                   SO (Master Input/Slave Output)
    D22                         GD0 (Interruption Line)
    D23(SCLK)                   SCK (SPI Clock)
    D24(CE0)                    CSN (Slave Select - option 1)
    D26(CE1)                    CSN (Slave Select - option 2)
    ----------------------------------------------
    WARNING: check if the SPI interface is activated before running the code
        (Preferences > Raspberry Pi Configuration > Interfaces > SPI > Enabled > Reboot)
'''

# Interpretation of every code which represents the CC1101 transceiver current state of operation
STATE_DICT = {
    0:  "SLEEP",
    1:  "IDLE",
    2:  "XOFF",
    3:  "VCOON_MC",
    4:  "REGON_MC",
    5:  "MANCAL",
    6:  "VCOON",
    7:  "REGON",
    8:  "STARTCAL",
    9:  "BWBOOST",
    10: "FS_LOCK",
    11: "IFADCON",
    12: "ENDCAL",
    13: "RX",
    14: "RX_END",
    15: "RX_RST",
    16: "TXRX_SWITCH",
    17: "RXFIFO_OVERFLOW",
    18: "FSTXON",
    19: "TX",
    20: "TX_END",
    21: "RXTX_SWITCH",
    22: "TXFIFO_UNDERFLOW"
}


class ReceptorSystem(AsyncEventSource):
    CARRIER_FREQ = 868
    SPI_BUS = 0
    SPI_MOSI_PIN = 10
    SPI_MISO_PIN = 9
    SPI_SCLK_PIN = 11

    RSSI_EVENT = "RSSI_EVENT"

    def __init__(self, interrupt_pin, device_num: int, nursery, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._data = data if data is not None else {'rssi': None}
        self._interrupt = DigitalInputDevice(interrupt_pin)
        if device_num == 0:
            ce_pin = 8
        elif device_num == 1:
            ce_pin = 7
        else:
            raise ValueError("Invalid device number")
        spi_conf = {
            "bus":      self.SPI_BUS,  # SPI bus used = 0
            "device":   device_num,  # SPI device used = 0 (up to 2 devices can be used by each bus)
            "MOSI":     self.SPI_MOSI_PIN, # Master Output/Slave Input (D19)
            "MISO":     self.SPI_MISO_PIN,  # Master Input/Slave Output (D21)
            "SCLK":     self.SPI_SCLK_PIN, # SPI clock (D23)
            "CE":       ce_pin   # Chip Enable (D24) (SPI numb.0 = CE0(D24) or CE1 = (D26))
        }
        self._radio = TICC1101(bus=spi_conf.get("bus"), device=spi_conf.get("device"))
        self._setup_device()
        self._is_running = False


    def _setup_device(self):
        self._radio.reset()  # send reset command (command strobe)
        self._radio.setDefaultValues()  # initialization of the CC1101 registers with its default values
        print("Initialization complete!")
        self._radio.setSyncWord("C70A")  # setting sync word... (default value = "FAFA")
        self._radio.setCarrierFrequency(self.CARRIER_FREQ)  # setting carrier frequency... (433 MHz or 868 MHz)
        self._radio.setChannel(0x1F)
        self._radio._writeSingleByte(self._radio.PKTCTRL1, 0x04)  # disable Address Check
        self._radio.sidle()  # enter the transceiver into IDLE mode
        self._radio._setRXState()

    def get_radio_state(self):
        code = (self._radio._getMRStateMachineState() and 0x1F)
        return STATE_DICT.get(code)

    def on_interrupt(self):
        print("GOT AN INTERRUPT!!")

    def print_number_plate(self):
        print("CC1101_PARTNUM: {}".format(self._radio._readSingleByte(self._radio.PARTNUM)))  # Chip part number
        print("CC1101_VERSION: {}".format(self._radio._readSingleByte(self._radio.VERSION)))  # Chip version number
        print("PaTable value: {}".format(self._radio._readSingleByte(self._radio.PATABLE)))  # PA power control
        base_frequency = (self._radio._readSingleByte(self._radio.FREQ2) << 16) | \
                         (self._radio._readSingleByte(self._radio.FREQ1) << 8) | \
                         self._radio._readSingleByte(self._radio.FREQ0)
        fxosc = 26 * pow(10, 6)
        # Carrier frequency (registers FREQ1, FREQ2 y FREQ3)
        print("Carrier frequency: {}".format(base_frequency * (fxosc / pow(2, 16))))
        print("Operation mode: {}".format(self.get_radio_state()))

    async def a_run_notification_loop(self):
        if self._is_running:
            return
        self._is_running = True
        self._interrupt.when_activated = self.on_interrupt
        print("Starting")
        while self._is_running:
            rssi = self._radio._getRSSI(self._radio.getRSSI())
            self._data['rssi'] = rssi
            await self.raise_event(ReceptorEventArgs(self.RSSI_EVENT, self._data))
            await trio.sleep(0.5)

    def stop_notification_loop(self):
        """
        Stops the update loop on the stored data. If it is not running, it does nothing.
        """
        self._is_running = False
        self._interrupt.when_activated = None


class ReceptorEventArgs(BaseEventArgs):
    def __init__(self, event_type: str, data: dict):
        super().__init__(event_type)
        self.data = data  # type: dict


class DummyReceptorSystem(AsyncEventSource):
    def __init__(self, interrupt_pin, device_num: int, nursery, data=None, notification_callbacks=None, error_callbacks=None):
        super().__init__(nursery, notification_callbacks, error_callbacks)
        self._data = data if data is not None else {'rssi': -60}
        self._data['rssi'] = -90
        self._is_running = False

    async def a_run_notification_loop(self):
        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            await trio.sleep(1)
            await self.raise_event(ReceptorEventArgs(ReceptorSystem.RSSI_EVENT, self._data))

    def stop_notification_loop(self):
        self._is_running = False

    def get_radio_state(self):
        return STATE_DICT.get(0)

    def print_number_plate(self):
        pass


if __name__ == "__main__":
    RX_INTERRUPTION_PIN = 16
    TX_DEVICE = 1


    # Simple async timer to run "in parallel" to all GPS shenanigans
    async def async_timer():
        counter = 0
        while True:
            print(f"### {counter}s ###")
            counter += 1
            await trio.sleep(1)

    async def event_listener(source, param: ReceptorEventArgs):
        print(f"New RSSI: {param.data}dBm")

    async def parent():
        async with trio.open_nursery() as nursery:
            receptor = ReceptorSystem(RX_INTERRUPTION_PIN, TX_DEVICE, nursery)
            receptor.subscribe(notification_callbacks=[event_listener])
            nursery.start_soon(receptor.a_run_notification_loop)
            nursery.start_soon(async_timer)

    trio.run(parent)