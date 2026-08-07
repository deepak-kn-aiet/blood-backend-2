"""
Gemini AI Chat Service Module

Provides a standalone, read-only AI Assistant for Blood Relay using Google Gemini.
Answers general queries regarding blood donation, compatibility, emergency requests,
and platform usage, and provides Explainable AI explanations for AI Commander decisions.
Supports in-memory multi-turn conversational session history.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
import google.generativeai as genai

from app.config import settings
from app.schemas import ChatResponse, AIContext
from app.services.chat_history_service import (
    get_or_create_session,
    add_message_to_session,
    get_session_history,
)

SYSTEM_INSTRUCTION = """You are the Blood Relay AI Assistant.

You answer questions related to:
- blood donation and eligibility
- blood group compatibility
- emergency blood requests
- hospitals and blood banks
- Blood Relay platform usage
- explaining AI Commander decisions when context is provided

Guidelines:
- Maintain helpful multi-turn conversation memory with the user.
- If AI Commander context is provided, explain the backend decisions in simple, clear language based strictly on the provided context.
- If asked to explain backend decisions without context, state clearly that decision context is missing.
- Never invent backend actions, database updates, reservations, or notification dispatches.
- You are a read-only informational assistant."""



def chat_with_gemini(
    message: str,
    user_id: uuid.UUID,
    context: Optional[AIContext] = None,
    session_id: Optional[uuid.UUID] = None,
) -> ChatResponse:
    """
    Generates an AI chat response or Explainable AI decision explanation using Google Gemini:
    1. Validates GEMINI_API_KEY presence (raises 500 if missing).
    2. Loads or generates in-memory chat session_id.
    3. Converts existing chat history into Gemini SDK format.
    4. Appends current user prompt and sends to Gemini model.
    5. Saves assistant reply turn to session memory.
    6. Returns ChatResponse DTO.
    """
    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API is not configured.",
        )

    # 1. Resolve / Create Session ID
    sid = get_or_create_session(session_id, user_id)

    # 2. Get past history prior to current message
    past_history = get_session_history(sid, user_id)

    # 3. Add current user message to session
    add_message_to_session(sid, user_id, "user", message)

    # 4. Construct prompt content based on presence of AIContext
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

    # 5. Format Gemini history format: [{"role": "user"|"model", "parts": ["..."]}]
    gemini_history = []
    for msg in past_history:
        g_role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": g_role, "parts": [msg["content"]]})

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
        )

        if gemini_history:
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(prompt_content)
        else:
            response = model.generate_content(prompt_content)

        answer_text = (
            response.text if response and response.text else "No response generated."
        )

        # 6. Save assistant reply turn to session memory
        add_message_to_session(sid, user_id, "assistant", answer_text)

        return ChatResponse(
            answer=answer_text,
            model=settings.GEMINI_MODEL,
            timestamp=datetime.now(timezone.utc),
            session_id=sid,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to generate AI response.",
        )
