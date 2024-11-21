This code is a BLE server written in Python but using a c socket (see hci_socket.py).

Code taken from the following repositories:
https://github.com/petzval/btferret
https://github.com/paulhamsh/HCI-BLE-Python

BLE Reference is 5.4:
https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html


GAP initiates the connection:
Devices advertise and scan using GAP.

Once connected, ACL links are established.
ACL transports all data:
Provides the medium for ATT and GATT communication.

ATT manages attribute communication:
Handles low-level data exchange of services and characteristics.

GATT organizes and structures the data:
Builds on ATT to provide a human-readable and application-friendly abstraction.


Here are the key characteristics typically found in the Device Information Service (0x180A):
# Device Name (0x2A00): The name of the device, e.g., "MyBLEDevice".
# Appearance (0x2A01): Describes the appearance of the device, like "Generic Heart Rate Monitor" or "Generic Sensor".
# Peripheral Preferred Connection Parameters (0x2A04): This characteristic provides parameters for how a peripheral prefers to connect (e.g., connection interval, slave latency, supervision timeout).
# Manufacturer Name String (0x2A29): The name of the device manufacturer.
# Model Number String (0x2A24): The model number of the device.
# Serial Number String (0x2A25): The serial number of the device.
# Hardware Revision String (0x2A27): The hardware revision of the device.
# Firmware Revision String (0x2A26): The firmware revision of the device.
# Software Revision String (0x2A28): The software revision of the device.
# IEEE 11073-20601 Regulatory Certification Data List (0x2A2A): Regulatory certification data, if applicable.
# PNP ID (0x2A50): Personal Network Profile (PNP) ID for identifying the device.