import threading
from time import sleep
from gpiozero import DigitalInputDevice
from pycc1101 import TICC1101

'''
    1byte CC1101 TRANSMITTER example.
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

GD0_PIN = 25    # Pin 22 (interrupt line)
                # When the Rx FIFO is full, the GD0 pin is set to high level
CARRIER_FREQ = 433

# Dictionary where the SPI constants used are stored
SPI_conf = {
    "bus":      0,  # SPI bus used = 0
    "device":   0,  # SPI device used = 0 (up to 2 devices can be used by each bus)
    "MOSI":     10, # Master Output/Slave Input (D19)
    "MISO":     9,  # Master Input/Slave Output (D21)
    "SCLK":     11, # SPI clock (D23)
    "CE":       8   # Chip Enable (D24) (SPI numb.0 = CE0(D24) or CE1 = (D26))
}

# Interpretation of every code which represents the CC1101 transceiver current state of operation
state_dict = {
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


def radio_state(cc1101_transceiver):
    # radioState:   this function returns the current state of operation by reading the
    #               CC1101 transceiver MARCSTATE register
    code = (cc1101_transceiver._getMRStateMachineState() and 0x1F)
    return state_dict.get(code)


def on_activated():
    # on_activated: every time the interrupt signal is set to high state, this function is triggered,
    #               launching a thread which is responsible for recovering the info. storde in the CC1101
    #               transceiver Rx FIFO
    th_worker = threading.Thread(target=_worker_)
    th_worker.daemon = True     # the thread "_worker_" is erased when it's finally done
    th_worker.start()           # starting _worker_ operation...
    return


def _worker_():
    # _worker_:     thread triggered by the on_activated function and responsible for managing the SPI transaction
    #               to recover the received data from the transceiver Rx FIFO
    received_data = radio.recvData()        # receiving data...
    radio.sidle()           # enters the transceiver into IDLE mode
    radio._setRXState()     # enters the transceiver into RX mode
    print("Operation mode: {}".format(radio_state(radio)))
    print(''.join([chr(code) for code in received_data]))
    #interrupt.when_activated = onActivated
    return


# CC1101 Transceiver Setup ----
radio = TICC1101(bus=SPI_conf.get("bus"), device=SPI_conf.get("device"))
#   CC1101 transceiver programming object
#   SPI bus numb.0 and device numb.0 (CE0)


interrupt = DigitalInputDevice(GD0_PIN)         # GPIO25 configuration ("new packet received" interrupt)
radio.reset()                                   # send reset command (command strobe)
radio.setDefaultValues()                        # initialization of the CC1101 registers with its default values
print("Initialization complete!")
radio.setSyncWord("C70A")                       # setting sync word... (default value = "FAFA")
radio.setCarrierFrequency(CARRIER_FREQ)         # setting carrier frequency... (433 MHz or 868 MHz)
radio._writeSingleByte(radio.PKTCTRL1, 0x04)    # disable Address Check
radio.sidle()                                   # enter the transceiver into IDLE mode
radio._setRXState()                             # enter the transceiver into RX mode

# Transceiver "number plate"
print("CC1101_PARTNUM: {}".format(radio._readSingleByte(radio.PARTNUM)))    # Chip part number
print("CC1101_VERSION: {}".format(radio._readSingleByte(radio.VERSION)))    # Chip version number
print("PaTable value: {}".format(radio._readSingleByte(radio.PATABLE)))     # PA power control
base_frequency = (radio._readSingleByte(radio.FREQ2)<<16) | (radio._readSingleByte(radio.FREQ1)<<8) | radio._readSingleByte(radio.FREQ0)
fxosc = 26*pow(10,6)
print("Carrier frequency: {}".format( base_frequency*(fxosc/pow(2,16)) ) )  # Carrier frequency (registers FREQ1, FREQ2 y FREQ3)
print("Operation mode: {}".format(radio_state(radio)))                       # Displaying the current state of the cc1101

# CC1101 Transceiver Operation ----
interrupt.when_activated = on_activated
#   on_activated is triggered every time the interrupt line is activated

while True:
    print("RSSI: {} dBm".format(radio._getRSSI(radio.getRSSI())))
    #    the main thread can access to the RSSI register every time it needs
    sleep(0.25)