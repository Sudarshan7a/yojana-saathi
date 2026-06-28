from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_current_user
from models import UserProfile

router = APIRouter()

NON_SENSITIVE_FIELDS = [
    "name",
    "age",
    "gender",
    "state",
    "area",
    "occupation",
    "is_student",
    "education_level",
    "marital_status",
    "has_children",
    "goals",
]

SENSITIVE_FIELDS = [
    "caste_category",
    "annual_income",
    "has_disability",
    "bpl_card",
    "is_pregnant",
]

PROFILE_FIELDS = NON_SENSITIVE_FIELDS + SENSITIVE_FIELDS


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    age: int | None = None
    gender: str | None = None
    state: str | None = None
    area: str | None = None
    caste_category: str | None = None
    annual_income: int | None = None
    has_disability: bool | None = None
    occupation: str | None = None
    is_student: bool | None = None
    education_level: str | None = None
    marital_status: str | None = None
    has_children: bool | None = None
    is_pregnant: bool | None = None
    bpl_card: bool | None = None
    goals: list[Any] | None = None


def get_or_create_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        return profile

    profile = UserProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def serialize_non_sensitive(profile: UserProfile) -> dict:
    return {field: getattr(profile, field) for field in NON_SENSITIVE_FIELDS}


def serialize_tracker(profile: UserProfile) -> dict:
    return {field: getattr(profile, field) is not None for field in PROFILE_FIELDS}


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    profile = get_or_create_profile(db, user_id)
    return {
        "non_sensitive": serialize_non_sensitive(profile),
        "tracker": serialize_tracker(profile),
    }


@router.patch("/profile")
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    profile = get_or_create_profile(db, user_id)
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return {
        "updated": True,
        "tracker": serialize_tracker(profile),
    }


@router.get("/profile/tracker")
def get_profile_tracker(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    profile = get_or_create_profile(db, user_id)
    return serialize_tracker(profile)


@router.delete("/profile")
def delete_profile(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        db.delete(profile)
        db.commit()

    return {"deleted": True}
