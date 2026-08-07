"""
AI Commander Orchestration Service Module

Provides the high-level orchestration entry point for AI workflow execution.
Validates emergency requests, delegates recommendation logic to matching_service,
and determines the next operational action via workflow_service.
"""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import EmergencyRequest
from app.schemas import AICommanderResponse
from app.services.matching_service import match_request_source
from app.services.workflow_service import determine_next_action


def execute_ai_commander(request_id: uuid.UUID, db: Session) -> AICommanderResponse:
    """
    Orchestrates the complete AI recommendation and workflow decision pipeline:
    1. Loads specified EmergencyRequest entity.
    2. Validates request existence and non-soft-deleted state (raises 404 if invalid).
    3. Computes AI match recommendation via matching_service.
    4. Evaluates workflow decision via workflow_service.
    5. Returns combined AICommanderResponse containing matching details and next_action.
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

    # 1. Compute AI Match Recommendation
    ai_result = match_request_source(db, request_obj)

    # 2. Determine Next Workflow Operational Action
    workflow_decision = determine_next_action(ai_result)

    # 3. Merge AI result with workflow decision
    response_data = ai_result.model_dump()
    response_data.update(workflow_decision)

    return AICommanderResponse(**response_data)
