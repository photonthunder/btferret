from ble import *
# sudo hcidump -x is a good troubleshooting command

MY_SCAN_DATA = bytes.fromhex('09094d79424c45446576'  # 0x09  Complete Local Name
                            )
MY_ADV_DATA =  bytes.fromhex('020106' +              # 0x01 Flags
                             '0303eeff'              # 0x03 16 bit Servuce UUID Complete
                            )

class BLE(BluetoothLEConnection):
    def adv(self):
        scan_rsp_data = MY_SCAN_DATA
        adv_data = MY_ADV_DATA

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
        self.wait_listen(0.1)
        self.wait_listen(0.1)
        self.wait_listen(0.1)
        self.wait_listen(10)

        # self.do_set_advertise_enable(False)
        # self.wait_listen(1)
        # self.do_set_advertising_parameters()
        # self.wait_listen(1)
        # self.do_set_advertising_data(adv_data)
        # self.wait_listen(1)
        # self.do_set_scan_response_data(scan_rsp_data)
        # self.wait_listen(1)
        # self.do_set_advertise_enable(True)
        # self.wait_listen(50)
    
if __name__ == "__main__":
    ble = BLE(0)
    #ble.conn()
    ble.adv()
    #ble.test()
    
    print("DONE")
    
    
