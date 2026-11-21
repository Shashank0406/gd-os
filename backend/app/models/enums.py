from enum import Enum


class DeviceType(str, Enum):
    PC = "PC"
    PS5 = "PS5"
    RACING_SIMULATOR = "RACING_SIMULATOR"
    ADMIN_WORKSTATION = "ADMIN_WORKSTATION"


class StationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_SESSION = "IN_SESSION"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"
