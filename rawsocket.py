#!/usr/bin/env python3

import socket
import struct
import fcntl
import time
import os

# Define constants from the C code
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

    # # Prepare the sockaddr_hci structure as a byte array
    # sa = bytearray(6)
    # sa[0] = AF_BLUETOOTH         # hci_family = AF_BLUETOOTH
    # sa[1] = 0                    # Padding byte (for alignment)
    # sa[2] = gpar['devid'] & 0xFF  # Low byte of device ID (hci_dev)
    # sa[3] = (gpar['devid'] >> 8) & 0xFF  # High byte of device ID
    # sa[4] = HCI_CHANNEL_USER     # hci_channel = HCI_CHANNEL_USER
    # sa[5] = 0                    # Padding byte (for alignment)

    # Prepare the sockaddr_hci structure correctly using struct.pack
    # This corresponds to: struct sockaddr_hci { sa_family_t hci_family; unsigned short hci_dev; unsigned short hci_channel; }
    hci_family = AF_BLUETOOTH
    hci_dev = gpar['devid']
    hci_channel = HCI_CHANNEL_USER
    
    # Pack sockaddr_hci structure using struct.pack: "H" for hci_family, "H" for devid, "H" for channel
    sa = struct.pack("BBBBBB", hci_family, 0, hci_dev, 0, hci_channel, 0)

    # Bind the socket to the device and HCI user channel
    try:
        print("Bind to Bluetooth devid user channel")
        dd.bind(sa)
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



