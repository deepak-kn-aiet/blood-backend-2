"""
Gemini AI Chat Service Module

Provides a standalone, read-only AI Assistant for Blood Relay using Google Gemini.
Answers general queries regarding blood donation, compatibility, emergency requests,
and platform usage, and provides Explainable AI explanations for AI Commander decisions.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
import google.generativeai as genai

from app.config import settings
from app.schemas import ChatResponse, AIContext

SYSTEM_INSTRUCTION = """You are the Explainable AI Assistant for Blood Relay.

Explain backend decisions in simple language.

Never invent facts.
Only use the provided AI Commander context.
If context is missing, clearly say that you cannot explain the decision.
Never claim actions happened unless they appear in the supplied context.
Never modify backend state.
You are a read-only assistant."""


def chat_with_gemini(
    message: str,
    context: Optional[AIContext] = None,
) -> ChatResponse:
    """
    Generates an AI chat response or Explainable AI decision explanation using Google Gemini:
    1. Validates GEMINI_API_KEY presence (raises 500 if missing).
    2. Constructs context-aware prompt if AIContext is supplied.
    3. Handles Gemini API errors gracefully (raises 502 without exposing stack traces).
    4. Returns ChatResponse DTO.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API is not configured.",
        )

    # Construct prompt content based on presence of AIContext
    if context:
        context_dict = context.model_dump()
        prompt_parts = [
            f"User Question: {message}",
            "\nProvided AI Commander Context:",
            f"- Request ID: {context_dict.get('request_id')}",
            f"- Recommended Source: {context_dict.get('recommended_source')}",
            f"- Blood Bank Available: {context_dict.get('blood_bank_available')}",
            f"- Matched Blood Bank: {context_dict.get('matched_blood_bank')}",
            f"- Top Donors: {context_dict.get('top_donors')}",
            f"- Next Action: {context_dict.get('next_action')}",
            f"- Workflow Reason: {context_dict.get('workflow_reason')}",
            f"- Reservation Details: {context_dict.get('reservation')}",
            f"- Notification Details: {context_dict.get('notification')}",
            f"- Radius Expansion Details: {context_dict.get('radius_expansion')}",
            f"- Hospital Escalation Details: {context_dict.get('hospital_escalation')}",
            "\nPlease explain clearly in friendly, natural language WHY these specific decisions were made based strictly on this provided AI Commander context.",
        ]
        prompt_content = "\n".join(prompt_parts)
    else:
        prompt_content = message

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        response = model.generate_content(prompt_content)
        
        answer_text = response.text if response and response.text else "No response generated."
        
        return ChatResponse(
            answer=answer_text,
            model=settings.GEMINI_MODEL,
            timestamp=datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to generate AI response.",
        )
