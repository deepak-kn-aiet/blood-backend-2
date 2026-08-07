"""
Radius Expansion Service Module

Simulates expanding the donor search radius from 10km to 25km when initial donor notifications
produce no response. Reuses existing AI matching scoring and blood group compatibility logic
to discover and rank NEW compatible donors.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import EmergencyRequest, Donor, User
from app.schemas import ScoredDonorResult, RadiusExpansionSummary
from app.services.matching_service import (
    get_compatible_blood_groups,
    haversine_distance,
    score_donor,
)


def expand_search_radius(
    db: Session,
    request_obj: EmergencyRequest,
    existing_donors: Optional[List[ScoredDonorResult]],
) -> RadiusExpansionSummary:
    """
    Simulates radius expansion workflow from 10km to 25km:
    1. Collects already notified donor IDs to exclude duplicates.
    2. Searches active, compatible donors within 25km radius.
    3. Evaluates and scores newly discovered donors using the AI engine.
    4. Ranks new donors and returns up to 10 expanded donors.
    5. Returns RadiusExpansionSummary.
    """
    previous_radius_km = 10.0
    expanded_radius_km = 25.0

    # 1. Identify excluded donor IDs (already notified in initial batch)
    excluded_ids = (
        {d.id for d in existing_donors} if existing_donors else set()
    )

    # 2. Query active, non-deleted compatible donors
    compatible_groups = get_compatible_blood_groups(request_obj.blood_group)
    candidate_donors = (
        db.query(Donor)
        .join(User, Donor.user_id == User.id)
        .filter(
            Donor.blood_group.in_(compatible_groups),
            Donor.is_available == True,
            Donor.is_deleted == False,
            User.is_active == True,
            User.is_deleted == False,
            Donor.latitude.isnot(None),
            Donor.longitude.isnot(None),
        )
        .all()
    )

    # 3. Filter distance within expanded radius & exclude previously notified donors
    expanded_scored_list: List[ScoredDonorResult] = []
    for d in candidate_donors:
        if d.id in excluded_ids:
            continue

        dist = haversine_distance(
            request_obj.latitude, request_obj.longitude, d.latitude, d.longitude
        )

        if dist <= expanded_radius_km:
            scored = score_donor(d, request_obj.latitude, request_obj.longitude)
            if scored:
                expanded_scored_list.append(scored)

    # 4. Sort newly discovered donors by AI matching score descending
    expanded_scored_list.sort(key=lambda x: x.score, reverse=True)

    # 5. Cap expanded donors to maximum 10
    top_expanded_donors = expanded_scored_list[:10]
    total_existing_count = len(existing_donors) if existing_donors else 0

    if top_expanded_donors:
        return RadiusExpansionSummary(
            expansion_performed=True,
            previous_radius_km=previous_radius_km,
            expanded_radius_km=expanded_radius_km,
            additional_donors_found=len(top_expanded_donors),
            total_donors_after_expansion=total_existing_count + len(top_expanded_donors),
            expanded_donors=top_expanded_donors,
            expansion_reason="No response from initial Top 5 donors. Radius expanded from 10km to 25km.",
        )
    else:
        return RadiusExpansionSummary(
            expansion_performed=False,
            previous_radius_km=previous_radius_km,
            expanded_radius_km=expanded_radius_km,
            additional_donors_found=0,
            total_donors_after_expansion=total_existing_count,
            expanded_donors=[],
            expansion_reason="Radius expansion to 25km produced no additional compatible donors.",
        )
