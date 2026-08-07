"""
Blood Bank Reservation Service Module

Simulates blood unit reservation against PostgreSQL inventory records when recommended by the AI Commander.
Handles atomic inventory unit deductions, status updates, and graceful failure handling.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models import EmergencyRequest, BloodInventory, BloodBank
from app.enums import RequestStatusEnum
from app.schemas import MatchedBloodBankInfo, ReservationInfo
from app.services.matching_service import get_compatible_blood_groups


def reserve_blood_units(
    db: Session,
    request_obj: EmergencyRequest,
    matched_blood_bank: Optional[MatchedBloodBankInfo],
) -> ReservationInfo:
    """
    Simulates inventory reservation for an emergency request:
    1. Validates presence of matched blood bank information.
    2. Queries compatible blood inventory at the blood bank.
    3. Verifies units_available >= units_required.
    4. Deducts units, updates request status, commits transaction.
    5. Returns ReservationInfo detailing success or failure.
    """
    if not matched_blood_bank or not matched_blood_bank.id:
        return ReservationInfo(
            reservation_success=False,
            reason="No blood bank specified for reservation.",
        )

    # 1. Determine compatible blood groups for request
    compatible_groups = get_compatible_blood_groups(request_obj.blood_group)

    # 2. Query matching blood inventory record with sufficient units
    inventory = (
        db.query(BloodInventory)
        .filter(
            BloodInventory.blood_bank_id == matched_blood_bank.id,
            BloodInventory.blood_group.in_(compatible_groups),
            BloodInventory.units_available >= request_obj.units_required,
            BloodInventory.is_deleted == False,
        )
        .order_by(BloodInventory.units_available.desc())
        .first()
    )

    # 3. Handle failure if inventory is unavailable or consumed concurrently
    if not inventory:
        return ReservationInfo(
            reservation_success=False,
            reason="Insufficient inventory during reservation.",
        )

    try:
        # 4. Atomic unit deduction & request status update
        inventory.units_available -= request_obj.units_required
        request_obj.status = RequestStatusEnum.MATCHED

        db.commit()
        db.refresh(inventory)

        bg_str = (
            request_obj.blood_group.value
            if hasattr(request_obj.blood_group, "value")
            else str(request_obj.blood_group)
        )

        return ReservationInfo(
            reservation_success=True,
            blood_bank_id=matched_blood_bank.id,
            blood_bank_name=matched_blood_bank.name,
            blood_group=bg_str,
            units_reserved=request_obj.units_required,
            remaining_units=inventory.units_available,
            reservation_timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        db.rollback()
        return ReservationInfo(
            reservation_success=False,
            reason=f"Reservation transaction failed: {str(e)}",
        )
