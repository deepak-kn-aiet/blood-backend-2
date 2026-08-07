"""
Donor Profiles Router Module

Defines API endpoints for donor profile registration, retrieval, updating, and soft-deletion.
Enforces strict profile ownership rules.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Donor
from app.enums import RoleEnum, BloodGroupEnum
from app.schemas import (
    DonorCreate,
    DonorUpdate,
    DonorResponse,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/donors", tags=["Donor Profiles"])


@router.post(
    "",
    response_model=DonorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a donor profile for authenticated user",
)
def create_donor_profile(
    payload: DonorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Donor Profile Endpoint

    Links a donor profile to the currently authenticated user.
    Prevents duplicate donor profile creation per user account.
    """
    # Check if user already has an active donor profile
    existing_donor = db.query(Donor).filter(
        Donor.user_id == current_user.id,
        Donor.is_deleted == False,
    ).first()

    if existing_donor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A donor profile already exists for this user account",
        )

    donor = Donor(
        user_id=current_user.id,
        blood_group=payload.blood_group,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_available=payload.is_available,
        last_donation_date=payload.last_donation_date,
        response_rate=payload.response_rate,
        health_status=payload.health_status,
    )

    try:
        db.add(donor)
        db.commit()
        db.refresh(donor)
        return donor
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create donor profile: {str(e)}",
        )


@router.get(
    "",
    response_model=List[DonorResponse],
    status_code=status.HTTP_200_OK,
    summary="List donor profiles",
)
def list_donor_profiles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    city: Optional[str] = Query(default=None),
    blood_group: Optional[BloodGroupEnum] = Query(default=None),
    is_available: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List Donor Profiles Endpoint

    Supports pagination and optional filtering by city, blood group, or availability.
    """
    query = db.query(Donor).filter(Donor.is_deleted == False)

    if city:
        query = query.filter(Donor.city.ilike(f"%{city}%"))
    if blood_group:
        query = query.filter(Donor.blood_group == blood_group)
    if is_available is not None:
        query = query.filter(Donor.is_available == is_available)

    return query.order_by(Donor.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/{id}",
    response_model=DonorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get donor profile by ID",
)
def get_donor_profile(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Donor Profile Endpoint

    Returns donor profile details for specified ID.
    """
    donor = db.query(Donor).filter(
        Donor.id == id,
        Donor.is_deleted == False,
    ).first()

    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found",
        )

    return donor


@router.patch(
    "/{id}",
    response_model=DonorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update donor profile",
)
def update_donor_profile(
    id: uuid.UUID,
    payload: DonorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update Donor Profile Endpoint

    - Ownership Enforcement: A donor may edit ONLY their own profile (or Admin).
    """
    donor = db.query(Donor).filter(
        Donor.id == id,
        Donor.is_deleted == False,
    ).first()

    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found",
        )

    # Ownership check: User can only update their own profile unless Admin
    if donor.user_id != current_user.id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only edit your own donor profile",
        )

    if payload.blood_group is not None:
        donor.blood_group = payload.blood_group
    if payload.city is not None:
        donor.city = payload.city
    if payload.latitude is not None:
        donor.latitude = payload.latitude
    if payload.longitude is not None:
        donor.longitude = payload.longitude
    if payload.is_available is not None:
        donor.is_available = payload.is_available
    if payload.last_donation_date is not None:
        donor.last_donation_date = payload.last_donation_date
    if payload.health_status is not None:
        donor.health_status = payload.health_status

    try:
        db.commit()
        db.refresh(donor)
        return donor
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update donor profile: {str(e)}",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete donor profile (Soft delete)",
)
def delete_donor_profile(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete Donor Profile Endpoint

    - Ownership Enforcement: A donor may delete ONLY their own profile (or Admin).
    """
    donor = db.query(Donor).filter(
        Donor.id == id,
        Donor.is_deleted == False,
    ).first()

    if not donor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donor profile not found",
        )

    # Ownership check
    if donor.user_id != current_user.id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You can only delete your own donor profile",
        )

    donor.is_deleted = True

    try:
        db.commit()
        return {
            "message": "Donor profile deleted successfully",
            "id": str(id),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete donor profile: {str(e)}",
        )
