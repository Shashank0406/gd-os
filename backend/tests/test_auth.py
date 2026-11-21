from sqlalchemy import select

from app.core.login_limit import login_limiter
from app.db.seed import seed
from app.main import app
from app.models.identity import User
from app.models.pricing import PriceChangeLog, PricingPlan
from app.models.enums import DeviceType
from app.db.session import get_db
from fastapi.testclient import TestClient
from tests.staff_client import TEST_PASSWORD, staff_client


def test_login_rejects_unknown_user_and_bad_password_the_same_way(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "cashier-login") as client:
        wrong = client.post("/auth/login", json={"username": "cashier-login", "password": "wrong-password"})
        missing = client.post("/auth/login", json={"username": "nobody-here", "password": "wrong-password"})
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_password_is_hashed() -> None:
    from app.core.security import hash_password

    stored = hash_password(TEST_PASSWORD)
    assert stored.startswith("$argon2")
    assert TEST_PASSWORD not in stored


def test_cashier_cannot_change_price_or_create_staff(db) -> None:
    seed(db)
    plan = db.scalar(select(PricingPlan).where(PricingPlan.device_type == DeviceType.PC, PricingPlan.station_id.is_(None)))
    assert plan is not None
    before = plan.hourly_rate_rupees
    with staff_client(db, "CASHIER", "cashier-blocked") as client:
        price = client.patch(f"/pricing/plans/{plan.id}", json={"hourly_rate_rupees": "180.00"})
        staff = client.post(
            "/staff",
            json={
                "username": "new-cashier",
                "password": TEST_PASSWORD,
                "display_name": "New",
                "role": "CASHIER",
            },
        )
        audit = client.get("/audit")
    assert price.status_code == 403
    assert staff.status_code == 403
    assert audit.status_code == 403
    db.refresh(plan)
    assert plan.hourly_rate_rupees == before


def test_super_admin_price_change_is_logged_in_rupees(db) -> None:
    seed(db)
    plan = db.scalar(select(PricingPlan).where(PricingPlan.device_type == DeviceType.PS5, PricingPlan.station_id.is_(None)))
    assert plan is not None
    with staff_client(db, "SUPER_ADMIN", "owner-one") as client:
        response = client.patch(f"/pricing/plans/{plan.id}", json={"hourly_rate_rupees": "275.00"})
        audit = client.get("/audit")
    assert response.status_code == 200
    assert response.json()["hourly_rate_rupees"] == "275.00"
    log = db.scalar(
        select(PriceChangeLog)
        .where(PriceChangeLog.entity_id == plan.id, PriceChangeLog.actor_label == "owner-one")
        .order_by(PriceChangeLog.created_at.desc())
    )
    assert log is not None
    assert log.old_value == "250.00"
    assert log.new_value == "275.00"
    assert log.field_name == "hourly_rate_rupees"
    actions = [item["action"] for item in audit.json()]
    assert "pricing.updated" in actions
    user = db.scalar(select(User).where(User.username == "owner-one"))
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert TEST_PASSWORD not in user.password_hash


def test_manager_cannot_create_staff(db) -> None:
    seed(db)
    with staff_client(db, "MANAGER", "manager-one") as client:
        response = client.post(
            "/staff",
            json={
                "username": "desk-one",
                "password": TEST_PASSWORD,
                "display_name": "Desk",
                "role": "CASHIER",
            },
        )
        listing = client.get("/staff")
    assert response.status_code == 403
    assert listing.status_code == 200


def test_super_admin_can_create_cashier(db) -> None:
    seed(db)
    with staff_client(db, "SUPER_ADMIN", "owner-two") as client:
        response = client.post(
            "/staff",
            json={
                "username": "desk-two",
                "password": TEST_PASSWORD,
                "display_name": "Desk Two",
                "role": "CASHIER",
            },
        )
    assert response.status_code == 201
    assert response.json()["role"] == "CASHIER"
    assert "password" not in response.json()


def test_pricing_requires_login(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/pricing")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_login_is_rate_limited(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "cashier-limit") as client:
        login_limiter.clear()
        for _ in range(5):
            failed = client.post("/auth/login", json={"username": "cashier-limit", "password": "wrong-password-1"})
            assert failed.status_code == 401
        blocked = client.post("/auth/login", json={"username": "cashier-limit", "password": TEST_PASSWORD})
    assert blocked.status_code == 429


def test_placeholder_jwt_secret_is_rejected(db, monkeypatch) -> None:
    seed(db)
    monkeypatch.setenv("JWT_SECRET", "change-me")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/auth/login",
            json={"username": "cashier-secret", "password": TEST_PASSWORD},
        )
    finally:
        app.dependency_overrides.clear()
    # User does not exist yet, so this is 401 before the secret is used.
    # Create the user, then the successful password path must refuse the placeholder secret.
    from app.services.access import create_user

    create_user(
        db,
        username="cashier-secret",
        password=TEST_PASSWORD,
        display_name="Cashier Secret",
        role_name="CASHIER",
        actor=None,
    )
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/auth/login",
            json={"username": "cashier-secret", "password": TEST_PASSWORD},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
