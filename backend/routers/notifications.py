from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_current_user
from models import Notification, Scheme

router = APIRouter()


def serialize_notification(notification: Notification, scheme_name: str | None) -> dict:
    return {
        "id": notification.id,
        "scheme_id": notification.scheme_id,
        "scheme_name": scheme_name,
        "message": notification.message,
        "type": notification.type,
        "is_read": notification.is_read,
        "is_cancelled": notification.is_cancelled,
        "created_at": notification.created_at,
    }


@router.get("/notifications")
def list_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> list[dict]:
    query = (
        db.query(Notification, Scheme.name)
        .outerjoin(Scheme, Notification.scheme_id == Scheme.id)
        .filter(
            Notification.user_id == user_id,
            Notification.is_cancelled.is_(False),
        )
    )

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    rows = query.order_by(Notification.created_at.desc()).all()
    return [
        serialize_notification(notification, scheme_name)
        for notification, scheme_name in rows
    ]


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.is_cancelled.is_(False),
        )
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    db.commit()

    return {"updated": True}


@router.patch("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
            Notification.is_cancelled.is_(False),
        )
        .update({Notification.is_read: True}, synchronize_session=False)
    )
    db.commit()

    return {"updated": updated}


@router.get("/notifications/unread-count")
def get_unread_notification_count(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> dict:
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
            Notification.is_cancelled.is_(False),
        )
        .count()
    )

    return {"count": count}
