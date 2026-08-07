"""
Pydantic Schemas Module

Defines request validation and response DTO schemas for API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.enums import RoleEnum, BloodGroupEnum, RequestStatusEnum, MatchStatusEnum


# ==========================================
# Authentication Schemas
# ==========================================

class RegisterRequest(BaseModel):
    """Payload for user registration."""
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="Unique email address")
    phone_number: str = Field(..., min_length=5, max_length=50, description="Unique phone number")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    role: RoleEnum = Field(default=RoleEnum.CITIZEN, description="User role (citizen, hospital, blood_bank, admin)")


class LoginRequest(BaseModel):
    """Payload for user authentication."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """DTO for returning user profile details."""
    id: uuid.UUID
    full_name: str
    email: str
    phone_number: str
    role: RoleEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """DTO for successful login authentication response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: UserResponse


# ==========================================
# Emergency Request Schemas
# ==========================================

class EmergencyRequestCreate(BaseModel):
    """Payload for creating an emergency blood request."""
    patient_name: str = Field(..., min_length=1, max_length=255, description="Name of the patient requiring blood")
    blood_group: BloodGroupEnum = Field(..., description="Required blood group")
    units_required: int = Field(default=1, ge=1, description="Number of blood units required")
    hospital_id: uuid.UUID = Field(..., description="UUID of the requesting hospital")
    latitude: float = Field(..., description="Latitude location of the emergency request")
    longitude: float = Field(..., description="Longitude location of the emergency request")


class EmergencyRequestUpdateStatus(BaseModel):
    """Payload for updating the status of an emergency request."""
    status: RequestStatusEnum = Field(..., description="Updated request status (pending, searching, matched, completed, cancelled)")


class EmergencyRequestResponse(BaseModel):
    """DTO for returning emergency request details."""
    id: uuid.UUID
    patient_name: str
    blood_group: BloodGroupEnum
    units_required: int
    hospital_id: uuid.UUID
    latitude: float
    longitude: float
    status: RequestStatusEnum
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Blood Inventory Schemas
# ==========================================

class BloodInventoryCreate(BaseModel):
    """Payload for adding blood inventory units."""
    blood_bank_id: uuid.UUID = Field(..., description="UUID of the blood bank facility")
    blood_group: BloodGroupEnum = Field(..., description="Blood group type")
    units_available: int = Field(default=0, ge=0, description="Available units in stock")
    expiry_date: Optional[datetime] = Field(default=None, description="Expiration date of blood units")


class BloodInventoryUpdate(BaseModel):
    """Payload for updating blood inventory units."""
    units_available: Optional[int] = Field(default=None, ge=0, description="Updated units count")
    expiry_date: Optional[datetime] = Field(default=None, description="Updated expiration date")
    blood_group: Optional[BloodGroupEnum] = Field(default=None, description="Updated blood group")


class BloodInventoryResponse(BaseModel):
    """DTO for returning blood inventory details."""
    id: uuid.UUID
    blood_bank_id: uuid.UUID
    blood_group: BloodGroupEnum
    units_available: int
    expiry_date: Optional[datetime]
    last_updated: datetime
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Donor Profile Schemas
# ==========================================

class DonorCreate(BaseModel):
    """Payload for creating a donor profile."""
    blood_group: BloodGroupEnum = Field(..., description="Donor's blood group")
    city: str = Field(..., min_length=1, max_length=100, description="Donor's current city")
    latitude: Optional[float] = Field(default=None, description="Current latitude location")
    longitude: Optional[float] = Field(default=None, description="Current longitude location")
    is_available: bool = Field(default=True, description="Availability flag for emergency calls")
    last_donation_date: Optional[datetime] = Field(default=None, description="Timestamp of last blood donation")
    response_rate: float = Field(default=100.0, ge=0.0, le=100.0, description="Donor response score percentage")
    health_status: Optional[str] = Field(default="Eligible", max_length=255, description="Health eligibility status")


class DonorUpdate(BaseModel):
    """Payload for updating donor profile details."""
    blood_group: Optional[BloodGroupEnum] = Field(default=None, description="Updated blood group")
    city: Optional[str] = Field(default=None, max_length=100, description="Updated city")
    latitude: Optional[float] = Field(default=None, description="Updated latitude")
    longitude: Optional[float] = Field(default=None, description="Updated longitude")
    is_available: Optional[bool] = Field(default=None, description="Updated availability flag")
    last_donation_date: Optional[datetime] = Field(default=None, description="Updated last donation timestamp")
    health_status: Optional[str] = Field(default=None, max_length=255, description="Updated health status")


class DonorResponse(BaseModel):
    """DTO for returning donor profile details."""
    id: uuid.UUID
    user_id: uuid.UUID
    blood_group: BloodGroupEnum
    city: str
    latitude: Optional[float]
    longitude: Optional[float]
    is_available: bool
    last_donation_date: Optional[datetime]
    response_rate: float
    health_status: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Hospital Profile Schemas
# ==========================================

class HospitalCreate(BaseModel):
    """Payload for registering a hospital profile."""
    hospital_name: str = Field(..., min_length=1, max_length=255, description="Name of the hospital")
    address: str = Field(..., min_length=1, description="Full address of the hospital")
    latitude: float = Field(..., description="Hospital latitude location")
    longitude: float = Field(..., description="Hospital longitude location")
    contact_number: str = Field(..., min_length=5, max_length=50, description="Hospital contact number")
    user_id: Optional[uuid.UUID] = Field(default=None, description="Optional associated user account UUID")


class HospitalUpdate(BaseModel):
    """Payload for updating hospital profile details."""
    hospital_name: Optional[str] = Field(default=None, max_length=255, description="Updated hospital name")
    address: Optional[str] = Field(default=None, description="Updated address")
    latitude: Optional[float] = Field(default=None, description="Updated latitude")
    longitude: Optional[float] = Field(default=None, description="Updated longitude")
    contact_number: Optional[str] = Field(default=None, max_length=50, description="Updated contact number")


class HospitalResponse(BaseModel):
    """DTO for returning hospital profile details."""
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    hospital_name: str
    address: str
    latitude: float
    longitude: float
    contact_number: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Search API Schemas
# ==========================================

class BloodBankSearchResult(BaseModel):
    """DTO for matching Blood Bank inventory search result."""
    id: uuid.UUID
    name: str
    address: str
    latitude: float
    longitude: float
    contact_number: str
    units_available: int
    blood_group: BloodGroupEnum
    distance_km: float

    model_config = ConfigDict(from_attributes=True)


class DonorSearchResult(BaseModel):
    """DTO for matching Donor search result."""
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone_number: str
    blood_group: BloodGroupEnum
    city: str
    latitude: float
    longitude: float
    is_available: bool
    response_rate: float
    distance_km: float

    model_config = ConfigDict(from_attributes=True)


class SearchSummary(BaseModel):
    """DTO for summary statistics of search results."""
    donors_found: int
    blood_banks_found: int
    radius: float


class SearchResponse(BaseModel):
    """DTO for unified geo-spatial search API response."""
    blood_banks: list[BloodBankSearchResult]
    donors: list[DonorSearchResult]
    summary: SearchSummary


# ==========================================
# AI Matching Engine Schemas
# ==========================================

class MatchedBloodBankInfo(BaseModel):
    """DTO for matched blood bank inventory details."""
    id: uuid.UUID
    name: str
    address: str
    contact_number: str
    units_available: int
    distance_km: float

    model_config = ConfigDict(from_attributes=True)


class ScoredDonorResult(BaseModel):
    """DTO for scored and ranked donor recommendation."""
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone_number: str
    blood_group: BloodGroupEnum
    city: str
    distance_km: float
    score: float
    response_rate: float
    reasons: list[str]

    model_config = ConfigDict(from_attributes=True)


class AIMatchSearchSummary(BaseModel):
    """DTO for summary statistics of AI matching search execution."""
    total_donors_evaluated: int
    top_donors_returned: int
    blood_banks_checked: int


class AIMatchResponse(BaseModel):
    """DTO for unified AI matching recommendation response."""
    request_id: uuid.UUID
    recommended_source: str = Field(..., description="Recommended source: 'blood_bank' or 'donors'")
    blood_bank_available: bool
    matched_blood_bank: Optional[MatchedBloodBankInfo] = None
    top_donors: list[ScoredDonorResult]
    search_summary: AIMatchSearchSummary


