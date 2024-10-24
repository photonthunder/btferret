#!/usr/bin/env python3

import socket
import struct

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

# Construct the HCI command packet (in Little Endian format)
command_pkt = struct.pack("<BHB", HCI_COMMAND_PKT, opcode, length)

# Output the HCI command being sent (in bytes)
print("HCI Command (in bytes):", command_pkt)
print("HCI Command (in hex):", command_pkt.hex())

# Send the HCI command packet to the Bluetooth controller
sock.send(command_pkt)

# Optionally read the response
response = sock.recv(1024)
print("HCI Response (in bytes):", response)
print("HCI Response (in hex):", response.hex())

# Close the socket
sock.close()
