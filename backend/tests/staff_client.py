from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.services.access import create_user

TEST_PASSWORD = "test-password-1"


@contextmanager
def staff_client(db, role: str, username: str) -> Iterator[TestClient]:
    create_user(
        db,
        username=username,
        password=TEST_PASSWORD,
        display_name=username,
        role_name=role,
        actor=None,
        bootstrap=role == "SUPER_ADMIN",
    )

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    response = client.post("/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
