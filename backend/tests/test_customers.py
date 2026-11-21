from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.customer import Customer
from tests.staff_client import TEST_PASSWORD, staff_client

CUSTOMER = {
    "username": "rahul.gamer",
    "password": "player-pass-1",
    "display_name": "Rahul",
    "mobile": "9876543210",
}


def test_customer_registers_and_logs_in_with_password(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        created = client.post("/customers/register", json=CUSTOMER)
        assert created.status_code == 201
        body = created.json()
        assert body["customer"]["mobile"] == "9876543210"
        assert body["customer"]["has_password"] is True
        assert "password" not in body["customer"]

        me = client.get("/customers/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
        assert me.json()["username"] == "rahul.gamer"

        staff_only = client.get("/pricing", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert staff_only.status_code == 401

        logged_out = client.post("/customers/login", json={"username": "rahul.gamer", "password": "wrong-password"})
        logged_in = client.post("/customers/login", json={"username": "Rahul.Gamer", "password": "player-pass-1"})
    finally:
        app.dependency_overrides.clear()

    assert logged_out.status_code == 401
    assert logged_in.status_code == 200
    stored = db.scalar(select(Customer).where(Customer.username == "rahul.gamer"))
    assert stored is not None
    assert stored.password_hash.startswith("$argon2")
    assert "player-pass-1" not in stored.password_hash


def test_duplicate_mobile_is_rejected(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        assert client.post("/customers/register", json=CUSTOMER).status_code == 201
        duplicate = client.post(
            "/customers/register",
            json={**CUSTOMER, "username": "other.name", "mobile": "+91 98765 43210"},
        )
    finally:
        app.dependency_overrides.clear()
    assert duplicate.status_code == 409


def test_cashier_registers_walk_in_and_searches_by_mobile(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "desk-customers") as client:
        created = client.post("/customers", json={"display_name": "Walk In", "mobile": "9123456789"})
        assert created.status_code == 201
        assert created.json()["has_password"] is False
        assert created.json()["username"] is None
        found = client.get("/customers/search", params={"mobile": "09123456789"})
        missing = client.get("/customers/search", params={"mobile": "9000000000"})
    assert found.status_code == 200
    assert found.json()["display_name"] == "Walk In"
    assert missing.status_code == 404

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        denied = TestClient(app).post(
            "/customers/login",
            json={"username": "walk-in", "password": TEST_PASSWORD},
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401


def test_staff_token_cannot_open_customer_profile(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "desk-profile") as client:
        response = client.get("/customers/me")
    assert response.status_code == 401
