#!/usr/bin/env python3

from ble import *
from test_gatt_server import GattServer
from ble_enum import Address
from ble_enum import AdvertisingDataType
import byte_utils as bu
import sys
import termios
import tty
import time
import select
import threading

class BLE(BluetoothLEConnection):
    def __init__(self, *args, **kwargs):
        test_gatt_server = GattServer()
        super().__init__(gatt_server=test_gatt_server, *args, **kwargs) 
        if self.gatt_server == None:
            print("self.gatt_sever == None")
            exit(0)

        self.escape_pressed = False
        self.last_print_time = time.time()
        self.old_settings = termios.tcgetattr(sys.stdin)
        self.long_wait = 0.05

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

    def updateCharacteristicValues(self):
        current_time = time.time()
        if current_time - self.last_print_time >= 5: # 5 seconds
            current_seconds = str(int(current_time) % 60)
            print("Set DEAF to {}".format(current_seconds))
            self.gatt_server.set_string_value_from_server(0x0016, current_seconds)
            self.last_print_time = current_time


    def adv(self):
        self.reset()
        self.wait_listen(self.long_wait)
        self.set_event_mask()
        self.wait_listen()
        self.set_le_event_mask()
        self.wait_listen()
        self.write_scan_enable()
        self.wait_listen()
        self.write_connection_accept_timeout()
        self.wait_listen()
        self.write_page_timeout_command()
        self.wait_listen()
        self.read_local_commands()
        self.wait_listen()
        self.read_local_board_address()
        self.wait_listen()
        self.read_le_buffer_size()
        self.wait_listen()
        self.write_local_name(self.gatt_server.device_name.encode("utf-8"))
        self.wait_listen()
        fields = [
            (AdvertisingDataType.FLAGS, bytes([0x06])), #0x06: General discoverable mode, BR/EDR not supported
            (AdvertisingDataType.SHORTENED_LOCAL_NAME, b"My Pi") 
        ]
        self.do_set_advertising_data(fields)
        self.wait_listen()
        fields = [
            (AdvertisingDataType.COMPLETE_LOCAL_NAME, self.gatt_server.device_name),
            (AdvertisingDataType.MANUFACTURER_SPECIFIC_DATA, bytes([0xAA, 0xBB, \
            0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0x00]))
        ]
        self.do_set_scan_response_data(fields)
        self.wait_listen()
        self.set_random_address()
        self.wait_listen()
        self.do_set_advertising_parameters(
            min_interval=0.320, 
            max_interval=0.320,
            own_addr_type=Address.RANDOM
        )
        self.wait_listen()
        self.do_set_advertise_enable(True)
        self.wait_listen()

        try:
            print("Press ESC and then Enter to terminate the program...")
            while self.escape_pressed == False:
                self.check_key_press()
                self.wait_listen()
                self.updateCharacteristicValues()
        finally:
            self.restore_terminal()

        # Closing steps
        self.do_set_advertise_enable(True)
        self.wait_listen(self.long_wait)
        self.do_set_advertising_parameters(
            min_interval=0.320,
            max_interval=0.320,
            own_addr_type=Address.PUBLIC # turn off random address
        )
        self.wait_listen()
        self.do_set_advertise_enable(False)
        self.wait_listen()


    
if __name__ == "__main__":
    ble = BLE(0)
    #ble.conn()
    ble.adv()
    #ble.test()
    
    print("DONE")
    
    
