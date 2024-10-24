#!/usr/bin/env python3
import socket
import struct
import fcntl
import ctypes
import time
import os

# Define constants
HCIDEVDOWN = 0x400448ca  # Value for HCIDEVDOWN (from Linux headers)
BTPROTO_HCI = 1          # Bluetooth protocol HCI
AF_BLUETOOTH = 31        # Bluetooth address family
HCI_CHANNEL_USER = 1     # HCI Channel for user-mode HCI socket
HCI_DEV = 0              # Typically, hci0 (use 0 for hci0, 1 for hci1, etc.)

# This would be a global parameter in your program
gpar = {
    'bluez': 1,  # Assuming BlueZ is currently up
    'devid': 0,  # hci0, usually device ID 0
    'hci': -1    # HCI socket descriptor, initially invalid
}

class SockaddrHCI(ctypes.Structure):
    _fields_ = [
        ("hci_family", ctypes.c_ushort),    # Address family (AF_BLUETOOTH)
        ("hci_dev", ctypes.c_ushort),       # Device ID (e.g., hci0 = 0)
        ("hci_channel", ctypes.c_ushort)    # HCI Channel (e.g., HCI_CHANNEL_USER)
    ]

def bluezdown():
    """ Bring down BlueZ stack. """
    if gpar['bluez'] == 0:
        print("BlueZ already down")
        return 1  # already down

    print("BlueZ down")

    retval = 0
    try:
        dd = socket.socket(AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, BTPROTO_HCI)
    except OSError as e:
        print(f"Failed to create socket: {e}")
        return retval

    try:
        if fcntl.ioctl(dd, HCIDEVDOWN, gpar['devid']) >= 0:
            retval = 1
    except OSError as e:
        print(f"Failed to bring BlueZ down: {e}")
    finally:
        dd.close()

    if retval == 0:
        print("BlueZ down failed")

    gpar['bluez'] = 0  # Update state: BlueZ is down
    time.sleep(1)
    return retval

def hcisock():
    """ Open an HCI user-mode socket, bind it to the device, and send HCI commands. """
    if gpar['hci'] > 0:
        return 1  # HCI socket is already open

    print("Open HCI user socket")
    
    try:
        # Open a RAW HCI socket
        print("Open BTPROTO socket")
        dd = socket.socket(AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, BTPROTO_HCI)
    except OSError as e:
        print(f"Socket open error: {e}")
        return 0

    # Prepare the sockaddr_hci structure using ctypes
    sa = SockaddrHCI()
    sa.hci_family = AF_BLUETOOTH
    sa.hci_dev = gpar['devid']
    sa.hci_channel = HCI_CHANNEL_USER

    # Bind the socket to the device and HCI user channel
    try:
        print("Bind to Bluetooth devid user channel")
        # Use the raw buffer of sa for the bind call
        dd.bind((bytes(sa),))
    except OSError as e:
        print(f"Bind failed: {e}")
        dd.close()
        return 0

    gpar['hci'] = dd  # Save the socket descriptor

    # Now send some HCI commands like Reset, Event Masks, etc.
    print("Reset")
    send_hci_command(dd, btreset)
    
    print("Set event masks")
    send_hci_command(dd, eventmask)
    send_hci_command(dd, lemask)

    print("Set page/inquiry scan and timeouts = 10 secs")
    send_hci_command(dd, scanip)
    send_hci_command(dd, setcto)
    send_hci_command(dd, setpto)

    print("HCI Socket OK")
    return 1

def send_hci_command(sock, command):
    """ Sends an HCI command packet through the socket. """
    try:
        sock.send(command)
    except OSError as e:
        print(f"Failed to send HCI command: {e}")

# Example HCI command packets (these are placeholders, you should define them)
btreset = struct.pack("<BHB", 0x01, 0x0C03, 0x00)  # Example reset command
eventmask = struct.pack("<BHB", 0x01, 0x0C01, 0x08)  # Example event mask command
lemask = struct.pack("<BHB", 0x01, 0x2001, 0x08)  # Example LE mask command
scanip = struct.pack("<BHB", 0x01, 0x0C13, 0x00)  # Example scan enable command
setcto = struct.pack("<BHB", 0x01, 0x0C1A, 0x10)  # Example connection timeout
setpto = struct.pack("<BHB", 0x01, 0x0C16, 0x10)  # Example page timeout

# Main flow:
bluezdown()  # Close BlueZ first
hcisock()    # Open the HCI socket and send commands
