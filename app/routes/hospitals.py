"""
Hospital Profiles Router Module

Defines API endpoints for hospital profile registration, retrieval, updating, and deletion.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Hospital
from app.enums import RoleEnum
from app.schemas import (
    HospitalCreate,
    HospitalUpdate,
    HospitalResponse,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/hospitals", tags=["Hospital Profiles"])


@router.post(
    "",
    response_model=HospitalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new hospital profile",
)
def create_hospital_profile(
    payload: HospitalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.HOSPITAL, RoleEnum.ADMIN)),
):
    """
    Create Hospital Profile Endpoint

    - Only Hospital role or Admin users may create hospital profiles.
    - Associates profile with current_user.id if user_id is unspecified.
    """
    target_user_id = payload.user_id if payload.user_id else (
        current_user.id if current_user.role == RoleEnum.HOSPITAL else None
    )

    if target_user_id:
        existing = db.query(Hospital).filter(
            Hospital.user_id == target_user_id,
            Hospital.is_deleted == False,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A hospital profile is already associated with this user account",
            )

    hospital = Hospital(
        user_id=target_user_id,
        hospital_name=payload.hospital_name,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        contact_number=payload.contact_number,
    )

    try:
        db.add(hospital)
        db.commit()
        db.refresh(hospital)
        return hospital
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create hospital profile: {str(e)}",
        )


@router.get(
    "",
    response_model=List[HospitalResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered hospital profiles",
)
def list_hospital_profiles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    name: Optional[str] = Query(default=None, description="Search filter by hospital name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List Hospital Profiles Endpoint

    Returns list of active hospital profiles. Supports pagination and name search.
    """
    query = db.query(Hospital).filter(Hospital.is_deleted == False)

    if name:
        query = query.filter(Hospital.hospital_name.ilike(f"%{name}%"))

    return query.order_by(Hospital.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/{id}",
    response_model=HospitalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get hospital profile by ID",
)
def get_hospital_profile(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Hospital Profile Endpoint

    Returns details for the specified hospital ID.
    """
    hospital = db.query(Hospital).filter(
        Hospital.id == id,
        Hospital.is_deleted == False,
    ).first()

    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital profile not found",
        )

    return hospital


@router.patch(
    "/{id}",
    response_model=HospitalResponse,
    status_code=status.HTTP_200_OK,
    summary="Update hospital profile",
)
def update_hospital_profile(
    id: uuid.UUID,
    payload: HospitalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.HOSPITAL, RoleEnum.ADMIN)),
):
    """
    Update Hospital Profile Endpoint

    - Requires Hospital role or Admin.
    - Enforces ownership: Hospital users may edit only their assigned profile.
    """
    hospital = db.query(Hospital).filter(
        Hospital.id == id,
        Hospital.is_deleted == False,
    ).first()

    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital profile not found",
        )

    if current_user.role == RoleEnum.HOSPITAL and hospital.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only edit your assigned hospital profile",
        )

    if payload.hospital_name is not None:
        hospital.hospital_name = payload.hospital_name
    if payload.address is not None:
        hospital.address = payload.address
    if payload.latitude is not None:
        hospital.latitude = payload.latitude
    if payload.longitude is not None:
        hospital.longitude = payload.longitude
    if payload.contact_number is not None:
        hospital.contact_number = payload.contact_number

    try:
        db.commit()
        db.refresh(hospital)
        return hospital
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update hospital profile: {str(e)}",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete hospital profile (Soft delete)",
)
def delete_hospital_profile(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.HOSPITAL, RoleEnum.ADMIN)),
):
    """
    Delete Hospital Profile Endpoint

    Soft-deletes the hospital profile. Only assigned Hospital staff or Admins allowed.
    """
    hospital = db.query(Hospital).filter(
        Hospital.id == id,
        Hospital.is_deleted == False,
    ).first()

    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital profile not found",
        )

    if current_user.role == RoleEnum.HOSPITAL and hospital.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only delete your assigned hospital profile",
        )

    hospital.is_deleted = True

    try:
        db.commit()
        return {
            "message": "Hospital profile deleted successfully",
            "id": str(id),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete hospital profile: {str(e)}",
        )
