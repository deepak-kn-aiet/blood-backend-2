"""
AI Commander Orchestration Service Module

Provides the high-level orchestration entry point for AI workflow execution.
Validates emergency requests, delegates recommendation logic to matching_service,
evaluates workflow decisions via workflow_service, and executes blood bank reservations.
"""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import EmergencyRequest, Donor
from app.schemas import AICommanderResponse
from app.services.matching_service import (
    match_request_source,
    get_compatible_blood_groups,
    score_donor,
)
from app.services.workflow_service import determine_next_action
from app.services.reservation_service import reserve_blood_units


def execute_ai_commander(request_id: uuid.UUID, db: Session) -> AICommanderResponse:
    """
    Orchestrates the complete AI recommendation, workflow decision, and blood bank reservation pipeline:
    1. Loads specified EmergencyRequest entity.
    2. Validates request existence and non-soft-deleted state (raises 404 if invalid).
    3. Computes AI match recommendation via matching_service.
    4. Evaluates workflow decision via workflow_service.
    5. If next_action == "reserve_blood_bank", executes blood unit reservation.
       - On success: Returns reservation details.
       - On failure: Gracefully switches next_action to "notify_top_donors" and evaluates donors.
    6. Returns combined AICommanderResponse.
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

    reservation_info = None

    # 3. Execute Blood Bank Reservation if action == "reserve_blood_bank"
    if workflow_decision.get("next_action") == "reserve_blood_bank":
        reservation_info = reserve_blood_units(
            db, request_obj, ai_result.matched_blood_bank
        )

        # Fallback handling if reservation fails due to inventory depletion
        if not reservation_info.reservation_success:
            workflow_decision["next_action"] = "notify_top_donors"
            workflow_decision[
                "workflow_reason"
            ] = "Insufficient inventory during reservation. Switched to donor notification."
            ai_result.recommended_source = "donors"

            # If top_donors list was empty, populate top donor recommendations
            if not ai_result.top_donors:
                compatible_groups = get_compatible_blood_groups(
                    request_obj.blood_group
                )
                active_donors = (
                    db.query(Donor)
                    .filter(
                        Donor.blood_group.in_(compatible_groups),
                        Donor.is_available == True,
                        Donor.is_deleted == False,
                    )
                    .all()
                )
                scored_list = []
                for d in active_donors:
                    scored = score_donor(
                        d, request_obj.latitude, request_obj.longitude
                    )
                    if scored:
                        scored_list.append(scored)
                scored_list.sort(key=lambda x: x.score, reverse=True)
                ai_result.top_donors = scored_list[:5]

    response_data = ai_result.model_dump()
    response_data.update(workflow_decision)
    response_data["reservation"] = reservation_info

    return AICommanderResponse(**response_data)
