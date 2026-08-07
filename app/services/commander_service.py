"""
AI Commander Orchestration Service Module

Provides the high-level orchestration entry point for AI workflow execution.
Validates emergency requests, delegates recommendation logic to matching_service,
evaluates workflow decisions via workflow_service, executes blood bank reservations,
triggers donor notification simulations, executes radius expansion logic, and escalates
unfulfilled requests to nearby hospitals.
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
from app.services.notification_service import notify_top_donors
from app.services.radius_service import expand_search_radius
from app.services.escalation_service import escalate_to_nearby_hospitals


def execute_ai_commander(request_id: uuid.UUID, db: Session) -> AICommanderResponse:
    """
    Orchestrates the complete AI recommendation, workflow decision, blood bank reservation,
    donor notification, radius expansion, and hospital escalation pipeline:
    1. Loads specified EmergencyRequest entity.
    2. Validates request existence and non-soft-deleted state (raises 404 if invalid).
    3. Computes AI match recommendation via matching_service.
    4. Evaluates workflow decision via workflow_service.
    5. If next_action == "reserve_blood_bank":
       - Executes blood bank reservation (reservation != None, notification = None, radius_expansion = None, hospital_escalation = None).
       - On reservation failure: Fallbacks next_action to "notify_top_donors", triggers notifications, radius expansion, and escalation if required.
    6. If next_action == "notify_top_donors":
       - Executes donor notification simulation (notification != None).
       - Executes radius expansion to 25km (radius_expansion != None).
       - If radius_expansion.additional_donors_found == 0:
         - Triggers hospital escalation simulation (hospital_escalation != None).
    7. If next_action == "manual_review":
       - Sets all optional fields to None.
    8. Returns combined AICommanderResponse.
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
    notification_info = None
    radius_info = None
    escalation_info = None

    # 3. Branch A: Blood Bank Reservation
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

            # Trigger notification simulation for fallback donors
            notification_info = notify_top_donors(
                db, request_obj, ai_result.top_donors
            )
            radius_info = expand_search_radius(
                db, request_obj, ai_result.top_donors
            )

            if radius_info and radius_info.additional_donors_found == 0:
                escalation_info = escalate_to_nearby_hospitals(db, request_obj)

    # 4. Branch B: Donor Notification, Radius Expansion & Hospital Escalation Simulation
    elif workflow_decision.get("next_action") == "notify_top_donors":
        notification_info = notify_top_donors(
            db, request_obj, ai_result.top_donors
        )
        radius_info = expand_search_radius(
            db, request_obj, ai_result.top_donors
        )

        if radius_info and radius_info.additional_donors_found == 0:
            escalation_info = escalate_to_nearby_hospitals(db, request_obj)

    # 5. Branch C: Manual Review (all optional fields None)

    response_data = ai_result.model_dump()
    response_data.update(workflow_decision)
    response_data["reservation"] = reservation_info
    response_data["notification"] = notification_info
    response_data["radius_expansion"] = radius_info
    response_data["hospital_escalation"] = escalation_info

    return AICommanderResponse(**response_data)
