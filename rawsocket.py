#!/usr/bin/env python3

import socket
import time
import struct
import fcntl
import os

# Constants
PRBUFSZ = 1024
INSTACKSIZE = 4096
INS_FREE = 0
INS_POP = 1
INS_LOCK = 2
INSHEADSIZE = 4
NUMDEVS = 10
BTPROTO_HCI = 1
HCIDEVDOWN = 0x400448ca  # ioctl command to bring HCI device down

class Gpar:
    def __init__(self):
        self.s = None
        self.maxpage = 0
        self.devid = 0
        self.blockflag = 0
        self.hci = -1

gpar = Gpar()

dev = [None] * NUMDEVS
instack = [INS_FREE] * INSTACKSIZE
insdat = instack[INSHEADSIZE:]
initflag = 0

def sendhci(command, length):
    pass  # Placeholder for sending HCI command

def statusok(arg1, arg2):
    pass  # Placeholder for checking status

def bluezdown():

    print("Bluez down")
    try:
        # Create the Bluetooth socket
        dd = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, BTPROTO_HCI)
        
        # Perform the ioctl call to bring the Bluetooth interface down
        try:
            fcntl.ioctl(dd, HCIDEVDOWN, gpar.devid)
            retval = 1
        except Exception as e:
            print(f"Bluez down ioctl failed: {e}")
        finally:
            dd.close()

    except socket.error as e:
        print(f"Socket creation error: {e}")

    time.sleep(1)
    return retval

def hcisock():
    if gpar.hci > 0:
        return 1

    print("Open HCI user socket")
    try:
        dd = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, BTPROTO_HCI)

    except socket.error as e:
        print(f"Socket open error: {e}")
        return 0

    print("Bind to Bluetooth devid user channel")
    
    sa = struct.pack("6B", 31, 0, gpar.devid & 0xFF, (gpar.devid >> 8) & 0xFF, 1, 0)

    try:
        # dd.bind(sa)
        dd.bind((0, 1))
    except socket.error as e:
        print(f"Bind failed: {e}")
        dd.close()
        return 0

    gpar.hci = dd

    print("Reset")
    sendhci('btreset', 0)
    statusok(0, 'btreset')

    print("Set event masks")
    sendhci('eventmask', 0)
    statusok(0, 'eventmask')
    sendhci('lemask', 0)
    statusok(0, 'lemask')

    print("Set page/inquiry scan and timeouts = 10 secs")
    sendhci('scanip', 0)  # SCAN_PAGE | SCAN_INQUIRY    
    statusok(0, 'scanip')
    sendhci('setcto', 0)  # connection timeout = 10 sec 
    statusok(0, 'setcto')
    sendhci('setpto', 0)  # page timeout = 10 sec
    statusok(0, 'setpto')

    print("HCI Socket OK")
    return 1

print("Initialization logic")
if initflag == 0:
    gpar.s = bytearray(PRBUFSZ)
    instack = bytearray([INS_FREE] * INSTACKSIZE)

if not gpar.s or not instack:
    print("Memory allocation failed")
    exit(0)

gpar.maxpage = 0

if initflag == 0:
    gpar.devid = 0  # hcin assumed to be 0
else:
    if gpar.devid != 0:
        print("Cannot change HCI device")
        exit(0)

gpar.blockflag = 0

bluezdown()

ndev = 0

dev[0] = {'type': 'BTYPE_LO', 'meshindex': 1, 'node': 0, 'name': "not in devices.txt"}

if initflag == 0:
    if hcisock() == 0:
        print(f"No root permission or Bluetooth (hci{gpar.devid}) is off or crashed")
        print("Must run with root permission via sudo as follows:")
        print("  sudo python3 btferret.py")
        exit(0)

