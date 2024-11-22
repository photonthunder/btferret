
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
        # Convert 2-byte UUID to a 4-character hex string
        return "{:02X}{:02X}".format(uuid_bytes[1], uuid_bytes[0])
    elif len(uuid_bytes) == 16:
        # Reverse the bytes and convert 16-byte UUID to string format with dashes
        reversed_uuid_bytes = uuid_bytes[::-1]
        uuid_str = ''.join(f"{b:02X}" for b in reversed_uuid_bytes)
        return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"
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
    # v1 = val & 0xFF
    # v2 = val >> 8
    # return bytes([v1]) + bytes([v2])

def from_u32(val):
    return val.to_bytes(4, byteorder='little')

def from_uuid(uuid):
    if isinstance(uuid, str):
        cleaned_uuid = clean_uuid(uuid)
        byte_pairs = [cleaned_uuid[i:i+2] for i in range(0, len(cleaned_uuid), 2)]
        little_endian_bytes = byte_pairs[::-1]
        little_endian_bytes = bytes(int(byte, 16) for byte in little_endian_bytes)
        return little_endian_bytes
    return None

def from_string(val):
    if isinstance(val, str):
        return val.encode("utf-8")
    return None

def from_addr(val):
    return bytes(reversed(bytes.fromhex(val.replace(':', ''))))

def from_data(val):
    return bytes(val)

def clean_uuid(uuid):
    return uuid.replace('-', '')

def get_uuid_byte_length(uuid):
    if isinstance(uuid, str):      
        cleaned_uuid = uuid.replace('-', '')
        return int(len(cleaned_uuid)/2)
    else:
        return 0