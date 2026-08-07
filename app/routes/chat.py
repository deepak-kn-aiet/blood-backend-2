"""
AI Assistant Router Module

Provides the standalone POST /ai/chat endpoint for Blood Relay informational queries.
Protected with JWT authentication.
"""

from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.models import User
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat_with_gemini

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with Blood Relay AI Assistant",
    description="Provides an informational AI assistant answering blood donation, compatibility, and platform FAQs.",
)
def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Executes Gemini AI chat query for authenticated users.
    """
    return chat_with_gemini(request.message)
