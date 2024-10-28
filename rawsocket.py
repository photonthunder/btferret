#!/usr/bin/env python3

import socket
import struct
import binascii

# Define constants for socket communication
HCI_DEVICE_ID = 0  # Typically 0 for the first Bluetooth adapter
HCI_COMMAND_PKT = 0x01  # Command packet type for HCI commands
HCI_EVENT_PKT = 0x04    # Event packet type for HCI events

# Define HCI opcodes (OGF and OCF)
OGF_HOST_CTL = 0x03
OGF_LE_CTL = 0x08

# Example HCI command opcodes
OCF_RESET = 0x0003  # Reset
OCF_SET_EVENT_MASK = 0x0001  # Set Event Mask
OCF_LE_SET_EVENT_MASK = 0x0001  # LE Set Event Mask
OCF_WRITE_SCAN_ENABLE = 0x001A  # Write Scan Enable (inquiry + page scan)
OCF_WRITE_CONN_ACCEPT_TIMEOUT = 0x0016  # Set Connection Accept Timeout
OCF_WRITE_PAGE_TIMEOUT = 0x0018  # Set Page Timeout

# Inquiry Scan + Page Scan
SCAN_PAGE = 0x02
SCAN_INQUIRY = 0x01
SCAN_IP = SCAN_PAGE | SCAN_INQUIRY  # Enable both scans

# Timeout values (in slots, 1 slot = 0.625ms, so 10 seconds = 16000 slots)
CONN_TIMEOUT_10_SEC = 16000
PAGE_TIMEOUT_10_SEC = 16000

def send_hci_command(sock, ogf, ocf, params=b''):
    """Function to send HCI command"""
    opcode = (ogf << 10) | ocf
    param_len = len(params)
    cmd_hdr = struct.pack('<HB', opcode, param_len)
    packet = struct.pack('<B', HCI_COMMAND_PKT) + cmd_hdr + params
    
    # Print the packet being sent (in hex)
    print(f"Sending HCI command: {binascii.hexlify(packet)}")
    
    # Send the packet
    sock.send(packet)

def receive_hci_event(sock):
    """Function to receive and print HCI events"""
    try:
        # Receive a response (event) from the HCI socket
        response = sock.recv(1024)
        
        # Print the received packet (in hex)
        print(f"Received HCI event: {binascii.hexlify(response)}")
    except socket.error as e:
        print(f"Socket error: {e}")

def main():
    # Open an HCI socket
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
    sock.bind((HCI_DEVICE_ID,))
    
    try:
        # 1. Send HCI Reset command
        send_hci_command(sock, OGF_HOST_CTL, OCF_RESET)
        receive_hci_event(sock)  # Receive the response

        # 2. Send eventmask HCI command (set the event mask)
        eventmask = struct.pack('<Q', 0xFFFFFFFFFFFFFBFF)  # Example event mask
        send_hci_command(sock, OGF_HOST_CTL, OCF_SET_EVENT_MASK, eventmask)
        receive_hci_event(sock)  # Receive the response

        # 3. Send lemask HCI command (set the LE event mask)
        lemask = struct.pack('<Q', 0xFFFFFFFFFFFFFBFF)  # Example LE event mask
        send_hci_command(sock, OGF_LE_CTL, OCF_LE_SET_EVENT_MASK, lemask)
        receive_hci_event(sock)  # Receive the response

        # 4. Send scanip HCI command (set scan mode: inquiry + page scan)
        scanip = struct.pack('<B', SCAN_IP)
        send_hci_command(sock, OGF_HOST_CTL, OCF_WRITE_SCAN_ENABLE, scanip)
        receive_hci_event(sock)  # Receive the response

        # 5. Send setcto HCI command (set connection timeout to 10 seconds)
        setcto = struct.pack('<H', CONN_TIMEOUT_10_SEC)
        send_hci_command(sock, OGF_HOST_CTL, OCF_WRITE_CONN_ACCEPT_TIMEOUT, setcto)
        receive_hci_event(sock)  # Receive the response

        # 6. Send setpto HCI command (set page timeout to 10 seconds)
        setpto = struct.pack('<H', PAGE_TIMEOUT_10_SEC)
        send_hci_command(sock, OGF_HOST_CTL, OCF_WRITE_PAGE_TIMEOUT, setpto)
        receive_hci_event(sock)  # Receive the response

        print("All HCI commands sent and responses received successfully!")
        
    finally:
        sock.close()

if __name__ == "__main__":
    main()
