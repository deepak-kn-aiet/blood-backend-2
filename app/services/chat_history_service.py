"""
In-Memory Chat History Management Service Module

Provides light-weight, user-isolated session history management for multi-turn Gemini chat.
Maintains history capped at 20 messages per session without database persistence.
"""

import uuid
from typing import Dict, List, Optional
from fastapi import HTTPException, status

MAX_HISTORY_MESSAGES = 20

# In-memory session store: {session_id: {"user_id": UUID, "messages": [{"role": "user"|"assistant", "content": "..."}]}}
_chat_sessions: Dict[uuid.UUID, Dict] = {}


def get_or_create_session(session_id: Optional[uuid.UUID], user_id: uuid.UUID) -> uuid.UUID:
    """
    Returns valid session_id; generates a new UUID if None.
    Enforces user isolation (raises 403 if user attempts to access another user's session).
    """
    if not session_id:
        session_id = uuid.uuid4()

    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = {
            "user_id": user_id,
            "messages": [],
        }
    else:
        if _chat_sessions[session_id]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session.",
            )

    return session_id


def add_message_to_session(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    content: str,
) -> None:
    """
    Appends message turn to session history and caps total stored history to 20 messages.
    """
    sid = get_or_create_session(session_id, user_id)
    session_data = _chat_sessions[sid]

    session_data["messages"].append({"role": role, "content": content})

    # Cap to MAX_HISTORY_MESSAGES (discard oldest if exceeded)
    if len(session_data["messages"]) > MAX_HISTORY_MESSAGES:
        session_data["messages"] = session_data["messages"][-MAX_HISTORY_MESSAGES:]


def get_session_history(session_id: uuid.UUID, user_id: uuid.UUID) -> List[Dict]:
    """
    Retrieves session message turns after validating session existence and user ownership.
    """
    if session_id not in _chat_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    if _chat_sessions[session_id]["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session.",
        )

    return _chat_sessions[session_id]["messages"]


def clear_session(session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """
    Removes chat session from in-memory dictionary after validating ownership.
    """
    if session_id not in _chat_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    if _chat_sessions[session_id]["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this chat session.",
        )

    del _chat_sessions[session_id]
    return True
