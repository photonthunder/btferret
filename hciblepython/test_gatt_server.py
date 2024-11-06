#!/usr/bin/env python3

class GattServer:
    def __init__(self):
        self.gatt_table = None
        self.getTestTable()

    def getTestTable(self):
        self.gatt_table = {
            # Generic Access Service (0x1800)
            0x0003: {"type": "primary_service", "uuid": "1800", "value": None},
            0x0004: {"type": "characteristic_declaration", "uuid": "2A00", "properties": "read", "value_handle": 0x0005},
            0x0005: {"type": "characteristic_value", "uuid": "2A00", "value": "MyDevice"},  # Device Name
            0x0006: {"type": "characteristic_declaration", "uuid": "2A01", "properties": "read", "value_handle": 0x0007},
            0x0007: {"type": "characteristic_value", "uuid": "2A01", "value": "0000"},  # Appearance

            # Generic Attribute Service (0x1801)
            0x0008: {"type": "primary_service", "uuid": "1801", "value": None},
            0x0009: {"type": "characteristic_declaration", "uuid": "2A05", "properties": "indicate", "value_handle": 0x000A},
            0x000A: {"type": "characteristic_value", "uuid": "2A05", "value": None},  # Service Changed
            0x000B: {"type": "descriptor", "uuid": "2902", "value": None},

            # Device Information Service (0x180A)
            0x000C: {"type": "primary_service", "uuid": "180A", "value": None},
            0x000D: {"type": "characteristic_declaration", "uuid": "2A50", "properties": "read", "value_handle": 0x000E},
            0x000E: {"type": "characteristic_value", "uuid": "2A50", "value": "1234-5678-9012"},  # PnP ID

            # Custom Service (11223344-5566-7788-99AA-BBCCDDEEFF00)
            0x000F: {"type": "primary_service", "uuid": "11223344-5566-7788-99AA-BBCCDDEEFF00", "value": None},
            0x0010: {"type": "characteristic_declaration", "uuid": "ABCD", "properties": "read|write", "value_handle": 0x0011},
            0x0011: {"type": "characteristic_value", "uuid": "ABCD", "value": "Initial Control"},  # Control characteristic
            0x0012: {"type": "characteristic_declaration", "uuid": "CDEF", "properties": "read|notify", "value_handle": 0x0013},
            0x0013: {"type": "characteristic_value", "uuid": "CDEF", "value": "Counter Data"},  # Counter characteristic
            0x0014: {"type": "descriptor", "uuid": "2902", "value": None},
            0x0015: {"type": "characteristic_declaration", "uuid": "DEAF", "properties": "read|notify", "value_handle": 0x0016},
            0x0016: {"type": "characteristic_value", "uuid": "DEAF", "value": "Sensor Data"},  # Data characteristic
            0x0017: {"type": "descriptor", "uuid": "2902", "value": None},
            0x0018: {"type": "characteristic_declaration", "uuid": "DCBA", "properties": "read|notify", "value_handle": 0x0019},
            0x0019: {"type": "characteristic_value", "uuid": "DCBA", "value": "Response Data"},  # Response characteristic
            0x001A: {"type": "descriptor", "uuid": "2902", "value": None},
        }

    def char_prop_to_byte(self, properties):
        prop_flags = {
            "broadcast": 0x01,
            "read": 0x02,
            "write_without_response": 0x04,
            "write": 0x08,
            "notify": 0x10,
            "indicate": 0x20,
            "authenticated_signed_writes": 0x40,
            "extended_properties": 0x80,
        }

        prop_byte = 0x00
        for prop in properties.split():
            if prop in prop_flags:
                prop_byte |= prop_flags[prop]

        return prop_byte

    def get_uuid_byte_length(self, uuid):
        cleaned_uuid = uuid.replace('-', '')
        return int(len(cleaned_uuid)/2)

    def uuid_string_to_bytes(self, uuid):
        cleaned_uuid = uuid.replace('-', '')
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
                print(handle, attr)
                properties = attr.get("properties")
                prop_byte = self.char_prop_to_byte(properties)
                value_handle = attr.get("value_handle")
                uuid = attr.get("uuid")
                uuid_bytes = self.uuid_string_to_bytes(uuid)
                characteristics.append((prop_byte, value_handle, uuid_bytes))
        return characteristics


    def add_service(self, handle, service_type, uuid, value=None):
        self.gatt_table[handle] = {"type": service_type, "uuid": uuid, "value": value}

    def get_service_handle_range(self, start_handle):
        first_handle = None
        last_handle = None
        primary_service = None
        in_service = False
        
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
        if first_handle is None:
            print("No primary service found starting at handle 0x{:X}.".format(start_handle))
            return None, None, ""
        return (first_handle, last_handle, primary_service)


if __name__ == "__main__":
    gatt_server = GattServer()
    first, last, primary = gatt_server.get_service_handle_range(0x000C)
    print("First Handle = 0x{:X}, Second Handle = 0x{:X}, Primary = {}".format(first, last, primary))
    print(gatt_server.get_uuid_byte_length(primary))
    uuid_bytes = gatt_server.uuid_string_to_bytes("2A50")
    print(uuid_bytes)
    print (gatt_server.uuid_bytes_to_string(uuid_bytes))
    uuid_bytes = gatt_server.uuid_string_to_bytes("11223344-5566-7788-99AA-BBCCDDEEFF00")
    print(uuid_bytes)
    print (gatt_server.uuid_bytes_to_string(uuid_bytes))
    print(gatt_server.read_uuid_value(0x0003, 0x007, "2A00"))
    print(gatt_server.read_char_uuid_value(0x000E, 0x0016))