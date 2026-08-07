"""
SQLAlchemy ORM Models Module

Defines domain entities for the Blood Relay platform using SQLAlchemy 2.0
declarative mapping, UUID primary keys, mixins, indexes, and bidirectional relationships.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Float,
    Integer,
    ForeignKey,
    DateTime,
    Enum as SQLEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import (
    RoleEnum,
    BloodGroupEnum,
    RequestStatusEnum,
    MatchStatusEnum,
)


class TimestampMixin:
    """
    Reusable Mixin for timezone-aware created_at and updated_at timestamps,
    plus soft-delete support.
    """
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )



class User(Base, TimestampMixin):
    """
    User Entity
    Represents system users (Citizens, Hospitals, Blood Banks, Admins).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(RoleEnum),
        nullable=False,
        default=RoleEnum.CITIZEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    donor: Mapped[Optional["Donor"]] = relationship(
        "Donor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    hospital: Mapped[Optional["Hospital"]] = relationship(
        "Hospital",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Donor(Base, TimestampMixin):
    """
    Donor Entity
    Extends User profile with blood donation details and location availability.
    """
    __tablename__ = "donors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    blood_group: Mapped[BloodGroupEnum] = mapped_column(
        SQLEnum(BloodGroupEnum),
        index=True,
        nullable=False,
    )
    city: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_donation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    response_rate: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    health_status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="donor")
    matches: Mapped[List["DonorMatch"]] = relationship(
        "DonorMatch",
        back_populates="donor",
        cascade="all, delete-orphan",
    )


class Hospital(Base, TimestampMixin):
    """
    Hospital Entity
    Represents healthcare institutions issuing emergency blood requests.
    """
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    hospital_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="hospital")
    emergency_requests: Mapped[List["EmergencyRequest"]] = relationship(
        "EmergencyRequest",
        back_populates="hospital",
        cascade="all, delete-orphan",
    )


class BloodBank(Base, TimestampMixin):
    """
    Blood Bank Entity
    Represents blood storage facilities maintaining blood inventory.
    """
    __tablename__ = "blood_banks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    inventories: Mapped[List["BloodInventory"]] = relationship(
        "BloodInventory",
        back_populates="blood_bank",
        cascade="all, delete-orphan",
    )


class BloodInventory(Base, TimestampMixin):
    """
    Blood Inventory Entity
    Tracks blood units available per blood group at a blood bank.
    """
    __tablename__ = "blood_inventories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    blood_bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blood_banks.id", ondelete="CASCADE"),
        nullable=False,
    )
    blood_group: Mapped[BloodGroupEnum] = mapped_column(
        SQLEnum(BloodGroupEnum),
        index=True,
        nullable=False,
    )
    units_available: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    blood_bank: Mapped["BloodBank"] = relationship(
        "BloodBank",
        back_populates="inventories",
    )


class EmergencyRequest(Base, TimestampMixin):
    """
    Emergency Request Entity
    Represents urgent blood requests broadcast by hospitals.
    """
    __tablename__ = "emergency_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    blood_group: Mapped[BloodGroupEnum] = mapped_column(
        SQLEnum(BloodGroupEnum),
        index=True,
        nullable=False,
    )
    units_required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[RequestStatusEnum] = mapped_column(
        SQLEnum(RequestStatusEnum),
        index=True,
        default=RequestStatusEnum.PENDING,
        nullable=False,
    )

    # Relationships
    hospital: Mapped["Hospital"] = relationship(
        "Hospital",
        back_populates="emergency_requests",
    )
    donor_matches: Mapped[List["DonorMatch"]] = relationship(
        "DonorMatch",
        back_populates="emergency_request",
        cascade="all, delete-orphan",
    )


class DonorMatch(Base, TimestampMixin):
    """
    Donor Match Entity
    Represents matches generated between an emergency blood request and potential donors.
    """
    __tablename__ = "donor_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emergency_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donors.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[MatchStatusEnum] = mapped_column(
        SQLEnum(MatchStatusEnum),
        index=True,
        default=MatchStatusEnum.NOTIFIED,
        nullable=False,
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    emergency_request: Mapped["EmergencyRequest"] = relationship(
        "EmergencyRequest",
        back_populates="donor_matches",
    )
    donor: Mapped["Donor"] = relationship(
        "Donor",
        back_populates="matches",
    )
