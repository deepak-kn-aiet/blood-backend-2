"""
AI Assistant Router Module

Provides the standalone POST /ai/chat, GET /ai/chat/{session_id}, and DELETE /ai/chat/{session_id}
endpoints for Blood Relay informational queries, Explainable AI decision explanations,
and multi-turn chat session history management. Protected with JWT authentication.
"""

import uuid
from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.models import User
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessage,
    ClearChatResponse,
)
from app.services.chat_service import chat_with_gemini
from app.services.chat_history_service import get_session_history, clear_session

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with Blood Relay AI Assistant",
    description="Provides an informational AI assistant answering blood donation, compatibility, platform FAQs, Explainable AI explanations, and multi-turn chat session memory.",
)
def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Executes Gemini AI chat query with optional AI Commander decision context and session memory.
    """
    return chat_with_gemini(
        message=request.message,
        user_id=current_user.id,
        context=request.context,
        session_id=request.session_id,
    )


@router.get(
    "/chat/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get Chat Session History",
    description="Retrieves in-memory conversation message history for a specific session UUID.",
)
def get_chat_history_endpoint(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    """
    Retrieves in-memory message history for an authenticated user's session.
    """
    messages_data = get_session_history(session_id, current_user.id)
    chat_messages = [ChatMessage(**m) for m in messages_data]
    return ChatHistoryResponse(session_id=session_id, messages=chat_messages)


@router.delete(
    "/chat/{session_id}",
    response_model=ClearChatResponse,
    summary="Clear Chat Session History",
    description="Clears in-memory conversation message history for a specific session UUID.",
)
def clear_chat_endpoint(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> ClearChatResponse:
    """
    Clears in-memory chat session history for an authenticated user.
    """
    clear_session(session_id, current_user.id)
    return ClearChatResponse(success=True, message="Conversation cleared.")
