#!/usr/bin/env python3

from ble import *
from gatt_server import GattServer
from ble_enum import Address
from ble_enum import AdvertisingDataType
from gatt_enum import PROP_FLAGS
import byte_utils as bu
import random
import sys
import termios
import tty
import time
import select

class BLE(BluetoothLEConnection):
    def __init__(self, device_name, *args, **kwargs):
        test_gatt_server = GattServer(device_name)
        super().__init__(gatt_server=test_gatt_server, *args, **kwargs) 
        if self.gatt_server == None:
            print("self.gatt_sever == None")
            exit(0)

        print("Device Name = ", device_name)
        self.device_name = device_name
        self.device_name_short = device_name
        self.escape_pressed = False
        self.last_print_time = time.time()
        self.old_settings = termios.tcgetattr(sys.stdin)
        self.long_wait = 0.05

        self.adv()

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

    def random_printable_bytes(self, length):
        allowed_chars = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        return bytes(random.choice(allowed_chars) for _ in range(length))

    def updateCharacteristicValues(self):
        current_time = time.time()
        if current_time - self.last_print_time >= 5: # 5 seconds
            current_seconds = str(int(current_time) % 60)
            print(f"Set DEAF to {current_seconds}")
            if self.deaf_char.set_value_server(current_seconds.encode('utf-8')) == False:
                print(f"Error: value {current_seconds} didn't update for DEAF")
            random_bytes = self.random_printable_bytes(8)
            print(f"Set DCBA to {random_bytes}")
            if self.dcba_char.set_value_server(random_bytes) == False:
                print(f"Error: value {random_bytes} didn't update for DCBA")
            self.last_print_time = current_time

    def abcd_value_changed(self, new_value):
        # new_value = self.abcd_char.get_value_server()
        print("ABCD Value Updated, Updating CDEF")
        if self.cdef_char.set_value_server(new_value) == False:
            print("Error: value didn't update for ABCD")

    def adv(self):
        self.custom_service = self.gatt_server.add_service('11223344-5566-7788-99AA-BBCCDDEEFF00', name="My Custom Service")
        if self.custom_service is None:
            raise ValueError("Failed to add My Custom Service")
        self.abcd_char = self.custom_service.add_characteristic(
            uuid="ABCD",
            properties=[PROP_FLAGS.READ, PROP_FLAGS.WRITE_WITHOUT_RESPONSE],
            value=b'ENTER'[::-1]
        )
        if self.abcd_char is None:
            raise ValueError("Failed to add ABCD characteristic to My Custom Service")
        self.abcd_char.callback = self.abcd_value_changed
        self.cdef_char = self.custom_service.add_characteristic(
            uuid="CDEF",
            properties=[PROP_FLAGS.READ, PROP_FLAGS.NOTIFY, PROP_FLAGS.WRITE_WITHOUT_RESPONSE],
            value=b'0'[::-1]
        )
        if self.cdef_char is None:
            raise ValueError("Failed to add CDEF characteristic to My Custom Service")
        self.deaf_char = self.custom_service.add_characteristic(
            uuid="DEAF",
            properties=[PROP_FLAGS.READ, PROP_FLAGS.INDICATE],
            value=b'210'[::-1]
        )
        if self.deaf_char is None:
            raise ValueError("Failed to add deaf characteristic to My Custom Service")
        self.dcba_char = self.custom_service.add_characteristic(
            uuid="DCBA",
            properties=[PROP_FLAGS.READ, PROP_FLAGS.NOTIFY],
            value=b'SET CNT'[::-1]
        )
        if self.dcba_char is None:
            raise ValueError("Failed to add DCBA characteristic to My Custom Service")
        print(self.gatt_server.print_string())


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
        # self.read_local_public_key()
        # self.wait_listen()
        self.write_local_name(self.device_name.encode('utf-8'))
        self.wait_listen()
        fields = [
            (AdvertisingDataType.FLAGS, bytes([0x06])), #0x06: General discoverable mode, BR/EDR not supported
            (AdvertisingDataType.SHORTENED_LOCAL_NAME, self.device_name_short) 
        ]
        self.do_set_advertising_data(fields)
        self.wait_listen()
        fields = [
            (AdvertisingDataType.COMPLETE_LOCAL_NAME, self.device_name),
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
        self.do_set_advertise_enable(Advertising.ENABLED)
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
        self.do_set_advertise_enable(Advertising.DISABLED)
        self.wait_listen()


    
if __name__ == "__main__":
    device_name = "My Super Pi"
    ble = BLE(device_name)
    print("DONE")
    
    
