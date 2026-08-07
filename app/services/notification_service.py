"""
Donor Notification Service Module

Simulates donor notification dispatch for emergency blood requests.
Formats queued notifications for top ranked donors without external SDKs or database mutations.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import EmergencyRequest
from app.schemas import ScoredDonorResult, DonorNotification, NotificationSummary


def notify_top_donors(
    db: Session,
    request_obj: EmergencyRequest,
    donors: Optional[List[ScoredDonorResult]],
) -> NotificationSummary:
    """
    Simulates queuing notifications for top-ranked donors:
    1. Selects maximum Top 5 donors preserving AI ranking score & order.
    2. Constructs DonorNotification DTOs with status 'queued'.
    3. Handles empty or None donor lists gracefully without raising HTTP 500.
    4. Returns a NotificationSummary DTO.
    """
    if not donors:
        return NotificationSummary(
            notification_success=False,
            total_donors=0,
            notified_count=0,
            failed_count=0,
            notification_timestamp=datetime.now(timezone.utc),
            notifications=[],
        )

    # 1. Select top 5 donors, preserving exact AI ranking order
    top_5_donors = donors[:5]
    notifications_list: List[DonorNotification] = []

    for d in top_5_donors:
        notification_entry = DonorNotification(
            donor_id=d.id,
            full_name=d.full_name,
            phone_number=d.phone_number,
            score=d.score,
            status="queued",
            message="Emergency blood request nearby. Please respond if available.",
        )
        notifications_list.append(notification_entry)

    return NotificationSummary(
        notification_success=True,
        total_donors=len(donors),
        notified_count=len(notifications_list),
        failed_count=0,
        notification_timestamp=datetime.now(timezone.utc),
        notifications=notifications_list,
    )
