from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.services.access import StaffError, create_user

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)
    role: str


class StaffOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    is_active: bool


def _to_out(user: User) -> StaffOut:
    return StaffOut(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        role=user.role.name,
        is_active=user.is_active,
    )


@router.get("", response_model=list[StaffOut])
def list_staff(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("staff.read")),
) -> list[StaffOut]:
    users = db.scalars(select(User).options(joinedload(User.role)).order_by(User.username))
    return [_to_out(user) for user in users]


@router.post("", response_model=StaffOut, status_code=201)
def add_staff(
    body: StaffIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("staff.write")),
) -> StaffOut:
    try:
        user = create_user(
            db,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            role_name=body.role,
            actor=actor,
        )
    except StaffError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _to_out(user)
