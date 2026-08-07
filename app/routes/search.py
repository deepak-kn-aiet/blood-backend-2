"""
Search & Geo-Matching Router Module

Defines the GET /search endpoint to discover available Blood Bank inventories and Donors
within a specified distance radius (in kilometers) using the Haversine geo-distance formula.
"""

import math
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Donor, BloodBank, BloodInventory
from app.enums import BloodGroupEnum
from app.schemas import (
    BloodBankSearchResult,
    DonorSearchResult,
    SearchSummary,
    SearchResponse,
)
from app.auth import get_current_user

router = APIRouter(prefix="/search", tags=["Search & Matching"])


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
    distance = R * c
    return round(distance, 2)


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for matching blood bank stock and donors within radius",
)
def search_blood_and_donors(
    blood_group: BloodGroupEnum = Query(..., description="Target blood group required"),
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Target search latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Target search longitude"),
    radius: float = Query(default=10.0, gt=0.0, le=500.0, description="Search radius distance threshold in kilometers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Geo-Spatial Search API Endpoint

    - Filters Blood Bank inventories matching `blood_group` with `units_available > 0`.
    - Filters Donors matching `blood_group` with `is_available == True`.
    - Computes distance in kilometers using the Haversine formula.
    - Filters results strictly within the specified `radius` threshold.
    - Sorts matching Blood Banks and Donors by nearest `distance_km` ascending.
    """
    matched_blood_banks: List[BloodBankSearchResult] = []
    matched_donors: List[DonorSearchResult] = []

    # 1. Search Blood Bank Inventories
    inventories = (
        db.query(BloodInventory, BloodBank)
        .join(BloodBank, BloodInventory.blood_bank_id == BloodBank.id)
        .filter(
            BloodInventory.blood_group == blood_group,
            BloodInventory.units_available > 0,
            BloodInventory.is_deleted == False,
            BloodBank.is_deleted == False,
        )
        .all()
    )

    for inventory, bank in inventories:
        dist = haversine_distance(latitude, longitude, bank.latitude, bank.longitude)
        if dist <= radius:
            matched_blood_banks.append(
                BloodBankSearchResult(
                    id=bank.id,
                    name=bank.name,
                    address=bank.address,
                    latitude=bank.latitude,
                    longitude=bank.longitude,
                    contact_number=bank.contact_number,
                    units_available=inventory.units_available,
                    blood_group=inventory.blood_group,
                    distance_km=dist,
                )
            )

    # 2. Search Available Donors
    donors_query = (
        db.query(Donor, User)
        .join(User, Donor.user_id == User.id)
        .filter(
            Donor.blood_group == blood_group,
            Donor.is_available == True,
            Donor.is_deleted == False,
            User.is_active == True,
            User.is_deleted == False,
            Donor.latitude.isnot(None),
            Donor.longitude.isnot(None),
        )
        .all()
    )

    for donor, user in donors_query:
        if donor.latitude is not None and donor.longitude is not None:
            dist = haversine_distance(latitude, longitude, donor.latitude, donor.longitude)
            if dist <= radius:
                matched_donors.append(
                    DonorSearchResult(
                        id=donor.id,
                        user_id=donor.user_id,
                        full_name=user.full_name,
                        phone_number=user.phone_number,
                        blood_group=donor.blood_group,
                        city=donor.city,
                        latitude=donor.latitude,
                        longitude=donor.longitude,
                        is_available=donor.is_available,
                        response_rate=donor.response_rate,
                        distance_km=dist,
                    )
                )

    # 3. Sort results by nearest distance
    matched_blood_banks.sort(key=lambda x: x.distance_km)
    matched_donors.sort(key=lambda x: x.distance_km)

    # 4. Construct Summary DTO
    summary = SearchSummary(
        donors_found=len(matched_donors),
        blood_banks_found=len(matched_blood_banks),
        radius=radius,
    )

    return SearchResponse(
        blood_banks=matched_blood_banks,
        donors=matched_donors,
        summary=summary,
    )
