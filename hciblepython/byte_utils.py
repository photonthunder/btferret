from uuid import UUID
from gatt_enum import UUID_TYPE


def as_addr (byts):
    return ':'.join('{:02x}'.format (a) for a in byts)

def as_hex (byts):
    return ' '.join('{:02x}'.format (a) for a in byts)

def as_printable(byts):
    return ''.join('{:c}'.format(a) if (a >= 32 and a <= 126) else '.' for a in byts) 

def to_u32(byts, ind):
    return int.from_bytes(byts[ind:ind+4], byteorder='little')

def to_u16 (byts, ind):
    return int.from_bytes(byts[ind:ind+2], byteorder='little')

def to_u8 (byts, ind):
    return byts[ind]

def to_uuid (uuid_bytes):
    if len(uuid_bytes) == 2:
        temp_string = f"{uuid_bytes[1]:02X}{uuid_bytes[0]:02X}"
        return temp_string
    elif len(uuid_bytes) == 16:
        uuid_bytes_reversed = uuid_bytes[::-1]
        print(uuid_bytes_reversed)
        uuid_obj = UUID(bytes=uuid_bytes_reversed)
        return str(uuid_obj).upper()
    else:
        return None

def to_string(byts):
    return byts.decode('utf-8')

def to_addr(byts, ind):
    return as_addr(bytes(reversed(byts [ind: ind+6])))

def to_data(byts, ind, length):
    return byts[ind: ind + length]

def to_data_rest(byts, ind):
    return byts[ind:]

def to_bits_u16 (byts, ind, start, num_bits):
    val = to_u16(byts, ind)
    val = val >> start
    mask = (1 << num_bits) - 1
    return val & mask

def from_u8(val):
    if val == None:
        return bytes()
    else:
        return bytes ([val])

def from_u16(val):
    return val.to_bytes(2, byteorder='little')

def from_u32(val):
    return val.to_bytes(4, byteorder='little')

def from_uuid_int(uuid):
    return format(uuid, 'X').encode('utf-8')

def from_uuid(uuid):
    if len(uuid) == 4:
        num = int(uuid, 16)
        little_endian_bytes = num.to_bytes(2, byteorder='little')
        return little_endian_bytes
    if len(uuid) == 36:
        binary_uuid = UUID(uuid).bytes
        return binary_uuid[::-1]
    return None
    
def from_string(val):
    if isinstance(val, str):
        return val.encode('utf-8')
    return None

def from_addr(val):
    return bytes(reversed(bytes.fromhex(val.replace(':', ''))))

def from_data(val):
    return bytes(val)

def clean_uuid(uuid):
    return uuid.replace('-', '')

def check_uuid(uuid):
    if len(uuid) == 4 and is_hex(uuid):
        return UUID_TYPE.UUID_16BIT
    if len(uuid) == 36:
        cleaned = clean_uuid(uuid)
        if len(cleaned) == 32 and is_hex(cleaned):
            return UUID_TYPE.UUID_128BIT
    return False

def is_hex(s):
    return all(c in '0123456789abcdefABCDEF' for c in s)

def get_uuid_byte_length(uuid):
    if isinstance(uuid, str):      
        cleaned_uuid = uuid.replace('-', '')
        return int(len(cleaned_uuid))
    else:
        return 0