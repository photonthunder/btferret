#!/usr/bin/env python3

import socket
import struct
import fcntl
import array

# Constants for HCI
HCI_DEV = 0  # Typically, hci0
HCI_FILTER = 2
HCI_COMMAND_PKT = 0x01

# Bluetooth HCI Commands (Example: Reset HCI Command)
OGF = 0x03  # Opcode Group Field (Controller & Baseband Commands)
OCF = 0x0003  # Opcode Command Field (Reset Command)
opcode = (OCF & 0x03FF) | (OGF << 10)
length = 0x00  # No parameters for HCI reset command

# Create the raw socket
sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
sock.bind((HCI_DEV,))

# Construct the HCI command packet
command_pkt = struct.pack("<BHB", HCI_COMMAND_PKT, opcode, length)

# Send the HCI command packet to the Bluetooth controller
sock.send(command_pkt)

# Optionally read a response if the command generates one
response = sock.recv(1024)
print("Response:", response)

# Close the socket
sock.close()
