# BLE library using HCI commands and events
#
# Uses Bluez on Linux
#
# A lot of information from the Bluetooth Specification v5.4
# Also reading the Bumble python source code here:
#     https://github.com/google/bumble
# And the python-hcipy library here:
#     https://github.com/TheBubbleworks/python-hcipy
#

from time import sleep
from hci_socket import *
#from hci_uart import *
from random import randint
from ble_helper import AdvertisingDataType
from ble_helper import ATTErrorCode
from ble_helper import ByteHelper
from ble_helper import GATTAttributes  

### constants

COMMAND_TIMEOUT = 0.1
DATA_TIMEOUT = 10

#gap_adv_type =  ['ADV_IND', 'ADV_DIRECT_IND', 'ADV_SCAN_IND', 'ADV_NONCONN_IND', 'SCAN_RSP']
#gap_addr_type = ['PUBLIC', 'RANDOM']

HCI_SUCCESS = 0x00

LE_PUBLIC_ADDRESS = 0x00
LE_RANDOM_ADDRESS = 0x01

HCI_COMMAND_PKT = 0x01
HCI_ACLDATA_PKT = 0x02
HCI_EVENT_PKT = 0x04

ATT_CID = 0x0004

SCAN_TYPE_ACTIVE  = 0x01
FILTER_POLICY_NO_WHITELIST = 0x00

cmd_text = "\nCommand:"
att_rsp_text = "\nATT RSP:"
att_req_text = "ATT REQ:"
event_text = "Event:"

################################################################
#
# Make the ACL and HCI command headers
#
################################################################

def make_acl(handle, length):
    header =  ByteHelper.from_u8 (0x02)       # hci command prefix for ACL
    header += ByteHelper.from_u16(handle)     # hci handle
    header += ByteHelper.from_u16(length + 4) # hci packet length
    header += ByteHelper.from_u16(length)     # l2cap length
    header += ByteHelper.from_u16(ATT_CID)    # channel for ATT - 4 for BLE
    return header

def make_cmd(cmd, length):
    header =  ByteHelper.from_u8 (0x01)       # hci command prefix
    header += ByteHelper.from_u16(cmd)        # hci command
    header += ByteHelper.from_u8 (length)     # hci packet length
    return header

################################################################
#
# Bluetooth class
#
# Contains core class and all command and event handling
#
################################################################

class BluetoothLEConnection:

    def __init__(self, dev_id=0, gatt_server=None):
        self.handle = 64
        self.user_socket = HCI(dev_id)
        self.gatt_server = gatt_server

        # ACL packet being constructed
        self.acl_packet = None
        self.acl_length = 0
        self.acl_total_length = 0

        # Last command complete information
        self.command_complete = None
        self.command_status = None

        self.local_board_address = None
        self.hc_le_data_packet_length = None
        self.hc_le_data_buffer = None
        self.local_name = None
        self.client_connected = False

    def __del__(self):
        self.user_socket.close()
        return

    ### helper functions calling BTUserSocket

    def send(self, data):
        print("<<", ByteHelper.as_hex(data))
        self.user_socket.send_raw(data)

    def receive(self):
        data = self.user_socket.receive_raw()
        print("\n>>", ByteHelper.as_hex(data))
        self.on_data(data)
        return data

    def readable(self):
        return self.user_socket.readable()

    def wait_listen(self, timeout = DATA_TIMEOUT):
        quanta = 0.001
        timer = timeout
        while timer > 0:
            timer -= quanta
            while self.readable():
                a = self.receive()
            self.check_notification()
            self.check_indication()
            sleep(quanta)

    def wait_complete(self, command, timeout = DATA_TIMEOUT):
        quanta = 0.1
        timer = timeout
        while timer > 0 and self.command_complete != command:
            timer -= quanta
            while self.readable():
                a = self.receive()
            sleep(quanta)

    def send_command(self, command, packet, wait = False):
        cmd = make_cmd(command, len(packet)) + packet
        self.send(cmd)
        if wait == True:
            self.wait_complete(command, COMMAND_TIMEOUT)

    def check_le_compatable(self, data):
        if (ByteHelper.to_u8(data, 32) & 0xA2 == 0xA2) and (ByteHelper.to_u8(data, 33) & 0x3E == 0x3E):
            print("LE Compatable")
        else:
            print("Error: Not LE Compatable")
            exit(0)

    def board_address(self, data):
        # The local board address is typically the last 6 bytes of the received data
        if len(data) < 6:
            self.local_board_address = None
            print("Error: not enough data bytes")
            return None  # Not enough data to extract address
        
        # Extract the last 6 bytes
        self.local_board_address = data[-6:]
        
        # Format the address as a hex string, usually shown in reversed order (little-endian)
        formatted_address = ':'.join(f'{byte:02X}' for byte in reversed(self.local_board_address))
        print('Local Board Address:', formatted_address)
        return formatted_address

    def read_buffer_size(self, data):
        self.hc_le_data_packet_length = ByteHelper.to_u16(data, 7)
        print("le data length = {}".format(self.hc_le_data_packet_length))
        self.hc_le_data_buffer = ByteHelper.to_u8(data, 9)
        print("le data buffer = {}".format(self.hc_le_data_buffer))
        





    ################################################################
    #
    # Event handling routines
    #
    # Process HCI events and meta-events
    #
    ################################################################

    # 1 = Command Packets
    # 2 = Data Packets for ACL
    # 3 = Data Packets for SCO
    # 4 = Event Packets

    # Handle HCI meta event types

    def on_le_connection_complete(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65.1 LE Connection Complete (p2235)
        # Event_code = 0x3e
        # HCI_LE_Connection_Complete = 0x01
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent code                                  1 octet
        #     status                                         1 octet
        #     connection_handle                              2 octets
        #     role                                           1 octets
        #     peer_address_type                              1 octet
        #     peer_address                                   6 octets
        #     connection_interval                            2 octets
        #     peripheral_latency                             2 octets
        #     supervision_timeout                            2 octets
        #     central_clock_accuracy                         1 octet
      
        status = ByteHelper.to_u8(data, 4)
        handle = ByteHelper.to_u16(data, 5)
        address = ByteHelper.to_addr(data, 9)
        
        self.handle = handle         # save this for other commands to use
        print("Event: LE Connection Complete")
        print("Status: {:02x} Address: {}".format(status, address))

    def on_le_advertising_report(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65.2 LE Advertising Report (p2238)
        # Event_code = 0x3e
        # HCI_LE_Advertising_Report = 0x02
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent_code                                  1 octet
        #     num_reports                                    1 octet
        #         event_type[i]                              1 octet
        #         address_type[i]                            1 octet
        #         address[i]                                 6 octets
        #         data_length[i]                             1 octet
        #         data[i]                                    data_length octets
        #         rssi[i]                                    1 octet
        
        # These lines double the report to test for num_reports = 2
        # num_reports = ByteHelper.to_u8       (data, 4)
        # reports =     ByteHelper.to_data_rest(data, 5)
        # data = data[0:4] + ByteHelper.from_u8(2) + reports + reports

        num_reports = ByteHelper.to_u8       (data, 4)
        reports =     ByteHelper.to_data_rest(data, 5)                  # the actual 'reports'
        
        report_offset = 0                                    # start of this entry in 'reports'
        for rep in range(0, num_reports):
            address =     ByteHelper.to_addr (reports, report_offset+2)
            data_len =    ByteHelper.to_u8   (reports, report_offset+8)
            report_data = ByteHelper.to_data (reports, report_offset+9, data_len)
            rssi =        ByteHelper.to_u8   (reports, report_offset+9+data_len)
            
            print("Address: {}      RSSI: {}".format(address, rssi))
            i = 0
            while i < data_len:
                entry_len = ByteHelper.to_u8(report_data, i) 
                if entry_len > 0:
                    typ = ByteHelper.to_u8  (report_data, i+1)
                    dat = ByteHelper.to_data(report_data, i+2, entry_len-1)
                    print("Length: {:3} Type: {:02x}  Data: {}      {}".format(entry_len, typ, ByteHelper.as_hex(dat), ByteHelper.as_printable(dat)))
                    i += entry_len
                i += 1
            report_offset += data_len+10                     # move on to next entry
                  
    def on_le_connection_update_complete(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65.3 LE Connection Update Complete (p2240)
        # Event_code = 0x3e
        # HCI_LE_Connection_Update_Complete = 0x03
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent code                                  1 octet
        #     status                                         1 octet
        #     connection_handle                              2 octets
        #     connection_interval                            2 octets
        #     peripheral_latency                             2 octets
        #     supervision_timeout                            2 octets

        status =   ByteHelper.to_u8(data, 4)
        handle =   ByteHelper.to_u16(data, 5)
        interval = ByteHelper.to_u16(data, 7)
        latency = ByteHelper.to_u16(data, 9)
        timeout =  ByteHelper.to_u16(data, 11)
        
        print("LE Connection Update Complete")
        print("Handle: {:04x} Status: {02x}".format(handle, status))
        
        #self.handle = handle         # save this for other commands to use

        # Should respond with 020001 ???

    def on_le_read_remote_features_complete(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65.4 LE Meta event (p2242)
        # Event_code = 0x3e
        # HCI_LE_Read_Remote_Features_Complete = 0x04
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent_code                                  1 octet
        #     status                                         1 octet
        #     connection_handle                              2 octets
        #     le features                                    8 octets      # need to update templates for this!!

        print("Read Remote Features Complete")
        
        handle = ByteHelper.to_u16(data, 5)
        features = ByteHelper.to_data_rest(data, 7)
        
        print("Handle: {} Features {}".format(handle, ByteHelper.as_hex(features)))

    def on_le_data_length_change(self, data):
        handle = ByteHelper.to_u16(data, 4)
        max_tx_octets = ByteHelper.to_u16(data, 6) # 0x001B to 0x00FB
        max_tx_time = ByteHelper.to_u16(data, 8) # 0x0148 to 0x4290
        max_rx_octets = ByteHelper.to_u16(data, 10) # 0x001B to 0x00FB
        max_rx_time = ByteHelper.to_u16(data, 12) # 0x0148 to 0x4290
        print(event_text, "Data length changed for 0x{:04X}".format(handle))

    def on_le_read_local_public_key(self, data):
        status = ByteHelper.to_u8(data, 4)
        key_x_coordinate = ByteHelper.to_data(data, 5, 37)  # 32 octets
        key_y_coordinate = ByteHelper.to_data(data, 37, 69) # 32 octets
        print(event_text, "Read Local Public Key Complete")

    def on_le_update_complete(self, data):
        status = ByteHelper.to_u8(data, 4)
        handle = ByteHelper.to_u16(data, 5)
        connection_interval = ByteHelper.to_u16(data, 7)
        supervision_timeout = ByteHelper.to_u16(data, 9)
        print(event_text, "Connection Update Complete")

    def on_hci_meta_event(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65 LE Meta event (p2235)
        # Event_code = 0x3e
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent_code                                  1 octet
        #     data                                           n octets

        subevent_code = ByteHelper.to_u8(data, 3)
        # print(event_text, "LE Meta event: ", hex(subevent_code))
        if   subevent_code == 0x01:                 # LE Connection Complete
            self.client_connected = True
            self.on_le_connection_complete(data)
        elif subevent_code == 0x02:                 # LE Advertising Report
            self.on_le_advertising_report(data)
        elif subevent_code == 0x03:                 # LE Connection Update Complete
            self.on_le_update_complete(data)
        elif subevent_code == 0x04:                 # LE Read Remove Features Complete
            self.on_le_read_remote_features_complete(data)
        elif subevent_code == 0x07:           
            self.on_le_data_length_change(data)
        elif subevent_code == 0x08:
            self.on_le_read_local_public_key(data)
        else:
            print("LE Meta Event: Unhandled:", hex(subevent_code))

    def on_hci_event_disconnect_complete(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.5 HCI_Disconnection_Complete (p2163)
        # HCI_Disconnection_Complete = 0x05
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     status                                         1 octet
        #     connection_handle                              2 octets
        #     reason                                         1 octet

        
        status = ByteHelper.to_u8  (data, 3)
        handle = ByteHelper.to_u16 (data, 4)
        reason = ByteHelper.to_u8  (data, 6)
        self.client_connected = False
        if status == 0:
            print("HCI Disconnection Complete, Handle = 0x{:04X}".format(handle))
        else:
            print("Error: Disconnection Not successful!!!")
        if reason == 0x13:
            print("Remote User terminated Connection")
        else:
            print("Disconnect Reason: 0x{:02X}".format(reason))
        self.gatt_server.clear_connection_settings()
        

    def handle_le_command(self, cmd, status_text, data=None):
        # Define a dictionary to map command values to their corresponding messages or functions
        command_map = {
            0x0C01: ('General Event Mask Complete', None),
            0x0C03: ('Reset Complete', None),
            0x0C13: ('Write Local Name Complete', None),
            0x0C16: ('Set Page Scan Interval and Window', None),
            0x0C18: ('Set Inquiry Interval and Window', None),
            0x0C1A: ('Set Page/Inquiry Scan Timeout Complete', None),
            0x1002: ('Read Local Supported Commands', 'check_le_compatable'),
            0x1009: ('Read Local Board Address', 'board_address'),
            0x2001: ('LE Event Mask Complete', None),
            0x2002: ('LE Read Buffer Size', 'read_buffer_size'),
            0x2005: ('LE Set Random Address', None),
            0x200b: ('LE Scan Parameters Set', None),
            0x200c: ('LE Scan Enable Set', None),
            0x2006: ('LE Advertising Parameters Set', None),
            0x2008: ('LE Advertising Data Set', None),
            0x2009: ('LE Scan Response Data Set', None),
            0x200a: ('LE Advertising Set', None),
            0x2025: ('LE Get Extended Advertising', None),

        }

        # Check if the command exists in the map
        if cmd in command_map:
            message, function_name = command_map[cmd]
            print(event_text, "{}: {}".format(message, status_text))

            # If there's a function to call, do so with data
            if function_name and hasattr(self, function_name):
                getattr(self, function_name)(data)
        else:
            print(f'Unknown Event: {cmd} ({hex(cmd)}), {status_text}')


    def on_hci_event_command_complete(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.14 HCI Command Complete (p2177)
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     num_hci_command_packets                        1 octet
        #     command_opcode                                 2 octets
        #     return_parameters                              n octets
        
        # First return_parameters field is usually
        #     status                                         1 octet

        # print(event_text, "HCI Command Complete")
        cmd =    ByteHelper.to_u16 (data, 4)
        status = ByteHelper.to_u8  (data, 6)
        status_text = "Success" if status == HCI_SUCCESS else "Failure"
        self.command_complete = cmd
        self.command_status =   status
        self.handle_le_command(cmd, status, data)

    def on_hci_event_command_status(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.15 HCI_Command_Status (p2179)
        # HCI_Command_Status = 0x0f
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     status                                         1 octet
        #     num_hci_command_packets                        1 octet
        #     command_opcode                                 2 octets

        # print(event_text, "HCI Command Status")
        status = ByteHelper.to_u8  (data, 3)
        opcode = ByteHelper.to_u16 (data, 5)
        if opcode == 0x2025:
            print(event_text, "Local Public Key Command Complete")
        else:
            print(event_text, "Unknown Opcode: {:02x} status: {:02x}".format(opcode, status))

    def on_hci_event_number_of_completed_packets(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.19 HCI Number Of Completed Packets (p2184)
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     num_handles                                    1 octet
        #     connection handle[i]                           2n octets
        #     num completed packets[i]                       2n octets

        print(event_text, "HCI Number Of Completed Packets = {}".format(ByteHelper.to_u16(data, len(data) - 2)))
        self.gatt_server.clear_ack()  # Appears that some use this as an ack to indication
        

    def on_hci_event_vendor_specific (self, data):
        print(event_text, "Vendor Specific")

    def on_hci_event(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.4 HCI Event Packet (p1804)
        #     [packet_type                                   1 octet]
        #     event_code                                     1 octet
        #     parameter_length                               1 octet
        #     parameters                                     n octets

        event = ByteHelper.to_u8(data, 1)         
        # print("\nHCI Event Packet:", hex(event))

        if   event == 0x0f:                                   # Command Status
            self.on_hci_event_command_status(data)
        elif event == 0x05:                                   # Disconnection Complete
            self.on_hci_event_disconnect_complete(data)
        elif event == 0x3e:                                   # LE Meta Event
            self.on_hci_meta_event(data)
        elif event == 0x0e:                                   # Command complete
            self.on_hci_event_command_complete(data)
        elif event == 0x13:                                   # Number of Completed Packets
            self.on_hci_event_number_of_completed_packets(data)
        elif event == 0xFF:                         
            self.on_hci_event_vendor_specific(data)
        else:
            print(event_text, "Unhandled", hex(event))

    def on_acl_packet(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet (p1801)
        #     [packet_type                                  1 octet]
        #     handle (BC[2] PB[2] handle[12])               2 octets
        #     packet length                                 2 octets
        #     data_length                                   2 octets
        #     channel                                       2 octets
        #     data                                          n octets

        # print("ACL Packet")

        handle = ByteHelper.to_bits_u16(data, 1, 0, 12)
        pb =     ByteHelper.to_bits_u16(data, 1, 12, 2)
        bc =     ByteHelper.to_bits_u16(data, 1, 14, 2)
        length = ByteHelper.to_u16(data, 3)  #di["packet length"]
 
        full_packet = False
        # print('ACL header: handle: {}  bc: {}  pb: {}'.format(handle, bc, pb))

        if pb & 0x01 == 0:
            size =     ByteHelper.to_u16(data, 5)
            channel =  ByteHelper.to_u16(data, 7)
            acl_data = ByteHelper.to_data_rest(data, 9)
            full_packet = length - size == 4

            print("Channel: {} Length: {} Data size: {} Full packet? {}".format(channel, length, size, full_packet))
            # print("ACL packet:    ", ByteHelper.as_hex(acl_data))

            self.acl_total_length = size
            self.acl_packet =       acl_data

        if pb & 0x01 == 1:
            print("ACL Packet Continuation")
            acl_data = ByteHelper.to_data_rest(data, 5)
            self.acl_packet += acl_data
            print("ACL data:  ", ByteHelper.as_hex(acl_data))
            if len(self.acl_packet) == self.acl_total_length:    # This was the last continuation packet
                full_packet = True
                print("ACL Packet Final")
                print("Full ACL data: ", ByteHelper.as_hex(self.acl_packet))
                
        if full_packet:
            self.on_acl_event(self.acl_packet)                 
            

    # HCI packet received handler

    def on_data(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.4 HCI Event Packet (p1804)
        # Specification v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet (p1801)
        #
        #     packet_type                                    1 octet

        packet_type = ByteHelper.to_u8(data, 0)
        # print("Packet type:", packet_type)

        self.command_complete = None               # set to None and changed by Command Complete event
        self.command_status = None

        if   packet_type == 0x04:                  # event packet
            self.on_hci_event(data)
        elif packet_type == 0x02:                  # ACL data packet
            self.on_acl_packet(data)
        else:
            print("Unhandled packet type", packet_type)

    ################################################################
    #
    # Command handling routines
    #
    # Process HCI commands
    #
    ################################################################

    def reset(self):
        print(cmd_text, "BLE Reset")
        
        packet = ByteHelper.from_u8(None)
        self.send_command(0x0C03, packet)

    def set_event_masks(self):
        print(cmd_text, "General Event Mask")
        # 8 byte event mask
        packet = bytes([0xFF, 0xFF, 0xFB, 0xFF, 0x07, 0xF8, 0xBF, 0x3D])
        self.send_command(0x0C01, packet)

    def set_le_event_masks(self):
        print(cmd_text, "LE Event Mask")
        # 8 byte event mask
        packet = bytes([0xFF, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.send_command(0x2001, packet)

    def set_inquiry_timeouts(self):
        print(cmd_text, "Set Page/Inquiry Scan and Tmeouts (10 secs)")
        packet = bytes([0x03])
        self.send_command(0x0C1A, packet)

    def set_page_scan_activity(self):
        print(cmd_text, "Set Page Scan Interval and Window (10 secs)")
        packet = bytes([0xA0, 0x3F])
        self.send_command(0x0C16, packet)

    def set_inquiry_scan_activity(self):
        print(cmd_text, "Set Inquiry Scan Interval and Window (10 secs)")
        packet = bytes([0x00, 0x40])
        self.send_command(0x0C18, packet)

    def read_local_commands(self):
        print(cmd_text, "Read Local Supported Commands")
        packet = ByteHelper.from_u8(None)
        self.send_command(0x1002, packet)

    def read_local_board_address(self):
        print(cmd_text, "Read Local Board Address")
        packet = ByteHelper.from_u8(None)
        self.send_command(0x1009, packet)

    def read_le_buffer_size(self):
        print(cmd_text, "Read LE Buffer Size")
        packet = ByteHelper.from_u8(None)
        self.send_command(0x2002, packet)

    def write_local_name(self, name):
        self.local_name = name
        print(cmd_text, "Write Local Name {}".format(name))
        name_bytes = name.encode('utf-8')
        if len(name_bytes) > 248:
            raise ValueError("Name is too long, must be 248 bytes or less.")
        packet = name_bytes.ljust(248, b'\x00')
        self.send_command(0x0C13, packet)

    def set_random_address(self):
        random_address = bytes([randint(0x00, 0xFF) for _ in range(6)])
        random_address_str = ':'.join(f'{byte:02X}' for byte in reversed(random_address))
        print(cmd_text, "Generated Random Bluetooth Address: {}".format(random_address_str))
        self.send_command(0x2005, random_address)

    def read_local_public_key(self):
        print(cmd_text, "Read Local Public Key")
        packet = ByteHelper.from_u8(None)
        self.send_command(0x2025, packet)



    def do_set_advertising_parameters(self, adv_type=0x00, own_addr_type=0x00,
                                      peer_addr='00:00:00:00:00:00', peer_addr_type=0x00,
                                      min_interval=0x00a0, max_interval=0x00a0, adv_channel_map=0x07,
                                      adv_filter_policy=0x00):
        # Specification v5.4  Vol 4 Part E 7.8.5 LE Set Advertising Parameters (p2350)
        # Opcode 0x2006
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octets]
        #     advertising interval min                      2 octets
        #     advertising interval max                      2 octets
        #     advertising type                              1 octet
        #     own address type                              1 octet
        #     peer address type                             1 octet
        #     peer address                                  6 octets
        #     advertising channel map                       1 octet
        #     advertising filter policy                     1 octet
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x2006

        print(cmd_text, "LE Set Advertising Parameters")
        
        packet =  ByteHelper.from_u16  (min_interval)
        packet += ByteHelper.from_u16  (max_interval)
        packet += ByteHelper.from_u8   (adv_type)
        packet += ByteHelper.from_u8   (own_addr_type)
        packet += ByteHelper.from_u8   (peer_addr_type)
        packet += ByteHelper.from_addr (peer_addr)
        packet += ByteHelper.from_u8   (adv_channel_map)
        packet += ByteHelper.from_u8   (adv_filter_policy)
        self.send_command(0x2006, packet)

    def create_advertising_packet(self, fields):
        packet = bytes()
        total_length = 0
        for field_type, field_data in fields:
            if not isinstance(field_type, AdvertisingDataType):
                raise ValueError(f"Field type must be an instance of AdvertisingDataType.")
            if not isinstance(field_data, bytes):
                raise ValueError(f"Data for type {field_type.name} must be provided as bytes.")
            length = len(field_data) + 1
            if length > 31:
                raise ValueError(f"Field data for type {field_type.name} exceeds the maximum allowed length.")
            packet += ByteHelper.from_u8(length)
            packet += ByteHelper.from_u8(field_type.value)
            packet += field_data
        if len(packet) > 31:
            raise ValueError("Total advertising packet exceeds the 31-byte maximum.")
        packet = ByteHelper.from_u8(len(packet)) + packet
        pad = bytes(b'\x00' * (32-len(packet)))
        packet += pad
        return bytes(packet)

    def do_set_advertising_data(self, fields, old_data = None):
        # Specification v5.4  Vol 4 Part E 7.8.7 LE Set Advertising Data (p2355)
        # Opcode 0x2008
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octets]
        #     advertising data length                       1 octet
        #     advertising data                              31 octets
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x2008
        packet = self.create_advertising_packet(fields)
        for i, (byte1, byte2) in enumerate(zip(packet, old_data)):
            if byte1 != byte2:
                print(f"Difference at index {i}: {byte1} != {byte2}")

        if packet != old_data:
            raise ValueError("Not equal {} {}".format(packet, old_data))

        print(cmd_text, "LE Set Advertising Data")
        self.send_command(0x2008, packet)

    def do_set_scan_response_data(self, data):
        # Specification v5.4  Vol 4 Part E 7.8.8 LE Set Scan Response Data (p2357)
        # Opcode 0x2009
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octets]
        #     advertising data length                       1 octet
        #     advertising data                              31 octets
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x2009

        print(cmd_text, "LE Set Scan Response Data")
        pad = bytes(b'\x00' * (31 - len(data)))

        # packet =  ByteHelper.from_u8 (len(data))
        packet =         data
        packet +=         pad
        self.send_command(0x2009, packet)

    def do_set_advertise_enable(self, enabled):
        # Specification v5.4  Vol 4 Part E 7.8.9 LE Set Advertising Enable (p2359)
        # Opcode 0x200a
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octets]
        #     advertising enable                            1 octet
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x200a
        #     HCI LE Connection Complete                    0x3e  0x01      (in some cases)
        if enabled:
            print(cmd_text, "LE Set Advertising: Enabled")
        else:
            print(cmd_text, "LE Set Advertising: Disabled")
        
        packet = ByteHelper.from_u8(0x01 if enabled else 0x00)
        self.send_command(0x200a, packet)

    def do_set_scan_parameters(self, scan_type=SCAN_TYPE_ACTIVE, scan_internal=0x0060, scan_window=0x0060,
                               own_addr_type=LE_PUBLIC_ADDRESS, scan_filter_policy=FILTER_POLICY_NO_WHITELIST):
        # Specification v5.4  Vol 4 Part E 7.8.10 LE Set Scan Parameters (p2361)
        # Opcode 0x200b
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octet]
        #     le scan type                                  1 octet
        #     le scan interval                              2 octets
        #     le scan window                                2 octets
        #     own address type                              1 octet
        #     scanning filter policy                        1 octet
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x200b

        print(cmd_text, "LE Set Scan Parameters")
        
        packet =  ByteHelper.from_u8  (scan_type)
        packet += ByteHelper.from_u16 (scan_internal)
        packet += ByteHelper.from_u16 (scan_window)
        packet += ByteHelper.from_u8  (own_addr_type)
        packet += ByteHelper.from_u8  (scan_filter_policy)
        self.send_command(0x200b, packet)

    def do_set_scan(self, enabled=False, duplicates=False):
        # Specification v5.4  Vol 4 Part E 7.8.11 LE Set Scan Enable (p2364)
        # Opcode 0x200c
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octet]
        #     le scan enable                                1 octet
        #     filter duplicates                             1 octet
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x200c
        #     HCI LE Advertising Report                     0x3e  0x02      (one or more)

        #enable = 0x01 if enabled else 0x00
        #dups   = 0x01 if duplicates else 0x00

        print(cmd_text, "LE Set Scan Enable" if enabled else "LE Set Scan Disable")
        
        packet =  ByteHelper.from_u8(0x01 if enabled else 0x00)
        packet += ByteHelper.from_u8(0x01 if duplicates else 0x00)        
        self.send_command(0x200c, packet)

    def do_create_connection(self, addr, addr_type, interval=0x0060, window=0x0060, initiator_filter=0x00,
                             own_addr_type= 0x00, min_interval=0x0018, max_interval=0x0028, latency=0x0000,
                             supervision_timeout=0x002a, min_ce_length=0x0000, max_ce_length = 0x0000):
        # Specification v5.4  Vol 4 Part E 7.8.12 LE Create Connection (p2366)
        # Opcode 0x200d
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octet]
        #     le scan interval                              2 octets
        #     le scan window                                2 octets
        #     initiator filter policy                       1 octet
        #     peer address type                             1 octet
        #     peer address                                  6 octets
        #     own address type                              1 octet
        #     connection interval min                       2 octets
        #     connection interval max                       2 octets
        #     max latency                                   2 octets
        #     supervision timeout                           2 octets
        #     min ce length                                 2 octets
        #     max ce length                                 2 octets
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x200d
        #     HCI LE Connection Complete                    0x3e  0x01

        print(cmd_text, "LE Create Connection")
        
        packet =  ByteHelper.from_u16 (interval)
        packet += ByteHelper.from_u16 (window)
        packet += ByteHelper.from_u8  (initiator_filter)
        packet += ByteHelper.from_u8  (addr_type)
        packet += ByteHelper.from_addr(addr)
        packet += ByteHelper.from_u8  (own_addr_type)
        packet += ByteHelper.from_u16 (min_interval)
        packet += ByteHelper.from_u16 (max_interval)
        packet += ByteHelper.from_u16 (latency)
        packet += ByteHelper.from_u16 (supervision_timeout)
        packet += ByteHelper.from_u16 (min_ce_length)
        packet += ByteHelper.from_u16 (max_ce_length)
        self.send_command(0x200d, packet)
        

    def do_add_device_to_accept_list(self, addr, addr_type):
        # Specification v5.4  Vol 4 Part E 7.8.16 LE Add Device To Filter Accept List (p2375)
        # Opcode 0x2011
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octet]
        #     address type                                  1 octet
        #     address                                       6 octets
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x2011


        print(cmd_text, "LE Add Device To Filter Accept List")
        
        packet =  ByteHelper.from_u8(addr_type)
        packet += ByteHelper.from_addr(addr)
        self.send_command(0x2011, packet)

    def do_read_remote_used_features(self):
        # Specification v5.4  Vol 4 Part E 7.8.21 LE Read Remote Features (p2385)
        # Opcode 0x2016
        #
        #     [packet_type                                  1 octet]
        #     [opcode                                       2 octets]
        #     [packet length                                1 octet]
        #     connection handle                             2 octets
        #
        # Response:
        #     HCI Command Complete                          0x0e  0x2016
        #     HCI LE Read Remote Features Complete          0x3e  0x04  

        print(cmd_text, "LE Read Remote Features")
        
        packet = ByteHelper.from_u16(self.handle)
        self.send_command(0x2016, packet)

    #
    # ACL commands
    #
    
    def do_att_error_rsp(self, request_opcode, handle, error_code):
        print(att_rsp_text, "Error")

        packet =  ByteHelper.from_u8(0x01) 
        packet += ByteHelper.from_u8(request_opcode)     
        packet += ByteHelper.from_u16(handle) 
        packet += ByteHelper.from_u8(error_code)
        
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_exchange_mtu_req(self, mtu_size = 244):
        # Specification v5.4  Vol 3 Part F 3.4.2.1 ATT_EXCHANGE_MTU_REQ (p1416)
        # ATT Opcode 0x02
        #     [packet_type                                  1 octet]
        #     [handle (BC[2] PB[2] handle[12])              2 octets]
        #     [packet length                                2 octets]
        #     [data_length                                  2 octets]
        #     [channel                                      2 octets]
        #     opcode                                        1 octet
        #     client receive mtu size                       2 octets

        print(att_req_text, "EXCHANGE MTU (0x02)")

        packet =  ByteHelper.from_u8  (0x02)           # ATT opcode ATT_EXCHANGE_MTU_REQ
        packet += ByteHelper.from_u16 (mtu_size)       # MTU size requested
        
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_exchange_mtu_rsp(self, mtu_size = 244):
        print(att_rsp_text, "EXCHANGE MTU (0x03)")

        packet =  ByteHelper.from_u8  (0x03)      
        packet += ByteHelper.from_u16 (mtu_size) 
        
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)


    def do_att_find_information_req(self, start_handle, end_handle):
        # Specification v5.4  Vol 3 Part F 3.4.3.1 ATT_FIND_INFORMATION_REQ (p1418)
        # ATT Opcode 0x04
        #
        #     [packet_type                                  1 octet]
        #     [handle (BC[2] PB[2] handle[12])              2 octets]
        #     [packet length                                2 octets]
        #     [data_length                                  2 octets]
        #     [channel                                      2 octets]
        #     opcode                                        1 octet
        #     starting handle                               2 octets
        #     ending handle                                 2 octets

        print(att_req_text, "FIND INFORMATION (0x04)")
        
        packet =  ByteHelper.from_u8(0x04)          # ATT opcode ATT_FIND_INFORMATION_REQ
        packet += ByteHelper.from_u16(start_handle)
        packet += ByteHelper.from_u16(end_handle)

        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_find_information_rsp(self, start_handle, end_handle):
        print(att_rsp_text, "FIND INFORMATION (0x05)")
        return_code, uuid_format, handle_uuid = self.gatt_server.find_information(start_handle, end_handle)
        if return_code != ATTErrorCode.SUCCESS:
            self.do_att_error_rsp(0x04, start_handle, return_code) 
            return
        packet =  ByteHelper.from_u8(0x05)
        packet += ByteHelper.from_u8(uuid_format)
        for each_handle_uuid in handle_uuid:
            handle, uuid = each_handle_uuid
            packet += ByteHelper.from_u16(start_handle)
            packet += uuid

        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)
        


    def do_att_read_by_type_req(self, start_handle, end_handle, attribute_type):
        # Specification v5.4  Vol 3 Part F 3.4.4.1 ATT_READ_BY_TYPE_REQ (p1422)
        # ATT Opcode 0x08
        #
        #     [packet_type                                  1 octet]
        #     [handle (BC[2] PB[2] handle[12])              2 octets]
        #     [packet length                                2 octets]
        #     [data_length                                  2 octets]
        #     [channel                                      2 octets]
        #     opcode                                        1 octet
        #     starting handle                               2 octets
        #     ending handle                                 2 octets
        #     attribute type (UUID)                         2 or 16 octets

        print(att_req_text, "READ BY TYPE (0x08)")
        
        packet =  ByteHelper.from_u8  (0x08)               # ATT opcode ATT_READ_BY_TYPE_REQ
        packet += ByteHelper.from_u16 (start_handle)
        packet += ByteHelper.from_u16 (end_handle)
        packet += ByteHelper.from_u16 (attribute_type)        
               
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_read_by_type_rsp(self, start_handle, end_handle, uuid):
        print(att_rsp_text, "READ BY TYPE (0x09)")
        packet =  ByteHelper.from_u8  (0x09)
        if uuid == GATTAttributes.CHARACTERISTIC.value:
            return_code, char_decl = self.gatt_server.read_char_uuid_value(start_handle, end_handle)
            if return_code != ATTErrorCode.SUCCESS:
                self.do_att_error_rsp(0x08, start_handle, return_code) 
                return
            elif not char_decl:
                print("No CD Handle in range of 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
                self.do_att_error_rsp(0x08, start_handle, return_code) 
                return
            else:
                # len_char_item = len(char_decl)
                packet += ByteHelper.from_u8(7) 
                # for idx, char_item in enumerate(char_decl):
                handle, prop_byte, value_handle, char_uuid = char_decl
                packet += ByteHelper.from_u16(handle)
                packet += ByteHelper.from_u8(prop_byte)
                packet += ByteHelper.from_u16(value_handle)
                packet += char_uuid
        
        else:
            return_code, handle, data = self.gatt_server.read_uuid_value(start_handle, end_handle, uuid)
            if return_code != ATTErrorCode.SUCCESS:
                self.do_att_error_rsp(0x08, start_handle, return_code) 
                return  
            packet += ByteHelper.from_u8(2 + len(data))
            packet += ByteHelper.from_u16 (handle)
            packet += data        
               
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_read_req(self, handle):
        # Specification v5.4  Vol 3 Part F 3.4.4.1 ATT_READ_REQ (p1425)
        # ATT Opcode 0x0a
        #
        #     [packet_type                                  1 octet]
        #     [handle (BC[2] PB[2] handle[12])              2 octets]
        #     [packet length                                2 octets]
        #     [data_length                                  2 octets]
        #     [channel                                      2 octets]
        #     opcode                                        1 octet
        #     handle                                        2 octets

        print(att_req_text, "GROUP TYPE (0x0A)")
        
        packet =  ByteHelper.from_u8  (0x0A)               # ATT opcode ATT_READ_REQ
        packet += ByteHelper.from_u16 (handle)
               
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_read_rsp(self, handle):
        print(att_rsp_text, "READ (0x0B)")
        return_code, byte_value = self.gatt_server.read_char_value(handle)
        if return_code != ATTErrorCode.SUCCESS: 
            self.do_att_error_rsp(0x0A, handle, return_code)
            return
        else: 
            packet = ByteHelper.from_u8(0x0B)
            packet += byte_value
            cmd = make_acl(self.handle, len(packet)) + packet
            self.send(cmd)

    def do_att_group_type_rsp(self, gatt_uuid, start_handle, end_handle):
        print(att_rsp_text, "GROUP TYPE (0x11)")
        packet =  ByteHelper.from_u8  (0x11)    
        if gatt_uuid == GATTAttributes.PRIMARY_SERVICE.value:
            print("Get primary services for handles 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
            return_code, return_start_handle, return_end_handle, primary_uuid = self.gatt_server.get_service_handle_range(start_handle)
            if return_code != ATTErrorCode.SUCCESS: 
                self.do_att_error_rsp(0x10, handle, return_code)
                return
            print("Handles 0x{:04X} to 0x{:04X}".format(return_start_handle, return_end_handle))
            if end_handle < return_end_handle:
                print("Service handle 0x{:04X} larger than request max 0x{:04X}, truncating".format(end_handle, return_end_handle))
                return_end_handle = end_handle
            att_length = 4 + len(primary_uuid)
            packet += ByteHelper.from_u8(att_length)  
            packet += ByteHelper.from_u16(return_start_handle)
            packet += ByteHelper.from_u16(return_end_handle)
            packet += primary_uuid
        else:
            print("GATT Attribute 0x{:04X} Not Implemented".format(gatt_uuid))
            self.do_att_error_rsp(0x10, start_handle, ATTErrorCode.UNLIKELY_ERROR)
            return

        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def do_att_write_rsp(self, handle, value):
        print(att_rsp_text, "WRITE (0x13)")
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code == ATTErrorCode.SUCCESS:
            packet =  ByteHelper.from_u8(0x13)   
            cmd = make_acl(self.handle, len(packet)) + packet
            self.send(cmd)
        else:
            self.do_att_error_rsp(0x12, handle, return_code)

    def check_notification(self):
        if self.client_connected == False:
            return
        notification_exists, handle, data = self.gatt_server.get_notification()
        if notification_exists == False:
            return
        if handle == None or data == None:
            # print("Notification has no handle or data")
            return
        print(att_rsp_text, "Notification (0x1B)")
        packet =  ByteHelper.from_u8(0x1B) 
        packet += ByteHelper.from_u16(handle)
        packet += data
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def check_indication(self):
        if self.client_connected == False:
            return
        indication_exists, handle, data = self.gatt_server.get_indication()
        if indication_exists == False:
            return
        if handle == None or data == None:
            # print("Indication has no handle or data")
            return
        print(att_rsp_text, "Indication (0x1D)")
        packet =  ByteHelper.from_u8(0x1B) 
        packet += ByteHelper.from_u16(handle)
        packet += data
        cmd = make_acl(self.handle, len(packet)) + packet
        self.send(cmd)

    def ack_indication(self):
        print("\nIndication ACK (0x1E)")
        self.gatt_server.clear_ack()

    def do_att_write_no_response(self, handle, value):
        print(att_rsp_text, "WRITE NO RESPONSE (0x52)")
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code != ATTErrorCode.SUCCESS:
            print("No response was requested but write was not successful, Error = 0x{:02X}".format(return_code))

    def on_acl_event(self, data):
        print("ACL data:      ", ByteHelper.as_hex(data))
        att_opcode = ByteHelper.to_u8(data, 0)
        if att_opcode == 0x02:
            print(att_req_text, "Exchange MTU (0x{:02X})".format(att_opcode))
            client_rx_mtu = ByteHelper.to_u16(data, 1)
            self.do_att_exchange_mtu_rsp()
        elif att_opcode == 0x03:
            print("Warning: Exchange MTU RSP (0x03) - should not get from client")
            # server_rx_mtu = ByteHelper.to_u16(data, 1)
        elif att_opcode == 0x04:
            print(att_req_text, "Find Information (0x{:02X})".format(att_opcode))
            start_handle = ByteHelper.to_u16(data, 1)
            end_handle = ByteHelper.to_u16(data, 3)
            self.do_att_find_information_rsp(start_handle, end_handle)
        elif att_opcode == 0x05:
            print("Warning: Find Information RSP (0x05) - should not get from client")      
        elif att_opcode == 0x06:
            print(att_req_text, "Find by Type Value (0x{:02X})".format(att_opcode))
            start_handle = ByteHelper.to_u16(data, 1)
            end_handle = ByteHelper.to_u16(data, 3)
            att_uuid = ByteHelper.to_u16(data, 5)
            att_value = data[7:]
        elif att_opcode == 0x07:
            print("Warning: Find by Type Value RSP (0x07) - should not get from client")         
        elif att_opcode == 0x08:
            start_handle = ByteHelper.to_u16(data, 1)
            end_handle = ByteHelper.to_u16(data, 3)
            uuid = ByteHelper.to_uuid(data[5:])
            print(att_req_text, "Read by Type (0x{:02X}), UUID = {}".format(att_opcode, uuid))
            self.do_att_read_by_type_rsp(start_handle, end_handle, uuid)
        elif att_opcode == 0x09:
            print("Read by Type RSP (0x09) - should not get from client")
        elif att_opcode == 0x0A:
            handle = ByteHelper.to_u16(data, 1)
            print(att_req_text, "READ (0x{:02X})".format(att_opcode))
            self.do_att_read_rsp(handle)
        elif att_opcode == 0x0B:
            print("Warning Read RSP (0x0B) - should not get from client")
        elif att_opcode == 0x10:
            start_handle = ByteHelper.to_u16(data, 1)
            end_handle = ByteHelper.to_u16(data, 3)
            uuid = ByteHelper.to_uuid(data[5:])
            print(att_req_text, "Read by Group Request (0x{:02X}), UUID = {}".format(att_opcode, uuid))
            self.do_att_group_type_rsp(uuid, start_handle, end_handle)
        elif att_opcode == 0x11:
            print("Warning: Read by Group RSP (0x11) - should not get from client") 
        elif att_opcode == 0x12:
            handle = ByteHelper.to_u16(data, 1)
            value = data[3:]
            print(att_req_text, "Write Request handle = 0x{:04X}, value = {}".format(handle, value))
            self.do_att_write_rsp(handle, value)
        elif att_opcode == 0x13:
            print("Warning: Write RSP (0x13) - should not get from client") 
        elif att_opcode == 0x1E:
            self.ack_indication()
        elif att_opcode == 0x52:
            handle = ByteHelper.to_u16(data, 1)
            value = data[3:]
            print(att_req_text, "Write without response handle = 0x{:04X}, value = {}".format(handle, value))
            self.do_att_write_no_response(handle, value)
        else:
            print("Warning: ATT Opcode 0x{:02X} Unknown".format(att_opcode))

