from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditOut(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None
    detail: str | None
    actor_username: str | None
    created_at: str


@router.get("", response_model=list[AuditOut])
def list_audit(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit.read")),
) -> list[AuditOut]:
    rows = db.execute(
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    return [
        AuditOut(
            id=str(entry.id),
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            detail=entry.detail,
            actor_username=username,
            created_at=entry.created_at.isoformat(),
        )
        for entry, username in rows
    ]
