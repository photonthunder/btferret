from time import sleep
from hci_socket import HCI
from random import randint
from ble_enum import Address, Advertising, AdvertisingChannelMap
from ble_enum import AdvertisingDataType, AdvertisingFilterPolicy
from ble_enum import AdvertisingEventType, AdvertisingType
from ble_enum import BLEErrorCode, BroadcastFlags
from ble_enum import CentralClockAccuracy
from ble_enum import EventMask, EventType
from ble_enum import HCIPacket
from ble_enum import InitiatorFilter
from ble_enum import PacketBoundaryFlags, PeerAddressType, Role
from ble_enum import ScanningFilter, ScanningFilterDuplicate
from ble_enum import ScanEnable, ScanningStatus, ScanningType
from ble_time import AdvertisingInterval
from ble_time import ConnectionAcceptTimeout, ConnectionEventTime, ConnectionInterval
from ble_time import MaxLatency
from ble_time import PageTimeout
from ble_time import ScanningTime, SupervisionTimeout
from gatt_enum import ATTChannelID, ATTCode, ATTR
import byte_utils as bu

hci_event_handlers = {}
meta_event_handlers = {}
acl_event_handler = {}

def register_event(event_code, registry):
    def decorator(func):
        func._event_code = event_code
        registry[event_code] = func
        return func
    return decorator


class BluetoothLEConnection:

    def __init__(self, dev_id=0, gatt_server=None):
        self.connection_handle = None
        self.user_socket = HCI(dev_id)
        self.gatt_server = gatt_server

        self.acl_packet = None
        self.acl_length = 0
        self.acl_total_length = 0

        self.client_connected = False
        self.command_timeout = 0.1
        self.data_timeout = 0.005
        self.total_connections = []
        
        self.hci_cc_event_handler = {}

        self.cmd_text = "\nCommand:"
        self.att_rsp_text = "\nATT RSP:"
        self.att_req_text = "ATT REQ:"
        self.event_text = "Event:"

    def __del__(self):
        self.user_socket.close()
        return

    def send(self, data):
        print("<<", bu.as_hex(data))
        self.user_socket.send_raw(data)

    def send_acl(self, sub_packet, handle = None):
        packet =  bu.from_u8 (HCIPacket.ACL_DATA)       # hci command prefix for ACL
        if handle == None:
            if self.connection_handle == None:
                print("No Connection, can't send ACL")
                return
            handle = self.connection_handle
        flag_handle = (handle & 0x0EFF) | \
                      (PacketBoundaryFlags.COMPLETE_MESSAGE << 12) | \
                      (BroadcastFlags.POINT_POINT << 14)
        packet += bu.from_u16(handle)     # hci handle
        length = len(sub_packet)
        packet += bu.from_u16(length + 4) # hci packet length
        packet += bu.from_u16(length)     # l2cap length
        packet += bu.from_u16(ATTChannelID.BLE)
        packet += sub_packet
        self.send(packet)

    def make_cmd(self, cmd, length):
        header =  bu.from_u8 (HCIPacket.COMMAND)       # hci command prefix
        header += bu.from_u16(cmd)        # hci command
        header += bu.from_u8 (length)     # hci packet length
        return header

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

    def send_command(self, opcode, cmd_name, packet, function = None):
        cmd = self.make_cmd(opcode, len(packet)) + packet
        self.send(cmd)
        if opcode not in self.hci_cc_event_handler:
            self.hci_cc_event_handler[opcode] = (cmd_name, function)

    def ble_error_check(self, return_code):       
        if return_code == BLEErrorCode.SUCCESS:
            return True
        else:
            print(f"BLE Error = {BLEErrorCode(return_code).name}")
            return False

    def handle_le_command(self, cmd, data):
        if cmd in self.hci_cc_event_handler:
            message, function_name = self.hci_cc_event_handler[cmd]
            if data[0] == BLEErrorCode.SUCCESS:
                print(self.event_text, f"{message} Complete")
                if function_name and hasattr(self, function_name):
                    print(f"Data: {bu.as_hex(data)}")
                    getattr(self, function_name)(data)
            else:
                print(self.event_text, f"{message} Error, {BLEErrorCode(data[0]).name}")
                return
        else:
            print(f'Unknown CC Event: {cmd} ({hex(cmd)}), {status_text}')

    def handle_le_status(self, cmd):
        if cmd in self.hci_cc_event_handler:
            message, function_name = self.hci_cc_event_handler[cmd]
            print(self.event_text, f"{message} Received but not complete")
        else:
            print(f'Unknown Status Event: {cmd} ({hex(cmd)}), {status_text}')

    @register_event(0x01, meta_event_handlers)
    def on_le_connection_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.65.1 LE Connection Complete
        # Subevent Code =  0x01
        status = bu.to_u8(data, 4)
        if self.ble_error_check(status) == False:
            print("Connection did not complete")
            return
        handle = bu.to_u16(data, 5)
        role = bu.to_u8(data, 7)
        peer_addr_type = bu.to_u8(data, 8)
        address = bu.to_addr(data, 9)
        connection_interval = bu.to_u16(data, 15)
        peripheral_latency = bu.to_u16(data, 17)
        supervision_timeout = bu.to_u16(data, 19)
        central_clock_accuracy = bu.to_u8(data, 21)
        self.connection_handle = handle 
        self.total_connections.append((handle, 0))
        self.client_connected = True
        print(f"Connection Complete 0x{handle:04X}, Role: {Role(role).name}")
        print(f"Peer: Type {PeerAddressType(peer_addr_type)}. Address: {address}")
        print(f"Connection Interval {ConnectionInterval.to_time(connection_interval)} seconds")
        print(f"Peripheral Latency 0x{peripheral_latency:04X} connection events")
        print(f"Supervision Timeout {SupervisionTimeout.to_time(supervision_timeout)} seconds")
        print(f"Central Clock Accuracy = {CentralClockAccuracy(central_clock_accuracy).name} ppm")

    @register_event(0x02, meta_event_handlers)
    def on_le_advertising_report(self, data):
        # v5.4 Vol 4 Part E 7.7.65.2 LE Advertising Report
        # Subevent Code = 0x02
        num_reports = bu.to_u8(data, 4)
        if num_reports > 0x19:
            print(f"Error, too many reports 0x{num_reports:X} > 0x19")
            return
        
        reports = bu.to_data_rest(data, 5)  # Get the payload after the Number of Reports byte
        report_offset = 0
        for rep in range(num_reports):
            event_type = bu.to_u8(reports, report_offset)
            address_type = bu.to_u8(reports, report_offset + 1)
            address = bu.to_addr(reports, report_offset + 2)
            data_len = bu.to_u8(reports, report_offset + 8)
            report_data = bu.to_data(reports, report_offset + 9, data_len)
            rssi = bu.to_u8(reports, report_offset + 8 + data_len)
            
            print(f"Advertising Report {rep}:")
            print(f"Event Type: {AdvertisingEventType(event_type).name}")
            print(f"Address Type: {Address(address_type).name}")
            print(f"Address: {address}")
            print(f"Report Data: {report_data}")
            print(f"RSSI: {rssi} dBm")
              
    @register_event(0x03, meta_event_handlers)
    def on_le_update_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.65.3 LE Connection Update Complete
        # Subevent Code = 0x03
        status =   bu.to_u8(data, 4)
        if self.ble_error_check(status) == False:
            print("Update did not complete")
            return
        handle =   bu.to_u16(data, 5)
        connection_interval = bu.to_u16(data, 7)
        peripheral_latency = bu.to_u16(data, 9)
        supervision_timeout =  bu.to_u16(data, 11)
        print("Connection Update Complete")
        print("Handle: {:04x} Status: {02x}".format(handle, status))
        print("Connection Interval {ConnectionInterval.to_time(connection_interval)} seconds}")
        print("Peripheral Latency 0x{peripheral_latency:04X} connection events}")
        print("Supervision Timeout {SupervisionTimeout.to_time(supervision_timeout)} seconds}")

    @register_event(0x04, meta_event_handlers)
    def on_le_read_remote_features_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.65.4 LE Read Remote Features Complete
        # Subevent Code = 0x04
        status =   bu.to_u8(data, 4)
        if self.ble_error_check(status) == False:
            print("Read Remote Features did not complete")
            return
        print("Read Remote Features Complete")
        handle = bu.to_u16(data, 5)
        features = bu.to_data_rest(data, 7)
        print("Handle: {} Features {}".format(handle, bu.as_hex(features)))

    @register_event(0x07, meta_event_handlers)
    def on_le_data_length_change(self, data):
        # v5.4  Vol 4 Part E 7.7.65.7 LE Data Length CHange Event
        # Subevent Code = 0x07
        handle = bu.to_u16(data, 4)
        max_tx_octets = bu.to_u16(data, 6) # 0x001B to 0x00FB
        max_tx_time = bu.to_u16(data, 8) # 0x0148 to 0x4290
        max_rx_octets = bu.to_u16(data, 10) # 0x001B to 0x00FB
        max_rx_time = bu.to_u16(data, 12) # 0x0148 to 0x4290
        print(self.event_text, "Data length changed for 0x{:04X}".format(handle))
        print(f"Max TX Octets: 0x{max_tx_octets:04X}, Max TX Time:  0x{max_tx_octets:04X}")
        print(f"Max RX Octets: 0x{max_tx_octets:04X}, Max RX Time:  0x{max_tx_octets:04X}")

    @register_event(0x08, meta_event_handlers)
    def on_le_read_local_public_key(self, data):
        # v5.4  Vol 4 Part E 7.7.65.8 LE Read Local P-256 Public Key Complete
        # Subevent Code = 0x08
        status =   bu.to_u8(data, 4)
        if self.ble_error_check(status) == False:
            print("Read Local Public Key did not complete")
            return
        key_x_coordinate = bu.to_data(data, 5, 37)  # 32 octets
        key_y_coordinate = bu.to_data(data, 37, 69) # 32 octets
        print(self.event_text, "Read Local Public Key Complete")

    @register_event(0x01, hci_event_handlers)
    def on_hci_inquiry_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.1 HCI Inquiry Complete
        # Event Code = 0x01
        status = bu.to_u8  (data, 3)
        if self.ble_error_check(status) == False:
            print("HCI Inquiry did not complete")
            return
        else:
            print("HCI Inquiry Complete")

    @register_event(0x05, hci_event_handlers)
    def on_hci_event_disconnect_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.5 HCI Disconnection Complete
        # Event Code = 0x05
        status = bu.to_u8  (data, 3)
        if self.ble_error_check(status) == False:
            print("Disconnection Failed")
            return
        handle = bu.to_u16 (data, 4)
        reason = bu.to_u8  (data, 6)
        self.client_connected = False
        print("HCI Disconnection Complete, Handle = 0x{:04X}".format(handle))
        if reason == BLEErrorCode.REMOTE_USER_TERMINATED_CONNECTION:
            print("Remote User terminated Connection")
        else:
            print("Disconnect Reason: {BLEErrorCode(reason).name}")
        self.gatt_server.clear_connection_settings()
        self.do_set_advertise_enable(Advertising.ENABLED)


    @register_event(0x0E, hci_event_handlers)
    def on_hci_event_command_complete(self, data):
        # v5.4  Vol 4 Part E 7.7.14 HCI Command Complete
        # Event Code = 0x0E
        num_hci_command_packets = bu.to_u8(data, 3)
        if num_hci_command_packets == 0x00:
            print("Error: Controller not ready for more commands")
            return
        cmd = bu.to_u16 (data, 4)
        if cmd == 0x0000:
            print(f"Controller ready for {num_hci_command_packets} new Commands")
            return
        self.handle_le_command(cmd, data[6:])

    @register_event(0x0F, hci_event_handlers)
    def on_hci_event_command_status(self, data):
        # v5.4  Vol 4 Part E 7.7.15 HCI_Command_Status
        # Event Code = 0x0F
        status = bu.to_u8  (data, 3)
        if self.ble_error_check(status) == False:
            print("Command Status Fail Report")
            return
        num_hci_command_packets = bu.to_u8(data, 4)
        if num_hci_command_packets == 0x00:
            print("Error: Controller not ready for more commands")
            return
        opcode = bu.to_u16 (data, 5)
        self.handle_le_status(opcode)

    @register_event(0x13, hci_event_handlers)
    def on_hci_event_number_of_completed_packets(self, data):
        # v5.4  Vol 4 Part E 7.7.19 HCI Number Of Completed Packets
        # Event Code = 0x13
        length = bu.to_u8(data, 2)
        number_handles = bu.to_u8(data, 3)
        # two byte handle and two byte completed packet + number_handles byte
        handle_packet_length = (number_handles * 4) + 1 
        chunk_size = 4
        if ((number_handles * 4) + 1) != length:
            print(f"Error: Incorrect packet length {length} or number of handles {number_handles}")
        for i in range(0, length - 1, chunk_size):
            handle = bu.to_u16(data, 4 + i)
            connections = bu.to_u16(data, 6 + i)
            for i, (ihandle, count) in enumerate(self.total_connections):
                if ihandle == handle:
                    new_count = count + connections
                    self.total_connections[i] = (handle, new_count)
                    break
            print(f"Handle 0x{handle:04X}, Connections = {connections}, Total Connections = {new_count}")

        # Appears that some use this as an ack to indication
        # self.gatt_server.indication_ack_received()  

    @register_event(0x3E, hci_event_handlers)
    def on_hci_meta_event(self, data):
        # v5.4  Vol 4 Part E 7.7.65 LE Meta event
        # Event Code = 0x3E
        event_code = bu.to_u8(data, 3)
        handler = meta_event_handlers.get(event_code)
        if handler:
            handler(self, data)
        else:
            print(self.event_text, f"Unhandled MetaEvent 0x{event_code:02X}")
        
    @register_event(0xFF, hci_event_handlers)
    def on_hci_event_vendor_specific (self, data):
        # v5.4  Vol 4 Part E 5.4.4 Mentions Vendor Specific Debugging Event
        # Event Code = 0xFF
        print(self.event_text, "Vendor Specific")

    def event_mask_conversion(self, event_types, class_name):
        event_mask = [0] * 8
        for event_type in event_types:
            if isinstance(event_type, class_name):
                bit_index = event_type.value
                byte_index = bit_index // 8
                bit_position = bit_index % 8
                event_mask[byte_index] |= (1 << bit_position)
            else:
                raise ValueError(f"Invalid {class_name} for event mask")
        # print("".join(f"{byte:02X}" for byte in reversed(event_mask)))
        return bytes(event_mask)

    def set_event_mask(self, event_mask=None):
        # v5.4  Vol 4 Part E 7.3.1 Set Event Mask Command
        opcode = 0x0C01
        cmd_name = "Set Event Mask"
        print(self.cmd_text, cmd_name)
        # 8 byte event mask
        if event_mask == None:
            event_mask = []
            for event_type in EventMask:
                event_mask.append(event_type)
        packet = self.event_mask_conversion(event_mask, EventMask)
        self.send_command(opcode, cmd_name, packet)

    def reset(self):
        # v5.4  Vol 4 Part E 7.3.2 Reset Command
        opcode = 0x0C03
        cmd_name = "BLE Reset"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(None)
        self.send_command(opcode, cmd_name, packet)

    def write_local_name(self, name_bytes):
        # v5.4  Vol 4 Part E 7.3.11 Write Local Name Command
        opcode = 0x0C13
        cmd_name = "Write Local Name"
        print(self.cmd_text, f"{cmd_name} {name_bytes}")
        if not isinstance(name_bytes, (bytes, bytearray)):
            raise TypeError("Expected 'name_bytes' to be of type 'bytes' or 'bytearray'")
        if len(name_bytes) > 248:
            raise ValueError("Name is too long, must be 248 bytes or less.")
        packet = name_bytes.ljust(248, b'\x00')
        self.send_command(opcode, cmd_name, packet)

    def write_connection_accept_timeout(self, connect_timeout = ConnectionAcceptTimeout.DEFAULT_TIME):
        # v5.4  Vol 4 Part E 7.3.14 Write Connection Accept Timeout Command
        opcode = 0x0C16
        cmd_name = "Write Connection Accept Timeout Command"
        print(self.cmd_text, cmd_name)
        packet = ConnectionAcceptTimeout.from_time(connect_timeout)
        self.send_command(opcode, cmd_name, packet)

    def write_page_timeout_command(self, page_timeout = PageTimeout.DEFAULT_TIME):
        # v5.4  Vol 4 Part E 7.3.16 Write Page Timeout Command
        opcode = 0x0C18
        cmd_name = "Write Page Timeout Command"
        print(self.cmd_text, cmd_name)
        packet = ConnectionAcceptTimeout.from_time(page_timeout)
        self.send_command(opcode, cmd_name, packet)

    def write_scan_enable(self, scan_enable = ScanEnable.ALL_ENABLED):
        # v5.4  Vol 4 Part E 7.3.18 Write Scan Enable Command
        opcode = 0x0C1A
        cmd_name = "Write Scan Enable Command"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(scan_enable)
        self.send_command(opcode, cmd_name, packet)

    def read_local_commands(self):
        # v5.4  Vol 4 Part E 7.4.2 Read Local Supported Commands
        opcode = 0x1002
        cmd_name = "Read Local Supported Commands"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(None)
        self.send_command(opcode, cmd_name, packet, "check_le_compatible")

    def check_le_compatible(self, data):
        if (bu.to_u8(data, 32) & 0xA2 == 0xA2) and (bu.to_u8(data, 33) & 0x3E == 0x3E):
            print("LE Compatible")
        else:
            raise ValueError("Error: Not LE Compatible")

    def read_local_board_address(self):
        # v5.4  Vol 4 Part E 7.4.2 Read BD_ADDR Commands
        opcode = 0x1009
        cmd_name = "Read Local Board Address"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(None)
        self.send_command(opcode, cmd_name, packet, "board_address")

    def board_address(self, data):
        if len(data) < 6:
            self.local_board_address = None
            print("Error: not enough data bytes")
            return None  # Not enough data to extract address
        self.local_board_address = data[-6:]
        formatted_address = ':'.join(f'{byte:02X}' for byte in reversed(self.local_board_address))
        print('Local Board Address:', formatted_address)
        return formatted_address

    def set_le_event_mask(self, event_mask = None):
        # v5.4  Vol 4 Part E 7.8.3 LE Set Event Mask Command
        opcode = 0x2001
        cmd_name = "LE Event Mask"
        print(self.cmd_text, cmd_name)
        # Default 8 byte event mask
        if event_mask == None:
            event_mask = [
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
            ]
        packet = self.event_mask_conversion(event_mask, EventType)
        self.send_command(opcode, cmd_name, packet)

    def read_le_buffer_size(self):
        # v5.4  Vol 4 Part E 7.8.3 LE Read Buffer Size Command
        opcode = 0x2002
        cmd_name = "Read LE Buffer Size"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(None)
        self.send_command(opcode, cmd_name, packet, "read_buffer_size")

    def read_buffer_size(self, data):
        status = bu.to_u8(data, 0)
        if self.ble_error_check(status) == False:
            print("Read Buffer Size did not complete")
            return
        hc_le_data_packet_length = bu.to_u16(data, 1)
        print(f"Data Length = 0x{hc_le_data_packet_length:04X}")
        hc_le_data_buffer = bu.to_u8(data, 3)
        print(f"Data Buffer = 0x{hc_le_data_buffer:02X}")

    def set_random_address(self):
        # v5.4  Vol 4 Part E 7.8.4 LE Set Random Address Command
        opcode = 0x2005
        cmd_name = "Set Random Bluetooth Address"
        random_address = bytes([randint(0x00, 0xFF) for _ in range(6)])
        random_address_str = ':'.join(f'{byte:02X}' for byte in reversed(random_address))
        print(self.cmd_text, f"{cmd_name}: {random_address_str}")
        self.send_command(opcode, cmd_name, random_address)

    def do_set_advertising_parameters(self, min_interval=AdvertisingInterval.DEFAULT_TIME,
                                      max_interval=AdvertisingInterval.DEFAULT_TIME, 
                                      adv_type=AdvertisingType.ADV_IND,
                                      own_addr_type=Address.PUBLIC,
                                      peer_addr_type=PeerAddressType.PUBLIC_DEVICE,
                                      peer_addr='00:00:00:00:00:00',
                                      adv_channel_map=AdvertisingChannelMap.ALL_CHANNELS,
                                      adv_filter_policy=AdvertisingFilterPolicy.SCAN_CONNECT_ALL):
        # v5.4  Vol 4 Part E 7.8.5 LE Set Advertising Parameters
        opcode = 0x2006
        cmd_name = "LE Set Advertising Parameters"
        print(self.cmd_text, cmd_name)
        packet = AdvertisingInterval.from_time(min_interval)
        packet += AdvertisingInterval.from_time(max_interval)
        packet += bu.from_u8   (adv_type)
        packet += bu.from_u8   (own_addr_type)
        packet += bu.from_u8   (peer_addr_type)
        packet += bu.from_addr (peer_addr)
        packet += bu.from_u8   (adv_channel_map)
        packet += bu.from_u8   (adv_filter_policy)
        self.send_command(opcode, cmd_name, packet)

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

    def do_set_advertising_data(self, fields):
        # v5.4  Vol 4 Part E 7.8.7 LE Set Advertising Data
        opcode = 0x2008
        cmd_name = "LE Set Advertising Data"
        packet = self.create_advertising_packet(fields)
        print(self.cmd_text, cmd_name)
        self.send_command(opcode, cmd_name, packet)

    def do_set_scan_response_data(self, fields):
        # v5.4  Vol 4 Part E 7.8.8 LE Set Scan Response Data
        opcode = 0x2009
        cmd_name = "LE Set Scan Response Data"
        packet = self.create_advertising_packet(fields)
        print(self.cmd_text, cmd_name)
        self.send_command(opcode, cmd_name, packet)

    def do_set_advertise_enable(self, enabled_status:Advertising):
        # v5.4  Vol 4 Part E 7.8.9 LE Set Advertising Enable
        opcode = 0x200A
        if enabled_status == Advertising.ENABLED:
            cmd_name = "LE Set Advertising: Enabled"
        elif enabled_status == Advertising.DISABLED:
            cmd_name = "LE Set Advertising: Disabled"
        else:
            raise ValueError("Invalid advertising parameter {}".format(enabled_status))
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(enabled_status)
        self.send_command(opcode, cmd_name, packet)

    def do_set_scan_parameters(self, scan_type=ScanningType.ACTIVE,
                               scan_interval=ScanningTime.DEFAULT_TIME,
                               scan_window=ScanningTime.DEFAULT_TIME,
                               own_addr_type=Address.PUBLIC,
                               scan_filter_policy=ScanningFilter.BASIC_UNFILTERED):
        # v5.4  Vol 4 Part E 7.8.10 LE Set Scan Parameters
        opcode = 0x200B
        cmd_name = "LE Set Scan Parameters"
        print(self.cmd_text, cmd_name)
        packet =  bu.from_u8  (scan_type)
        packet += ScanningTime.from_time(scan_interval)
        packet += ScanningTime.from_time(scan_window)
        packet += bu.from_u8  (own_addr_type)
        packet += bu.from_u8  (scan_filter_policy)
        self.send_command(opcode, cmd_name, packet)

    def do_set_scan(self, enabled_status=ScanningStatus.DISABLED,
                    duplicates=ScanningFilterDuplicate.DISABLED):
        # v5.4  Vol 4 Part E 7.8.11 LE Set Scan Enable
        opcode = 0x200C
        if enabled:
            cmd_name = "LE Set Scan Enable"
        else:
            cmd_name = "LE Set Scan Disable"
        print(self.cmd_text, cmd_name)
        packet =  bu.from_u8(enabled_status)
        packet += bu.from_u8(duplicates)        
        self.send_command(opcode, cmd_name, packet)

    def do_create_connection(self, scan_interval=ScanningTime.DEFAULT_TIME,
                             scan_window=ScanningTime.DEFAULT_TIME,
                             initiator_filter=InitiatorFilter.FILTER_ACCEPT_NOT_USED,
                             peer_addr_type = PeerAddressType.PUBLIC_DEVICE,
                             peer_addr='00:00:00:00:00:00',
                             own_addr_type=Address.PUBLIC,
                             min_interval=ConnectionInterval.DEFAULT_TIME_MIN,
                             max_interval=ConnectionInterval.DEFAULT_TIME_MAX,
                             latency=MaxLatency.DEFAULT_TIME,
                             supervision_timeout=SupervisionTimeout.DEFAULT_TIME,
                             min_ce_length=ConnectionEventTime.DEFAULT_TIME,
                             max_ce_length = ConnectionEventTime.DEFAULT_TIME):
        # v5.4  Vol 4 Part E 7.8.12 LE Create Connection
        opcode = 0x200d
        cmd_name = "LE Create Connection"
        print(self.cmd_text, cmd_name)
        packet =  ScanningTime.from_time(scan_interval)
        packet += ScanningTime.from_time(scan_window)
        packet += bu.from_u8  (initiator_filter)
        packet += bu.from_u8  (peer_addr_type)
        packet += bu.from_addr(peer_addr)
        packet += bu.from_u8  (own_addr_type)
        packet += ConnectionInterval.from_time(min_interval)
        packet += ConnectionInterval.from_time(max_interval)
        packet += MaxLatency.from_time(latency)
        packet += SupervisionTimeout.from_time(supervision_timeout)
        packet += ConnectionEventTime.from_time(min_ce_length)
        packet += ConnectionEventTime.from_time(max_ce_length)
        self.send_command(opcode, cmd_name, packet)

    def do_add_device_to_accept_list(self, addr=Address.PUBLIC, addr_type='00:00:00:00:00:00'):
        # v5.4  Vol 4 Part E 7.8.16 LE Add Device To Filter Accept List
        opcode = 0x2011
        cmd_name = "LE Add Device To Filter Accept List"
        print(self.cmd_text, cmd_name)
        packet =  bu.from_u8(addr_type)
        packet += bu.from_addr(addr)
        self.send_command(opcode, cmd_name, packet)

    def do_read_remote_used_features(self):
        # v5.4  Vol 4 Part E 7.8.21 LE Read Remote Features
        opcode = 0x2016 
        cmd_name = "LE Read Remote Features"
        print(self.cmd_text, cmd_name)
        if self.connection_handle == None:
            print("Error: No connection handle")
            return
        packet = bu.from_u16(self.connection_handle)
        self.send_command(opcode, cmd_name, packet)

    def read_local_public_key(self):
        # v5.4  Vol 4 Part E 7.8.36 LE Read Local P-256 Public Key Command
        opcode = 0x2025
        cmd_name = "Read Local Public Key"
        print(self.cmd_text, cmd_name)
        packet = bu.from_u8(None)
        self.send_command(opcode, cmd_name, packet)
    
    def do_att_error_rsp(self, request_opcode, handle, error_code):
        # v5.4  Vol 3 Part F 3.4.1.1 ATT_ERROR_RSP
        att_opcode = 0x01
        cmd_name = "Error Response"
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8(att_opcode) 
        packet += bu.from_u8(request_opcode)     
        packet += bu.from_u16(handle) 
        packet += bu.from_u8(error_code)
        self.send_acl(packet)

    def do_att_exchange_mtu_req(self, mtu_size = 244):
        # v5.4  Vol 3 Part F 3.4.2.1 ATT_EXCHANGE_MTU_REQ
        att_opcode = 0x02
        cmd_name = "Exchance MTU"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode:02X}")
        packet =  bu.from_u8  (att_opcode)           # ATT opcode ATT_EXCHANGE_MTU_REQ
        packet += bu.from_u16 (mtu_size)       # MTU size requested 
        self.send_acl(packet)

    @register_event(0x02, acl_event_handler)
    def do_att_exchange_mtu_rsp(self, data, mtu_size = 244):
        # v5.4  Vol 3 Part F 3.4.2.1 ATT_EXCHANGE_MTU_REQ
        att_opcode_req = 0x02
        cmd_name = "Exchance MTU"
        print(self.att_req_text, f"{cmd_name} (0x{att_opcode_req:02X})")
        client_rx_mtu = bu.to_u16(data, 1)
        print(f"Client RX MTU = {client_rx_mtu}")

        # v5.4  Vol 3 Part F 3.4.2.2 ATT_EXCHANGE_MTU_RSP
        att_opcode = 0x03
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8  (att_opcode)      
        packet += bu.from_u16 (mtu_size) 
        self.send_acl(packet)

    def do_att_find_information_req(self, start_handle, end_handle):
        # v5.4  Vol 3 Part F 3.4.3.1 ATT_FIND_INFORMATION_REQ
        att_opcode = 0x04
        cmd_name = "FIND INFORMATION"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode:02X}")
        packet =  bu.from_u8(att_opcode)
        packet += bu.from_u16(start_handle)
        packet += bu.from_u16(end_handle)
        self.send_acl(packet)

    @register_event(0x04, acl_event_handler)
    def do_att_find_information_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.3.1 ATT_FIND_INFORMATION_REQ
        att_opcode_req = 0x04
        cmd_name = "FIND INFORMATION"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        start_handle = bu.to_u16(data, 1)
        end_handle = bu.to_u16(data, 3)
        print(f"Start Handle 0x{start_handle:04X}, End Handle 0x{end_handle:04X}")

        # v5.4  Vol 3 Part F 3.4.3.2 ATT_FIND_INFORMATION_RSP
        att_opcode = 0x05
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        return_code, uuid_format, handle_uuid = self.gatt_server.find_information(start_handle, end_handle)
        if return_code != ATTCode.SUCCESS:
            self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
            return
        packet =  bu.from_u8(att_opcode)
        packet += bu.from_u8(uuid_format)
        for each_handle_uuid in handle_uuid:
            handle, uuid = each_handle_uuid
            packet += bu.from_u16(start_handle)
            packet += uuid
        self.send_acl(packet)

    @register_event(0x06, acl_event_handler)
    def do_att_find_by_type_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.3.3 ATT_FIND_BY_TYPE_VALUE_REQ
        att_opcode_req = 0x06
        cmd_name = "FIND BY TYPE"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        start_handle = bu.to_u16(data, 1)
        end_handle = bu.to_u16(data, 3)
        print(f"Start Handle 0x{start_handle:04X}, End Handle 0x{end_handle:04X}")
        att_uuid = bu.to_u16(data, 5)
        att_value = data[7:]
        print(f"UUID to find 0x{att_uuid:04X}, {att_value}")

        # v5.4  Vol 3 Part F 3.4.3.4 ATT_FIND_BY_TYPE_VALUE_RSP
        att_opcode = 0x07
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        return_code, value_handles = self.gatt_server.find_by_value(start_handle,
                                                end_handle, att_uuid, att_value)
        if return_code != ATTCode.SUCCESS:
            self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
            return
        packet =  bu.from_u8(att_opcode)
        for i in range(0, len(value_handles), 2):
            packet += bu.from_u16(value_handles[i])
            if i + 1 < len(value_handles):
                packet += bu.from_u16(value_handles[i + 1])
            else:
                packet += bu.from_u16(value_handles[i])
        self.send_acl(packet)

    def do_att_read_by_type_req(self, start_handle, end_handle, attribute_type):
        # v5.4  Vol 3 Part F 3.4.4.1 ATT_READ_BY_TYPE_REQ
        att_opcode = 0x08
        cmd_name = "READ BY TYPE"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode:02X}")
        packet =  bu.from_u8  (att_opcode) 
        packet += bu.from_u16 (start_handle)
        packet += bu.from_u16 (end_handle)
        packet += bu.from_u16 (attribute_type)        
        self.send_acl(packet)

    @register_event(0x08, acl_event_handler)
    def do_att_read_by_type_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.4.1 ATT_READ_BY_TYPE_REQ
        att_opcode_req = 0x08
        cmd_name = "READ BY TYPE"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        start_handle = bu.to_u16(data, 1)
        end_handle = bu.to_u16(data, 3)
        uuid = bu.to_uuid(data[5:])
        print(f"Start Handle 0x{start_handle:04X}, End Handle 0x{end_handle:04X}")
        print(f"UUID = {uuid}")

        # v5.4  Vol 3 Part F 3.4.4.2 ATT_READ_BY_TYPE_RSP
        att_opcode = 0x09
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8  (att_opcode)
        return_code, data = self.gatt_server.read_by_value(start_handle, end_handle, uuid)
        if return_code != ATTCode.SUCCESS:
            self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
            return
        packet += data

        # if uuid == bu.from_uuid_int(ATTR.CHARACTERISTIC):
        #     return_code, char_decl = self.gatt_server.read_char_uuid_value(start_handle, end_handle)
        #     if return_code != ATTCode.SUCCESS:
        #         self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
        #         return
        #     elif not char_decl:
        #         print("No CD Handle in range of 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
        #         self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
        #         return
        #     else:
        #         # len_char_item = len(char_decl)
        #         packet += bu.from_u8(7) 
        #         # for idx, char_item in enumerate(char_decl):
        #         handle, prop_byte, value_handle, char_uuid = char_decl
        #         packet += bu.from_u16(handle)
        #         packet += bu.from_u8(prop_byte)
        #         packet += bu.from_u16(value_handle)
        #         packet += char_uuid
        # else:
        #     return_code, handle, data = self.gatt_server.read_uuid_value(start_handle, end_handle, uuid)
        #     if return_code != ATTCode.SUCCESS:
        #         self.do_att_error_rsp(att_opcode_req, start_handle, return_code) 
        #         return  
        #     packet += bu.from_u8(2 + len(data))
        #     packet += bu.from_u16 (handle)
        #     packet += data        
        self.send_acl(packet)

    def do_att_read_req(self, handle):
        # v5.4  Vol 3 Part F 3.4.4.3 ATT_READ_REQ
        att_opcode = 0x0A
        cmd_name = "READ"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode:02X}")
        
        packet =  bu.from_u8  (att_opcode)
        packet += bu.from_u16 (handle)
        self.send_acl(packet)

    @register_event(0x0A, acl_event_handler)
    def do_att_read_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.4.3 ATT_READ_REQ
        att_opcode_req = 0x0A
        cmd_name = "READ"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        handle = bu.to_u16(data, 1)
        print(f"Handle 0x{handle:04X}")

        # v5.4  Vol 3 Part F 3.4.4.4 ATT_READ_RSP
        att_opcode = 0x0B
        cmd_name = "READ"
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        return_code, byte_value = self.gatt_server.read_char_value(handle)
        if return_code != ATTCode.SUCCESS: 
            self.do_att_error_rsp(att_opcode_req, handle, return_code)
            return
        else: 
            packet = bu.from_u8(att_opcode)
            packet += byte_value
            self.send_acl(packet)

    @register_event(0x10, acl_event_handler)
    def do_att_group_type_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.4.9 ATT_READ_BY_GROUP_TYPE_REQ
        att_opcode_req = 0x10
        cmd_name = "GROUP TYPE"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        start_handle = bu.to_u16(data, 1)
        end_handle = bu.to_u16(data, 3)
        gatt_uuid = bu.to_uuid(data[5:])
        print(f"Start Handle 0x{start_handle:04X}, End Handle 0x{end_handle:04X}")
        print(f"UUID = {gatt_uuid}")

        # v5.4  Vol 3 Part F 3.4.4.10 ATT_READ_BY_GROUP_TYPE_RSP
        att_opcode = 0x11
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8  (att_opcode)   
        print("Get primary services for handles 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
        return_code, data = self.gatt_server.get_service_handle_range(gatt_uuid, start_handle, end_handle)
        if return_code != ATTCode.SUCCESS: 
            self.do_att_error_rsp(att_opcode_req, handle, return_code)
            return
        packet += data


        # if gatt_uuid == bu.from_uuid_int(ATTR.PRIMARY_SERVICE):
        #     print("Get primary services for handles 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
        #     return_code, return_start_handle, return_end_handle, primary_uuid = self.gatt_server.get_service_handle_range(start_handle)
        #     if return_code != ATTCode.SUCCESS: 
        #         self.do_att_error_rsp(att_opcode_req, handle, return_code)
        #         return
        #     print("Handles 0x{:04X} to 0x{:04X}".format(return_start_handle, return_end_handle))
        #     if end_handle < return_end_handle:
        #         print("Service handle 0x{:04X} larger than request max 0x{:04X}, truncating".format(end_handle, return_end_handle))
        #         return_end_handle = end_handle
        #     att_length = 4 + len(primary_uuid)
        #     packet += bu.from_u8(att_length)  
        #     packet += bu.from_u16(return_start_handle)
        #     packet += bu.from_u16(return_end_handle)
        #     packet += primary_uuid
        # else:
        #     print(f"GATT Attribute {gatt_uuid} Not Implemented")
        #     self.do_att_error_rsp(att_opcode_req, start_handle, ATTCode.UNLIKELY_ERROR)
        #     return
        self.send_acl(packet)

    @register_event(0x12, acl_event_handler)
    def do_att_write_rsp(self, data):
        # v5.4  Vol 3 Part F 3.4.5.1 ATT_WRITE_REQ
        att_opcode_req = 0x12
        cmd_name = "WRITE"
        print(self.att_req_text, f"{cmd_name}: 0x{att_opcode_req:02X}")
        handle = bu.to_u16(data, 1)
        value = data[3:]
        print(f"Handle 0x{handle:04X}, Value {value}")

        # v5.4  Vol 3 Part F 3.4.5.2 ATT_WRITE_RSP
        att_opcode = 0x13
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code == ATTCode.SUCCESS:
            packet =  bu.from_u8(att_opcode)   
            self.send_acl(packet)
        else:
            self.do_att_error_rsp(att_opcode_req, handle, return_code)

    def check_notification(self):
        # v5.4  Vol 3 Part F 3.4.7.1 ATT_HANDLE_VALUE_NTF
        att_opcode = 0x1B
        cmd_name = "NOTIFICATION"
        if self.client_connected == False:
            return
        notification_exists, handle, data = self.gatt_server.get_notification()
        if notification_exists == False:
            return
        if handle == None or data == None:
            # print("Notification has no handle or data")
            return
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8(att_opcode) 
        packet += bu.from_u16(handle)
        packet += data
        self.send_acl(packet)

    def check_indication(self):
        # v5.4  Vol 3 Part F 3.4.7.2 ATT_HANDLE_VALUE_IND
        att_opcode = 0x1D
        cmd_name = "INDICATION"
        if self.client_connected == False:
            return
        indication_exists, handle, data = self.gatt_server.get_indication()
        if indication_exists == False:
            return
        if handle == None or data == None:
            # print("Indication has no handle or data")
            return
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode:02X}")
        packet =  bu.from_u8(att_opcode) 
        packet += bu.from_u16(handle)
        packet += data
        self.send_acl(packet)

    @register_event(0x1E, acl_event_handler)
    def ack_indication(self, data):
        # v5.4  Vol 3 Part F 3.4.7.3 ATT_HANDLE_VALUE_CFM
        att_opcode_req = 0x1E
        cmd_name = "Indication ACK"
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode_req:02X}")
        self.gatt_server.clear_ack()

    @register_event(0x52, acl_event_handler)
    def do_att_write_no_response(self, data):
         # v5.4  Vol 3 Part F 3.4.5.3 ATT_WRITE_CMD
        att_opcode_req = 0x52
        cmd_name = "WRITE NO RESPONSE"
        print(self.att_rsp_text, f"{cmd_name} 0x{att_opcode_req:02X}")
        handle = bu.to_u16(data, 1)
        value = data[3:]
        return_code = self.gatt_server.write_char_value(handle, value)
        if return_code != ATTCode.SUCCESS:
            print("No response was requested but write was not successful, Error = 0x{:02X}".format(return_code))

    def on_acl_event(self, data):
        print("ACL data:      ", bu.as_hex(data))
        att_opcode = bu.to_u8(data, 0)
        handler = acl_event_handler.get(att_opcode)
        if handler:
            handler(self, data)
        else:
            print(self.event_text, f"Unhandled ATT Req 0x{att_opcode:02X}")

    def on_hci_event(self, data):
        event_code = bu.to_u8(data, 1)
        handler = hci_event_handlers.get(event_code)
        if handler:
            handler(self, data)
        else:
            print(self.event_text, f"Unhandled HCI Req 0x{event_code:02X}")

    def on_acl_packet(self, data):
        # v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet
        handle = bu.to_bits_u16(data, 1, 0, 12)
        if self.connection_handle is not None and handle != self.connection_handle:
            print(f"Warning: Handle does not match 0x{handle:04X} != 0x{self.connection_handle:04X}")
        pb =     bu.to_bits_u16(data, 1, 12, 2)
        if pb != PacketBoundaryFlags.COMPLETE_MESSAGE:
            print(f"Warning: PB is not a complete message.  Fragemented packets not tested ")
        bc =     bu.to_bits_u16(data, 1, 14, 2)
        if bc != BroadcastFlags.POINT_POINT:
            print("Warning: BC only supports Point to Point.")
        length = bu.to_u16(data, 3) 
 
        full_packet = False
        # print('ACL header: handle: {}  bc: {}  pb: {}'.format(handle, bc, pb))
        if pb & PacketBoundaryFlags.CONTINUING_FRAGMENT == PacketBoundaryFlags.CONTINUING_FRAGMENT:
            size =     bu.to_u16(data, 5)
            channel =  bu.to_u16(data, 7)
            acl_data = bu.to_data_rest(data, 9)
            full_packet = length - size == 4
            print("Channel: {} Length: {} Data size: {} Full packet? {}".format(channel, length, size, full_packet))
            # print("ACL packet:    ", bu.as_hex(acl_data))
            self.acl_total_length = size
            self.acl_packet =       acl_data
        if pb & PacketBoundaryFlags.FIRST_FRAGMENT == PacketBoundaryFlags.FIRST_FRAGMENT:
            print("ACL Packet Continuation")
            acl_data = bu.to_data_rest(data, 5)
            self.acl_packet += acl_data
            print("ACL data:  ", bu.as_hex(acl_data))
            if len(self.acl_packet) == self.acl_total_length:    # This was the last continuation packet
                full_packet = True
                # print("ACL Packet Final")
                print("Full ACL data: ", bu.as_hex(self.acl_packet))
        if full_packet:
            self.on_acl_event(self.acl_packet)                 
            
    def on_data(self, data):
        # v5.4  Vol 4 Part E 5.4.4 HCI Event Packet
        # v5.4  Vol 4 Part E 5.4.2 HCI ACL Packet
        packet_type = bu.to_u8(data, 0)
        if   packet_type == HCIPacket.EVENT: 
            self.on_hci_event(data)
        elif packet_type == HCIPacket.ACL_DATA:
            self.on_acl_packet(data)
        else:
            print("Unhandled packet type", packet_type)


if __name__ == "__main__":
    bc = BluetoothLEConnection()
    bc.do_set_scan_parameters()
    bc.do_set_advertising_parameters()
    # bc.do_set_advertise_enable(Advertising.ENABLED)
    # bc.do_set_advertise_enable(Advertising.DISABLED)
    # bc.do_set_advertise_enable('ABC')
    bc.do_create_connection()
    bc.set_le_event_mask()
    bc.set_event_mask()
    bc.write_connection_accept_timeout()
    bc.write_page_timeout_command()
    bc.write_scan_enable()
    # bc.on_acl_packet(bytes([0x02, 0x40, 0x60, 0x07, 0x00, 0x03, 0x00, 0x04, 0x00, 0x0a, 0x16, 0x00]))
    # print(bc.ble_error_check(0x04))
    bc.on_le_advertising_report([0x04,0x3E,0x1E,0x02,0x01,0x00,0x01,0x66,0x55,0x44,0x33,0x22,0x11,0x05,0x02,0x01,0x06,0x03,0x19,0xC1,0x03,0xC5])