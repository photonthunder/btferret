# Specification v5.4  Vol 4 Part E

# BLE_DEFAULT is the default given in the spec
# DEFAULT_TIME is the default used in this code
class IntervalBase:
    @classmethod
    def from_time(cls, interval_time):
        min_value = cls.MIN
        max_value = cls.MAX
        constant = cls.CONSTANT

        if interval_time < min_value or interval_time > max_value:
            raise ValueError(f"Error: Interval Time {interval_time} needs to be between {min_value * 1000} ms and {max_value} s")
        
        interval_conversion = int(interval_time / constant)
        # print(f"Interval {interval_time} -> 0x{interval_conversion:04X}")
        return interval_conversion.to_bytes(2, byteorder='little')

    @classmethod
    def to_time(cls, interval):
        min_value = cls.MIN
        max_value = cls.MAX
        constant = cls.CONSTANT

        interval_time = interval * constant

        if interval_time < min_value or interval_time > max_value:
            print(f"Error: Interval Time {interval_time} needs to be between {min_value * 1000} ms and {max_value} s")
            return None
        print(f"Interval {interval_time} -> 0x{interval:04X}")
        return interval_time


class AdvertisingInterval(IntervalBase):
    MIN = 0.02  
    MAX = 10.24 
    CONSTANT = 0.625E-3
    BLE_DEFAULT = 1.28
    DEFAULT_TIME = 1.28

class ConnectionAcceptTimeout(IntervalBase):
    MIN = 0.625E-3
    MAX = 29
    CONSTANT = 0.625E-3
    BLE_DEFAULT = 5.06 
    DEFAULT_TIME = 10.18

class ConnectionEventTime(IntervalBase):
    MIN = 0       #0x0000
    MAX = 40.959  #0xFFFF
    CONSTANT = 0.625E-3  
    BLE_DEFAULT = None
    DEFAULT_TIME = 0

class ConnectionInterval(IntervalBase):
    MIN = 0.0075
    MAX = 4 
    CONSTANT = 1.25E-3
    BLE_DEFAULT = None
    DEFAULT_TIME_MIN = 0.03
    DEFAULT_TIME_MAX = 0.48

class MaxLatency(IntervalBase):
    MIN = 0x0000
    MAX = 0x01F3
    CONSTANT = 1
    BLE_DEFAULT = None
    DEFAULT_TIME = 0x0000

class PageTimeout(IntervalBase):
    MIN = 0.625
    MAX = 40.9
    CONSTANT = 0.625E-3
    BLE_DEFAULT = 5.12
    DEFAULT_TIME = 10.24

class ScanningTime(IntervalBase):
    MIN = 0.0025
    MAX = 10.24
    CONSTANT = 0.625E-3
    BLE_DEFAULT = 0.01
    DEFAULT_TIME = 0.01

class SupervisionTimeout(IntervalBase):
    MIN = 0.1
    MAX = 32
    CONSTANT = 0.01
    BLE_DEFAULT = None
    DEFAULT_TIME = 0.42


