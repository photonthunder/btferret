#!/usr/bin/env python3
from ble_helper import ByteHelper
from ble_helper import ATTErrorCode
from ble_helper import GATTAttributes
import logging

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
            print("end_handle 0x{:04X} is less than start_handle 0x{:04X}".format(end_handle, start_handle))
            return ATTErrorCode.UNLIKELY_ERROR
        # print("start_handle 0x{:04X}, end_handle 0x{:04X}".format(start_handle << 8, end_handle))
        self.service_changed = (start_handle << 16) | end_handle
        print("Service changed: 0x{:08X}".format(self.service_changed))
        return ATTErrorCode.SUCCESS

    def validate_uuid(self, uuid):
        if len(uuid) == 4 and all(c in '0123456789ABCDEFabcdef' for c in uuid):
            return True
        if len(uuid) == 36 and uuid[8] == '-' and uuid[13] == '-' and uuid[18] == '-' and uuid[23] == '-':
            hex_parts = uuid.replace('-', '')
            if len(hex_parts) == 32 and all(c in '0123456789ABCDEFabcdef' for c in hex_parts):
                return True
        return False

    def validate_properties(self, properties):
        for prop in properties.split('|'):
            if prop not in self.prop_flags:
                return False
        return True

    def validate_value_type(self, value_type):
        return value_type in self.value_type

    def validate_cccd(self, value):
        return value in self.cccd

    def check_gatt_table(self):
        for handle, entry in self.gatt_table.items():
            if entry["type"] == "primary_service":
                if not self.validate_uuid(entry["uuid"]):
                    raise ValueError(f"Error at handle 0x{handle:04X}: Invalid UUID {entry['uuid']}")
            
            elif entry["type"] == "characteristic_declaration":
                if "properties" not in entry or not self.validate_properties(entry["properties"]):
                    raise ValueError(f"Error at handle 0x{handle:04X}: Invalid properties {entry.get('properties', 'None')}")
                
                if "value_handle" not in entry:
                    raise ValueError(f"Error at handle 0x{handle:04X}: Missing value_handle")

                if "value_type" not in entry or not self.validate_value_type(entry["value_type"]):
                    raise ValueError(f"Error at handle 0x{handle:04X}: Invalid value_type {entry.get('value_type', 'None')}")
            
            elif entry["type"] == "characteristic_value":
                # Ensure there is a value field
                if "value" not in entry:
                    raise ValueError(f"Error at handle 0x{handle:04X}: Missing value")

                # Validate UUID
                if not self.validate_uuid(entry["uuid"]):
                    raise ValueError(f"Error at handle 0x{handle:04X}: Invalid UUID {entry['uuid']}")

            elif entry["type"] == "descriptor":
                # Check if this is a CCCD and if the value is valid
                if entry["uuid"] == "2902" and not self.validate_cccd(entry["value"]):
                    raise ValueError(f"Error at handle 0x{handle:04X}: Invalid CCCD value {entry['value']}")
            else:
                raise ValueError(f"Error at handle 0x{handle:04X}: Unknown type {entry['type']}")
        
        print("GATT table check complete.")

    def getTestTable(self):
        self.device_name = "My New Pi"
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
            0x0011: {"type": "characteristic_value", "uuid": "ABCD", "value": "ENTER"},  # Control characteristic
            # 0x00XX: {"type": "descriptor", "uuid": GATTAttributes.CHARACTERISTIC_USER_DESC.value, "value": "User description, such as Control Characteristic"},
            0x0012: {"type": "characteristic_declaration", "uuid": "CDEF", "properties": "read|notify|write_without_response", "value_type": "string", "value_handle": 0x0013},
            0x0013: {"type": "characteristic_value", "uuid": "CDEF", "value": "0"},  # Counter characteristic
            0x0014: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},
            0x0015: {"type": "characteristic_declaration", "uuid": "DEAF", "properties": "read|notify", "value_type": "string", "value_handle": 0x0016},
            0x0016: {"type": "characteristic_value", "uuid": "DEAF", "value": "210"},  # Data characteristic
            0x0017: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},
            0x0018: {"type": "characteristic_declaration", "uuid": "DCBA", "properties": "read|notify", "value_type": "string", "value_handle": 0x0019},
            0x0019: {"type": "characteristic_value", "uuid": "DCBA", "value": "SET CNT"},  # Response characteristic
            0x001A: {"type": "descriptor", "uuid": GATTAttributes.CLIENT_CHAR_CONFIG.value, "value": "disabled"},
        }

        self.check_gatt_table()


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
            print("Handle 0x{:04X} not found in gatt_table.".format(handle))
            return ATTErrorCode.INVALID_HANDLE

    def read_cccd(self, handle):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                value = entry.get('value')
                if value not in self.cccd:
                    print("Invalid value for CCCD {}.".format(value))
                    return ATTErrorCode.VALUE_NOT_ALLOWED, None
                # print("CCCD at handle 0x{:04X} = {}".format(handle, value))
                value_int = self.cccd.get(value)
                return ATTErrorCode.SUCCESS, value_int.to_bytes(2, byteorder='little')
            else:
                print("Handle 0x{:04X} is not a valid CCCD descriptor 0x{:04X}.".format( handle, GATTAttributes.CLIENT_CHAR_CONFIG.value))
                return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None
        else:
            print("Handle 0x{:04X} not found in gatt_table.".format(handle))
            return ATTErrorCode.INVALID_HANDLE, None

    def has_property(self, handle, one_prop_value):
        if '|' in one_prop_value:
            print("Should only be a single property: write, read, indication, etc")
            return False
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
                            return ATTErrorCode.INVALID_ATTRIBUTE_VALUE_LENGTH
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
                        print("Write: Unknown value type {} for handle 0x{:04X}".format(value_type, handle))
                        return ATTErrorCode.VALUE_NOT_ALLOWED
                else:
                    print("Write: No value for handle 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND
        print("Write: Handle 0x{:04X} not found in gatt_table.".format(handle))
        return ATTErrorCode.INVALID_HANDLE

    def read_table_variable(self, uuid):
        if uuid == "2A00":
            return ATTErrorCode.SUCCESS, self.device_name.encode("utf-8")
        elif uuid == "2A01":
            return ATTErrorCode.SUCCESS, ByteHelper.from_u16(self.appearance)
        elif uuid == "2A05":
            v1 = self.service_changed & 0xFF
            v2 = (self.service_changed >> 8) & 0xFF
            v3 = (self.service_changed >> 16) & 0xFF
            v4 = (self.service_changed >> 24) & 0xFF
            sc_value = bytes([v3]) + bytes([v4]) + bytes([v1]) + bytes([v2])
            return ATTErrorCode.SUCCESS, sc_value
        elif uuid == "2A50":
            return ATTErrorCode.SUCCESS, self.pnp_id
        else:
            print("Error: UUID not found {}".format(uuid))
            return ATTErrorCode.VALUE_NOT_ALLOWED, None

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
                            return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None
                        int_value = value_entry.get("value")
                        int_bytes = int_value.to_bytes(int_len, byteorder='little')
                        if int_len != len(int_bytes):
                            print("Read: Int requires a specific len of bytes {} != {}".format(int_len, len(int_bytes)))
                            return ATTErrorCode.INVALID_ATTRIBUTE_VALUE_LENGTH, None
                        return ATTErrorCode.SUCCESS, int_bytes
                    elif value_type == "string":
                        string_value = value_entry.get("value")
                        if string_value == None:
                            print("Read: No string value at 0x{:04X}".format(handle))
                            return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None
                        return ATTErrorCode.SUCCESS, ByteHelper.from_string(string_value)
                    elif value_type == "variable":
                        uuid = entry.get("uuid")
                        if uuid == None:
                            print("Read: No uuid attribute in handle 0x{:04X}".format(handle))
                            return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None
                        return self.read_table_variable(uuid)
                    else:
                        print("Read: Unknown value type {} for handle 0x{:04X}".format(value_type, handle))
                        return ATTErrorCode.VALUE_NOT_ALLOWED, None
                else:
                    print("Read: No value for handle 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None
        print("Read: Characteristic value handle 0x{:04X} not found in gatt_table.".format(handle))
        return ATTErrorCode.INVALID_HANDLE, None

    def write_char_value(self, handle, value):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                int_value = ByteHelper.to_u16(value, 0)
                return self.set_cccd(handle, int_value)
            if self.has_property(handle, 'write') or self.has_property(handle, 'write_without_response'):
                return self.convert_and_write(handle, value)
            else:
                return ATTErrorCode.WRITE_NOT_PERMITTED
        print("No handle 0x{:04X}".format(handle))
        return ATTErrorCode.INVALID_HANDLE

    def read_char_value(self, handle):
        if handle in self.gatt_table:
            entry = self.gatt_table[handle]
            if entry.get('type') == 'descriptor' and entry.get('uuid') == GATTAttributes.CLIENT_CHAR_CONFIG.value:
                return self.read_cccd(handle)
            if self.has_property(handle, 'read'):
                return self.read_and_convert(handle)
        return ATTErrorCode.INVALID_HANDLE, None

    def uuid_string_to_bytes(self, uuid):
        if isinstance(uuid, str):  # Check if uuid is a string
            length_uuid = ByteHelper.get_uuid_byte_length(uuid)
            if length_uuid == 16 or length_uuid == 2:
                little_endian_bytes = ByteHelper.from_uuid(uuid)
                return ATTErrorCode.SUCCESS, little_endian_bytes
            else:
                print("Invalid UUID length {}, must be 128-bit (32 hex characters).".format(length_uuid))
                return ATTErrorCode.INVALID_ATTRIBUTE_VALUE_LENGTH, None
        else:
            print("Expected a string, but got {}".format(type(uuid)))
            return ATTErrorCode.UNLIKELY_ERROR, None

    def find_information(self, start_handle, end_handle):
        uuid_format = None
        handle_uuid = []
        for handle in range(start_handle, end_handle + 1):
            if handle in self.gatt_table:
                uuid = self.gatt_table[handle].get("uuid")
                return_code, uuid_byte = self.uuid_string_to_bytes(uuid)
                if return_code != ATTErrorCode.SUCCESS:
                    return return_code, None, None
                len_uuid_byte = len(uuid_byte)
                if uuid_format == None:
                    if len_uuid_byte == 2:
                        uuid_format = 0x01
                    elif len_uuid_byte == 16:
                        uuid_format = 0x02
                    else:
                        print("Invalid UUID length {}".format(len_uuid_byte))
                        return ATTErrorCode.INVALID_ATTRIBUTE_VALUE_LENGTH, None, None
                    handle_uuid.append([handle, uuid_byte])
                else:
                    if len_uuid_byte == 2 and uuid_format == 0x01:
                        handle_uuid.append([handle, uuid_byte])
                    elif len_uuid_byte == 16 and uuid_format == 0x02:
                        handle_uuid.append([handle, uuid_byte])
                    else:
                        print("Can't send UUID of different length in find information packet, ignoring")
                        return ATTErrorCode.SUCCESS, uuid_format, handle_uuid
        return ATTErrorCode.SUCCESS, uuid_format, handle_uuid


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
                    return ATTErrorCode.SUCCESS, handle, value.encode('utf-8')
        print("No match {} found bewtween 0x{:04X} and 0x{:04X}".format(uuid, start_handle, end_handle))
        return ATTErrorCode.ATTRIBUTE_NOT_FOUND, None, None

    def read_char_uuid_value(self, start_handle, end_handle):
        # print("Handle range of 0x{:04X} to 0x{:04X}".format(start_handle, end_handle))
        characteristics = []
        for handle, attr in self.gatt_table.items():
            if start_handle <= handle <= end_handle and attr["type"] == "characteristic_declaration":
                properties = attr.get("properties")
                if properties == None:
                    print("No properties found at 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND, characteristics
                prop_byte = self.char_prop_to_byte(properties)
                value_handle = attr.get("value_handle")
                if value_handle == None:
                    print("No value_handle found at 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND, characteristics
                uuid = attr.get("uuid")
                if uuid == None:
                    print("No uuid found at 0x{:04X}".format(handle))
                    return ATTErrorCode.ATTRIBUTE_NOT_FOUND, characteristics
                return_code, uuid_bytes = self.uuid_string_to_bytes(uuid)
                if return_code != ATTErrorCode.SUCCESS:
                    return ATTErrorCode.UNLIKELY_ERROR, characteristics
                #characteristics.append((handle, prop_byte, value_handle, uuid_bytes))
                characteristics = [handle, prop_byte, value_handle, uuid_bytes]
                break
        return ATTErrorCode.SUCCESS, characteristics


    def add_service(self, handle, service_type, uuid, value=None):
        self.gatt_table[handle] = {"type": service_type, "uuid": uuid, "value": value}

    def get_service_handle_range(self, start_handle):
        first_handle = None
        last_handle = None
        primary_service_uuid = None
        in_service = False
        max_handle = max(sorted(self.gatt_table.keys()))
        for handle in sorted(self.gatt_table.keys()):
            if handle < start_handle:
                continue 
            attribute = self.gatt_table[handle]
            if attribute["type"] == "primary_service":
                if in_service:
                    break
                first_handle = handle
                string_uuid = attribute["uuid"]
                primary_service_uuid = ByteHelper.from_uuid(string_uuid)
                in_service = True
            if in_service:
                last_handle = handle
                if last_handle == max_handle:
                    print("End of Handles")
                    last_handle = 0xFFFF
        if first_handle is None:
            print("No primary service found starting at handle 0x{:04X}.".format(start_handle))
            return ATTErrorCode.SUCCESS, None, None, ""
        return ATTErrorCode.SUCCESS, first_handle, last_handle, primary_service_uuid

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, format='%(message)s')

def error_check(condition, message, error_code=None):
    if not condition:
        if error_code is not None:
            logging.error(f"Error 0x{error_code:02X}: {message}")
            return
        else:
            logging.error(f"Error: {message}")
            return
    if error_code is not None:
        if error_code != ATTErrorCode.SUCCESS:
            logging.error(f"Error 0x{error_code:02X}: {message}")
            return

if __name__ == "__main__":
    gatt_server = GattServer()

    return_code, first, last, primary = gatt_server.get_service_handle_range(0x000C)
    expected_first = 0x000C
    expected_last = 0x000E
    expected_primary = b'\n\x18'
    error_check(first == expected_first and last == expected_last and primary == expected_primary, f"First Handle = 0x{first:04X}, Last Handle = 0x{last:04X}, Primary UUID = {primary}", return_code)
    
    return_code, uuid_bytes = gatt_server.uuid_string_to_bytes("11223344-5566-7788-99AA-BBCCDDEEFF00")
    expected_uuid_bytes = b'\x00\xff\xee\xdd\xcc\xbb\xaa\x99\x88wfUD3"\x11'
    error_check(uuid_bytes == expected_uuid_bytes, "UUID conversion failed", return_code)
    
    return_code, cccd = gatt_server.read_cccd(0x0014)
    error_check(cccd == b'\x00\x00', f"gatt_server.read_cccd(0x0014) != 'disabled'", return_code)
    
    return_code = gatt_server.set_cccd(0x0014, 1)
    error_check(return_code == ATTErrorCode.SUCCESS, "Failed to set CCCD at 0x0014 to notifications", return_code)
    
    return_code, cccd = gatt_server.read_cccd(0x0014)
    error_check(cccd == b'\x01\x00', "CCCD not set to 'notifications'", return_code)
    
    return_code = gatt_server.set_cccd(0x0014, 2)
    error_check(return_code == ATTErrorCode.SUCCESS, "Failed to set CCCD at 0x0014 to indications", return_code)

    return_code, cccd = gatt_server.read_cccd(0x0014)
    error_check(cccd == b'\x02\x00', "CCCD not set to 'indications'", return_code)
    
    test_property = gatt_server.char_prop_to_byte("read|write_without_response|notify")
    error_check(test_property == 0x16, f"Property is not 0x16, but 0x{test_property:02X}")
    
    return_code, data = gatt_server.read_char_value(0x0013)
    error_check(data == bytes([0x30]), f"gatt_server.read_char_value(0x0013) {data} != {bytes([0])}", return_code)
    
    return_code = gatt_server.write_char_value(0x0013, b'1234-5678') 
    error_check(return_code == ATTErrorCode.SUCCESS, f"gatt_server.write_char_value(0x0013, b'1234-5678') was successful", return_code)
    
    return_code, data = gatt_server.read_char_value(0x0013)
    error_check(data == b'1234-5678', f"gatt_server.read_char_value(0x0013) != written value", return_code)
    
    return_code = gatt_server.write_char_value(0x0016, b'abcd1234') 
    error_check(return_code != ATTErrorCode.SUCCESS, f"gatt_server.write_char_value(0x0016, b'abcd1234')")
    
    return_code, data = gatt_server.read_char_value(0x0011)
    error_check(data == b"ENTER", "gatt_server.read_char_value(0x0011)", return_code)
    
    return_code = gatt_server.write_char_value(0x0011, b'right-way')
    error_check(return_code == ATTErrorCode.SUCCESS, "gatt_server.write_char_value(0x0011, b'right-way')", return_code)

    return_code, data = gatt_server.read_char_value(0x0011)
    error_check(data == b'right-way', "gatt_server.read_char_value(0x0011) != 'right-way'", return_code)

    return_code, data = gatt_server.read_char_value(0x0019)
    error_check(data == b'SET CNT', "gatt_server.read_char_value(0x0019)", return_code)
    
    return_code = gatt_server.updateServiceCharacteristic(0x0011, 0x0013)
    error_check(return_code == ATTErrorCode.SUCCESS, "gatt_server.updateServiceCharacteristic(0x0011, 0x0013)", return_code)
    
    return_code, data = gatt_server.read_and_convert(0x000A)
    error_check(data == b'\x11\x00\x13\x00', f"gatt_server.read_and_convert(0x000A) != expected bytes", return_code)

    return_code, data = gatt_server.read_char_uuid_value(0x000C, 0x000E)
    error_check(data == [13, 2, 14, b'P*'], f"gatt_server.read_char_uuid_value(0x000C, 0x000E)", return_code)

    return_code, data = gatt_server.read_char_uuid_value(0x001A, 0x00FF)
    error_check(not data, f"gatt_server.read_char_uuid_value(0x001A, 0x00FF)", return_code)