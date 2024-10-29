from ble import *
# sudo hcidump -x is a good troubleshooting command

class BLE(BluetoothLEConnection):
    def adv(self):
        self.reset()
        self.wait_listen(0.5)
        self.set_event_masks()
        self.wait_listen(0.1)
        self.set_le_event_masks()
        self.wait_listen(0.1)
        self.set_inquiry_timeouts()
        self.wait_listen(0.1)
        self.set_page_scan_activity()
        self.wait_listen(0.1)
        self.set_inquiry_scan_activity()
        self.wait_listen(0.1)
        self.read_local_commands()
        self.wait_listen(0.1)
        self.read_local_board_address()
        self.wait_listen(0.1)
        self.read_le_buffer_size()
        self.wait_listen(0.1)
        self.write_local_name("Super PI")
        self.wait_listen(0.1)
        self.set_random_address()
        self.wait_listen(0.1)
        self.do_set_advertising_parameters(
            min_interval=0x0200, # 320 ms
            max_interval=0x0200, # 320 ms
        )
        self.wait_listen(1)
        # adv_data = bytes([  0x0F, 0x08, 0xFF, 0x34, 0x12, 0x00, 0x00, 0xC0, 0xDE, 0x99, 0x05, 0x08,
        #                     0x61, 0x62, 0x63, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        #                     0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        # ])
        adv_data = bytes([  0x14, 0x08, 0xFF, 0x42, 0xC4, 0x00, 0x00, 0xC0, 0xDE, 0x99, 0x0A, 0x08,
                            0x4D, 0x79, 0x20, 0x4E, 0x65, 0x77, 0x20, 0x50, 0x69, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        self.do_set_advertising_data(adv_data)
        self.wait_listen(1)
        scan_rsp_data = bytes([ 0x0B, 0x09, 0x4D, 0x79, 0x20, 0x42, 0x4C, 0x45, 0x20, 0x44, 0x65, 0x76, 
                                0x12, 0xFF, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22, 0x33, 0x44,
                                0x55, 0x66, 0x77, 0x88, 0x99, 0x00, 0x00, 0x00
        ])

        self.do_set_scan_response_data(scan_rsp_data)
        self.wait_listen(1)
        # self.do_set_advertise_enable(True)
        # self.wait_listen(50)
    
if __name__ == "__main__":
    ble = BLE(0)
    #ble.conn()
    ble.adv()
    #ble.test()
    
    print("DONE")
    
    
