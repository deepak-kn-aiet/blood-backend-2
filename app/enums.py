"""
Application Enumerations Module

Defines domain enums used across database models and API schemas.
Uses str-derived Enums for clean JSON serialization.
"""

from enum import Enum


class RoleEnum(str, Enum):
    """User System Roles"""
    CITIZEN = "citizen"
    HOSPITAL = "hospital"
    BLOOD_BANK = "blood_bank"
    ADMIN = "admin"


class BloodGroupEnum(str, Enum):
    """Standard Blood Groups"""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class RequestStatusEnum(str, Enum):
    """Emergency Blood Request Statuses"""
    PENDING = "pending"
    SEARCHING = "searching"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MatchStatusEnum(str, Enum):
    """Donor Match Request Statuses"""
    NOTIFIED = "notified"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    COMPLETED = "completed"
