from time import sleep
from hci_socket import HCI
from random import randint
from ble_enum import Address, Advertising, AdvertisingChannelMap
from ble_enum import AdvertisingDataType, AdvertisingFilterPolicy, AdvertisingType
from ble_enum import ATTChannelID, ATTErrorCode, BLEErrorCode
from ble_enum import EventType
from ble_enum import GATTAttributes, HCIPacket, InitiatorFilter
from ble_enum import PeerAddress, ScanningFilter, ScanningFilterDuplicate
from ble_enum import ScanningStatus, ScanningType
from ble_time import AdvertisingInterval, ConnectionInterval, MaxLatency
from ble_time import ScanningTime, SupervisionTimeout, ConnectionEventTime
import byte_utils as bu

class BluetoothLEConnection:

    def __init__(self, dev_id=0, gatt_server=None):
        self.connection_handle = None
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
        self.command_timeout = 0.1
        self.data_timeout = 0.005

        self.cmd_text = "\nCommand:"
        self.att_rsp_text = "\nATT RSP:"
        self.att_req_text = "ATT REQ:"
        self.event_text = "Event:"

    def __del__(self):
        self.user_socket.close()
        return

    def make_acl(self, handle, length):
        header =  bu.from_u8 (0x02)       # hci command prefix for ACL
        if handle == None:
            print("Error: No connection Handle")
            return
        header += bu.from_u16(handle)     # hci handle
        header += bu.from_u16(length + 4) # hci packet length
        header += bu.from_u16(length)     # l2cap length
        header += bu.from_u16(ATTChannelID.BLE)
        return header

    def make_cmd(self, cmd, length):
        header =  bu.from_u8 (0x01)       # hci command prefix
        header += bu.from_u16(cmd)        # hci command
        header += bu.from_u8 (length)     # hci packet length
        return header

    def send(self, data):
        print("<<", bu.as_hex(data))
        self.user_socket.send_raw(data)

    def receive(self):
        data = self.user_socket.receive_raw()
        print("\n>>", bu.as_hex(data))
        self.on_data(data)
        return data

    def readable(self):
        return self.user_socket.readable()

    def wait_listen(self, timeout = None):
        if timeout == None:
            timeout = self.data_timeout
        quanta = 0.001
        timer = timeout
        while timer > 0:
            timer -= quanta
            while self.readable():
                a = self.receive()
            self.check_notification()
            self.check_indication()
            sleep(quanta)

    def send_command(self, command, packet):
        cmd = self.make_cmd(command, len(packet)) + packet
        self.send(cmd)

    def check_le_compatable(self, data):
        if (bu.to_u8(data, 32) & 0xA2 == 0xA2) and (bu.to_u8(data, 33) & 0x3E == 0x3E):
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
        self.hc_le_data_packet_length = bu.to_u16(data, 7)
        print("le data length = {}".format(self.hc_le_data_packet_length))
        self.hc_le_data_buffer = bu.to_u8(data, 9)
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
      
        status = bu.to_u8(data, 4)
        handle = bu.to_u16(data, 5)
        address = bu.to_addr(data, 9)
        
        self.connection_handle = handle         # save this for other commands to use
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
        # num_reports = bu.to_u8       (data, 4)
        # reports =     bu.to_data_rest(data, 5)
        # data = data[0:4] + bu.from_u8(2) + reports + reports

        num_reports = bu.to_u8       (data, 4)
        reports =     bu.to_data_rest(data, 5)                  # the actual 'reports'
        
        report_offset = 0                                    # start of this entry in 'reports'
        for rep in range(0, num_reports):
            address =     bu.to_addr (reports, report_offset+2)
            data_len =    bu.to_u8   (reports, report_offset+8)
            report_data = bu.to_data (reports, report_offset+9, data_len)
            rssi =        bu.to_u8   (reports, report_offset+9+data_len)
            
            print("Address: {}      RSSI: {}".format(address, rssi))
            i = 0
            while i < data_len:
                entry_len = bu.to_u8(report_data, i) 
                if entry_len > 0:
                    typ = bu.to_u8  (report_data, i+1)
                    dat = bu.to_data(report_data, i+2, entry_len-1)
                    print("Length: {:3} Type: {:02x}  Data: {}      {}".format(entry_len, typ, bu.as_hex(dat), bu.as_printable(dat)))
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

        status =   bu.to_u8(data, 4)
        handle =   bu.to_u16(data, 5)
        interval = bu.to_u16(data, 7)
        latency = bu.to_u16(data, 9)
        timeout =  bu.to_u16(data, 11)
        
        print("LE Connection Update Complete")
        print("Handle: {:04x} Status: {02x}".format(handle, status))
        
        #self.connection_handle = handle         # save this for other commands to use

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
        
        handle = bu.to_u16(data, 5)
        features = bu.to_data_rest(data, 7)
        
        print("Handle: {} Features {}".format(handle, bu.as_hex(features)))

    def on_le_data_length_change(self, data):
        handle = bu.to_u16(data, 4)
        max_tx_octets = bu.to_u16(data, 6) # 0x001B to 0x00FB
        max_tx_time = bu.to_u16(data, 8) # 0x0148 to 0x4290
        max_rx_octets = bu.to_u16(data, 10) # 0x001B to 0x00FB
        max_rx_time = bu.to_u16(data, 12) # 0x0148 to 0x4290
        print(self.event_text, "Data length changed for 0x{:04X}".format(handle))

    def on_le_read_local_public_key(self, data):
        status = bu.to_u8(data, 4)
        key_x_coordinate = bu.to_data(data, 5, 37)  # 32 octets
        key_y_coordinate = bu.to_data(data, 37, 69) # 32 octets
        print(self.event_text, "Read Local Public Key Complete")

    def on_le_update_complete(self, data):
        status = bu.to_u8(data, 4)
        handle = bu.to_u16(data, 5)
        connection_interval = bu.to_u16(data, 7)
        supervision_timeout = bu.to_u16(data, 9)
        print(self.event_text, "Connection Update Complete")

    def on_hci_meta_event(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.65 LE Meta event (p2235)
        # Event_code = 0x3e
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     subevent_code                                  1 octet
        #     data                                           n octets

        subevent_code = bu.to_u8(data, 3)
        # print(self.event_text, "LE Meta event: ", hex(subevent_code))
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

        
        status = bu.to_u8  (data, 3)
        handle = bu.to_u16 (data, 4)
        reason = bu.to_u8  (data, 6)
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
            print(self.event_text, "{}: {}".format(message, status_text))

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

        # print(self.event_text, "HCI Command Complete")
        cmd =    bu.to_u16 (data, 4)
        status = bu.to_u8  (data, 6)
        status_text = "Success" if status == ATTErrorCode.SUCCESS else "Failure"
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

        # print(self.event_text, "HCI Command Status")
        status = bu.to_u8  (data, 3)
        opcode = bu.to_u16 (data, 5)
        if opcode == 0x2025:
            print(self.event_text, "Local Public Key Command Complete")
        else:
            print(self.event_text, "Unknown Opcode: {:02x} status: {:02x}".format(opcode, status))

    def on_hci_event_number_of_completed_packets(self, data):
        # Specification v5.4  Vol 4 Part E 7.7.19 HCI Number Of Completed Packets (p2184)
        #     [packet_type                                   1 octet]
        #     [event_code                                    1 octet]
        #     [parameter_length                              1 octet]
        #     num_handles                                    1 octet
        #     connection handle[i]                           2n octets
        #     num completed packets[i]                       2n octets

        print(self.event_text, "HCI Number Of Completed Packets = {}".format(bu.to_u16(data, len(data) - 2)))
        self.gatt_server.clear_ack()  # Appears that some use this as an ack to indication
        

    def on_hci_event_vendor_specific (self, data):
        print(self.event_text, "Vendor Specific")

    def on_hci_event(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.4 HCI Event Packet (p1804)
        #     [packet_type                                   1 octet]
        #     event_code                                     1 octet
        #     parameter_length                               1 octet
        #     parameters                                     n octets

        event = bu.to_u8(data, 1)         
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
            print(self.event_text, "Unhandled", hex(event))

    def on_acl_packet(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet (p1801)
        #     [packet_type                                  1 octet]
        #     handle (BC[2] PB[2] handle[12])               2 octets
        #     packet length                                 2 octets
        #     data_length                                   2 octets
        #     channel                                       2 octets
        #     data                                          n octets

        # print("ACL Packet")

        handle = bu.to_bits_u16(data, 1, 0, 12)
        pb =     bu.to_bits_u16(data, 1, 12, 2)
        bc =     bu.to_bits_u16(data, 1, 14, 2)
        length = bu.to_u16(data, 3)  #di["packet length"]
 
        full_packet = False
        # print('ACL header: handle: {}  bc: {}  pb: {}'.format(handle, bc, pb))

        if pb & 0x01 == 0:
            size =     bu.to_u16(data, 5)
            channel =  bu.to_u16(data, 7)
            acl_data = bu.to_data_rest(data, 9)
            full_packet = length - size == 4

            print("Channel: {} Length: {} Data size: {} Full packet? {}".format(channel, length, size, full_packet))
            # print("ACL packet:    ", bu.as_hex(acl_data))

            self.acl_total_length = size
            self.acl_packet =       acl_data

        if pb & 0x01 == 1:
            print("ACL Packet Continuation")
            acl_data = bu.to_data_rest(data, 5)
            self.acl_packet += acl_data
            print("ACL data:  ", bu.as_hex(acl_data))
            if len(self.acl_packet) == self.acl_total_length:    # This was the last continuation packet
                full_packet = True
                print("ACL Packet Final")
                print("Full ACL data: ", bu.as_hex(self.acl_packet))
                
        if full_packet:
            self.on_acl_event(self.acl_packet)                 
            
    def on_data(self, data):
        # Specification v5.4  Vol 4 Part E 5.4.4 HCI Event Packet (p1804)
        # Specification v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet (p1801)
        #
        #     packet_type                                    1 octet

        packet_type = bu.to_u8(data, 0)
        # print("Packet type:", packet_type)

        self.command_complete = None               # set to None and changed by Command Complete event
        self.command_status = None

        if   packet_type == 0x04:                  # event packet
            self.on_hci_event(data)
        elif packet_type == 0x02:                  # ACL data packet
            self.on_acl_packet(data)
        else:
            print("Unhandled packet type", packet_type)


    def create_advertising_packet(self, fields):
        packet = bytes()
        total_length = 0
        for field_type, field_data in fields:
            if not isinstance(field_type, AdvertisingDataType):
                raise ValueError(f"Field type must be an instance of AdvertisingDataType.")
            if not isinstance(field_data, bytes):
                if field_type == AdvertisingDataType.SHORTENED_LOCAL_NAME and isinstance(field_data, str):
                    field_data = bu.from_string(field_data)
                elif field_type == AdvertisingDataType.COMPLETE_LOCAL_NAME and isinstance(field_data, str):
                    field_data = bu.from_string(field_data)
                else:
                    raise ValueError(f"Data for type {field_type.name} must be provided as bytes.")
            length = len(field_data) + 1
            if length > 31:
                raise ValueError(f"Field data for type {field_type.name} exceeds the maximum allowed length.")
            packet += bu.from_u8(length)
            packet += bu.from_u8(field_type.value)
            packet += field_data
        if len(packet) > 31:
            raise ValueError("Total advertising packet exceeds the 31-byte maximum.")
        packet = bu.from_u8(len(packet)) + packet
        pad = bytes(b'\x00' * (32-len(packet)))
        packet += pad
        return bytes(packet)

    def event_mask_conversion(self, event_types):
        event_mask = [0] * 8
        for event_type in event_types:
            if isinstance(event_type, EventType):
                bit_index = event_type.value
                byte_index = bit_index // 8
                bit_position = bit_index % 8
                event_mask[byte_index] |= (1 << bit_position)
            else:
                raise ValueError("Invalid EventType for event mask")
        print("".join(f"{byte:02X}" for byte in reversed(event_mask)))
        return bytes(event_mask)

    # HCI commands

    def reset(self):
        print(self.cmd_text, "BLE Reset")
        
        packet = bu.from_u8(None)
        self.send_command(0x0C03, packet)

    def set_event_masks(self):
        print(self.cmd_text, "General Event Mask")
        # 8 byte event mask
        packet = bytes([0xFF, 0xFF, 0xFB, 0xFF, 0x07, 0xF8, 0xBF, 0x3D])
        self.send_command(0x0C01, packet)

    def set_inquiry_timeouts(self):
        print(self.cmd_text, "Set Page/Inquiry Scan and Tmeouts (10 secs)")
        packet = bytes([0x03])
        self.send_command(0x0C1A, packet)

    def set_page_scan_activity(self):
        print(self.cmd_text, "Set Page Scan Interval and Window (10 secs)")
        packet = bytes([0xA0, 0x3F])
        self.send_command(0x0C16, packet)

    def set_inquiry_scan_activity(self):
        print(self.cmd_text, "Set Inquiry Scan Interval and Window (10 secs)")
        packet = bytes([0x00, 0x40])
        self.send_command(0x0C18, packet)

    def read_local_commands(self):
        print(self.cmd_text, "Read Local Supported Commands")
        packet = bu.from_u8(None)
        self.send_command(0x1002, packet)

    def read_local_board_address(self):
        print(self.cmd_text, "Read Local Board Address")
        packet = bu.from_u8(None)
        self.send_command(0x1009, packet)

    def write_local_name(self, name):
        self.local_name = name
        print(self.cmd_text, "Write Local Name {}".format(name))
        name_bytes = name.encode('utf-8')
        if len(name_bytes) > 248:
            raise ValueError("Name is too long, must be 248 bytes or less.")
        packet = name_bytes.ljust(248, b'\x00')
        self.send_command(0x0C13, packet)

    def set_le_event_masks(self):
        # Specification v5.4  Vol 4 Part E 7.8.3 LE Set Event Mask Command
        # Opcode 0x2001
        print(self.cmd_text, "LE Event Mask")
        # 8 byte event mask
        packet_old = bytes([0xFF, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        packet = self.event_mask_conversion([
            EventType.CONNECTION_COMPLETE,
            EventType.ADVERTISING_REPORT,
            EventType.CONNECTION_UPDATE_COMPLETE,
            EventType.READ_REMOTE_FEATURES_COMPLETE,
            EventType.LONG_TERM_KEY_REQUEST,
            EventType.REMOTE_CONNECTION_PARAMETER_REQUEST,
            EventType.DATA_LENGTH_CHANGE,
            EventType.READ_LOCAL_P256_PUBLIC_KEY_COMPLETE,
            EventType.GENERATE_DHKEY_COMPLETE,
            EventType.DIRECTED_ADVERTISING_REPORT
        ])
        if packet != packet_old:
            raise ValueError(f"Not the same event mask {packet} != {packet_old}")
        self.send_command(0x2001, packet)

    def read_le_buffer_size(self):
        # Specification v5.4  Vol 4 Part E 7.8.3 LE Read Buffer Size Command
        # Opcode 0x2002
        print(self.cmd_text, "Read LE Buffer Size")
        packet = bu.from_u8(None)
        self.send_command(0x2002, packet)

    def set_random_address(self):
        # Specification v5.4  Vol 4 Part E 7.8.4 LE Set Random Address Command
        # Opcode 0x2005
        random_address = bytes([randint(0x00, 0xFF) for _ in range(6)])
        random_address_str = ':'.join(f'{byte:02X}' for byte in reversed(random_address))
        print(self.cmd_text, "Generated Random Bluetooth Address: {}".format(random_address_str))
        self.send_command(0x2005, random_address)

    def do_set_advertising_parameters(self, min_interval=AdvertisingInterval.DEFAULT_TIME,
                                      max_interval=AdvertisingInterval.DEFAULT_TIME, 
                                      adv_type=AdvertisingType.ADV_IND,
                                      own_addr_type=Address.PUBLIC,
                                      peer_addr_type=PeerAddress.PUBLIC_DEVICE,
                                      peer_addr='00:00:00:00:00:00',
                                      adv_channel_map=AdvertisingChannelMap.ALL_CHANNELS,
                                      adv_filter_policy=AdvertisingFilterPolicy.SCAN_CONNECT_ALL):
        # Specification v5.4  Vol 4 Part E 7.8.5 LE Set Advertising Parameters
        # Opcode 0x2006
        print(self.cmd_text, "LE Set Advertising Parameters")
        
        packet =  bu.from_u16  (AdvertisingInterval.conversion(min_interval))
        packet += bu.from_u16  (AdvertisingInterval.conversion(max_interval))
        packet += bu.from_u8   (adv_type)
        packet += bu.from_u8   (own_addr_type)
        packet += bu.from_u8   (peer_addr_type)
        packet += bu.from_addr (peer_addr)
        packet += bu.from_u8   (adv_channel_map)
        packet += bu.from_u8   (adv_filter_policy)
        self.send_command(0x2006, packet)

    def do_set_advertising_data(self, fields):
        # Specification v5.4  Vol 4 Part E 7.8.7 LE Set Advertising Data
        # Opcode 0x2008
        packet = self.create_advertising_packet(fields)
        print(self.cmd_text, "LE Set Advertising Data")
        self.send_command(0x2008, packet)

    def do_set_scan_response_data(self, fields):
        # Specification v5.4  Vol 4 Part E 7.8.8 LE Set Scan Response Data
        # Opcode 0x2009
        packet = self.create_advertising_packet(fields)
        print(self.cmd_text, "LE Set Scan Response Data")
        self.send_command(0x2009, packet)

    def do_set_advertise_enable(self, enabled_status:Advertising):
        # Specification v5.4  Vol 4 Part E 7.8.9 LE Set Advertising Enable
        # Opcode 0x200a
        if enabled_status == Advertising.ENABLED:
            print(self.cmd_text, "LE Set Advertising: Enabled")
        elif enabled_status == Advertising.DISABLED:
            print(self.cmd_text, "LE Set Advertising: Disabled")
        else:
            raise ValueError("Invalid advertising parameter {}".format(enabled_status))
        packet = bu.from_u8(enabled_status)
        self.send_command(0x200a, packet)

    def do_set_scan_parameters(self, scan_type=ScanningType.ACTIVE,
                               scan_interval=ScanningTime.DEFAULT_TIME,
                               scan_window=ScanningTime.DEFAULT_TIME,
                               own_addr_type=Address.PUBLIC,
                               scan_filter_policy=ScanningFilter.BASIC_UNFILTERED):
        # Specification v5.4  Vol 4 Part E 7.8.10 LE Set Scan Parameters
        # Opcode 0x200B
        print(self.cmd_text, "LE Set Scan Parameters")
        packet =  bu.from_u8  (scan_type)
        packet += bu.from_u16 (ScanningTime.conversion(scan_interval))
        packet += bu.from_u16 (ScanningTime.conversion(scan_window))
        packet += bu.from_u8  (own_addr_type)
        packet += bu.from_u8  (scan_filter_policy)
        self.send_command(0x200b, packet)

    def do_set_scan(self, enabled_status=ScanningStatus.DISABLED,
                    duplicates=ScanningFilterDuplicate.DISABLED):
        # Specification v5.4  Vol 4 Part E 7.8.11 LE Set Scan Enable
        # Opcode 0x200c
        print(self.cmd_text, "LE Set Scan Enable" if enabled else "LE Set Scan Disable")
        
        packet =  bu.from_u8(enabled_status)
        packet += bu.from_u8(duplicates)        
        self.send_command(0x200c, packet)

    def do_create_connection(self, scan_interval=ScanningTime.DEFAULT_TIME,
                             scan_window=ScanningTime.DEFAULT_TIME,
                             initiator_filter=InitiatorFilter.FILTER_ACCEPT_NOT_USED,
                             peer_addr_type = PeerAddress.PUBLIC_DEVICE,
                             peer_addr='00:00:00:00:00:00',
                             own_addr_type=Address.PUBLIC,
                             min_interval=ConnectionInterval.DEFAULT_TIME_MIN,
                             max_interval=ConnectionInterval.DEFAULT_TIME_MAX,
                             latency=MaxLatency.DEFAULT_TIME,
                             supervision_timeout=SupervisionTimeout.DEFAULT_TIME,
                             min_ce_length=ConnectionEventTime.DEFAULT_TIME,
                             max_ce_length = ConnectionEventTime.DEFAULT_TIME):
        # Specification v5.4  Vol 4 Part E 7.8.12 LE Create Connection
        # Opcode 0x200d
        print(self.cmd_text, "LE Create Connection")
        packet =  bu.from_u16 (ScanningTime.conversion(scan_interval))
        packet += bu.from_u16 (ScanningTime.conversion(scan_window))
        packet += bu.from_u8  (initiator_filter)
        packet += bu.from_u8  (peer_addr_type)
        packet += bu.from_addr(peer_addr)
        packet += bu.from_u8  (own_addr_type)
        packet += bu.from_u16 (ConnectionInterval.conversion(min_interval))
        packet += bu.from_u16 (ConnectionInterval.conversion(max_interval))
        packet += bu.from_u16 (MaxLatency.conversion(latency))
        packet += bu.from_u16 (SupervisionTimeout.conversion(supervision_timeout))
        packet += bu.from_u16 (ConnectionEventTime.conversion(min_ce_length))
        packet += bu.from_u16 (ConnectionEventTime.conversion(max_ce_length))
        self.send_command(0x200d, packet)
        

    def do_add_device_to_accept_list(self, addr=Address.PUBLIC, addr_type='00:00:00:00:00:00'):
        # Specification v5.4  Vol 4 Part E 7.8.16 LE Add Device To Filter Accept List
        # Opcode 0x2011
        print(self.cmd_text, "LE Add Device To Filter Accept List")
        
        packet =  bu.from_u8(addr_type)
        packet += bu.from_addr(addr)
        self.send_command(0x2011, packet)

    def do_read_remote_used_features(self):
        # Specification v5.4  Vol 4 Part E 7.8.21 LE Read Remote Features
        # Opcode 0x2016 
        print(self.cmd_text, "LE Read Remote Features")
        if self.connection_handle == None:
            print("Error: No connection handle")
            return
        packet = bu.from_u16(self.connection_handle)
        self.send_command(0x2016, packet)

    def read_local_public_key(self):
        # Specification v5.4  Vol 4 Part E 7.8.36 LE Read Local P-256 Public Key Command
        # Opcode 0x2025
        print(self.cmd_text, "Read Local Public Key")
        packet = bu.from_u8(None)
        self.send_command(0x2025, packet)

    #
    # ACL commands
    #
    
    def do_att_error_rsp(self, request_opcode, handle, error_code):
        print(self.att_rsp_text, "Error")

        packet =  bu.from_u8(0x01) 
        packet += bu.from_u8(request_opcode)     
        packet += bu.from_u16(handle) 
        packet += bu.from_u8(error_code)
        
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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

        print(self.att_req_text, "EXCHANGE MTU (0x02)")

        packet =  bu.from_u8  (0x02)           # ATT opcode ATT_EXCHANGE_MTU_REQ
        packet += bu.from_u16 (mtu_size)       # MTU size requested
        
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def do_att_exchange_mtu_rsp(self, mtu_size = 244):
        print(self.att_rsp_text, "EXCHANGE MTU (0x03)")

        packet =  bu.from_u8  (0x03)      
        packet += bu.from_u16 (mtu_size) 
        
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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

        print(self.att_req_text, "FIND INFORMATION (0x04)")
        
        packet =  bu.from_u8(0x04)          # ATT opcode ATT_FIND_INFORMATION_REQ
        packet += bu.from_u16(start_handle)
        packet += bu.from_u16(end_handle)

        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def do_att_find_information_rsp(self, start_handle, end_handle):
        print(self.att_rsp_text, "FIND INFORMATION (0x05)")
        return_code, uuid_format, handle_uuid = self.gatt_server.find_information(start_handle, end_handle)
        if return_code != ATTErrorCode.SUCCESS:
            self.do_att_error_rsp(0x04, start_handle, return_code) 
            return
        packet =  bu.from_u8(0x05)
        packet += bu.from_u8(uuid_format)
        for each_handle_uuid in handle_uuid:
            handle, uuid = each_handle_uuid
            packet += bu.from_u16(start_handle)
            packet += uuid

        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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

        print(self.att_req_text, "READ BY TYPE (0x08)")
        
        packet =  bu.from_u8  (0x08)               # ATT opcode ATT_READ_BY_TYPE_REQ
        packet += bu.from_u16 (start_handle)
        packet += bu.from_u16 (end_handle)
        packet += bu.from_u16 (attribute_type)        
               
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def do_att_read_by_type_rsp(self, start_handle, end_handle, uuid):
        print(self.att_rsp_text, "READ BY TYPE (0x09)")
        packet =  bu.from_u8  (0x09)
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
                packet += bu.from_u8(7) 
                # for idx, char_item in enumerate(char_decl):
                handle, prop_byte, value_handle, char_uuid = char_decl
                packet += bu.from_u16(handle)
                packet += bu.from_u8(prop_byte)
                packet += bu.from_u16(value_handle)
                packet += char_uuid
        
        else:
            return_code, handle, data = self.gatt_server.read_uuid_value(start_handle, end_handle, uuid)
            if return_code != ATTErrorCode.SUCCESS:
                self.do_att_error_rsp(0x08, start_handle, return_code) 
                return  
            packet += bu.from_u8(2 + len(data))
            packet += bu.from_u16 (handle)
            packet += data        
               
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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

        print(self.att_req_text, "GROUP TYPE (0x0A)")
        
        packet =  bu.from_u8  (0x0A)               # ATT opcode ATT_READ_REQ
        packet += bu.from_u16 (handle)
               
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def do_att_read_rsp(self, handle):
        print(self.att_rsp_text, "READ (0x0B)")
        return_code, byte_value = self.gatt_server.read_char_value(handle)
        if return_code != ATTErrorCode.SUCCESS: 
            self.do_att_error_rsp(0x0A, handle, return_code)
            return
        else: 
            packet = bu.from_u8(0x0B)
            packet += byte_value
            cmd = self.make_acl(self.connection_handle, len(packet)) + packet
            self.send(cmd)

    def do_att_group_type_rsp(self, gatt_uuid, start_handle, end_handle):
        print(self.att_rsp_text, "GROUP TYPE (0x11)")
        packet =  bu.from_u8  (0x11)    
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
            packet += bu.from_u8(att_length)  
            packet += bu.from_u16(return_start_handle)
            packet += bu.from_u16(return_end_handle)
            packet += primary_uuid
        else:
            print("GATT Attribute 0x{:04X} Not Implemented".format(gatt_uuid))
            self.do_att_error_rsp(0x10, start_handle, ATTErrorCode.UNLIKELY_ERROR)
            return

        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def do_att_write_rsp(self, handle, value):
        print(self.att_rsp_text, "WRITE (0x13)")
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code == ATTErrorCode.SUCCESS:
            packet =  bu.from_u8(0x13)   
            cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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
        print(self.att_rsp_text, "Notification (0x1B)")
        packet =  bu.from_u8(0x1B) 
        packet += bu.from_u16(handle)
        packet += data
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
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
        print(self.att_rsp_text, "Indication (0x1D)")
        packet =  bu.from_u8(0x1B) 
        packet += bu.from_u16(handle)
        packet += data
        cmd = self.make_acl(self.connection_handle, len(packet)) + packet
        self.send(cmd)

    def ack_indication(self):
        print("\nIndication ACK (0x1E)")
        self.gatt_server.clear_ack()

    def do_att_write_no_response(self, handle, value):
        print(self.att_rsp_text, "WRITE NO RESPONSE (0x52)")
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code != ATTErrorCode.SUCCESS:
            print("No response was requested but write was not successful, Error = 0x{:02X}".format(return_code))

    def on_acl_event(self, data):
        print("ACL data:      ", bu.as_hex(data))
        att_opcode = bu.to_u8(data, 0)
        if att_opcode == 0x02:
            print(self.att_req_text, "Exchange MTU (0x{:02X})".format(att_opcode))
            client_rx_mtu = bu.to_u16(data, 1)
            self.do_att_exchange_mtu_rsp()
        elif att_opcode == 0x03:
            print("Warning: Exchange MTU RSP (0x03) - should not get from client")
            # server_rx_mtu = bu.to_u16(data, 1)
        elif att_opcode == 0x04:
            print(self.att_req_text, "Find Information (0x{:02X})".format(att_opcode))
            start_handle = bu.to_u16(data, 1)
            end_handle = bu.to_u16(data, 3)
            self.do_att_find_information_rsp(start_handle, end_handle)
        elif att_opcode == 0x05:
            print("Warning: Find Information RSP (0x05) - should not get from client")      
        elif att_opcode == 0x06:
            print(self.att_req_text, "Find by Type Value (0x{:02X})".format(att_opcode))
            start_handle = bu.to_u16(data, 1)
            end_handle = bu.to_u16(data, 3)
            att_uuid = bu.to_u16(data, 5)
            att_value = data[7:]
        elif att_opcode == 0x07:
            print("Warning: Find by Type Value RSP (0x07) - should not get from client")         
        elif att_opcode == 0x08:
            start_handle = bu.to_u16(data, 1)
            end_handle = bu.to_u16(data, 3)
            uuid = bu.to_uuid(data[5:])
            print(self.att_req_text, "Read by Type (0x{:02X}), UUID = {}".format(att_opcode, uuid))
            self.do_att_read_by_type_rsp(start_handle, end_handle, uuid)
        elif att_opcode == 0x09:
            print("Read by Type RSP (0x09) - should not get from client")
        elif att_opcode == 0x0A:
            handle = bu.to_u16(data, 1)
            print(self.att_req_text, "READ (0x{:02X})".format(att_opcode))
            self.do_att_read_rsp(handle)
        elif att_opcode == 0x0B:
            print("Warning Read RSP (0x0B) - should not get from client")
        elif att_opcode == 0x10:
            start_handle = bu.to_u16(data, 1)
            end_handle = bu.to_u16(data, 3)
            uuid = bu.to_uuid(data[5:])
            print(self.att_req_text, "Read by Group Request (0x{:02X}), UUID = {}".format(att_opcode, uuid))
            self.do_att_group_type_rsp(uuid, start_handle, end_handle)
        elif att_opcode == 0x11:
            print("Warning: Read by Group RSP (0x11) - should not get from client") 
        elif att_opcode == 0x12:
            handle = bu.to_u16(data, 1)
            value = data[3:]
            print(self.att_req_text, "Write Request handle = 0x{:04X}, value = {}".format(handle, value))
            self.do_att_write_rsp(handle, value)
        elif att_opcode == 0x13:
            print("Warning: Write RSP (0x13) - should not get from client") 
        elif att_opcode == 0x1E:
            self.ack_indication()
        elif att_opcode == 0x52:
            handle = bu.to_u16(data, 1)
            value = data[3:]
            print(self.att_req_text, "Write without response handle = 0x{:04X}, value = {}".format(handle, value))
            self.do_att_write_no_response(handle, value)
        else:
            print("Warning: ATT Opcode 0x{:02X} Unknown".format(att_opcode))

if __name__ == "__main__":
    bc = BluetoothLEConnection()
    bc.do_set_scan_parameters()
    bc.do_set_advertising_parameters()
    # bc.do_set_advertise_enable(Advertising.ENABLED)
    # bc.do_set_advertise_enable(Advertising.DISABLED)
    # bc.do_set_advertise_enable('ABC')
    bc.do_create_connection()
    bc.event_mask_conversion([
        EventType.CONNECTION_COMPLETE,
        EventType.ADVERTISING_REPORT,
        EventType.CONNECTION_UPDATE_COMPLETE,
        EventType.READ_REMOTE_FEATURES_COMPLETE,
        EventType.LONG_TERM_KEY_REQUEST,
        EventType.REMOTE_CONNECTION_PARAMETER_REQUEST,
        EventType.DATA_LENGTH_CHANGE,
        EventType.READ_LOCAL_P256_PUBLIC_KEY_COMPLETE,
        EventType.GENERATE_DHKEY_COMPLETE,
        EventType.DIRECTED_ADVERTISING_REPORT
    ])

    bc.set_le_event_masks()