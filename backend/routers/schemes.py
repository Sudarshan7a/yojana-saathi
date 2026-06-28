from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Scheme

router = APIRouter()


def serialize_scheme_summary(scheme: Scheme) -> dict:
    return {
        "id": scheme.id,
        "name": scheme.name,
        "category": scheme.category,
        "state": scheme.state,
        "status": scheme.status,
        "last_synced_at": scheme.last_synced_at,
        "tags": scheme.tags,
        "source_url": scheme.source_url,
    }


def serialize_scheme_detail(scheme: Scheme) -> dict:
    return {
        "id": scheme.id,
        "name": scheme.name,
        "eligibility": scheme.eligibility,
        "benefits": scheme.benefits,
        "description": scheme.description,
        "application_process": scheme.application_process,
        "required_documents": scheme.required_documents,
        "ministry": scheme.ministry,
        "application_url": scheme.application_url,
        "category": scheme.category,
        "state": scheme.state,
        "status": scheme.status,
        "tags": scheme.tags,
        "source_url": scheme.source_url,
        "last_synced_at": scheme.last_synced_at,
        "created_at": scheme.created_at,
        "updated_at": scheme.updated_at,
    }


@router.get("/schemes")
def list_schemes(
    category: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(Scheme)

    if category:
        query = query.filter(Scheme.category == category)
    if state:
        query = query.filter(Scheme.state == state)
    if status_filter:
        query = query.filter(Scheme.status == status_filter)
    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Scheme.name.ilike(search),
                Scheme.description.ilike(search),
                Scheme.eligibility.ilike(search),
                Scheme.benefits.ilike(search),
            )
        )

    schemes = query.order_by(Scheme.name.asc()).all()
    return [serialize_scheme_summary(scheme) for scheme in schemes]


@router.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: str, db: Session = Depends(get_db)) -> dict:
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found",
        )

    return serialize_scheme_detail(scheme)


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)) -> list[str]:
    categories = (
        db.query(Scheme.category)
        .filter(Scheme.category.isnot(None))
        .distinct()
        .order_by(Scheme.category.asc())
        .all()
    )
    return [category for (category,) in categories]


@router.get("/states")
def list_states(db: Session = Depends(get_db)) -> list[str]:
    states = (
        db.query(Scheme.state)
        .filter(Scheme.state.isnot(None))
        .distinct()
        .order_by(Scheme.state.asc())
        .all()
    )
    return [state for (state,) in states]
