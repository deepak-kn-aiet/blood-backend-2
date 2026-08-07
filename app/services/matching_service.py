"""
AI Matching Engine Service Module

Contains core algorithmic business logic for evaluating emergency blood requests,
checking blood bank inventory sufficiency, and scoring/ranking compatible donors.
Includes blood group compatibility mapping for medical donor-recipient matching.
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import User, Donor, BloodBank, BloodInventory, EmergencyRequest
from app.enums import BloodGroupEnum
from app.schemas import (
    MatchedBloodBankInfo,
    ScoredDonorResult,
    AIMatchSearchSummary,
    AIMatchResponse,
)

# Reusable Blood Group Compatibility Matrix
# Maps Recipient Blood Group -> Compatible Donor/Inventory Blood Groups
COMPATIBILITY_MAP = {
    BloodGroupEnum.O_NEGATIVE: [BloodGroupEnum.O_NEGATIVE],
    BloodGroupEnum.O_POSITIVE: [BloodGroupEnum.O_POSITIVE, BloodGroupEnum.O_NEGATIVE],
    BloodGroupEnum.A_NEGATIVE: [BloodGroupEnum.A_NEGATIVE, BloodGroupEnum.O_NEGATIVE],
    BloodGroupEnum.A_POSITIVE: [
        BloodGroupEnum.A_POSITIVE,
        BloodGroupEnum.A_NEGATIVE,
        BloodGroupEnum.O_POSITIVE,
        BloodGroupEnum.O_NEGATIVE,
    ],
    BloodGroupEnum.B_NEGATIVE: [BloodGroupEnum.B_NEGATIVE, BloodGroupEnum.O_NEGATIVE],
    BloodGroupEnum.B_POSITIVE: [
        BloodGroupEnum.B_POSITIVE,
        BloodGroupEnum.B_NEGATIVE,
        BloodGroupEnum.O_POSITIVE,
        BloodGroupEnum.O_NEGATIVE,
    ],
    BloodGroupEnum.AB_NEGATIVE: [
        BloodGroupEnum.AB_NEGATIVE,
        BloodGroupEnum.A_NEGATIVE,
        BloodGroupEnum.B_NEGATIVE,
        BloodGroupEnum.O_NEGATIVE,
    ],
    BloodGroupEnum.AB_POSITIVE: [
        BloodGroupEnum.AB_POSITIVE,
        BloodGroupEnum.AB_NEGATIVE,
        BloodGroupEnum.A_POSITIVE,
        BloodGroupEnum.A_NEGATIVE,
        BloodGroupEnum.B_POSITIVE,
        BloodGroupEnum.B_NEGATIVE,
        BloodGroupEnum.O_POSITIVE,
        BloodGroupEnum.O_NEGATIVE,
    ],
}


def get_compatible_blood_groups(request_group: BloodGroupEnum) -> List[BloodGroupEnum]:
    """
    Returns a list of compatible donor/inventory blood groups
    for a given recipient request blood group based on standard red cell compatibility rules.
    """
    return COMPATIBILITY_MAP.get(request_group, [request_group])


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth in kilometers
    using the Haversine formula.
    """
    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def score_donor(donor: Donor, user: User, request: EmergencyRequest) -> ScoredDonorResult:
    """
    Evaluates a candidate donor against an EmergencyRequest and calculates
    a matching score (max 100 points) based on four weighted criteria:
    1. Availability: 40 points
    2. Distance Proximity: Up to 30 points
    3. Response Rate: Up to 20 points
    4. Last Donation Recency: Up to 10 points
    """
    reasons: List[str] = []

    # 1. Availability Score (40 pts)
    availability_score = 40.0
    reasons.append("Available for urgent donation (+40 pts)")

    # 2. Distance Score (Up to 30 pts)
    dist_km = haversine_distance(request.latitude, request.longitude, donor.latitude, donor.longitude)
    if dist_km < 5.0:
        dist_score = 30.0
        reasons.append(f"Proximity: {dist_km} km away (<5 km) (+30 pts)")
    elif 5.0 <= dist_km <= 10.0:
        dist_score = 20.0
        reasons.append(f"Proximity: {dist_km} km away (5-10 km) (+20 pts)")
    elif 10.0 < dist_km <= 20.0:
        dist_score = 10.0
        reasons.append(f"Proximity: {dist_km} km away (10-20 km) (+10 pts)")
    else:
        dist_score = 0.0
        reasons.append(f"Proximity: {dist_km} km away (>20 km) (+0 pts)")

    # 3. Response Rate Score (Up to 20 pts)
    rate = donor.response_rate
    if rate >= 95.0:
        rate_score = 20.0
        reasons.append(f"High response rate: {rate}% (>=95%) (+20 pts)")
    elif 80.0 <= rate < 95.0:
        rate_score = 15.0
        reasons.append(f"Good response rate: {rate}% (80-95%) (+15 pts)")
    elif 60.0 <= rate < 80.0:
        rate_score = 10.0
        reasons.append(f"Moderate response rate: {rate}% (60-80%) (+10 pts)")
    else:
        rate_score = 5.0
        reasons.append(f"Low response rate: {rate}% (<60%) (+5 pts)")

    # 4. Last Donation Recency Score (Up to 10 pts)
    if donor.last_donation_date is not None:
        now = datetime.now(timezone.utc)
        last_donation = donor.last_donation_date
        if last_donation.tzinfo is None:
            last_donation = last_donation.replace(tzinfo=timezone.utc)
        days_elapsed = (now - last_donation).days
    else:
        days_elapsed = 999  # No prior record, fully eligible

    if days_elapsed > 120:
        recency_score = 10.0
        days_str = "No prior" if donor.last_donation_date is None else f"{days_elapsed}"
        reasons.append(f"Eligible donation recency: {days_str} days (>120 days) (+10 pts)")
    elif 90 <= days_elapsed <= 120:
        recency_score = 8.0
        reasons.append(f"Eligible donation recency: {days_elapsed} days (90-120 days) (+8 pts)")
    elif 60 <= days_elapsed < 90:
        recency_score = 5.0
        reasons.append(f"Recent donation: {days_elapsed} days (60-90 days) (+5 pts)")
    else:
        recency_score = 0.0
        reasons.append(f"Ineligible donation recency: {days_elapsed} days (<60 days) (+0 pts)")

    total_score = availability_score + dist_score + rate_score + recency_score

    return ScoredDonorResult(
        id=donor.id,
        user_id=donor.user_id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        blood_group=donor.blood_group,
        city=donor.city,
        distance_km=dist_km,
        score=total_score,
        response_rate=rate,
        reasons=reasons,
    )


def match_request_source(db: Session, request_obj: EmergencyRequest) -> AIMatchResponse:
    """
    Executes the full AI matching recommendation workflow for an EmergencyRequest:
    1. Determines medical blood group compatibility using get_compatible_blood_groups().
    2. Checks BloodBank inventories matching compatible blood groups with units_available >= units_required.
    3. If stock is available, selects the nearest Blood Bank facility.
    4. If stock is insufficient, searches available compatible Donors, scores them, and returns Top 5.
    """
    compatible_groups = get_compatible_blood_groups(request_obj.blood_group)

    # 1. Search Blood Bank Inventories with compatibility filtering
    matching_inventories = (
        db.query(BloodInventory, BloodBank)
        .join(BloodBank, BloodInventory.blood_bank_id == BloodBank.id)
        .filter(
            BloodInventory.blood_group.in_(compatible_groups),
            BloodInventory.units_available >= request_obj.units_required,
            BloodInventory.is_deleted == False,
            BloodBank.is_deleted == False,
        )
        .all()
    )

    if matching_inventories:
        # Calculate distance to each matching blood bank and pick the nearest
        bank_matches: List[Tuple[float, BloodInventory, BloodBank]] = []
        for inv, bank in matching_inventories:
            d_km = haversine_distance(request_obj.latitude, request_obj.longitude, bank.latitude, bank.longitude)
            bank_matches.append((d_km, inv, bank))

        bank_matches.sort(key=lambda x: x[0])  # Nearest first
        nearest_dist, nearest_inv, nearest_bank = bank_matches[0]

        matched_bank_info = MatchedBloodBankInfo(
            id=nearest_bank.id,
            name=nearest_bank.name,
            address=nearest_bank.address,
            contact_number=nearest_bank.contact_number,
            units_available=nearest_inv.units_available,
            distance_km=nearest_dist,
        )

        return AIMatchResponse(
            request_id=request_obj.id,
            recommended_source="blood_bank",
            blood_bank_available=True,
            matched_blood_bank=matched_bank_info,
            top_donors=[],
            search_summary=AIMatchSearchSummary(
                total_donors_evaluated=0,
                top_donors_returned=0,
                blood_banks_checked=len(matching_inventories),
            ),
        )

    # 2. Search Available Donors with compatibility filtering
    donors_query = (
        db.query(Donor, User)
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

    scored_donors: List[ScoredDonorResult] = []
    for donor, user in donors_query:
        scored = score_donor(donor, user, request_obj)
        scored_donors.append(scored)

    # Sort donors by score descending (highest score first)
    scored_donors.sort(key=lambda x: x.score, reverse=True)
    top_5_donors = scored_donors[:5]

    return AIMatchResponse(
        request_id=request_obj.id,
        recommended_source="donors",
        blood_bank_available=False,
        matched_blood_bank=None,
        top_donors=top_5_donors,
        search_summary=AIMatchSearchSummary(
            total_donors_evaluated=len(scored_donors),
            top_donors_returned=len(top_5_donors),
            blood_banks_checked=0,
        ),
    )
