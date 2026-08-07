"""
Gemini AI Chat Service Module

Provides a standalone, read-only AI Assistant for Blood Relay using Google Gemini.
Answers general queries regarding blood donation, compatibility, emergency requests,
and platform usage without modifying database or executing backend workflows.
"""

from datetime import datetime, timezone
from fastapi import HTTPException, status
import google.generativeai as genai

from app.config import settings
from app.schemas import ChatResponse

SYSTEM_INSTRUCTION = """You are the Blood Relay AI Assistant.

You answer questions related to:
- blood donation
- blood compatibility
- emergency blood requests
- hospitals
- blood banks
- donor eligibility
- Blood Relay platform usage

Never invent backend actions.
Never claim blood has been reserved.
Never claim notifications were sent.
Never claim database updates occurred.
If asked to perform actions, explain that you are an informational assistant only."""


def chat_with_gemini(message: str) -> ChatResponse:
    """
    Generates an AI chat response using Google Gemini:
    1. Validates GEMINI_API_KEY presence (raises 500 if missing).
    2. Configures GenerativeModel with system instructions.
    3. Handles Gemini API errors gracefully (raises 502 without exposing stack traces).
    4. Returns ChatResponse DTO.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API is not configured.",
        )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        response = model.generate_content(message)
        
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
