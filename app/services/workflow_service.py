"""
Workflow Decision Engine Module

Evaluates AI matching outputs and determines the next operational action
(e.g., blood bank reservation, donor notification, or manual review) without executing side effects.
"""

from typing import Dict, Any
from app.schemas import AIMatchResponse


def determine_next_action(ai_result: AIMatchResponse) -> Dict[str, str]:
    """
    Determines the next workflow step based on AI matching recommendation results:

    Case 1 - Blood Bank Available:
        If recommended_source == "blood_bank", returns reserve_blood_bank action.

    Case 2 - Donors Available:
        If recommended_source == "donors", returns notify_top_donors action.

    Case 3 - No Match:
        Otherwise, returns manual_review action.
    """
    source = getattr(ai_result, "recommended_source", None)
    if isinstance(ai_result, dict):
        source = ai_result.get("recommended_source")

    if source == "blood_bank":
        return {
            "next_action": "reserve_blood_bank",
            "workflow_reason": "Compatible blood inventory is available and sufficient.",
        }
    elif source == "donors":
        return {
            "next_action": "notify_top_donors",
            "workflow_reason": "Compatible inventory unavailable. Notify highest ranked donors.",
        }
    else:
        return {
            "next_action": "manual_review",
            "workflow_reason": "No compatible blood source could be identified.",
        }
