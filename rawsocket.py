#!/usr/bin/env python3

import socket
import struct
import binascii
import time
import select

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

def set_hci_filter(sock):
    """Set an HCI filter to capture all events and responses."""
    # Accept all event types
    flt = struct.pack("IIII", 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    sock.setsockopt(socket.SOL_HCI, socket.HCI_FILTER, flt)

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
    """Function to receive HCI events."""
    while True:
        try:
            # Receive a response (event) from the HCI socket
            response = sock.recv(1024)

            # Check if we received a valid HCI event packet
            if response:
                # Print the received packet (in hex)
                print(f"Received HCI event: {binascii.hexlify(response)}")

                # Check if the first byte indicates an HCI event
                if response[0] == HCI_EVENT_PKT:
                    # Parse the event (for example, check status)
                    plen = response[2]  # The length of the event data
                    event_code = response[1]
                    print(f"Event Code: {event_code}, Length: {plen}")

                return response
            else:
                print("No response received.")
                break
        except socket.error as e:
            print(f"Socket error: {e}")
            break

def main():
    # Open an HCI socket with SOCK_NONBLOCK and SOCK_CLOEXEC
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW | socket.SOCK_CLOEXEC, socket.BTPROTO_HCI)
    sock.bind((HCI_DEVICE_ID,))
    
    # Set HCI filter to capture all events and command completions
    set_hci_filter(sock)
    
    try:
        # 1. Send HCI Reset command
        send_hci_command(sock, OGF_HOST_CTL, OCF_RESET)
        # time.sleep(0.1)  # Wait a bit for the response
        receive_hci_event(sock)  # Receive the response

        # 2. Send event mask command
        eventmask = struct.pack('<Q', 0xFFFBFFFFFFFFFFFF)  # Example event mask
        send_hci_command(sock, OGF_HOST_CTL, OCF_SET_EVENT_MASK, eventmask)
        time.sleep(0.1)  # Wait a bit for the response
        receive_hci_event(sock)  # Receive the response

        # Continue with other HCI commands...
        
    finally:
        sock.close()

if __name__ == "__main__":
    main()
