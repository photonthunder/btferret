from enum import IntEnum
from enum import Enum
from enum import unique

class CCCD(IntEnum):  # Client Characteristic Configuration Descriptor
    DISABLED = 0x0000
    NOTIFICATION = 0x0001
    INDICATIONS = 0x0002

class PERM_FLAGS(IntEnum):
    READ = 0x01
    WRITE = 0x02
    READ_ENCRYPT = 0x04
    WRITE_ENCRYPT = 0x08
    AUTH_READ = 0x10
    AUTH_WRITE = 0x20
    AUTH_REQ = 0x40

class PROP_FLAGS(IntEnum):
    BROADCAST = 0x01
    READ = 0x02
    WRITE_WITHOUT_RESPONSE = 0x04
    WRITE = 0x08
    NOTIFY = 0x10
    INDICATE = 0x20
    AUTH_SIGN_WRITE = 0x40
    EXTENDED_PROP = 0x80


