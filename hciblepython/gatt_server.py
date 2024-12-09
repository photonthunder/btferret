#!/usr/bin/env python3
from gatt_enum import APPEARANCE, ATTCode, ATTR, CCCD, KEY_CHAR
from gatt_enum import KEY_SERVICE, PERM_FLAGS, PROP_FLAGS, UUID_TYPE
import byte_utils as bu
import logging
import time
import bisect
import threading
import struct

class GattHandles:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.min_handle = 0x0000
        self.max_handle = 0xFFFF
        self.start_handle = 0x0003
        self.next_handle = self.start_handle
        self.end_handle = self.start_handle
        self.assigned_handles = []
        self.one_loop = False

    def set_start_handle(self, start_handle):
        if start_handle < self.min_handle or start_handle > self.end_handle:
            print(f"Error: start_handle 0x{start_handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.end_handle:04X}.")
            return False
        self.start_handle = start_handle
        return True

    def set_end_handle(self, end_handle):
        if end_handle < self.start_handle or end_handle > self.max_handle:
            print(f"Error: end_handle 0x{end_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.max_handle:04X}.")
            return False
        self.end_handle = end_handle
        return True

    def handle_available(self, handle):
        if handle in self.assigned_handles:
            return False
        elif handle < self.min_handle or handle > self.max_handle:
            print(f"Error: Handle 0x{handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.max_handle:04X}.")
            return False
        else:
            return True

    def get_new_handle(self, set_handle = None):
        if set_handle == None:
            new_handle = self.next_handle
            # print(f"New Handle 0x{new_handle:04X} allocating... 0x{self.end_handle:04X}")
            if self.handle_available(new_handle) == False:
                print(f"Error: New Handle 0x{new_handle:04X} Already allocated")
                return None
            if new_handle < self.start_handle or new_handle > (self.end_handle + 1):
                print(f"Error: new_handle 0x{new_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.end_handle+1:04X}.")
                return None
        else:
            if self.handle_available(set_handle):
                if set_handle < self.start_handle and set_handle > self.min_handle:
                    self.start_handle = set_handle
                if set_handle > self.end_handle and set_handle < self.max_handle:
                    self.end_handle = set_handle
                if set_handle == self.next_handle:
                    new_handle = set_handle
                else:
                    bisect.insort(self.assigned_handles, set_handle)
                    # print(f"Set Handle 0x{new_handle:04X}")
                    return new_handle

        next_handle = new_handle + 1
        while next_handle <= self.max_handle:
            if self.handle_available(next_handle) == True:
                self.next_handle = next_handle
                self.set_end_handle(new_handle)
                bisect.insort(self.assigned_handles, new_handle)
                # print(f"New Handle 0x{self.start_handle:04X} 0x{new_handle:04X} 0x{self.next_handle:04X} 0x{self.end_handle:04X} Allocated")
                return new_handle
            else:
                next_handle += 1
                if next_handle > self.max_handle:
                    if self.one_loop == False:
                        next_handle = self.min_handle
                        self.one_loop = True
                    else:
                        print("Error: Looped through all handles, non available")
                        return None
        print(f"Error: No handles available: next_handle 0x{next_handle:04X} > 0x{self.max_handle:04X}.")
        return None

    def remove_handle(self, handle):
        if handle in self.assigned_handles:
            self.assigned_handles.remove(handle)
            return True
        else:
            print(f"Warning: Handle 0x{handle:04X} not assigned.")
            return False

    def print_string(self):
        return (
            f"\nHandles:\nMin = 0x{self.min_handle:04X}, Max = 0x{self.max_handle:04X}\n"
            f"Start = 0x{self.start_handle:04X}, End = 0x{self.end_handle:04X}\n"
        )

class Characteristic:
    def __init__(
        self,
        uuid,
        uuid_type,
        properties,
        value,
        cd_handle = None,
        value_handle = None,
        permissions = None,
        constant = False,
        fixed_length = False,
        length = None
    ):
        self._value = None
        self.callback = None

        self.gatt_handles = GattHandles()
        self.uuid = uuid
        self.uuid_type = uuid_type
        self.properties = properties or []
        self.value = value
        self.cd_handle = cd_handle
        self.value_handle = value_handle

        self.descr_handle = None
        self.descr_uuid = None
        self.descr_uuid_type = None
        self.descr_value = None
        self.notification = False
        self.indication = False
        self.wait_indication_ack = False
        self.value_updated = False
        
        self.permissions = permissions or []
        self.constant = constant
        self.fixed_length = fixed_length
        self.length = length

        self.set_handles()
        self.need_descriptor()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if self._value != new_value:
            self._value = new_value
            if self.callback:
                self.callback(new_value)

    def set_handles(self):
        if self.cd_handle == None:
            self.cd_handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(self.cd_handle)

        # print(f"CD handle = {self.cd_handle}")
                
        if self.value_handle == None:
            self.value_handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(self.value_handle)
        # print(f"value handle = {self.value_handle}")

    def properties_byte(self):
        return bu.from_u8(sum(prop.value for prop in self.properties))

    def need_descriptor(self):
        if any(flag in self.properties for flag in [PROP_FLAGS["NOTIFY"], PROP_FLAGS["INDICATE"]]):
            self.add_descriptor(ATTR.CLIENT_CHAR_CONFIG.value, CCCD.DISABLED)

    def add_descriptor(self, uuid, value, handle = None):
        if handle == None:
            handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(handle)

        if check_uuid(uuid) != UUID_TYPE.UUID_16BIT:
            print(f"Error: Descriptor has bad uuid {uuid}")
            return False
        self.descr_uuid_type = UUID_TYPE.UUID_16BIT
        self.descr_handle = handle
        self.descr_uuid = uuid
        self.set_descr_value(value)
        return True

    def remove_descriptor(self, uuid):
        self.descr_handle = None
        self.descr_uuid = None
        self.descr_value = None
        self.descr_uuid_type = None

    def set_descr_value(self, cccd_value):
        if cccd_value == CCCD.NOTIFICATION.value:
            self.notification = True
        elif cccd_value == CCCD.INDICATION.value:
            self.indication = True
        elif cccd_value == CCCD.DISABLED.value:
            self.clear_notif_indic()
        else:
            print(f"Error, invalid value {cccd_value} for descriptor")
            return ATTCode.VALUE_NOT_ALLOWED
        self.descr_value = bu.from_u16(cccd_value)
        return ATTCode.SUCCESS


    def clear_notif_indic(self):
        self.notification = False
        self.indication = False

    def get_value_server(self):
        return self.value
        
    def set_value_server(self, value):
        self.value = value
        self.value_updated = True

    def set_value_client(self, handle, value):
        if not isinstance(value, bytes):
            print("Error: Value must be a binary string (bytes).")
            return ATTCode.VALUE_NOT_ALLOWED
        if handle == self.value_handle:
            if any(flag in self.properties for flag in (PROP_FLAGS.WRITE_WITHOUT_RESPONSE, PROP_FLAGS.WRITE)):
                self.value = value
                return ATTCode.SUCCESS
            else:
                print("Error: Write not allowed")
                return ATTCode.WRITE_NOT_PERMITTED
        if handle == self.cd_handle:
            print("Error: Can't write to Character Decleration")
            return ATTCode.WRITE_NOT_PERMITTED
        if self.descr_handle == handle:
            cccd_value = bu.to_u16(value, 0)
            return self.set_descr_value(cccd_value)
        print(f"Error: Handle 0x{handle:04X} not matched")
        return ATTCode.INVALID_HANDLE

    def get_value(self, handle):
        # print(handle, self.cd_handle, self.value_handle, self.descr_handle)
        if handle == self.value_handle:
            if PROP_FLAGS.READ in self.properties:
                return ATTCode.SUCCESS, self.value
            else:
                print("Error: Read not allowed")
                return ATTCode.READ_NOT_PERMITTED
        if handle == self.cd_handle:
            return_bytes = bytes()
            return_bytes += self.properties_byte()
            return_bytes += bu.from_u16(self.value_handle)
            return_bytes += bu.from_uuid(self.uuid)
            return ATTCode.SUCCESS, return_bytes
        if self.descr_handle == handle:
                return ATTCode.SUCCESS, self.descr_value
        return ATTCode.INVALID_HANDLE, None

    def __repr__(self):
        return f"<Characteristic (uuid={self.uuid})>"

    def print_string(self):
        properties_str = ", ".join(prop.name for prop in self.properties) if self.properties else "None"
        const_str = "CONSTANT" if self.constant else "VARIABLE"
        vh_str = f"VH = 0x{self.value_handle:04X}" if self.value_handle else "VH = Not Assigned"
        uuid = self.descr_uuid
        value = self.descr_value
        handle = self.descr_handle
        if uuid == None or value == None or handle == None:
            descriptors_str = ""
        else:
            descriptors_str = f"\n0x{handle:04X}: Descriptor, UUID: {uuid}, Value: {value!r}"

        return (
            f"\n0x{self.cd_handle:04X}: Characteristic Declaration, UUID: {self.uuid}, Properties: [{properties_str}], {const_str}, {vh_str}"
            f"\n0x{self.value_handle:04X}: Characteristic Value, UUID: {self.uuid}, Value: {self.value!r}"
            f"{descriptors_str}"
        )

class Service:
    def __init__(self,
        uuid,
        uuid_type,
        name = None,
        handle = None,
        primary = True,
        notify_callback = None
        ):
        self.gatt_handles = GattHandles()
        self.uuid = uuid
        self.uuid_type = uuid_type
        self.primary = primary
        self.name = name or 'Unnamed Service'
        self.handle = handle
        self.notify_callback = notify_callback
        self.characteristics = {}
        self.set_handle()

    def set_handle(self):
        if self.handle == None:
            self.handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(self.handle)

    def add_characteristic(self, uuid, properties, value, **kwargs):
        uuid_type = check_uuid(uuid)
        if uuid_type is None:
            print(f"Error: Invalid char uuid {uuid}")
            return None
        char_inst = Characteristic(uuid, uuid_type, properties, value, **kwargs)
        if char_inst is not None:
            self.characteristics[char_inst.cd_handle] = char_inst
            self.characteristics = dict(sorted(self.characteristics.items()))
            if self.notify_callback:
                    self.notify_callback()
        return char_inst

    def remove_char_uuid(self, uuid):
        for handle, char_inst in self.characteristics.items():
            if char_inst.uuid == uuid:
                return self.remove_char_handle(handle)
        return False

    def remove_char_handle(self, handle):
        if handle in self.characteristics:
            del self.characteristics[handle]
            return True
        return False

    def get_char_uuid(self, uuid):
        for handle, char_inst in self.characteristics.items():
            if char_inst.uuid == uuid:
                return char_inst
        return None

    def get_char_handle(self, handle):
        return self.characteristics.get(handle)

    def __repr__(self):
        return f"<Service (uuid={self.uuid})>"

    def print_string(self):
        if self.primary:
            service_type = "Primary Service"
        else:
            service_type = "Secondary Service"
        service_str = f"\n\n0x{self.handle:04X}: {service_type}: UUID={self.uuid}, Name={self.name}"
        characteristics_str = ""
        for ch in self.characteristics.values():
            characteristics_str += ch.print_string()
        return service_str + characteristics_str

class GattServer:
    def __init__(self, device_name):
        self.gatt_handles = GattHandles()
        self.device_name = device_name
        self.services = {}
        self.indication_ack_inst = None
        self.indication_sent_time = time.time()
        self.indication_timeout = 30  #seconds
        self.initial_add = False
        
        self.set_base_services()
        
    def get_service_change_range(self):
        if self.initial_add == False:
            return None
        service_change_bytes = struct.pack("<HH",self.gatt_handles.start_handle, self.gatt_handles.end_handle)
        self.gen_att_char_2A05.value = service_change_bytes
        # self.set_char_value_uuid(KEY_SERVICE.GENERIC_ATTRIBUTE.value, KEY_CHAR.SERVICE_CHANGED.value, service_change_bytes)
        # print(service_change_bytes)
        return service_change_bytes

    def on_add_char(self):
        self.get_service_change_range()

    def create_pnp_id(self, vendor_id_source = 0x01, vendor_id = 0x1234, product_id = 0x0203, product_version = 0x0001):
        # vendor_id_source = 0x01   # Bluetooth SIG
        # vendor_id = 0x1234        # Any value you want since we are not official
        # product_id = 0x0203       # Product ID
        # product_version = 0x0001  # Product Version

        if not (0 <= vendor_id_source <= 0xFF):
            print("Error: Vendor ID Source must be a 1-byte value (0-255).")
            return None
        if not (0 <= vendor_id <= 0xFFFF):
            print("Error: Vendor ID must be a 2-byte value (0-65535).")
            return None
        if not (0 <= product_id <= 0xFFFF):
            print("Error: Product ID must be a 2-byte value (0-65535).")
            return None
        if not (0 <= product_version <= 0xFFFF):
            print("Error: Product Version must be a 2-byte value (0-65535).")
            return None

        pnp_id = struct.pack(
            "<BHHH",
            vendor_id_source,    # 1 byte for Vendor ID Source
            vendor_id,           # 2 bytes for Vendor ID (little-endian)
            product_id,          # 2 bytes for Product ID (little-endian)
            product_version      # 2 bytes for Product Version (little-endian)
        )
        return pnp_id

    def set_base_services(self):
        self.generic_access = self.add_service(uuid=KEY_SERVICE.GENERIC_ACCESS.value, name="Generic Access")
        self.gen_acc_char_2A00 = self.generic_access.add_characteristic(
            uuid=KEY_CHAR.DEVICE_NAME.value,
            properties=[PROP_FLAGS.READ],
            value=self.device_name.encode('utf-8'),
            constant=True
        )
        self.gen_acc_char_2A01 = self.generic_access.add_characteristic(
            uuid=KEY_CHAR.APPEARANCE.value,
            properties=[PROP_FLAGS.READ],
            value=bu.from_u16(APPEARANCE.MINI_PC),
            constant=True
        )
        self.generic_attribute = self.add_service(uuid=KEY_SERVICE.GENERIC_ATTRIBUTE.value, name="Generic Attribute")
        self.gen_att_char_2A05 = self.generic_attribute.add_characteristic(
            uuid=KEY_CHAR.SERVICE_CHANGED.value,
            properties=[PROP_FLAGS.INDICATE],
            value=b'\x00\x00\x00\x00',
            fixed_length = True,
            length = 4
        )
        self.device_information = self.add_service(uuid=KEY_SERVICE.DEVICE_INFORMATION.value, name="Device Information")
        self.dev_inf_char_2A50 = self.device_information.add_characteristic(
            uuid=KEY_CHAR.PNP_ID.value,
            properties=[PROP_FLAGS.READ],
            value=self.create_pnp_id(),
            cd_handle = 0x000D,
            constant = True
        )
        self.initial_add = True
        self.get_service_change_range()

    def get_char_inst_handle(self, handle):
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if char_inst.cd_handle == handle or char_inst.value_handle == handle or char_inst.descr_handle == handle:
                    return char_inst
        return None

    def add_service(self, uuid, name = None, handle = None, primary = True):
        uuid_type = check_uuid(uuid)
        if uuid_type is None:
            print(f"Error: Invalid service uuid {uuid}")
            return None
        service = Service(uuid, uuid_type, name, handle, primary, self.on_add_char)
        self.services[service.handle] = service
        self.services = dict(sorted(self.services.items()))
        self.get_service_change_range()
        return service

    def remove_service_uuid(self, uuid):
        for handle, service in self.services.items():
            if service.uuid == uuid:
                return self.remove_service_handle(handle)
        return False

    def remove_service_handle(self, handle):
        if handle in self.services:
            service = self.services[handle]
            del self.services[handle]
            return True
        return False

    def get_service_uuid(self, uuid):
        for handle, service in self.services.items():
            if service.uuid == uuid:
                return self.get_service_handle(handle)
        return None

    def get_service_handle(self, handle):
        return self.services.get(handle)

    def get_char_value_handle(self, handle):
        char_inst = self.get_char_inst_handle(handle)
        if char_inst is not None:
            return char_inst.get_value(handle)
        else:
            print(f"Error: Handle 0x{handle:04X} not attached to char")
            return ATTCode.INVALID_HANDLE, None
        
    def set_char_value_handle(self, handle, new_value):
        char_inst = self.get_char_inst_handle(handle)
        if char_inst is not None:
            return char_inst.set_value_client(handle, new_value)
        else:
            print(f"Error: Handle 0x{handle:04X} not attached to char")
            return ATTCode.INVALID_HANDLE

    def clear_connection_settings(self):
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if char_inst.uuid == ATTR.CLIENT_CHAR_CONFIG:
                    char_inst.set_descr_value(CCCD.DISABLED)
                
    def get_notification(self):
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if char_inst.notification == True and char_inst.value_updated == True:
                    char_inst.value_updated = False
                    return True, char_inst.value_handle, char_inst.value
        return False, None, None

    def check_indication_timeout(self):
        if (time.time() - self.indication_sent_time) > self.indication_timeout:
            return True
        else:
            return False

    def get_indication(self):
        if self.indication_ack_inst is not None:
            if self.check_indication_timeout() == False:
                return False, None, None
            else:
                print(f"Warning: No indication ack received in {self.indication_timeout} seconds")
                self.indication_ack_inst.wait_indication_ack = False
                self.indication_ack_inst = None
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if char_inst.indication == True and char_inst.value_updated == True and char_inst.wait_indication_ack == False:
                    self.indication_ack_inst = char_inst
                    char_inst.wait_indication_ack = True
                    char_inst.value_updated = False
                    self.indication_sent_time = time.time()
                    return True, char_inst.value_handle, char_inst.value
        return False, None, None

    def indication_ack_received(self):
        self.indication_ack_inst.wait_indication_ack = False
        self.indication_ack_inst = None

    def find_information(self, start_handle, end_handle):
        return_bytes = bytes()
        uuid_type = None
        for handle in range(start_handle, end_handle + 1):
            for service_handle, service in self.services.items():
                for char_handle, char_inst in service.characteristics.items():
                    if char_inst.cd_handle == handle:
                        if uuid_type is None:
                            uuid_type = char_inst.uuid_type
                            return_bytes += bu.from_u8(uuid_type)
                        if uuid_type == char_inst.uuid_type:
                            return_bytes += bu.from_u16(handle)
                            return_bytes += bu.from_uuid(char_inst.uuid)
                        else:
                            return ATTCode.SUCCESS, return_bytes
                    if char_inst.descr_handle == handle:
                        if uuid_type is None:
                            uuid_type = char_inst.descr_uuid_type
                            return_bytes += bu.from_u8(uuid_type)
                        if uuid_type == char_inst.descr_uuid_type:
                            return_bytes += bu.from_u16(handle)
                            return_bytes += bu.from_uuid(char_inst.descr_uuid)
                        else:
                            return ATTCode.SUCCESS, return_bytes
        if uuid_type is not None:
            return ATTCode.SUCCESS, return_bytes
        else:
            return ATTCode.ATTRIBUTE_NOT_FOUND, None

    def find_by_value(self, start_handle, end_handle, att_uuid, att_value):
        return_bytes = bytes()
        test_uuid = bu.to_uuid(att_value, 0)
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if start_handle <= char_handle <= end_handle:
                    if att_uuid == ATTR.PRIMARY_SERVICE.value:
                        if service.uuid == test_uuid:
                            return_bytes += bu.from_u16(service_handle)
                            group_end_handle = service_handle
                            for char_handle, char_inst in service.characteristics.items():
                                group_end_handle = char_inst.value_handle
                            return_bytes += bu.from_u16(group_end_handle)
                            return ATTCode.SUCCESS, return_bytes
                        else:
                            print(f"Error, ATTR {att_uuid} not implemented in find by value")
                            return ATTCode.REQUEST_NOT_SUPPORTED, None
        print(f"Warning, No Primary Service attribute {att_value} found")
        return ATTCode.ATTRIBUTE_NOT_FOUND, None

    def read_by_type(self, start_handle, end_handle, att_uuid):
        return_bytes = bytes()
        for service_handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if start_handle <= char_handle <= end_handle:
                    if att_uuid == ATTR.CHARACTERISTIC.value:
                        return_bytes += bu.from_u16(char_inst.cd_handle)
                        return_bytes += char_inst.properties_byte()
                        # if char_inst.descr_handle != None:
                        #     return_bytes += bu.from_u16(char_inst.descr_handle)
                        # else:
                        #     return_bytes += bu.from_u16(char_inst.value_handle)
                        return_bytes += bu.from_u16(char_inst.value_handle)
                        return_bytes += bu.from_uuid(char_inst.uuid)
                        len_bytes = bu.from_u8(len(return_bytes))
                        return_bytes = len_bytes + return_bytes
                        return ATTCode.SUCCESS, return_bytes
                    elif att_uuid == char_inst.uuid:
                            return_bytes += bu.from_u16(char_inst.value_handle)
                            return_bytes += char_inst.value
                            len_bytes = bu.from_u8(len(return_bytes))
                            return_bytes = len_bytes + return_bytes
                            return ATTCode.SUCCESS, return_bytes
                    else:
                        print(f"Error, ATTR {att_uuid} not implemented in read by value")
                        return ATTCode.REQUEST_NOT_SUPPORTED, None
        print(f"Warning, No Char attribute {att_uuid} found")
        return ATTCode.ATTRIBUTE_NOT_FOUND, None

    def get_service_handle_range(self, att_uuid, start_handle, end_handle):
        return_bytes = bytes()
        for service_handle, service in self.services.items():
            if start_handle <= service_handle <= end_handle:
                if att_uuid == ATTR.PRIMARY_SERVICE.value:
                    return_bytes += bu.from_u16(service_handle)
                    last_char_handle, last_char_inst = next(reversed(service.characteristics.items()))
                    if last_char_inst.descr_handle is not None:
                        last_handle = last_char_inst.descr_handle
                    else:
                        last_handle = last_char_inst.value_handle
                    if end_handle < last_handle:
                        last_handle = end_handle
                    return_bytes += bu.from_u16(last_handle)
                    return_bytes += bu.from_uuid(service.uuid)
                    len_bytes = bu.from_u8(len(return_bytes))
                    return_bytes = len_bytes + return_bytes
                    print(f"Primary Service {service.uuid}: 0x{service_handle:04X} to 0x{last_handle:04X}")
                    return ATTCode.SUCCESS, return_bytes
                else:
                    print(f"Error, ATTR {att_uuid} not implemented in service handle range")
                    return ATTCode.REQUEST_NOT_SUPPORTED, None
        print(f"No Service Handle in range 0x{start_handle:04X} to 0x{end_handle:04X}")
        return ATTCode.ATTRIBUTE_NOT_FOUND, None

    def print_string(self):
        gatt_print = "\nGatt Server:"
        services_str = ""
        for service in self.services.values():
            services_str += service.print_string()
        return gatt_print + services_str

if __name__ == "__main__":
    device_name = "MyDevice"
    gatt_server = GattServer(device_name)
    custom_service = gatt_server.add_service('11223344-5566-7788-99AA-BBCCDDEEFF00', name="My Custom Service")
    custom_service.add_characteristic(
        uuid="ABCD",
        properties=[PROP_FLAGS.READ, PROP_FLAGS.WRITE_WITHOUT_RESPONSE],
        value=b'ENTER'[::-1]
    )
    custom_service.add_characteristic(
        uuid="CDEF",
        properties=[PROP_FLAGS.READ, PROP_FLAGS.NOTIFY, PROP_FLAGS.WRITE_WITHOUT_RESPONSE],
        value=b'0'[::-1]
    )
    custom_service.add_characteristic(
        uuid="DEAF",
        properties=[PROP_FLAGS.READ, PROP_FLAGS.INDICATE],
        value=b'210'[::-1]
    )
    custom_service.add_characteristic(
        uuid="DCBA",
        properties=[PROP_FLAGS.READ, PROP_FLAGS.NOTIFY],
        value=b'SET CNT'[::-1]
    )


    print(gatt_server.print_string())

    # uuid = '11223344-5566-7788-99AA-BBCCDDEEFF00'
    # uuid = '1801'

    # if gatt_server.remove_service_uuid(uuid) == True:
    #     print(gatt_server.print_string())
    # else:
    #     print("No service found to remove")

    # uuid_char = 'CDEF'

    # if custom_service.remove_char_uuid(uuid_char) == True:
    #     print(gatt_server.print_string())
    # else:
    #     print("No char found to remove")

    # temp_service = gatt_server.get_service_uuid(uuid)
    # if temp_service:
    #     print(temp_service.uuid, temp_service.handle)
    #     temp_char = temp_service.get_char_uuid(uuid_char)
    #     if temp_char:
    #         print(temp_char.uuid, temp_char.cd_handle)

    # print(uuid)
    # result = bu.from_uuid(uuid)
    # print(result)
    # result = bu.to_uuid(result)
    # print(result)

    # print(gatt_server.gatt_handles.print_string())

    # new_value = b'awesome'[::-1]
    # service_uuid = '11223344-5566-7788-99AA-BBCCDDEEFF00'
    # char_uuid = 'ABCD'
    # for handle in range(0x000F, 0x001A):
    #     value = gatt_server.get_char_value_handle(handle)
    #     print(f"0x{handle:04X} -> value {value}")

    # new_value = b'great'[::-1]
    # handle = 0x0011
    # value = gatt_server.get_char_value_handle(handle)
    # print(f"0x{handle:04X} -> value {value}")
    # return_code = gatt_server.set_char_value_handle(handle, new_value)
    # if return_code != ATTCode.SUCCESS:
    #     print(return_code)
    # value = gatt_server.get_char_value_handle(handle)
    # print(f"0x{handle:04X} -> value {value}")
    # new_value = b'power'[::-1]

    