#!/usr/bin/env python3
# from ble_enum import ATTErrorCode
from gatt_enum import ATTR, CCCD, PERM_FLAGS, PROP_FLAGS
import byte_utils as bu
import logging
import time
import bisect

class GattHandles:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        cls._instance.min_handle = 0x0000
        cls._instance.max_handle = 0xFFFF
        cls._instance.start_handle = 0x0003
        cls._instance.next_handle = cls._instance.start_handle
        cls._instance.end_handle = cls._instance.start_handle
        cls._instance.assigned_handles = []
        cls._instance.primary_service_handles = []
        return cls._instance

    def set_start_handle(self, start_handle):
        if start_handle < self.min_handle or start_handle > self.end_handle:
            raise ValueError(f"start_handle 0x{start_handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.end_handle:04X}.")
        self.start_handle = start_handle
        return True

    def set_end_handle(self, end_handle):
        if end_handle < self.start_handle or end_handle > self.max_handle:
            raise ValueError(f"end_handle 0x{end_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.max_handle:04X}.")
        self.end_handle = end_handle
        return True

    def handle_available(self, handle):
        if handle in self.assigned_handles:
            return False
        elif handle < self.min_handle or handle > self.max_handle:
            raise ValueError(f"Handle 0x{handle:04X} must be between 0x{self.min_handle:04X} and 0x{self.max_handle:04X}.")
        else:
            return True

    def get_new_handle(self):
        new_handle = self.next_handle
        if new_handle < self.start_handle or new_handle > self.end_handle:
            raise ValueError(f"new_handle 0x{new_handle:04X} must be between 0x{self.start_handle:04X} and 0x{self.end_handle:04X}.")
        next_handle = new_handle + 1
        while next_handle <= self.max_handle:
            if self.handle_available(next_handle) == True:
                self.next_handle = next_handle
                self.set_end_handle(next_handle)
                self.assigned_handles.append(next_handle)
                return new_handle
            else:
                next_handle += 1
        raise ValueError(f"No handles available: next_handle 0x{next_handle:04X} > 0x{self.max_handle:04X}.")

    def set_handle(self, set_handle):
        if self.handle_available(set_handle):
            self.assigned_handles.append(set_handle)
            if set_handle < self.start_handle and set_handle > self.min_handle:
                self.start_handle = set_handle
            if set_handle > self.end_handle and set_handle < self.max_handle:
                self.end_handle = set_handle
            return True
        else:
            print("Error: Handle 0x{set_handle:04X} not available")
            return False

    def remove_handle(self, handle):
        if handle in self.assigned_handles:
            self.assigned_handles.remove(handle)
            return True
        else:
            print(f"Warning: Handle 0x{handle:04X} not assigned.")
            return False

    def add_primary_service_handle(self, handle):
        if handle < self.min_handle or handle > self.max_handle:
            print(f"PS Handle must be within 0x{self.min_handle:04X} and 0x{self.max_handle:04X}.")
            return False
        if handle not in self.primary_service_handles:
            bisect.insort(self.primary_service_handles, handle)
        return True

    def remove_primary_service_handle(self, handle):
        if handle in self.primary_service_handles:
            self.primary_service_handles.remove(handle)
            return True
        return False

    def clear_primary_service_handles(self):
        self.primary_service_handles.clear()

    def __repr__(self):
        handles_hex = [f"0x{handle:04X}\n" for handle in self.primary_service_handles]
        return (
            f"Handles(min_handle=0x{self.min_handle:04X}\n"
            f"max_handle=0x{self.max_handle:04X}\n"
            f"primary_service_handles\n{handles_hex})"
        )

class Characteristic:
    def __init__(
        self,
        uuid: bytes,
        properties: list,
        value: bytes,
        cd_handle: int = None,
        value_handle: int = None,
        descriptor: dict = None,
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

        self.descriptor = descriptor or {"uuid": None, "value": None, "handle": None}
        self.descr_uuid = self.descriptor.get("uuid")
        self.descr_value = self.descriptor.get("value")
        self.descr_handle = self.descriptor.get("handle")

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
            self.gatt_handles.set_handle(self.cd_handle)
                
        if self.value_handle == None:
            self.value_handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.set_handle(self.value_handle)

    def check_descriptor(self, descr_value):
        if descr_value not in PROP_FLAGS:
            raise ValueError(f"Description Value 0x{descr_value:04X} not in PROP_FLAGS")

    def need_descriptor(self):
        if any(flag in self.properties for flag in [PROP_FLAGS["NOTIFY"], PROP_FLAGS["INDICATE"]]):
            self.add_descriptor()

    def add_descriptor(self):
        if self.descr_handle == None:
            self.descr_handle = self.gatt_handles.get_new_handle()
        else:
            self.gatt_handles.set_handle(self.descr_handle)

        if self.descr_value == None:
            self.descr_value = CCCD.DISABLED
        else:
            self.check_descriptor(self.descr_value)

    def remove_descriptor(self):
        if uuid in self.descriptors:
            del self.descriptors[uuid]

    def set_value(self, value: bytes):
        if not isinstance(value, bytes):
            raise ValueError("Value must be a binary string (bytes).")
        self.value = value

    def get_value(self) -> bytes:
        return self.value

    def __str__(self):
        properties_str = ", ".join(prop.name for prop in self.properties)
        permissions_str = ", ".join(perm.name for perm in self.permissions)
        const_str = "CONSTANT" if self.constant else "VARIABLE"
        vh_str = f"VH = 0x{self.value_handle:04X}" if self.value_handle else ""
        descriptors_str = (
            "\n        Descriptors:\n" +
            "\n".join(
                f"          Descriptor(UUID: {uuid}, Value: {value})"
                for uuid, value in self.descriptor.items()
            )
            if self.descriptor
            else ""
        )
        return (
            f"Characteristic Declaration, b'{self.uuid}', {properties_str}, {const_str}, {vh_str}\n"
            f"Characteristic Value, b'{self.uuid}', {self.value!r}, Permissions: [{permissions_str}]"
            f"{descriptors_str}"
        )


class Service:
    def __init__(self, uuid: str, primary=True, name=""):
        self.uuid = uuid
        self.primary = primary
        self.name = name
        self.characteristics = {}

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

    def __str__(self):
        service_type = "Primary Service" if self.primary else "Secondary Service"
        characteristics_str = "\n".join(
            f"  0x{handle:04X}: {characteristic}"
            for handle, characteristic in self.characteristics.items()
        )
        return f"{self.name or 'Unnamed Service'}\n" \
               f"0x{self.uuid}: {service_type}, b'{self.uuid}'\n{characteristics_str}"

class GattServer:
    def __init__(self):
        self.services = {}

    def add_service(self, handle: int, service: Service):
        self.services[handle] = service

    def remove_service(self, handle: int):
        if handle in self.services:
            del self.services[handle]

    def get_service(self, handle: int) -> Service:
        return self.services.get(handle)

    def __str__(self):
        services_str = "\n".join(
            f"Handle 0x{handle:04X}:\n{service}" for handle, service in self.services.items()
        )
        return f"Gatt Server\n{services_str}"


if __name__ == "__main__":
    # Create GATT Server
    gatt_server = GattServer()

    # Generic Access Service
    generic_access = Service(uuid="1800", name="Generic Access")
    generic_access.add_characteristic(
        uuid="2A00",
        properties=[PROP_FLAGS.READ],
        value=b"MyDevice",
        cd_handle = 0x0005,
        constant=True
    )
    generic_access.add_characteristic(
        uuid="2A01",
        properties=[PROP_FLAGS.READ],
        value=b"\x00\x80",
        cd_handle = 0x0007,
        constant=True
    )
    gatt_server.add_service(0x0003, generic_access)

    # Print GATT Server
    print(gatt_server)
