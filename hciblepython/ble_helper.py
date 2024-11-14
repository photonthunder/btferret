from enum import IntEnum
from enum import Enum

class ByteHelper:
    @staticmethod
    def as_addr (byts):
        return ':'.join('{:02x}'.format (a) for a in byts)

    @staticmethod
    def as_hex (byts):
        return ' '.join('{:02x}'.format (a) for a in byts)

    @staticmethod
    def as_printable(byts):
        return ''.join('{:c}'.format(a) if (a >= 32 and a <= 126) else '.' for a in byts) 

    @staticmethod
    def to_u32(byts, ind):
        return byts[ind] | (byts [ind+1] << 8) | (byts [ind+2] << 16) | (byts [ind+3] << 24)

    @staticmethod
    def to_u16 (byts, ind):
        return byts[ind] | (byts [ind+1] << 8)

    @staticmethod
    def to_u8 (byts, ind):
        return byts[ind]

    @staticmethod
    def to_uuid (uuid_bytes):
        if len(uuid_bytes) == 2:
            # Convert 2-byte UUID to a 4-character hex string
            return "{:02X}{:02X}".format(uuid_bytes[1], uuid_bytes[0])
        elif len(uuid_bytes) == 16:
            # Reverse the bytes and convert 16-byte UUID to string format with dashes
            reversed_uuid_bytes = uuid_bytes[::-1]
            uuid_str = ''.join(f"{b:02X}" for b in reversed_uuid_bytes)
            return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"
        else:
            return None
        
    @staticmethod
    def to_string(byts):
        return byts.decode('utf-8')

    @staticmethod
    def to_addr(byts, ind):
        return ByteHelper.as_addr(bytes(reversed(byts [ind: ind+6])))

    @staticmethod
    def to_data(byts, ind, length):
        return byts[ind: ind + length]

    @staticmethod
    def to_data_rest(byts, ind):
        return byts[ind:]

    @staticmethod
    def to_bits_u16 (byts, ind, start, num_bits):
        val = ByteHelper.to_u16(byts, ind)
        val = val >> start
        mask = (1 << num_bits) - 1
        return val & mask

    @staticmethod
    def from_u8(val):
        if val == None:
            return bytes()
        else:
            return bytes ([val])

    @staticmethod
    def from_u16(val):
        v1 = val & 0xFF
        v2 = val >> 8
        return bytes([v1]) + bytes([v2])

    @staticmethod
    def from_u32(val):
        v1 = val & 0xFF
        v2 = (val >> 8) & 0xFF
        v3 = (val >> 16) & 0xFF
        v4 = (val >> 24) & 0xFF
        return bytes([v1]) + bytes([v2]) + bytes([v3]) + bytes([v4])

    @staticmethod
    def from_uuid(uuid):
        if isinstance(uuid, str):
            cleaned_uuid = ByteHelper.clean_uuid(uuid)
            byte_pairs = [cleaned_uuid[i:i+2] for i in range(0, len(cleaned_uuid), 2)]
            little_endian_bytes = byte_pairs[::-1]
            little_endian_bytes = bytes(int(byte, 16) for byte in little_endian_bytes)
            return little_endian_bytes
        return None

    @staticmethod
    def from_string(val):
        return val.encode("utf-8")

    @staticmethod
    def from_addr(val):
        return bytes(reversed(bytes.fromhex(val.replace(':', ''))))

    @staticmethod
    def from_data(val):
        return bytes(val)

    @staticmethod
    def clean_uuid(uuid):
        return uuid.replace('-', '')

    @staticmethod
    def get_uuid_byte_length(uuid):
        if isinstance(uuid, str):      
            cleaned_uuid = uuid.replace('-', '')
            return int(len(cleaned_uuid)/2)
        else:
            return 0



class ATTErrorCode(IntEnum):
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

class BLEErrorCode(IntEnum):
    SUCCESS = 0x00
    UNKNOWN_HCI_COMMAND = 0x01
    UNKNOWN_CONNECTION_IDENTIFIER = 0x02
    HARDWARE_FAILURE = 0x03
    PAGE_TIMEOUT = 0x04
    AUTHENTICATION_FAILURE = 0x05
    PIN_OR_KEY_MISSING = 0x06
    MEMORY_CAPACITY_EXCEEDED = 0x07
    CONNECTION_TIMEOUT = 0x08
    CONNECTION_LIMIT_EXCEEDED = 0x09
    SYNC_CONN_LIMIT_TO_DEVICE_EXCEEDED = 0x0A
    CONNECTION_ALREADY_EXISTS = 0x0B
    COMMAND_DISALLOWED = 0x0C
    CONNECTION_REJECTED_DUE_TO_LIMITED_RESOURCES = 0x0D
    CONNECTION_REJECTED_DUE_TO_SECURITY = 0x0E
    CONNECTION_REJECTED_DUE_TO_UNACCEPTABLE_BD_ADDR = 0x0F
    CONNECTION_ACCEPT_TIMEOUT_EXCEEDED = 0x10
    UNSUPPORTED_FEATURE_OR_PARAMETER_VALUE = 0x11
    INVALID_HCI_COMMAND_PARAMETERS = 0x12
    REMOTE_USER_TERMINATED_CONNECTION = 0x13
    REMOTE_DEVICE_TERMINATED_LOW_RESOURCES = 0x14
    REMOTE_DEVICE_TERMINATED_POWER_OFF = 0x15
    CONNECTION_TERMINATED_BY_LOCAL_HOST = 0x16
    REPEATED_ATTEMPTS = 0x17
    PAIRING_NOT_ALLOWED = 0x18
    UNKNOWN_LMP_PDU = 0x19
    UNSUPPORTED_REMOTE_FEATURE = 0x1A
    SCO_OFFSET_REJECTED = 0x1B
    SCO_INTERVAL_REJECTED = 0x1C
    SCO_AIR_MODE_REJECTED = 0x1D
    INVALID_LMP_PARAMETERS = 0x1E
    UNSPECIFIED_ERROR = 0x1F
    UNSUPPORTED_LMP_PARAMETER_VALUE = 0x20
    ROLE_CHANGE_NOT_ALLOWED = 0x21
    LMP_RESPONSE_TIMEOUT = 0x22
    LMP_ERROR_TRANSACTION_COLLISION = 0x23
    LMP_PDU_NOT_ALLOWED = 0x24
    ENCRYPTION_MODE_NOT_ACCEPTABLE = 0x25
    LINK_KEY_CANNOT_BE_CHANGED = 0x26
    REQUESTED_QOS_NOT_SUPPORTED = 0x27
    INSTANT_PASSED = 0x28
    PAIRING_WITH_UNIT_KEY_NOT_SUPPORTED = 0x29
    DIFFERENT_TRANSACTION_COLLISION = 0x2A
    RESERVED_FOR_FUTURE_USE_2B = 0x2B
    QOS_UNACCEPTABLE_PARAMETER = 0x2C
    QOS_REJECTED = 0x2D
    CHANNEL_CLASSIFICATION_NOT_SUPPORTED = 0x2E
    INSUFFICIENT_SECURITY = 0x2F
    PARAMETER_OUT_OF_MANDATORY_RANGE = 0x30
    RESERVED_FOR_FUTURE_USE_31 = 0x31
    ROLE_SWITCH_PENDING = 0x32
    RESERVED_FOR_FUTURE_USE_33 = 0x33
    RESERVED_SLOT_VIOLATION = 0x34
    ROLE_SWITCH_FAILED = 0x35
    EXTENDED_INQUIRY_RESPONSE_TOO_LARGE = 0x36
    SSP_NOT_SUPPORTED_BY_HOST = 0x37
    HOST_BUSY_PAIRING = 0x38
    CONNECTION_REJECTED_NO_SUITABLE_CHANNEL = 0x39
    CONTROLLER_BUSY = 0x3A
    UNACCEPTABLE_CONNECTION_PARAMETERS = 0x3B
    ADVERTISING_TIMEOUT = 0x3C
    CONNECTION_TERMINATED_DUE_TO_MIC_FAILURE = 0x3D
    CONNECTION_FAILED_TO_BE_ESTABLISHED = 0x3E
    PREVIOUSLY_USED = 0x3F
    COARSE_CLOCK_ADJUSTMENT_REJECTED = 0x40
    TYPE0_SUBMAP_NOT_DEFINED = 0x41
    UNKNOWN_ADVERTISING_IDENTIFIER = 0x42
    LIMIT_REACHED = 0x43
    OPERATION_CANCELLED_BY_HOST = 0x44
    PACKET_TOO_LONG = 0x45
    TOO_LATE = 0x46
    TOO_EARLY = 0x47

class GATTAttributes(Enum):
    PRIMARY_SERVICE = "2800"
    SECONDARY_SERVICE = "2801"
    INCLUDE = "2802"
    CHARACTERISTIC = "2803"
    CHARACTERISTIC_EXT_PROPERTIES = "2900"
    CHARACTERISTIC_USER_DESC = "2901"
    CLIENT_CHAR_CONFIG = "2902"
    SERVER_CHAR_CONFIG = "2903"
    CHARACTERISTIC_PRESENTATION_FORMAT = "2904"
    CHARACTERISTIC_AGGREGATE_FORMAT = "2905"

# class BLECharacteristics(IntEnum):
#     Here are the key characteristics typically found in the Device Information Service (0x180A):
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