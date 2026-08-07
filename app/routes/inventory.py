"""
Blood Inventory Router Module

Defines API endpoints for managing blood inventory units at blood banks.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, BloodBank, BloodInventory
from app.enums import RoleEnum, BloodGroupEnum
from app.schemas import (
    BloodInventoryCreate,
    BloodInventoryUpdate,
    BloodInventoryResponse,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/inventory", tags=["Blood Inventory"])


@router.post(
    "",
    response_model=BloodInventoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add blood inventory units",
)
def create_inventory_item(
    payload: BloodInventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.BLOOD_BANK, RoleEnum.ADMIN)),
):
    """
    Add Blood Inventory Endpoint

    - Only Blood Bank staff or Admins can modify inventory.
    - Validates blood bank existence.
    """
    # Verify blood bank existence
    blood_bank = db.query(BloodBank).filter(
        BloodBank.id == payload.blood_bank_id,
        BloodBank.is_deleted == False,
    ).first()

    if not blood_bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood Bank with specified ID does not exist",
        )

    inventory_item = BloodInventory(
        blood_bank_id=payload.blood_bank_id,
        blood_group=payload.blood_group,
        units_available=payload.units_available,
        expiry_date=payload.expiry_date,
    )

    try:
        db.add(inventory_item)
        db.commit()
        db.refresh(inventory_item)
        return inventory_item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add inventory record: {str(e)}",
        )


@router.get(
    "",
    response_model=List[BloodInventoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List blood inventory records",
)
def list_inventory_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    blood_bank_id: Optional[uuid.UUID] = Query(default=None),
    blood_group: Optional[BloodGroupEnum] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List Blood Inventory Endpoint

    Allows citizens and authenticated users to read available blood inventory.
    """
    query = db.query(BloodInventory).filter(BloodInventory.is_deleted == False)

    if blood_bank_id:
        query = query.filter(BloodInventory.blood_bank_id == blood_bank_id)
    if blood_group:
        query = query.filter(BloodInventory.blood_group == blood_group)

    return query.order_by(BloodInventory.updated_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/{id}",
    response_model=BloodInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory record details by ID",
)
def get_inventory_item(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Blood Inventory Endpoint

    Returns inventory record by ID.
    """
    item = db.query(BloodInventory).filter(
        BloodInventory.id == id,
        BloodInventory.is_deleted == False,
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood inventory record not found",
        )

    return item


@router.patch(
    "/{id}",
    response_model=BloodInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update blood inventory record",
)
def update_inventory_item(
    id: uuid.UUID,
    payload: BloodInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.BLOOD_BANK, RoleEnum.ADMIN)),
):
    """
    Update Blood Inventory Endpoint

    - Only Blood Bank staff or Admins can modify inventory.
    """
    item = db.query(BloodInventory).filter(
        BloodInventory.id == id,
        BloodInventory.is_deleted == False,
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood inventory record not found",
        )

    if payload.units_available is not None:
        item.units_available = payload.units_available
    if payload.expiry_date is not None:
        item.expiry_date = payload.expiry_date
    if payload.blood_group is not None:
        item.blood_group = payload.blood_group

    try:
        db.commit()
        db.refresh(item)
        return item
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update inventory record: {str(e)}",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete blood inventory record (Soft delete)",
)
def delete_inventory_item(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.BLOOD_BANK, RoleEnum.ADMIN)),
):
    """
    Delete Blood Inventory Endpoint

    Soft-deletes the inventory record. Only Blood Bank staff or Admins allowed.
    """
    item = db.query(BloodInventory).filter(
        BloodInventory.id == id,
        BloodInventory.is_deleted == False,
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blood inventory record not found",
        )

    item.is_deleted = True

    try:
        db.commit()
        return {
            "message": "Blood inventory record deleted successfully",
            "id": str(id),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete inventory record: {str(e)}",
        )
