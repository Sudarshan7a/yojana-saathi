from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from agent.conversation import ConversationManager
from database import get_db
from middleware.auth import get_current_user
from models import Conversation, Message, UserProfile

router = APIRouter()

PROFILE_FIELDS = [
    "name",
    "age",
    "gender",
    "state",
    "area",
    "caste_category",
    "annual_income",
    "has_disability",
    "occupation",
    "is_student",
    "education_level",
    "marital_status",
    "has_children",
    "is_pregnant",
    "bpl_card",
    "goals",
]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    question: str


def _serialize_message(message: Message) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def _get_or_create_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        return profile

    profile = UserProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _serialize_profile(profile: UserProfile) -> dict:
    return {field: getattr(profile, field) for field in PROFILE_FIELDS}


def _serialize_tracker(profile: UserProfile) -> dict:
    return {field: getattr(profile, field) is not None for field in PROFILE_FIELDS}


def _get_or_create_conversation(
    db: Session,
    conversation_id: str,
    user_id: str,
) -> Conversation:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conversation does not belong to current user",
            )
        return conversation

    conversation = Conversation(id=conversation_id, user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )

    conversation = _get_or_create_conversation(db, payload.conversation_id, user_id)
    history_rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [_serialize_message(message) for message in history_rows]

    profile = _get_or_create_profile(db, user_id)
    profile_data = _serialize_profile(profile)
    tracker = _serialize_tracker(profile)

    manager = ConversationManager(db)
    result = await manager.process(
        conversation_id=conversation.id,
        user_message=question,
        history=history,
        profile=profile_data,
        tracker=tracker,
    )

    db.add(
        Message(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=question,
            created_at=datetime.utcnow(),
        )
    )
    db.add(
        Message(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role="assistant",
            content=result["reply"],
            created_at=datetime.utcnow(),
        )
    )
    db.commit()

    return result


@router.post("/conversations")
def create_conversation(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    conversation = Conversation(id=str(uuid4()), user_id=user_id)
    db.add(conversation)
    db.commit()

    return {"id": conversation.id}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation does not belong to current user",
        )

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at,
        "messages": [_serialize_message(message) for message in messages],
    }
