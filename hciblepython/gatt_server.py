#!/usr/bin/env python3
from ble_enum import ATTCode
from gatt_enum import APPEARANCE, ATTR, CCCD, KEY_CHAR
from gatt_enum import KEY_SERVICE, PERM_FLAGS, PROP_FLAGS
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
        # print(f"End Handle 0x{self.end_handle:04X}")
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
        properties,
        value,
        cd_handle = None,
        value_handle = None,
        permissions = None,
        constant = False,
        fixed_length = False,
        length = None
    ):
        self.gatt_handles = GattHandles()
        self.uuid = uuid
        self.properties = properties or []
        self.value = value
        self.cd_handle = cd_handle
        self.value_handle = value_handle

        self.descriptors = []
        # self.descriptor = {"handle": None, "uuid": None, "value": None}
        # self.descr_handle = self.descriptor.get("handle")
        # self.descr_uuid = self.descriptor.get("uuid")
        # self.descr_value = self.descriptor.get("value")
        
        self.permissions = permissions or []
        self.constant = constant
        self.fixed_length = fixed_length
        self.length = length

        self.set_handles()
        self.need_descriptor()

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

    def check_descriptor(self, descr_value):
        if descr_value not in CCCD:
            print(f"Error: Description Value 0x{descr_value:04X} not in PROP_FLAGS")
            return False
        else:
            return True

    def need_descriptor(self):
        if any(flag in self.properties for flag in [PROP_FLAGS["NOTIFY"], PROP_FLAGS["INDICATE"]]):
            self.add_descriptor(ATTR.CLIENT_CHAR_CONFIG.value, CCCD.DISABLED)

    def add_descriptor(self, uuid, value, handle = None):
        if handle == None:
            handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(handle)
        descriptor = {}
        descriptor["handle"] = handle

        if value == None or self.check_descriptor(value) == False:
            value = CCCD.DISABLED
        descriptor["value"] = bu.from_u16(value)
        bu.check_uuid(uuid)
        descriptor["uuid"] = uuid
        self.descriptors.append(descriptor)

    def remove_descriptor(self, uuid):
        for descriptor in self.descriptors:
            if uuid == descriptor["uuid"]:
                del self.descriptors[uuid]
                return True
        print(f"Warning: uuid {uuid} not in descriptors")
        return False

    def set_value(self, value):
        if not isinstance(value, bytes):
            print("Error: Value must be a binary string (bytes).")
            return False
        self.value = value
        return True

    def get_value(self):
        return self.value

    def __repr__(self):
        return f"<Characteristic (uuid={self.uuid})>"

    def print_string(self):
        properties_str = ", ".join(prop.name for prop in self.properties) if self.properties else "None"
        const_str = "CONSTANT" if self.constant else "VARIABLE"
        vh_str = f"VH = 0x{self.value_handle:04X}" if self.value_handle else "VH = Not Assigned"
        descriptors_str = ""
        for descriptor in self.descriptors:
            uuid = descriptor.get("uuid")
            value = descriptor.get("value")
            handle = descriptor.get("handle")
            descriptors_str += f"\n0x{handle:04X}: Descriptor, UUID: {uuid}, Value: {value!r}"

        return (
            f"\n0x{self.cd_handle:04X}: Characteristic Declaration, UUID: {self.uuid}, Properties: [{properties_str}], {const_str}, {vh_str}"
            f"\n0x{self.value_handle:04X}: Characteristic Value, UUID: {self.uuid}, Value: {self.value!r}"
            f"{descriptors_str}"
        )

class Service:
    def __init__(self,
        uuid,
        name = None,
        handle = None,
        primary = True,
        notify_callback = None
        ):
        self.gatt_handles = GattHandles()
        self.uuid = uuid
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
        if bu.check_uuid(uuid) == False:
            print(f"Error: Invalid char uuid {uuid}")
            return False
        char_inst = Characteristic(uuid, properties, value, **kwargs)
        self.characteristics[char_inst.cd_handle] = char_inst
        if self.notify_callback:
            self.notify_callback(char_inst.cd_handle, char_inst)
            self.notify_callback(char_inst.value_handle, char_inst)
            for descriptor in char_inst.descriptors:
                self.notify_callback(descriptor["handle"], char_inst)
        return True

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
                return self.get_char_handle(handle)
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
        self.all_char = {}
        self.primary_service_handles = []
        self.secondary_service_handles = []
        self.set_base_services()

    def add_global_char(self, handle, char_inst):
        self.all_char[handle] = char_inst

    def get_service_change_range(self):
        service_change_bytes = struct.pack("<HH",self.gatt_handles.start_handle, self.gatt_handles.end_handle)
        self.change_char_value_uuid(KEY_SERVICE.GENERIC_ATTRIBUTE.value, KEY_CHAR.SERVICE_CHANGED.value, service_change_bytes)
        # print(service_change_bytes)
        return service_change_bytes

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

    def on_add_char(self, handle, char_inst):
        self.add_global_char(handle, char_inst)
        self.get_service_change_range()

    def set_base_services(self):
        generic_access = self.add_service(uuid=KEY_SERVICE.GENERIC_ACCESS.value, name="Generic Access")
        generic_access.add_characteristic(
            uuid=KEY_CHAR.DEVICE_NAME.value,
            properties=[PROP_FLAGS.READ],
            value=self.device_name,
            constant=True
        )
        generic_access.add_characteristic(
            uuid=KEY_CHAR.APPEARANCE.value,
            properties=[PROP_FLAGS.READ],
            value=bu.from_u16(APPEARANCE.MINI_PC),
            constant=True
        )
        generic_attribute = self.add_service(uuid=KEY_SERVICE.GENERIC_ATTRIBUTE.value, name="Generic Attribute")
        generic_attribute.add_characteristic(
            uuid=KEY_CHAR.SERVICE_CHANGED.value,
            properties=[PROP_FLAGS.INDICATE],
            value=b'\x00\x00\x00\x00',
            fixed_length = True,
            length = 4
        )
        device_information = self.add_service(uuid=KEY_SERVICE.DEVICE_INFORMATION.value, name="Device Information")
        device_information.add_characteristic(
            uuid=KEY_CHAR.PNP_ID.value,
            properties=[PROP_FLAGS.READ],
            value=self.create_pnp_id(),
            cd_handle = 0x000D,
            constant = True
        )
        self.get_service_change_range()

    def get_char_value_uuid(self, service_uuid, char_uuid):
        for handle, service in self.services.items():
            if service.uuid == service_uuid:
                # print(f"Service Match {service_uuid}")
                for handle, char in service.characteristics.items():
                    if char.uuid == char_uuid:
                        # print(f"Char Match {char_uuid}")
                        return ATTCode.SUCCESS, char.value
        return ATTCODE.ATTRIBUTE_NOT_FOUND, None
        

    # def change_char_value_handle(self, handle, new_value):
    #     if self.gatt_handles.handle_available(handle) == True:
    #         print("Error: Handle 0x{handle:04X} not set")
    #         return ATTCode.INVALID_HANDLE
    #     if handle in self.services:

    def change_char_value_uuid(self, service_uuid, char_uuid, new_value):
        for handle, service in self.services.items():
            if service.uuid == service_uuid:
                # print(f"Service Match {service_uuid}")
                for handle, char in service.characteristics.items():
                    if char.uuid == char_uuid:
                        # print(f"Char Match {char_uuid}")
                        char.value = new_value

    def add_service(self, uuid, name = None, handle = None, primary = True):
        if bu.check_uuid(uuid) == False:
            print(f"Error: Invalid service uuid {uuid}")
            return None
        service = Service(uuid, name, handle, primary, self.on_add_char)
        self.services[service.handle] = service
        if primary == True:
            self.primary_service_handles.append(service.handle)
        else:
            self.secondary_service_handles.append(service.handle)
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
            if service.primary == True:
                self.primary_service_handles.remove(service.handle)
            else:
                self.secondary_service_handles.remove(service.handle)
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

    def clear_connection_settings(self):
        for handle, service in self.services.items():
            for char_handle, char_inst in service.characteristics.items():
                if char_inst.uuid == ATTR.CLIENT_CHAR_CONFIG:
                    char_inst.value = bu.from_u16(CCCD.DISABLED)

    def print_all_char_string(self):
        char_str = ""
        for handle, char_inst in self.all_char.items():
            char_str += f"\n0x{handle:04X} {char_inst}"
        return char_str
        
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

    # if custom_service.remove_char_uuid(uuid) == True:
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

    print(gatt_server.gatt_handles.print_string())
    print()
    print(gatt_server.print_all_char_string())
