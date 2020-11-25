from gpiozero import DigitalInputDevice
from pycc1101 import TICC1101
from time import sleep

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

SPI_conf = {
    "bus":      0,
    "device":   0,
    "MOSI":     10,
    "MISO":     9,
    "SCLK":     11,
    "CE":       8
}

state_dict = {
    0: "SLEEP",
    1: "IDLE",
    2: "XOFF",
    3: "VCOON_MC",
    4: "REGON_MC",
    5: "MANCAL",
    6: "VCOON",
    7: "REGON",
    8: "STARTCAL",
    9: "BWBOOST",
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
    22: "TXFIFO_UNDERWFLOW"
}


def radioState(cc1101_transceiver):
    code = cc1101_transceiver._getMRStateMachineState()
    return state_dict.get(code)


GD0_PIN = 25    # Pin 22 (interrupt line)

# CC1101 Transceiver Setup -----
radio = TICC1101(bus=SPI_conf.get("bus"), device=SPI_conf.get("device"))
    # CC1101 transceiver programming object
    # SPI bus numb.1 and device numb.1 (CE0)

interrupt = DigitalInputDevice(GD0_PIN)         # GPIO25 configuration ("new packet received" interrupt)
radio.reset()                                   # send reset command (command strobe)
radio.setDefaultValues()                        # initialization of the CC1101 registers with its default values
radio._writeSingleByte(radio.PATABLE, 0xC0)     # cc1101 transmission power configuration
print("Initialization complete!")
radio.setSyncWord()                             # setting sync word... (default value = "FAFA")
radio.setCarrierFrequency(433)                  # setting carrier frequency... (433 MHz or 868 MHz)
radio._writeSingleByte(radio.PKTCTRL1, 0x04)    # disable Address Check
radio.sidle()                                   # enter the transceiver into IDLE mode
radio._setTXState()                             # enter the transceiver into TX mode

# Transceiver "number plate"
print("CC1101_PARTNUM: {}".format(radio._readSingleByte(radio.PARTNUM)))    # Chip part number
print("CC1101_VERSION: {}".format(radio._readSingleByte(radio.VERSION)))    # Chip version number
print("PaTable value: {}".format(radio._readSingleByte(radio.PATABLE)))     # PA power control
base_frequency = (radio._readSingleByte(radio.FREQ2)<<16) | (radio._readSingleByte(radio.FREQ1)<<8) | radio._readSingleByte(radio.FREQ0)
fxosc = 26*pow(10,6)
print("Carrier frequency: {}".format( base_frequency*fxosc/pow(2,16) ))     # Carrier frequency (registers FREQ2, FREQ1 y FREQ0)
print("Operation mode: {}".format(radioState(radio)))                       # Displaying the current state of the cc1101

# CC1101 Transceiver Operation -----
while True:
    # Copy-pasted from the pycc1101.py documentation (tx.py)
    toSend = "hola mundo".encode("utf-8")
    flag = radio.sendData(toSend)
    while not flag:
        radio.sendData(toSend)
    sleep(0.1)  # Time interval between transmissions