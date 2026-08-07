"""
AI Commander Orchestration Service Module

Provides the high-level orchestration entry point for AI workflow execution.
Validates emergency requests and delegates recommendation logic to matching_service.
"""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import EmergencyRequest
from app.schemas import AIMatchResponse
from app.services.matching_service import match_request_source


def execute_ai_commander(request_id: uuid.UUID, db: Session) -> AIMatchResponse:
    """
    Orchestrates the AI recommendation workflow for an EmergencyRequest:
    1. Loads the specified EmergencyRequest entity.
    2. Validates request existence and non-soft-deleted state (raises 404 if invalid).
    3. Delegates match computation to the matching service.
    4. Returns the structured AIMatchResponse.
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
