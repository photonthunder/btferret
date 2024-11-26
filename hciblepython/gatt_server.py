#!/usr/bin/env python3
# from ble_enum import ATTErrorCode
# from ble_enum import GATTAttributes
from gatt_enum import CCCD, PERM_FLAGS, PROP_FLAGS
import byte_utils as bu
import logging
import time
import bisect

class Handles:
    def __init__(self):
        self.min_handle = 0x0003
        self.max_handle = 0xFFFF
        self.primary_service_handles = []  # Stores a list of handles

    def set_min_handle(self, handle):
        if handle < 0 or handle > self.max_handle:
            print(f"min_handle 0x{handle:04X} must be between 0x0000 and 0x{self.max_handle:04X}.")
            return False
        self.min_handle = handle
        return True

    def set_max_handle(self, handle):
        if handle < self.min_handle or handle > 0xFFFF:
            print(f"max_handle 0x{handle:04X} must be between 0x{self.min_handle:04X} and 0xFFFF.")
            return False
        self.max_handle = handle

    def add_primary_service_handle(self, handle):
        if handle < self.min_handle or handle > self.max_handle:
            print("PS Handle must be within 0x{self.min_handle:04X} and 0x{self.max_handle:04X}.")
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
        """String representation of the Handles class."""
        return (
            f"Handles(min_handle={hex(self.min_handle)}, "
            f"max_handle={hex(self.max_handle)}, "
            f"primary_service_handles={self.primary_service_handles})"
        )

class Characteristic:
    def __init__(
        self,
        uuid: str,
        properties: list[PROP_FLAGS],
        value: bytes = b"",
        permissions: list[PERM_FLAGS] = None,
        constant=False,
        value_handle=None,
    ):
        self.uuid = uuid
        self.properties = properties
        self.permissions = permissions or []
        self.value = value
        self.constant = constant
        self.value_handle = value_handle
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
        properties_str = ", ".join(prop.name for prop in self.properties)
        permissions_str = ", ".join(perm.name for perm in self.permissions)
        const_str = "CONSTANT" if self.constant else "VARIABLE"
        vh_str = f"VH = 0x{self.value_handle:04X}" if self.value_handle else ""
        descriptors_str = (
            "\n        Descriptors:\n" +
            "\n".join(
                f"          Descriptor(UUID: {uuid}, Value: {value})"
                for uuid, value in self.descriptors.items()
            )
            if self.descriptors
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

    def add_characteristic(self, handle: int, characteristic: Characteristic):
        self.characteristics[handle] = characteristic

    def remove_characteristic(self, handle: int):
        if handle in self.characteristics:
            del self.characteristics[handle]

    def get_characteristic(self, handle: int) -> Characteristic:
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
        0x0005,
        Characteristic(
            uuid="2A00",
            properties=[PROP_FLAGS.READ],
            permissions=[PERM_FLAGS.READ],
            value=b"MyDevice",
            constant=True,
            value_handle=0x0005,
        )
    )
    generic_access.add_characteristic(
        0x0007,
        Characteristic(
            uuid="2A01",
            properties=[PROP_FLAGS.READ],
            permissions=[PERM_FLAGS.READ],
            value=b"\x00\x80",
            constant=True,
            value_handle=0x0007,
        )
    )
    gatt_server.add_service(0x0003, generic_access)

    # Print GATT Server
    print(gatt_server)
