This code is a BLE server written in Python but using a c socket.

Code taken from the following repositories:
https://github.com/petzval/btferret
https://github.com/paulhamsh/HCI-BLE-Python



GAP initiates the connection:
Devices advertise and scan using GAP.

Once connected, ACL links are established.
ACL transports all data:
Provides the medium for ATT and GATT communication.

ATT manages attribute communication:
Handles low-level data exchange of services and characteristics.

GATT organizes and structures the data:
Builds on ATT to provide a human-readable and application-friendly abstraction.
