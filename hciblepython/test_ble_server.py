#!/usr/bin/env python3

from ble import *
from test_gatt_server import GattServer
import sys
import termios
import tty
import time
import select
import threading

WAIT_TIME = 0.005

class BLE(BluetoothLEConnection):
    def __init__(self, *args, **kwargs):
        test_gatt_server = GattServer()
        super().__init__(gatt_server=test_gatt_server, *args, **kwargs) 
        if self.gatt_server == None:
            print("self.gatt_sever == None")
            exit(0)

        self.escape_pressed = False
        self.old_settings = termios.tcgetattr(sys.stdin)

    def enable_raw_mode(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    def restore_terminal(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def check_key_press(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key == '\x1b':  # Escape key (ASCII code)
                self.escape_pressed = True

    def adv(self):
        self.reset()
        self.wait_listen(5 * WAIT_TIME)
        self.set_event_masks()
        self.wait_listen(WAIT_TIME)
        self.set_le_event_masks()
        self.wait_listen(WAIT_TIME)
        self.set_inquiry_timeouts()
        self.wait_listen(WAIT_TIME)
        self.set_page_scan_activity()
        self.wait_listen(WAIT_TIME)
        self.set_inquiry_scan_activity()
        self.wait_listen(WAIT_TIME)
        self.read_local_commands()
        self.wait_listen(WAIT_TIME)
        self.read_local_board_address()
        self.wait_listen(WAIT_TIME)
        self.read_le_buffer_size()
        self.wait_listen(WAIT_TIME)
        self.write_local_name(self.gatt_server.device_name)
        self.wait_listen(WAIT_TIME)

        # self.do_set_advertise_enable(False)
        # self.wait_listen(WAIT_TIME)

        self.set_random_address()
        self.wait_listen(WAIT_TIME)
        self.do_set_advertising_parameters(
            min_interval=0x0200, # 320 ms
            max_interval=0x0200, # 320 ms
        )
        self.wait_listen(WAIT_TIME)
        adv_data = bytes([
            0x14,  # Total Data Length
            0x08,  # Length of manufacturer-specific data
            0xFF,  # Manufacturer-specific data type
            0x42, 0xC4,  # Manufacturer ID (0xC442)
            0x00, 0x00, 0xC0, 0xDE, 0x99, # Manufacturer data
            0x0A,  # Length of complete local name
            0x08,  # Complete local name type
            # 0x4D, 0x79, 0x20, 0x4F, 0x74, 0x68, 0x65, 0x72, 0x20, 0x50, 0x69,  # "My Other Pi"
            0x4D, 0x79, 0x20, 0x4E, 0x65, 0x77, 0x20, 0x50, 0x69,  # "My New Pi"
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # Padding
        ])
        self.do_set_advertising_data(adv_data)
        self.wait_listen(WAIT_TIME)
        scan_rsp_data = bytes([
            0x0B,  # Length of Complete Local Name
            0x09,  # Complete Local Name Type
            # 0x4D, 0x79, 0x20, 0x4F, 0x74, 0x68, 0x65, 0x72, 0x20, 0x50, 0x69,  # "My Other Pi"
            # 0x4D, 0x79, 0x20, 0x4E, 0x65, 0x77, 0x20, 0x50, 0x69,  # "My New Pi"
            0x4D, 0x79, 0x20, 0x42, 0x4C, 0x45, 0x20, 0x44, 0x65, 0x76, # My BLE Dev

            0x12,  # Length of manufacturer-specific data
            0xFF,  # Manufacturer-specific data type
            0xAA, 0xBB,  # Manufacturer ID (0xBBAA)
            0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, # Manufacturer data
            0x00, 0x00, 0x00  # Padding
        ])

        self.do_set_scan_response_data(scan_rsp_data)
        self.wait_listen(WAIT_TIME)
        # self.read_local_public_key()
        # self.wait_listen(WAIT_TIME)
        self.set_random_address()
        self.wait_listen(WAIT_TIME)
        self.do_set_advertising_parameters(
            min_interval=0x0200, # 320 ms
            max_interval=0x0200, # 320 ms
            own_addr_type=0x01 # random address
        )
        self.wait_listen(WAIT_TIME)
        # Advertising data in byte array format
        adv_data = bytes([
            0x17,  # Total Data Length
            0x08,  # Length of manufacturer-specific data
            0xFF,  # Manufacturer-specific data type
            # 0x42, 0xC4,  # Manufacturer ID (0xC442)
            0x34, 0x12,  # Manufacturer ID (0xC442)
            0x00, 0x00, 0xC0, 0xDE, 0x99, # Manufacturer data
            0x02, # Length of Bluetooth Flags
            0x01, # Bluetooth Flags Type
            0x06,   # Bit 0 (0x01): LE Limited Discoverable Mode.
                    # Bit 1 (0x02): LE General Discoverable Mode (this is set).
                    # Bit 2 (0x04): BR/EDR Not Supported (this is set).
            0x0A,  # Length of complete local name
            0x08,  # Complete local name type
            # 0x4D, 0x79, 0x20, 0x4F, 0x74, 0x68, 0x65, 0x72, 0x20, 0x50, 0x69,  # "My Other Pi"
            0x4D, 0x79, 0x20, 0x4E, 0x65, 0x77, 0x20, 0x50, 0x69,  # "My New Pi"
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # Padding
        ])
        self.do_set_advertising_data(adv_data)
        self.wait_listen(WAIT_TIME)

        
        self.do_set_advertise_enable(True)
        self.wait_listen(WAIT_TIME)

        try:
            print("Press ESC and then Enter to terminate the program...")
            while self.escape_pressed == False:
                self.check_key_press()
                self.wait_listen(WAIT_TIME)
        finally:
            self.restore_terminal()

        # Closing steps
        self.do_set_advertise_enable(True)
        self.wait_listen(5 * WAIT_TIME)
        self.do_set_advertising_parameters(
            min_interval=0x0200, # 320 ms
            max_interval=0x0200, # 320 ms
            own_addr_type=0x00 # turn off random address
        )
        self.wait_listen(WAIT_TIME)
        self.do_set_advertise_enable(False)
        self.wait_listen(WAIT_TIME)


    
if __name__ == "__main__":
    ble = BLE(0)
    #ble.conn()
    ble.adv()
    #ble.test()
    
    print("DONE")
    
    
