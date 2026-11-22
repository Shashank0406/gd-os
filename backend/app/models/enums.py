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


class BillingMode(str, Enum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"
    FREE_PLAY = "FREE_PLAY"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class ReservationStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    STARTED = "STARTED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    FREE = "FREE"
