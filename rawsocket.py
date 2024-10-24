#!/usr/bin/env python3

import socket
import struct
import socket
import fcntl
import struct
import time
import os

# Define the necessary constants
HCIDEVDOWN = 0x400448ca  # This is the value for HCIDEVDOWN (from Linux headers)
BTPROTO_HCI = 1          # Bluetooth protocol HCI
AF_BLUETOOTH = 31        # Bluetooth address family (31 corresponds to AF_BLUETOOTH)

# This would be a global parameter in your program, as per the original C code
gpar = {
    'bluez': 1,  # Assuming bluez is currently up
    'devid': 0   # hci0, usually device ID 0
}

def bluezdown():
    if gpar['bluez'] == 0:
        print("BlueZ already down")
        return 1  # already down

    print("BlueZ down")

    retval = 0
    
    # Create an HCI raw socket (similar to the C code)
    try:
        dd = socket.socket(AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK, BTPROTO_HCI)
    except OSError as e:
        print(f"Failed to create socket: {e}")
        return retval

    # Perform the HCIDEVDOWN ioctl to bring the interface down
    try:
        if fcntl.ioctl(dd, HCIDEVDOWN, gpar['devid']) >= 0:
            retval = 1
    except OSError as e:
        print(f"Failed to bring BlueZ down: {e}")
    finally:
        dd.close()

    if retval == 0:
        print("BlueZ down failed")

    # Emulate the print flushing in the original C code
    os.sys.stdout.flush()

    # Update the global state to reflect that BlueZ is down
    gpar['bluez'] = 0  # BlueZ down

    # Sleep to allow the system to process the change
    time.sleep(1)

    return retval

# Call the function
bluezdown()




# Constants for HCI
HCI_DEV = 0  # Typically, hci0 (use 0 for hci0, 1 for hci1, etc.)
HCI_COMMAND_PKT = 0x01  # Packet indicator for HCI command

# Bluetooth HCI Commands (Example: Reset HCI Command)
OGF = 0x03  # Opcode Group Field (Controller & Baseband Commands)
OCF = 0x0003  # Opcode Command Field (Reset Command)
opcode = (OCF & 0x03FF) | (OGF << 10)  # Opcode is a combination of OGF and OCF
length = 0x00  # No parameters for the HCI reset command

# Create a raw socket
sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
sock.bind((HCI_DEV,))

# Set a timeout (e.g., 5 seconds)
sock.settimeout(5.0)

# Construct the HCI command packet (in Little Endian format)
command_pkt = struct.pack("<BHB", HCI_COMMAND_PKT, opcode, length)

# Output the HCI command being sent (in bytes)
print("HCI Command (in bytes):", command_pkt)
print("HCI Command (in hex):", command_pkt.hex())

# Send the HCI command packet to the Bluetooth controller
sock.send(command_pkt)

# Try to receive the response with a timeout
try:
    response = sock.recv(1024)
    print("HCI Response (in bytes):", response)
    print("HCI Response (in hex):", response.hex())
except socket.timeout:
    print("No response received within the timeout period")

# Close the socket
sock.close()

