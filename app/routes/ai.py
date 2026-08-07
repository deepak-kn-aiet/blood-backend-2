"""
AI Matching Engine Router Module

Defines the POST /ai/match/{request_id} endpoint to trigger the intelligent donor
and blood bank recommendation workflow for emergency requests.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, EmergencyRequest
from app.schemas import AIMatchResponse
from app.auth import get_current_user
from app.services.matching_service import match_request_source

router = APIRouter(prefix="/ai", tags=["AI Matching Engine"])


@router.post(
    "/match/{request_id}",
    response_model=AIMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate intelligent donor or blood bank recommendation for request",
)
def match_emergency_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI Recommendation Endpoint

    - Loads the specified `EmergencyRequest`.
    - Verifies request existence (raises HTTP 404 if missing or soft-deleted).
    - Evaluates Blood Bank stock: if sufficient inventory exists, recommends nearest Blood Bank.
    - Otherwise, searches compatible active Donors, scores them (Availability, Proximity, Response Rate, Recency),
      and returns the Top 5 ranked donors with detailed scoring reason breakdowns.
    """
    request_obj = (
        db.query(EmergencyRequest)
        .filter(
            EmergencyRequest.id == request_id,
            EmergencyRequest.is_deleted == False,
        )
        .first()
    )

    if not request_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency request not found",
        )

    return match_request_source(db, request_obj)
