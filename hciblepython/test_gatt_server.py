#!/usr/bin/env python3
from ble_helper import ByteHelper
from ble_helper import ATTErrorCode
from ble_helper import GATTAttributes

class GattServer:
    def __init__(self):
        self.gatt_table = None
        self.device_name = None
        self.service_changed = 0x0000
        self.getTestTable()

    def create_pnp_id(self, vendor_id_source = 0x01, vendor_id = 0x1234, product_id = 0x0203, product_version = 0x0001):
        # vendor_id_source = 0x01   # Bluetooth SIG
        # vendor_id = 0x1234        # Any value you want since we are not official
        # product_id = 0x0203       # Product ID
        # product_version = 0x0001  # Product Version

        if not (0 <= vendor_id_source <= 0xFF):
            raise ValueError("Vendor ID Source must be a 1-byte value (0-255).")
        if not (0 <= vendor_id <= 0xFFFF):
            raise ValueError("Vendor ID must be a 2-byte value (0-65535).")
        if not (0 <= product_id <= 0xFFFF):
            raise ValueError("Product ID must be a 2-byte value (0-65535).")
        if not (0 <= product_version <= 0xFFFF):
            raise ValueError("Product Version must be a 2-byte value (0-65535).")
        
        pnp_id = bytes([
            vendor_id_source,                              # 1 byte for Vendor ID Source
            vendor_id & 0xFF, (vendor_id >> 8) & 0xFF,     # 2 bytes for Vendor ID (little-endian)
            product_id & 0xFF, (product_id >> 8) & 0xFF,   # 2 bytes for Product ID (little-endian)
            product_version & 0xFF, (product_version >> 8) & 0xFF  # 2 bytes for Product Version (little-endian)
        ])
        return pnp_id

    def updateServiceCharacteristic(self, start_handle, end_handle):
        if end_handle < start_handle:
            raise ValueError("end_handle 0x{:04X} is less than start_handle 0x{:04X}".format(end_handle, start_handle))
        # print("start_handle 0x{:04X}, end_handle 0x{:04X}".format(start_handle << 8, end_handle))
        self.service_changed = (start_handle << 16) | end_handle
        print("Service changed: 0x{:08X}".format(self.service_changed))

    def getTestTable(self):
        self.device_name = "My  Pi"
        self.prop_flags = {
            "broadcast": 0x01,
            "read": 0x02,
            "write_without_response": 0x04,
            "write": 0x08,
            "notify": 0x10,
            "indicate": 0x20,
            "authenticated_signed_writes": 0x40,
            "extended_properties": 0x80,
        }

        self.perm_flags = {
            "read": 0x01,
            "write": 0x02,
            "Read Encrypted": 0x04,
            "Write Encrypted": 0x08,
            "Authenticated Read": 0x10,
            "Authenticated Write": 0x20,
            "Authorization Required": 0x40,

        }

        self.cccd = {  # Client Characteristic Configuration Descriptor
            "disabled": 0x0000,
            "notifications": 0x0001,
            "indications": 0x0002
        }

        self.value_type = {
            "bytes": 0x00,
            "int": 0x01,
            "string": 0x02,
            "variable": 0x04
        }

        self.max_value_length = 247 # Bytes

        self.pnp_id = self.create_pnp_id()

        self.appearance = 0x0080 # Generic Computer (0x0080)

        # GATT Table
        # Type: Current options are primary_service, characteristic_declaration, characteristic_value, and descriptor
        # Descriptor represents CCCD (Client Characteristic Configuration Descriptor: 0x2902) or CUD (Client User Description: 0x2901)
        # If Descriptor is CCCD then the value should be one of the choices in self.cccd
        # CUD Descriptor should be a more descriptive name (only needed if called by client)
        # UUID: 2 bytes or 16 bytes in string format (4 chars, 36 chars including the 4 '-')
        # Value Handle: the handle that has the actual value
        # Value Type: the type of value, see self.value_type. Fixed Length required for INTs
        # Properties: see options in self.perm_flags
        # Permissions for each handle are dictated by the property values and are not included since
        # we are not using Encryption or Authentication.  Putting permission read or write seems redundant
        # Advertise isn't used since we assume all services should be advertised
        # Constant is only added if True
        # Fixed length only added if True, length is then added as well. For int, length refers to the number of bytes in the data
        self.gatt_table = {
            # Generic Access Service (0x1800)
            0x0003: {"type": "primary_service", "uuid": "1800"},
            0x0004: {"type": "characteristic_declaration", "uuid": "2A00", "properties": "read", "constant": "True", "value_type": "variable", "value_handle": 0x0005},
            0x0005: {"type": "characteristic_value", "uuid": "2A00", "value": self.device_name},  # Device Name (string)
            0x0006: {"type": "characteristic_declaration", "uuid": "2A01", "properties": "read", "constant": "True", "value_type": "variable", "value_handle": 0x0007},
            0x0007: {"type": "characteristic_value", "uuid": "2A01", "value": self.appearance},  # Appearance

            # Generic Attribute Service (0x1801)
            0x0008: {"type": "primary_service", "uuid": "1801"},
            0x0009: {"type": "characteristic_declaration", "uuid": "2A05", "properties": "indicate", "fixed_length": "True", "length": 8, "value_type": "variable", "value_handle": 0x000A},
            0x000A: {"type": "characteristic_value", "uuid": "2A05", "value": self.service_changed},  # Service Changed
            0x000B: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},

            # Device Information Service (0x180A)
            0x000C: {"type": "primary_service", "uuid": "180A"},
            0x000D: {"type": "characteristic_declaration", "uuid": "2A50", "properties": "read", "value_type": "variable", "value_handle": 0x000E},
            0x000E: {"type": "characteristic_value", "uuid": "2A50", "value": self.pnp_id},  # PnP ID

            # Custom Service (11223344-5566-7788-99AA-BBCCDDEEFF00)
            0x000F: {"type": "primary_service", "uuid": "11223344-5566-7788-99AA-BBCCDDEEFF00"},
            0x0010: {"type": "characteristic_declaration", "uuid": "ABCD", "properties": "read|write_without_response", "value_type": "string", "value_handle": 0x0011},
            0x0011: {"type": "characteristic_value", "uuid": "ABCD", "value": ""},  # Control characteristic
            # 0x00XX: {"type": "descriptor", "uuid": GATTAttributes.CHARACTERISTIC_USER_DESC.value, "value": "User description, such as Control Characteristic"},
            0x0012: {"type": "characteristic_declaration", "uuid": "CDEF", "properties": "read|notify|write_without_response", "value_type": "string", "value_handle": 0x0013},
            0x0013: {"type": "characteristic_value", "uuid": "CDEF", "value": ""},  # Counter characteristic
            0x0014: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},
            0x0015: {"type": "characteristic_declaration", "uuid": "DEAF", "properties": "read|notify", "value_type": "string", "value_handle": 0x0016},
            0x0016: {"type": "characteristic_value", "uuid": "DEAF", "value": ""},  # Data characteristic
            0x0017: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value_type": "string", "value": "disabled"},
            0x0018: {"type": "characteristic_declaration", "uuid": "DCBA", "properties": "read|notify", "value_handle": 0x0019},
            0x0019: {"type": "characteristic_value", "uuid": "DCBA", "value": ""},  # Response characteristic
            0x001A: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},
        }

    def get_device_name(self):
        return self.device_name.encode('utf-8')

    def char_prop_to_byte(self, properties):
        prop_byte = 0x00
        for prop in properties.split('|'):
            if prop in self.prop_flags:
                prop_byte |= self.prop_flags[prop]
        return prop_byte

    def set_cccd(self, handle, value):
        if value not in self.cccd.values():
            print("Invalid value for CCCD. Use 0x0001 for notifications, 0x0002 for indications, or 0x0000 to disable.")
            return ATTErrorCode.VALUE_NOT_ALLOWED
        value_string = None
        for key, val in self.cccd.items():
            if val == value:
                value_string = key
                break
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                entry['value'] = value_string
                print("Updated CCCD at handle 0x{:04X} to {}".format(handle, value_string))
                return ATTErrorCode.SUCCESS
            else:
                print("Handle 0x{:04X} is not a valid CCCD descriptor 0x{:04X}.".format( handle, GATTAttributes.CLIENT_CHAR_CONFIG.value))
                return ATTErrorCode.ATTRIBUTE_NOT_FOUND
        else:
            print(f"Handle 0x{handle:04X} not found in gatt_table.")
            return ATTErrorCode.INVALID_HANDLE

    def read_cccd(self, handle):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                value = entry.get('value')
                if value not in self.cccd:
                    raise ValueError("Invalid value for CCCD {}.".format(value))
                # print("CCCD at handle 0x{:04X} = {}".format(handle, value))
                return value
            else:
                print("Handle 0x{:04X} is not a valid CCCD descriptor 0x{:04X}.".format( handle, GATTAttributes.CLIENT_CHAR_CONFIG.value))
                return None
        else:
            print(f"Handle 0x{handle:04X} not found in gatt_table.")
            return None

    def has_property(self, handle, one_prop_value):
        if '-' in one_prop_value:
            raise ValueError("Should only be a single property: write, read, indication, etc")
        for _, entry in self.gatt_table.items():
            if entry.get('type') == 'characteristic_declaration' and entry.get('value_handle') == handle:
                properties = entry.get('properties', '')
                if one_prop_value in properties.split('|'):
                    return True
                else:
                    # print("No {} Property for handle 0x{:04X}".format(one_prop_value, handle))
                    return False
        print("Characteristic value handle 0x{:04X} not found in gatt_table.".format(handle))
        return False

    def write_table_variable(self, uuid, value):
        print("No Variable can be written at this time")
        return ATTErrorCode.VALUE_NOT_ALLOWED

    def convert_and_write(self, handle, value):
        for _, entry in self.gatt_table.items():
            if entry.get('type') == 'characteristic_declaration' and entry.get('value_handle') == handle:
                value_type = entry.get("value_type")
                if handle in self.gatt_table:
                    value_entry = self.gatt_table[handle]
                    if value_type == "bytes":
                        value_entry["value"] = value
                        return ATTErrorCode.SUCCESS
                    elif value_type == "int":
                        int_len = entry.get("length")
                        if int_len == None:
                            print("Write: No length attribute in handle 0x{:04X}".format(handle))
                            return ATTErrorCode.ATTRIBUTE_NOT_FOUND
                        if int_len != len(value):
                            print("Write: Int requires a specific len of bytes {}".format(len(value)))
                        value_entry["value"] = int.from_bytes(value, byteorder='little')
                        return ATTErrorCode.SUCCESS
                    elif value_type == "string":
                        value_entry["value"] = ByteHelper.to_string(value)
                        return ATTErrorCode.SUCCESS
                    elif value_type == "variable":
                        uuid = entry.get("uuid")
                        if uuid == None:
                            print("Write: No uuid attribute in handle 0x{:04X}".format(handle))
                            return ATTErrorCode.ATTRIBUTE_NOT_FOUND
                        return self.write_table_variable(uuid, value)
                    else:
                        print("Write: Unkown value type {} for handle 0x{:04X}".format(value_type, handle))
                        return ATTErrorCode.VALUE_NOT_ALLOWED
                else:
                    print("Write: No value for handle 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND
        print("Write: Handle 0x{:04X} not found in gatt_table.".format(handle))
        return ATTErrorCode.INVALID_HANDLE

    def read_table_variable(self, uuid):
        if uuid == "2A00":
            return self.device_name.encode("utf-8")
        elif uuid == "2A01":
            return ByteHelper.from_u16(self.appearance)
        elif uuid == "2A05":
            v1 = self.service_changed & 0xFF
            v2 = (self.service_changed >> 8) & 0xFF
            v3 = (self.service_changed >> 16) & 0xFF
            v4 = (self.service_changed >> 24) & 0xFF
            sc_value = bytes([v3]) + bytes([v4]) + bytes([v1]) + bytes([v2])
            return sc_value
        elif uuid == "2A50":
            return self.pnp_id
        else:
            raise ValueError("UUID not found {}".format(uuid))

    def read_and_convert(self, handle):
        for _, entry in self.gatt_table.items():
            if entry.get('type') == 'characteristic_declaration' and entry.get('value_handle') == handle:
                value_type = entry.get("value_type")
                if handle in self.gatt_table:
                    value_entry = self.gatt_table[handle]
                    if value_type == "bytes":
                        return value_entry.get("value")
                    elif value_type == "int":
                        int_len = entry.get("length")
                        if int_len == None:
                            print("Read: No length attribute in handle 0x{:04X}".format(handle))
                            return None
                        int_value = value_entry.get("value")
                        int_bytes = int_value.to_bytes(int_len, byteorder='little')
                        if int_len != len(int_bytes):
                            print("Read: Int requires a specific len of bytes {} != {}".format(int_len, len(int_bytes)))
                            return None
                        return int_bytes
                    elif value_type == "string":
                        string_value = value_entry.get("value")
                        if string_value == None:
                            print("Read: No string value at 0x{:04X}".format(handle))
                            return None
                        return ByteHelper.from_string(string_value)
                    elif value_type == "variable":
                        uuid = entry.get("uuid")
                        if uuid == None:
                            print("Read: No uuid attribute in handle 0x{:04X}".format(handle))
                            return None
                        return self.read_table_variable(uuid)
                    else:
                        print("Read: Unkown value type {} for handle 0x{:04X}".format(value_type, handle))
                        return None
                else:
                    print("Read: No value for handle 0x{:04X}".format(handle))
                    return None
        print("Read: Characteristic value handle 0x{:04X} not found in gatt_table.".format(handle))
        return None

    def write_char_value(self, handle, value):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                return self.set_cccd(handle, value)
            if self.has_property(handle, 'write') or self.has_property(handle, 'write_without_response'):
                return self.convert_and_write(handle, value)
            else:
                return ATTErrorCode.WRITE_NOT_PERMITTED
        print("No handle 0x{:04X}".format(handle))
        return ATTErrorCode.INVALID_HANDLE

    def read_char_value(self, handle):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            # if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
            #     return self.read_cccd(handle)
            if self.has_property(handle, 'read'):
                return self.read_and_convert(handle)
        return None

    def get_uuid_byte_length(self, uuid):
        cleaned_uuid = uuid.replace('-', '')
        return int(len(cleaned_uuid)/2)

    def uuid_string_to_bytes(self, uuid):
        if isinstance(uuid, str):  # Check if uuid is a string
            cleaned_uuid = uuid.replace('-', '')
        else:
            raise TypeError(f"Expected a string, but got {type(uuid)}")
        length_uuid = len(cleaned_uuid)
        if length_uuid != 32 and length_uuid != 4:
            raise ValueError("Invalid UUID length {}, must be 128-bit (32 hex characters).".format(length_uuid))
        byte_pairs = [cleaned_uuid[i:i+2] for i in range(0, len(cleaned_uuid), 2)]
        little_endian_bytes = byte_pairs[::-1]
        little_endian_bytes = bytes(int(byte, 16) for byte in little_endian_bytes)
        return little_endian_bytes

    def uuid_bytes_to_string(self, uuid_bytes):
        if len(uuid_bytes) == 2:
            # Convert 2-byte UUID to a 4-character hex string
            return f"{uuid_bytes[1]:02X}{uuid_bytes[0]:02X}"

        elif len(uuid_bytes) == 16:
            # Reverse the bytes and convert 16-byte UUID to string format with dashes
            reversed_uuid_bytes = uuid_bytes[::-1]
            uuid_str = ''.join(f"{b:02X}" for b in reversed_uuid_bytes)
            return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"

        else:
            raise ValueError("Invalid UUID length. UUID must be either 2 or 16 bytes.")

    def find_information(self, start_handle, end_handle):
        uuid_format = None
        handle_uuid = []
        for handle in range(start_handle, end_handle + 1):
            if handle in self.gatt_table:
                uuid = self.gatt_table[handle].get("uuid")
                uuid_byte = self.uuid_string_to_bytes(uuid)
                len_uuid_byte = len(uuid_byte)
                if uuid_format == None:
                    if len_uuid_byte == 2:
                        uuid_format = 0x01
                    elif len_uuid_byte == 16:
                        uuid_format = 0x02
                    else:
                        raise ValueError("Invalid UUID length {}".format(len_uuid_byte))
                    handle_uuid.append([handle, uuid_byte])
                else:
                    if len_uuid_byte == 2 and uuid_format == 0x01:
                        handle_uuid.append([handle, uuid_byte])
                    elif len_uuid_byte == 16 and uuid_format == 0x02:
                        handle_uuid.append([handle, uuid_byte])
                    else:
                        print("Can't send UUID of different length in find information packet")
                        return uuid_format, handle_uuid
        return uuid_format, handle_uuid


    def read_uuid_value(self, start_handle, end_handle, target_uuid):     
        for handle in range(start_handle, end_handle + 1):
            if handle in self.gatt_table:
                uuid = self.gatt_table[handle].get("uuid")
                # print(uuid, target_uuid)
                if uuid == target_uuid:
                    value = self.gatt_table[handle].get("value")
                    if value == None:
                        continue
                    # print(value)
                    return handle, value.encode('utf-8')
        return None, None

    def read_char_uuid_value(self, start_handle, end_handle):
        characteristics = []
        for handle, attr in self.gatt_table.items():
            if start_handle <= handle <= end_handle and attr["type"] == "characteristic_declaration":
                properties = attr.get("properties")
                if properties == None:
                    print("No properties found at 0x{:04X}".format(handle))
                    return characteristics
                prop_byte = self.char_prop_to_byte(properties)
                value_handle = attr.get("value_handle")
                if value_handle == None:
                    print("No value_handle found at 0x{:04X}".format(handle))
                    return characteristics
                uuid = attr.get("uuid")
                if uuid == None:
                    print("No uuid found at 0x{:04X}".format(handle))
                    return characteristics
                uuid_bytes = self.uuid_string_to_bytes(uuid)
                #characteristics.append((handle, prop_byte, value_handle, uuid_bytes))
                characteristics = [handle, prop_byte, value_handle, uuid_bytes]
                break
        return characteristics


    def add_service(self, handle, service_type, uuid, value=None):
        self.gatt_table[handle] = {"type": service_type, "uuid": uuid, "value": value}

    def get_service_handle_range(self, start_handle):
        first_handle = None
        last_handle = None
        primary_service = None
        in_service = False
        max_handle = max(sorted(self.gatt_table.keys()))
        for handle in sorted(self.gatt_table.keys()):
            if handle < start_handle:
                continue 
            attribute = self.gatt_table[handle]
            if attribute["type"] == "primary_service":
                if in_service:
                    return (first_handle, last_handle, primary_service)
                first_handle = handle
                primary_service = attribute["uuid"]
                in_service = True
            if in_service:
                last_handle = handle
                if last_handle == max_handle:
                    print("End of Handles")
                    last_handle = 0xFFFF
        if first_handle is None:
            print("No primary service found starting at handle 0x{:04X}.".format(start_handle))
            return None, None, ""
        return (first_handle, last_handle, primary_service)


if __name__ == "__main__":
    gatt_server = GattServer()
    first, last, primary = gatt_server.get_service_handle_range(0x000C)
    print("First Handle = 0x{:04X}, Second Handle = 0x{:04X}, Primary = {}".format(first, last, primary))
    if gatt_server.get_uuid_byte_length(primary) != 2:
        print("Error, gatt_server.get_uuid_byte_length(primary) != 2")
    uuid_bytes = gatt_server.uuid_string_to_bytes("2A50")
    if uuid_bytes != b'P*':
        print("Error: gatt_server.uuid_string_to_bytes(\"2A50\")")
    if gatt_server.uuid_bytes_to_string(uuid_bytes) != '2A50':
        print("Error: gatt_server.uuid_bytes_to_string(uuid_bytes)")
    uuid_bytes = gatt_server.uuid_string_to_bytes("11223344-5566-7788-99AA-BBCCDDEEFF00")
    if uuid_bytes != b'\x00\xff\xee\xdd\xcc\xbb\xaa\x99\x88wfUD3"\x11':
        print("Error: uuid_bytes")
    # print(gatt_server.find_information(0x0010, 0x001A))
    # gatt_server.read_uuid_value(0x0003, 0x007, "2A00"))
    # print(gatt_server.read_char_uuid_value(0x000F, 0xFFFF))
    if gatt_server.read_cccd(0x0014) != 'disabled':
        print("Error: gatt_server.read_cccd(0x0014) != 'disabled'")
    gatt_server.set_cccd(0x0014, 1)
    if gatt_server.read_cccd(0x0014) != 'notifications':
        print("Error: gatt_server.read_cccd(0x0014) != 'notifications'")
    gatt_server.set_cccd(0x0014, 2)
    if gatt_server.read_cccd(0x0014) != 'indications':
        print("Error: gatt_server.read_cccd(0x0014) != 'indications'")

    test_property = gatt_server.char_prop_to_byte("read|write_without_response|notify")
    if test_property != 0x16:
        print("Property is not 0x16, but 0x{:02X}".format(test_property))

    if gatt_server.read_char_value(0x0013) != b"":
        print(gatt_server.read_char_value(0x0013))
        print("Error: gatt_server.read_char_value(0x0013) != empty string")
    test_write = gatt_server.write_char_value(0x0013, b'1234-5678') 
    if test_write != ATTErrorCode.SUCCESS:
        print("0x{:02X}".format(test_write))
        print("Error: gatt_server.write_char_value(0x0013, b'1234-5678') != ATTErrorCode.SUCCESS")
    if gatt_server.read_char_value(0x0013) != b'1234-5678':
        print("Error: gatt_server.read_char_value(0x0013) = write value")
    if gatt_server.write_char_value(0x0016, b'abcd1234') == ATTErrorCode.SUCCESS:
        print("Error: gatt_server.write_char_value(0x0016, b'abcd1234') == ATTErrorCode.SUCCESS")
    if gatt_server.read_char_value(0x0011) != b"":
        print("Error: gatt_server.read_char_value(0x0011)")
    gatt_server.write_char_value(0x0011, b'right-way')
    if gatt_server.read_char_value(0x0011) != b'right-way':
        print("Error: gatt_server.read_char_value(0x0011) != b'right-way'")
    gatt_server.updateServiceCharacteristic(0x0011, 0x0013)
    if gatt_server.read_and_convert(0x000A) != b'\x11\x00\x13\x00':
        print("Error: gatt_server.read_and_convert(0x000A) != b'\x11\x00\x13\x00'")


    