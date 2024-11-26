#!/usr/bin/env python3
# from ble_enum import ATTErrorCode
# from ble_enum import GATTAttributes
from gatt_enum import CCCD, PERM_FLAGS, PROP_FLAGS
import byte_utils as bu
import logging
import time

class Characteristic:
    def __init__(self, uuid: str, properties: list[PROP_FLAGS], value: bytes = b"", value_type="variable", fixed_length=False, length=None):
        self.uuid = uuid  # Binary strings can be converted to UUIDs as needed
        self.properties = properties  # List of enums
        self.value = value  # Binary string
        self.value_type = value_type
        self.fixed_length = fixed_length
        self.length = length
        self.descriptors = {}

    def add_descriptor(self, uuid: str, value: bytes):
        self.descriptors[uuid] = value

    def remove_descriptor(self, uuid: str):
        if uuid in self.descriptors:
            del self.descriptors[uuid]

    def set_value(self, value: bytes):
        if not isinstance(value, bytes):
            raise ValueError("Value must be a binary string (bytes).")
        self.value = value

    def get_value(self) -> bytes:
        return self.value

    def __str__(self):
        properties = ", ".join(str(prop) for prop in self.properties)
        descriptors = ", ".join(f"{uuid}: {value}" for uuid, value in self.descriptors.items())
        return (
            f"Characteristic(UUID: {self.uuid}, Properties: [{properties}], "
            f"Value: {self.value}, Descriptors: {{{descriptors}}})"
        )

class Service:
    def __init__(self, uuid: str, primary=True):
        self.uuid = uuid  # Binary string representation of UUID
        self.primary = primary
        self.characteristics = {}

    def add_characteristic(self, handle: int, characteristic: Characteristic):
        self.characteristics[handle] = characteristic

    def remove_characteristic(self, handle: int):
        if handle in self.characteristics:
            del self.characteristics[handle]

    def get_characteristic(self, handle: int) -> Characteristic:
        return self.characteristics.get(handle)

    def __str__(self):
        characteristics_str = "\n    ".join(
            f"Handle 0x{handle:04X}: {characteristic}" for handle, characteristic in self.characteristics.items()
        )
        return f"Service(UUID: {self.uuid}, Primary: {self.primary})\n    {characteristics_str}"

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
            f"Handle 0x{handle:04X}: {service}" for handle, service in self.services.items()
        )
        return f"GattServer:\n{services_str}"

if __name__ == "__main__":
    gatt_server = GattServer()

    # Generic Access Service
    generic_access = Service(uuid="1800")
    generic_access.add_characteristic(
        0x0005, Characteristic(uuid="2A00", properties="read", value="MyDevice")
    )
    generic_access.add_characteristic(
        0x0007, Characteristic(uuid="2A01", properties="read", value="Appearance")
    )
    gatt_server.add_service(0x0003, generic_access)

    print(gatt_server)