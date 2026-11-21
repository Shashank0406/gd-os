"""Roles, permissions, and staff accounts."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.identity import AuditLog, Permission, Role, RolePermission, User

PERMISSIONS: tuple[str, ...] = (
    "stations.read",
    "pricing.read",
    "pricing.write",
    "staff.read",
    "staff.write",
    "audit.read",
    "customers.read",
    "customers.write",
    "sessions.read",
    "sessions.operate",
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "SUPER_ADMIN": PERMISSIONS,
    "MANAGER": (
        "stations.read",
        "pricing.read",
        "staff.read",
        "audit.read",
        "customers.read",
        "customers.write",
        "sessions.read",
        "sessions.operate",
    ),
    "CASHIER": (
        "stations.read",
        "pricing.read",
        "customers.read",
        "customers.write",
        "sessions.read",
        "sessions.operate",
    ),
}


class StaffError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def ensure_access(session: Session) -> None:
    permission_ids = _ensure_permissions(session)
    role_ids = _ensure_roles(session)
    _ensure_role_permissions(session, role_ids, permission_ids)
    _ensure_super_admin(session, role_ids["SUPER_ADMIN"])


def permissions_for(session: Session, user: User) -> set[str]:
    codes = session.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    )
    return set(codes)


def create_user(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str,
    role_name: str,
    actor: User | None,
    bootstrap: bool = False,
) -> User:
    normalized = _normalize_username(username)
    if len(password) < 8:
        raise StaffError(422, "Password must be at least 8 characters")
    role = session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise StaffError(422, "Unknown role")
    if role_name == "SUPER_ADMIN" and not bootstrap:
        if actor is None or actor.role.name != "SUPER_ADMIN":
            raise StaffError(403, "Only a super admin can create a super admin")
    if not bootstrap and actor is not None and "staff.write" not in permissions_for(session, actor):
        raise StaffError(403, "You do not have permission for this action")
    existing = session.scalar(select(User.id).where(User.username == normalized))
    if existing is not None:
        raise StaffError(409, "Username already exists")
    user = User(
        username=normalized,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role_id=role.id,
        is_active=True,
    )
    session.add(user)
    session.flush()
    record_audit(
        session,
        actor=actor,
        action="staff.created",
        entity_type="user",
        entity_id=str(user.id),
        detail=f"username={user.username}; role={role_name}",
    )
    session.commit()
    session.refresh(user)
    return user


def record_audit(
    session: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=None if actor is None else actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            ip_address=ip_address,
        )
    )


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3 or len(normalized) > 32:
        raise StaffError(422, "Username must be 3 to 32 characters")
    if any(not (character.isalnum() or character in "._-") for character in normalized):
        raise StaffError(422, "Username may contain letters, numbers, dots, underscores, and hyphens")
    return normalized


def _ensure_permissions(session: Session) -> dict[str, object]:
    ids: dict[str, object] = {}
    for code in PERMISSIONS:
        permission = session.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code)
            session.add(permission)
            session.flush()
        ids[code] = permission.id
    return ids


def _ensure_roles(session: Session) -> dict[str, object]:
    ids: dict[str, object] = {}
    for name in ROLE_PERMISSIONS:
        role = session.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name)
            session.add(role)
            session.flush()
        ids[name] = role.id
    return ids


def _ensure_role_permissions(session: Session, role_ids: dict[str, object], permission_ids: dict[str, object]) -> None:
    for role_name, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            exists = session.scalar(
                select(RolePermission.role_id).where(
                    RolePermission.role_id == role_ids[role_name],
                    RolePermission.permission_id == permission_ids[code],
                )
            )
            if exists is None:
                session.add(RolePermission(role_id=role_ids[role_name], permission_id=permission_ids[code]))
    session.flush()


def _ensure_super_admin(session: Session, role_id: object) -> None:
    settings = get_settings()
    username = settings.admin_username.strip().lower()
    password = settings.admin_password
    if not username or password == "change-me" or len(password) < 8:
        return
    exists = session.scalar(select(User.id).where(User.role_id == role_id))
    if exists is not None:
        return
    session.add(
        User(
            username=username,
            display_name="Super Admin",
            password_hash=hash_password(password),
            role_id=role_id,
            is_active=True,
        )
    )
    session.flush()
