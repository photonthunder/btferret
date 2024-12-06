from enum import Enum, IntEnum, unique


# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 2.6.2 and 2.6.3
class APPEARANCE(IntEnum):
    IOT_GATEWAY = 0x008D
    MINI_PC = 0x008E
    ACCESS_POINT = 0x0501
    MESH_DEVICE = 0x0502

class ATTChannelID(IntEnum):
    BLE = 0x0004

# v5.4  Vol 3 Part F 3.4.1.1 Table 3.4
@unique
class ATTCode(IntEnum):
    SUCCESS = 0x00
    INVALID_HANDLE = 0x01  # The attribute handle given was not valid on this server.
    READ_NOT_PERMITTED = 0x02  # The attribute cannot be read.
    WRITE_NOT_PERMITTED = 0x03  # The attribute cannot be written.
    INVALID_PDU = 0x04  # The attribute PDU was invalid.
    INSUFFICIENT_AUTHENTICATION = 0x05  # The attribute requires authentication before it can be read or written.
    REQUEST_NOT_SUPPORTED = 0x06  # ATT Server does not support the request received from the client.
    INVALID_OFFSET = 0x07  # Offset specified was past the end of the attribute.
    INSUFFICIENT_AUTHORIZATION = 0x08  # The attribute requires authorization before it can be read or written.
    PREPARE_QUEUE_FULL = 0x09  # Too many prepare writes have been queued.
    ATTRIBUTE_NOT_FOUND = 0x0A  # No attribute found within the given attribute handle range.
    ATTRIBUTE_NOT_LONG = 0x0B  # The attribute cannot be read using the ATT_READ_BLOB_REQ PDU.
    ENCRYPTION_KEY_SIZE_TOO_SHORT = 0x0C  # The Encryption Key Size used for encrypting this link is too short.
    INVALID_ATTRIBUTE_VALUE_LENGTH = 0x0D  # The attribute value length is invalid for the operation.
    UNLIKELY_ERROR = 0x0E  # The request encountered an unlikely error.
    INSUFFICIENT_ENCRYPTION = 0x0F  # The attribute requires encryption before it can be read or written.
    UNSUPPORTED_GROUP_TYPE = 0x10  # The attribute type is not a supported grouping attribute.
    INSUFFICIENT_RESOURCES = 0x11  # Insufficient resources to complete the request.
    DATABASE_OUT_OF_SYNC = 0x12  # The server requests the client to rediscover the database.
    VALUE_NOT_ALLOWED = 0x13  # The attribute parameter value was not allowed.
    APPLICATION_ERROR_START = 0x80  # Application-specific error codes start here (0x80 to 0x9F).
    APPLICATION_ERROR_END = 0x9F
    COMMON_PROFILE_SERVICE_ERROR_START = 0xE0  # Common profile and service error codes start here (0xE0 to 0xFF).
    COMMON_PROFILE_SERVICE_ERROR_END = 0xFF

# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.6 and 3.7
class ATTR(Enum):
    PRIMARY_SERVICE = '2800'
    SECONDARY_SERVICE = '2801'
    INCLUDE = '2802'
    CHARACTERISTIC = '2803'
    CHARACTERISTIC_EXT_PROPERTIES = '2900'
    CHARACTERISTIC_USER_DESC = '2901'
    CLIENT_CHAR_CONFIG = '2902'
    SERVER_CHAR_CONFIG = '2903'
    CHARACTERISTIC_PRESENTATION_FORMAT = '2904'
    CHARACTERISTIC_AGGREGATE_FORMAT = '2905'

# v5.4  Vol 3 Part G 3.3.3
class CCCD(IntEnum):  # Client Characteristic Configuration Descriptor
    DISABLED = 0x0000
    NOTIFICATION = 0x0001
    INDICATION = 0x0002

# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.8.1
class KEY_CHAR(Enum):
    DEVICE_NAME = '2A00'
    APPEARANCE = '2A01'
    PPCP = '2A04'
    SERVICE_CHANGED = '2A05'
    MANUFACTURER_NAME = '2A29'
    MODEL_NUMBER = '2A24'
    SERIAL_NUMBER = '2A25'
    FIRMWARE_REVISION = '2A26'
    HARDWARE_REVISION = '2A27'
    SOFTWARE_REVISION = '2A28'
    PNP_ID = '2A50'

# https://www.bluetooth.com/specifications/assigned-numbers/
# Section 3.4.1
class KEY_SERVICE(Enum):
    GENERIC_ACCESS = '1800'
    GENERIC_ATTRIBUTE = '1801'
    DEVICE_INFORMATION = '180A'

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

class UUID_TYPE(IntEnum):
    UUID_16BIT = 0x01
    UUID_128BIT = 0x02


