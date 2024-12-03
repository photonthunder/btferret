from enum import Enum, IntEnum


# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 2.6.2 and 2.6.3
class APPEARANCE(IntEnum):
    IOT_GATEWAY = 0x008D
    MINI_PC = 0x008E
    ACCESS_POINT = 0x0501
    MESH_DEVICE = 0x0502


# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.6 and 3.7
class ATTR(Enum):
    PRIMARY_SERVICE = b'2800'
    SECONDARY_SERVICE = b'2801'
    INCLUDE = b'2802'
    CHARACTERISTIC = b'2803'
    CHARACTERISTIC_EXT_PROPERTIES = b'2900'
    CHARACTERISTIC_USER_DESC = b'2901'
    CLIENT_CHAR_CONFIG = b'2902'
    SERVER_CHAR_CONFIG = b'2903'
    CHARACTERISTIC_PRESENTATION_FORMAT = b'2904'
    CHARACTERISTIC_AGGREGATE_FORMAT = b'2905'

# v5.4  Vol 3 Part G 3.3.3
class CCCD(IntEnum):  # Client Characteristic Configuration Descriptor
    DISABLED = 0x0000
    NOTIFICATION = 0x0001
    INDICATIONS = 0x0002

# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.8.1
class KEY_CHAR(Enum):
    DEVICE_NAME = b'2A00'
    APPEARANCE = b'2A01'
    PPCP = b'2A04'
    SERVICE_CHANGED = b'2A05'
    MANUFACTURER_NAME = b'2A29'
    MODEL_NUMBER = b'2A24'
    SERIAL_NUMBER = b'2A25'
    FIRMWARE_REVISION = b'2A26'
    HARDWARE_REVISION = b'2A27'
    SOFTWARE_REVISION = b'2A28'
    PNP_ID = b'2A50'

# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.4.1
class KEY_SERVICE(Enum):
    GENERIC_ACCESS = b'1800'
    GENERIC_ATTRIBUTE = b'1801'
    DEVICE_INFORMATION = b'180A'

# v5.4  Vol 3 Part F 3.2.5
class PERM_FLAGS(IntEnum):
    READ = 0x01
    WRITE = 0x02
    READ_ENCRYPT = 0x04
    WRITE_ENCRYPT = 0x08
    AUTH_READ = 0x10
    AUTH_WRITE = 0x20
    AUTH_REQ = 0x40

# v5.4  Vol 3 Part G 3.3.1.1
class PROP_FLAGS(IntEnum):
    BROADCAST = 0x01
    READ = 0x02
    WRITE_WITHOUT_RESPONSE = 0x04
    WRITE = 0x08
    NOTIFY = 0x10
    INDICATE = 0x20
    AUTH_SIGN_WRITE = 0x40
    EXTENDED_PROP = 0x80

