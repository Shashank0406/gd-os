"""Customer registration, walk-ins, and username login."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.customer import Customer
from app.models.identity import User
from app.services.access import record_audit


class CustomerError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def normalize_mobile(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise CustomerError(422, "Enter a 10-digit Indian mobile number")
    return digits


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) < 3 or len(normalized) > 32:
        raise CustomerError(422, "Username must be 3 to 32 characters")
    if any(not (character.isalnum() or character in "._-") for character in normalized):
        raise CustomerError(422, "Username may contain letters, numbers, dots, underscores, and hyphens")
    return normalized


def register_customer(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str,
    mobile: str,
    actor: User | None = None,
) -> Customer:
    if len(password) < 8:
        raise CustomerError(422, "Password must be at least 8 characters")
    return _insert_customer(
        session,
        username=normalize_username(username),
        password=password,
        display_name=display_name,
        mobile=normalize_mobile(mobile),
        actor=actor,
    )


def register_walk_in(
    session: Session,
    *,
    display_name: str,
    mobile: str,
    actor: User,
    username: str | None = None,
    password: str | None = None,
) -> Customer:
    normalized_username = None
    if username:
        normalized_username = normalize_username(username)
    if password and not normalized_username:
        raise CustomerError(422, "A username is required when a password is set")
    if password and len(password) < 8:
        raise CustomerError(422, "Password must be at least 8 characters")
    return _insert_customer(
        session,
        username=normalized_username,
        password=password,
        display_name=display_name,
        mobile=normalize_mobile(mobile),
        actor=actor,
    )


def find_by_mobile(session: Session, mobile: str) -> Customer | None:
    return session.scalar(select(Customer).where(Customer.mobile == normalize_mobile(mobile)))


def find_for_login(session: Session, username: str) -> Customer | None:
    normalized = username.strip().lower()
    return session.scalar(select(Customer).where(Customer.username == normalized, Customer.is_active.is_(True)))


def _insert_customer(
    session: Session,
    *,
    username: str | None,
    password: str | None,
    display_name: str,
    mobile: str,
    actor: User | None,
) -> Customer:
    name = display_name.strip()
    if not name:
        raise CustomerError(422, "Name is required")
    existing = session.scalar(
        select(Customer.id).where(or_(Customer.mobile == mobile, Customer.username == username) if username else Customer.mobile == mobile)
    )
    if existing is not None:
        raise CustomerError(409, "A customer with that mobile number or username already exists")
    customer = Customer(
        username=username,
        display_name=name,
        mobile=mobile,
        password_hash=hash_password(password) if password else None,
        is_active=True,
        created_by_user_id=None if actor is None else actor.id,
    )
    session.add(customer)
    session.flush()
    record_audit(
        session,
        actor=actor,
        action="customer.registered",
        entity_type="customer",
        entity_id=str(customer.id),
        detail=f"username={customer.username or ''}; mobile={customer.mobile}",
    )
    session.commit()
    session.refresh(customer)
    return customer
