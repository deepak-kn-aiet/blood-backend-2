"""
Emergency Requests Router Module

Defines API endpoints for creating, retrieving, updating status, and deleting emergency blood requests.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Hospital, EmergencyRequest
from app.enums import RoleEnum, BloodGroupEnum, RequestStatusEnum
from app.schemas import (
    EmergencyRequestCreate,
    EmergencyRequestUpdateStatus,
    EmergencyRequestResponse,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/requests", tags=["Emergency Requests"])


@router.post(
    "",
    response_model=EmergencyRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new emergency blood request",
)
def create_emergency_request(
    payload: EmergencyRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Emergency Request Endpoint

    - Only authenticated users may issue emergency requests.
    - Validates target hospital existence.
    """
    # Verify hospital existence
    hospital = db.query(Hospital).filter(
        Hospital.id == payload.hospital_id,
        Hospital.is_deleted == False,
    ).first()

    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital with specified ID does not exist",
        )

    new_request = EmergencyRequest(
        patient_name=payload.patient_name,
        blood_group=payload.blood_group,
        units_required=payload.units_required,
        hospital_id=payload.hospital_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status=RequestStatusEnum.PENDING,
    )

    try:
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create emergency request: {str(e)}",
        )


@router.get(
    "",
    response_model=List[EmergencyRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List all emergency blood requests",
)
def list_emergency_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    req_status: Optional[RequestStatusEnum] = Query(default=None, alias="status"),
    blood_group: Optional[BloodGroupEnum] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List Emergency Requests Endpoint

    Supports pagination and optional filtering by status or blood group.
    """
    query = db.query(EmergencyRequest).filter(EmergencyRequest.is_deleted == False)

    if req_status:
        query = query.filter(EmergencyRequest.status == req_status)
    if blood_group:
        query = query.filter(EmergencyRequest.blood_group == blood_group)

    return query.order_by(EmergencyRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/{id}",
    response_model=EmergencyRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get emergency request details by ID",
)
def get_emergency_request(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Emergency Request Endpoint

    Returns request details for the specified request ID.
    """
    request_obj = db.query(EmergencyRequest).filter(
        EmergencyRequest.id == id,
        EmergencyRequest.is_deleted == False,
    ).first()

    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency request not found",
        )

    return request_obj


@router.patch(
    "/{id}/status",
    response_model=EmergencyRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Update status of an emergency request",
)
def update_emergency_request_status(
    id: uuid.UUID,
    payload: EmergencyRequestUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.HOSPITAL, RoleEnum.ADMIN)),
):
    """
    Update Request Status Endpoint

    - Only Hospital staff or Admins are authorized to update status.
    - Status transitions: pending -> searching -> matched -> completed / cancelled.
    """
    request_obj = db.query(EmergencyRequest).filter(
        EmergencyRequest.id == id,
        EmergencyRequest.is_deleted == False,
    ).first()

    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency request not found",
        )

    # If current user is Hospital role, verify ownership of request's hospital
    if current_user.role == RoleEnum.HOSPITAL and current_user.hospital:
        if request_obj.hospital_id != current_user.hospital.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update status for another hospital's request",
            )

    request_obj.status = payload.status

    try:
        db.commit()
        db.refresh(request_obj)
        return request_obj
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update request status: {str(e)}",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an emergency request (Soft delete)",
)
def delete_emergency_request(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.HOSPITAL, RoleEnum.ADMIN)),
):
    """
    Delete Emergency Request Endpoint

    Soft-deletes the emergency request. Only Hospital staff or Admins allowed.
    """
    request_obj = db.query(EmergencyRequest).filter(
        EmergencyRequest.id == id,
        EmergencyRequest.is_deleted == False,
    ).first()

    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency request not found",
        )

    request_obj.is_deleted = True

    try:
        db.commit()
        return {
            "message": "Emergency request deleted successfully",
            "id": str(id),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete request: {str(e)}",
        )
