from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_customer, require_permission
from app.core.login_limit import login_limiter
from app.core.security import create_access_token, dummy_password_hash, verify_password
from app.db.session import get_db
from app.models.customer import Customer
from app.models.identity import User
from app.services.access import record_audit
from app.services.customers import CustomerError, find_by_mobile, find_for_login, register_customer, register_walk_in

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerOut(BaseModel):
    id: str
    username: str | None
    display_name: str
    mobile: str
    has_password: bool


class CustomerAuthOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    customer: CustomerOut


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)
    mobile: str = Field(min_length=10, max_length=16)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=200)


class WalkInIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    mobile: str = Field(min_length=10, max_length=16)
    username: str | None = None
    password: str | None = None


def _out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=str(customer.id),
        username=customer.username,
        display_name=customer.display_name,
        mobile=customer.mobile,
        has_password=customer.password_hash is not None,
    )


def _auth(customer: Customer) -> CustomerAuthOut:
    token, expires_in = create_access_token(customer.id, kind="customer")
    return CustomerAuthOut(access_token=token, token_type="bearer", expires_in=expires_in, customer=_out(customer))


@router.post("/register", response_model=CustomerAuthOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)) -> CustomerAuthOut:
    client_key = f"customer-register:{_client(request)}"
    login_limiter.check(client_key)
    login_limiter.record_failure(client_key)
    try:
        customer = register_customer(
            db,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            mobile=body.mobile,
        )
    except CustomerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _auth(customer)


@router.post("/login", response_model=CustomerAuthOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> CustomerAuthOut:
    client_key = f"customer-login:{_client(request)}"
    login_limiter.check(client_key)
    customer = find_for_login(db, body.username)
    password_hash = customer.password_hash if customer and customer.password_hash else dummy_password_hash()
    if customer is None or customer.password_hash is None or not verify_password(body.password, password_hash):
        login_limiter.record_failure(client_key)
        record_audit(
            db,
            actor=None,
            action="customer.login_failed",
            entity_type="customer",
            entity_id=None if customer is None else str(customer.id),
            detail=f"username={body.username.strip().lower()}",
            ip_address=_client(request),
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token_body = _auth(customer)
    record_audit(
        db,
        actor=None,
        action="customer.login_succeeded",
        entity_type="customer",
        entity_id=str(customer.id),
        detail=f"username={customer.username}",
        ip_address=_client(request),
    )
    db.commit()
    return token_body


@router.get("/me", response_model=CustomerOut)
def me(customer: Customer = Depends(get_current_customer)) -> CustomerOut:
    return _out(customer)


@router.get("/search", response_model=CustomerOut)
def search(
    mobile: str = Query(min_length=10, max_length=16),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("customers.read")),
) -> CustomerOut:
    try:
        customer = find_by_mobile(db, mobile)
    except CustomerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if customer is None:
        raise HTTPException(status_code=404, detail="No customer found for that mobile number")
    return _out(customer)


@router.post("", response_model=CustomerOut, status_code=201)
def create_walk_in(
    body: WalkInIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("customers.write")),
) -> CustomerOut:
    try:
        customer = register_walk_in(
            db,
            display_name=body.display_name,
            mobile=body.mobile,
            username=body.username,
            password=body.password,
            actor=actor,
        )
    except CustomerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return _out(customer)


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"
