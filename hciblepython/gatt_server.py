#!/usr/bin/env python3
# from ble_enum import ATTErrorCode
from gatt_enum import APPEARANCE, ATTR, CCCD, KEY_CHAR
from gatt_enum import KEY_SERVICE, PERM_FLAGS, PROP_FLAGS
import byte_utils as bu
import logging
import time
import bisect
import threading

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
            raise ValueError(f"start_handle 0x{start_handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.end_handle:04X}.")
        self.start_handle = start_handle
        return True

    def set_end_handle(self, end_handle):
        if end_handle < self.start_handle or end_handle > self.max_handle:
            raise ValueError(f"end_handle 0x{end_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.max_handle:04X}.")
        self.end_handle = end_handle
        # print(f"End Handle 0x{self.end_handle:04X}")
        return True

    def handle_available(self, handle):
        if handle in self.assigned_handles:
            return False
        elif handle < self.min_handle or handle > self.max_handle:
            raise ValueError(f"Handle 0x{handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.max_handle:04X}.")
        else:
            return True

    def get_new_handle(self, set_handle = None):
        if set_handle == None:
            new_handle = self.next_handle
            # print(f"New Handle 0x{new_handle:04X} allocating... 0x{self.end_handle:04X}")
            if self.handle_available(new_handle) == False:
                raise ValueError(f"New Handle 0x{new_handle:04X} Already allocated")
            if new_handle < self.start_handle or new_handle > (self.end_handle + 1):
                raise ValueError(f"new_handle 0x{new_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.end_handle+1:04X}.")
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
                    return

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
                        raise ValueError("Looped through all handles, non available")
        raise ValueError(f"No handles available: next_handle 0x{next_handle:04X} > 0x{self.max_handle:04X}.")

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
        uuid: bytes,
        properties: list,
        value: bytes,
        cd_handle: int = None,
        value_handle: int = None,
        permissions: list = None,
        constant: bool = False,
        fixed_length: bool = False,
        length: int = None
    ):
        self.gatt_handles = GattHandles()
        self.uuid = uuid
        self.properties = properties or []
        self.value = value
        self.cd_handle = cd_handle
        self.value_handle = value_handle

        self.descriptors = []
        self.descriptor = {"handle": None, "uuid": None, "value": None}
        self.descr_handle = self.descriptor.get("handle")
        self.descr_uuid = self.descriptor.get("uuid")
        self.descr_value = self.descriptor.get("value")
        

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

    def check_uuid(self, uuid):
        print(f"Length = {len(uuid)}")
        return True

    def check_descriptor(self, descr_value):
        if descr_value not in CCCD:
            raise ValueError(f"Description Value 0x{descr_value:04X} not in PROP_FLAGS")

    def need_descriptor(self):
        if any(flag in self.properties for flag in [PROP_FLAGS["NOTIFY"], PROP_FLAGS["INDICATE"]]):
            self.add_descriptor(ATTR.CLIENT_CHAR_CONFIG.value, CCCD.DISABLED)

    def add_descriptor(self, uuid, value, handle = None):
        if handle == None:
            handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(handle)
        self.descriptor["handle"] = handle

        if value == None:
            value = CCCD.DISABLED
        else:
            self.check_descriptor(value)
        self.descriptor["value"] = value
        self.check_uuid(uuid)
        self.descriptor["uuid"] = uuid
        self.descriptors.append(self.descriptor)

    def remove_descriptor(self, uuid):
        for descriptor in self.descriptors:
            if uuid == descriptor["uuid"]:
                del self.descriptors[uuid]
                return True
        print(f"uuid {uuid} not in descriptors")
        return False

    def set_value(self, value: bytes):
        if not isinstance(value, bytes):
            raise ValueError("Value must be a binary string (bytes).")
        self.value = value

    def get_value(self) -> bytes:
        return self.value

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
        uuid: bytes,
        name:str = None,
        handle: int = None,
        primary:bool = True
        ):
        self.gatt_handles = GattHandles()
        self.uuid = uuid
        self.primary = primary
        self.name = name or 'Unnamed Service'
        self.handle = handle
        self.characteristics = {}
        self.set_handle()

    def set_handle(self):
        if self.handle == None:
            self.handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.get_new_handle(self.handle)

    def add_characteristic(self, uuid, properties, value, **kwargs):
        characteristic = Characteristic(uuid, properties, value, **kwargs)
        self.characteristics[characteristic.cd_handle] = characteristic

    def remove_characteristic(self, handle: int):
        if handle in self.characteristics:
            del self.characteristics[handle]
            return True
        return False

    def get_characteristic(self, handle: int):
        return self.characteristics.get(handle)

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
    def __init__(self, device_name: bytes):
        self.gatt_handles = GattHandles()
        self.device_name = device_name
        self.services = {}
        self.primary_service_handles = []
        self.secondary_service_handles = []
        self.gacc_service = None
        self.gatt_service = None
        self.set_base_services()
        self.service_change_range = 0x00000000
        self.get_service_change_range()

    def get_service_change_range(self):
        self.service_change_range =  (self.gatt_handles.start_handle << 16) & self.gatt_handles.end_handle
        print(f"Service Change Range = 0x{self.service_change_range:08X}")

    def set_base_services(self):
        generic_access = self.add_service(uuid=KEY_SERVICE.GENERIC_ACCESS.value, name=b"Generic Access")
        generic_access.add_characteristic(
            uuid=KEY_CHAR.DEVICE_NAME.value,
            properties=[PROP_FLAGS.READ],
            value=self.device_name,
            cd_handle = 0x0004,
            constant=True
        )
        generic_access.add_characteristic(
            uuid=KEY_CHAR.APPEARANCE.value,
            properties=[PROP_FLAGS.READ],
            value=APPEARANCE.MINI_PC,
            cd_handle = 0x0006,
            constant=True
        )
        generic_attribute = self.add_service(uuid=KEY_SERVICE.GENERIC_ATTRIBUTE.value, name=b"Generic Attribute")
        generic_attribute.add_characteristic(
            uuid=KEY_CHAR.SERVICE_CHANGED.value,
            properties=[PROP_FLAGS.INDICATE],
            value=0x00000000,
            cd_handle = 0x0009,
            fixed_length = True,
            length = 4

        )

    def add_service(self, uuid: bytes, name: str = None, handle: int = None, primary: bool = True):
        service = Service(uuid, name, handle, primary)
        self.services[service.handle] = service
        if primary == True:
            self.primary_service_handles.append(service.handle)
        else:
            self.secondary_service_handles.append(service.handle)
        return service

    def remove_service(self, handle: int):
        if handle in self.services:
            service = self.services[handle]
            if primary == True:
                self.primary_service_handles.remove(service.handle)
            else:
                self.secondary_service_handles.remove(service.handle)
            del self.services[handle]
            return True
        return False

    def get_service(self, handle: int):
        return self.services.get(handle)

    def print_string(self):
        gatt_print = "\nGatt Server:"
        services_str = ""
        for service in self.services.values():
            services_str += service.print_string()
        return gatt_print + services_str



if __name__ == "__main__":
    device_name = b"MyDevice"
    gatt_server = GattServer(device_name)


    print(gatt_server.print_string())
    print(gatt_server.gatt_handles.print_string())

