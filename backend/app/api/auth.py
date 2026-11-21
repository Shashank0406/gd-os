from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.login_limit import login_limiter
from app.core.security import create_access_token, dummy_password_hash, verify_password
from app.db.session import get_db
from app.models.identity import User
from app.services.access import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    username: str
    role: str


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    client_key = request.client.host if request.client else "unknown"
    login_limiter.check(f"staff:{client_key}")
    username = body.username.strip().lower()
    user = db.scalar(select(User).options(joinedload(User.role)).where(User.username == username))
    password_ok = verify_password(body.password, user.password_hash if user else dummy_password_hash())
    if user is None or not user.is_active or not password_ok:
        login_limiter.record_failure(f"staff:{client_key}")
        record_audit(
            db,
            actor=user if user is not None and user.is_active else None,
            action="auth.login_failed",
            entity_type="user",
            entity_id=None if user is None else str(user.id),
            detail=f"username={username}",
            ip_address=client_key,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, expires_in = create_access_token(user.id, kind="staff")
    record_audit(
        db,
        actor=user,
        action="auth.login_succeeded",
        entity_type="user",
        entity_id=str(user.id),
        detail=f"username={user.username}",
        ip_address=client_key,
    )
    db.commit()
    return TokenOut(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        username=user.username,
        role=user.role.name,
    )
