import re 

class GattServer:
    def __init__(self):
        self.gatt_table = None
        self.getTestTable()

    def getTestTable(self):
        self.gatt_table = {
            # Primary Service: Generic Access (0x1800)
            0x0003: {"type": "primary_service", "uuid": "1800", "value": None},
            0x0004: {"type": "characteristic_declaration", "uuid": "2A00", "properties": "read", "value_handle": 0x0003},
            0x0005: {"type": "characteristic_value", "uuid": "2A00", "value": "MyDevice"},  # Device Name
            0x0006: {"type": "characteristic_declaration", "uuid": "2A01", "properties": "read", "value_handle": 0x0005},
            0x0007: {"type": "characteristic_value", "uuid": "2A01", "value": "0000"},  # Appearance

            # Primary Service: Generic Attribute (0x1801)
            0x0008: {"type": "primary_service", "uuid": "1801", "value": None},
            0x0009: {"type": "characteristic_declaration", "uuid": "2A05", "properties": "indicate", "value_handle": 0x0008},
            0x000A: {"type": "characteristic_value", "uuid": "2A05", "value": None},  # Service Changed

            # Primary Service: Device Information (0x180A)
            0x000B: {"type": "primary_service", "uuid": "180A", "value": None},
            0x000C: {"type": "characteristic_declaration", "uuid": "2A50", "properties": "read", "value_handle": 0x000B},
            0x000D: {"type": "characteristic_value", "uuid": "2A50", "value": "1234-5678-9012"},  # PnP ID

            # Custom Service (11223344-5566-7788-99AA-BBCCDDEEFF00)
            0x000E: {"type": "primary_service", "uuid": "11223344-5566-7788-99AA-BBCCDDEEFF00", "value": None},
            0x000F: {"type": "characteristic_declaration", "uuid": "ABCD", "properties": "read|write", "value_handle": 0x000E},
            0x0010: {"type": "characteristic_value", "uuid": "ABCD", "value": "Initial Control"},  # Control characteristic
            0x0011: {"type": "characteristic_declaration", "uuid": "CDEF", "properties": "read|notify", "value_handle": 0x0010},
            0x0012: {"type": "characteristic_value", "uuid": "CDEF", "value": "Counter Data"},  # Counter characteristic
            0x0013: {"type": "characteristic_declaration", "uuid": "DEAF", "properties": "read|notify", "value_handle": 0x0012},
            0x0014: {"type": "characteristic_value", "uuid": "DEAF", "value": "Sensor Data"},  # Data characteristic
            0x0015: {"type": "characteristic_declaration", "uuid": "DCBA", "properties": "read|notify", "value_handle": 0x0014},
            0x0016: {"type": "characteristic_value", "uuid": "DCBA", "value": "Response Data"},  # Response characteristic
        }

    def get_uuid_byte_length(self, uuid):
        cleaned_uuid = re.sub(r'[^0-9a-fA-F]', '', uuid)
        return int(len(cleaned_uuid)/2)

    def uuid_to_bytes(self, uuid):
        cleaned_uuid = re.sub(r'[^0-9a-fA-F]', '', uuid)
        length_uuid = len(cleaned_uuid)
        if length_uuid != 32 and length_uuid != 4:
            raise ValueError("Invalid UUID length {}, must be 128-bit (32 hex characters).".format(length_uuid))
        byte_pairs = [cleaned_uuid[i:i+2] for i in range(0, len(cleaned_uuid), 2)]
        little_endian_bytes = byte_pairs[::-1]
        little_endian_bytes = bytes(int(byte, 16) for byte in little_endian_bytes)
        return little_endian_bytes

    def add_service(self, handle, service_type, uuid, value=None):
        self.gatt_table[handle] = {"type": service_type, "uuid": uuid, "value": value}

    def get_service_handle_range(self, start_handle):
        first_handle = None
        last_handle = None
        primary_service = None
        in_service = False
        
        for handle in sorted(self.gatt_table.keys()):
            if handle < start_handle:
                continue  # Skip handles until we reach the start handle
            
            attribute = self.gatt_table[handle]
            
            if attribute["type"] == "primary_service":
                if in_service:
                    # If we find a new primary service, return the last handle of the previous service
                    return (first_handle, last_handle, primary_service)
                # Start of a new service
                first_handle = handle
                primary_service = attribute["uuid"]
                in_service = True
            
            if in_service:
                # Update the last handle as we iterate through the service
                last_handle = handle
        
        if first_handle is None:
            print("No primary service found starting at handle 0x{:X}.".format(start_handle))
            return None, None, ""
        
        # Return the first and last handle of the found service
        return (first_handle, last_handle, primary_service)


if __name__ == "__main__":
    gatt_server = GattServer()
    first, last, primary = gatt_server.get_service_handle_range(0x000C)
    print("First Handle = 0x{:X}, Second Handle = 0x{:X}, Primary = {}", first, last, primary)
    print(gatt_server.get_uuid_byte_length(primary))
    print(gatt_server.uuid_to_bytes("11223344-5566-7788-99AA-BBCCDDEEFF00"))