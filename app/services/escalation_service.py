"""
Nearby Hospital Escalation Service Module

Simulates escalating unfulfilled emergency blood requests to nearby hospitals
within a 30km radius when blood bank inventory and donor radius expansion fail.
"""

from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from app.models import EmergencyRequest, Hospital
from app.schemas import HospitalEscalation, HospitalEscalationSummary
from app.services.matching_service import haversine_distance


def escalate_to_nearby_hospitals(
    db: Session,
    request_obj: EmergencyRequest,
) -> HospitalEscalationSummary:
    """
    Simulates nearby hospital escalation workflow:
    1. Queries active hospitals within 30km radius (excluding issuing hospital).
    2. Uses haversine_distance to compute distance to each hospital.
    3. Sorts hospitals by nearest distance ascending.
    4. Formats HospitalEscalation DTOs for top 5 nearest hospitals.
    5. Returns HospitalEscalationSummary.
    """
    max_radius_km = 30.0

    # 1. Query non-deleted hospitals
    candidate_hospitals = (
        db.query(Hospital)
        .filter(
            Hospital.is_deleted == False,
            Hospital.latitude.isnot(None),
            Hospital.longitude.isnot(None),
        )
        .all()
    )

    escalation_list: List[HospitalEscalation] = []

    for hosp in candidate_hospitals:
        # Exclude issuing hospital if matching request hospital_id
        if hosp.id == request_obj.hospital_id:
            continue

        dist = haversine_distance(
            request_obj.latitude, request_obj.longitude, hosp.latitude, hosp.longitude
        )

        if dist <= max_radius_km:
            # Extract city from address or fallback
            city_str = "Bangalore"
            if hosp.address:
                parts = [p.strip() for p in hosp.address.split(",")]
                if len(parts) >= 2:
                    city_str = parts[1]

            item = HospitalEscalation(
                hospital_id=hosp.id,
                hospital_name=hosp.hospital_name,
                contact_number=hosp.contact_number,
                city=city_str,
                distance_km=round(dist, 2),
                status="queued",
                message="Emergency blood request could not be fulfilled. Please review and assist.",
            )
            escalation_list.append(item)

    # 2. Sort by distance ascending
    escalation_list.sort(key=lambda x: x.distance_km)

    # 3. Take Top 5 nearest hospitals
    top_5_hospitals = escalation_list[:5]

    if top_5_hospitals:
        return HospitalEscalationSummary(
            escalation_success=True,
            total_hospitals_checked=len(escalation_list),
            hospitals_notified=len(top_5_hospitals),
            escalation_timestamp=datetime.now(timezone.utc),
            escalation_reason="No compatible donors found after radius expansion.",
            nearby_hospitals=top_5_hospitals,
        )
    else:
        return HospitalEscalationSummary(
            escalation_success=False,
            total_hospitals_checked=0,
            hospitals_notified=0,
            escalation_timestamp=datetime.now(timezone.utc),
            escalation_reason="No nearby hospitals found within 30km radius.",
            nearby_hospitals=[],
        )
