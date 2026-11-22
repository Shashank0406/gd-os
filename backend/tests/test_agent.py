from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from app.models.enums import BillingMode, PaymentMethod
from app.services.access import create_user
from app.services.sessions import end_session, start_session
from tests.staff_client import TEST_PASSWORD, staff_client

MAC = "aa:bb:cc:dd:ee:01"
OTHER_MAC = "AA-BB-CC-DD-EE-02"
HARDWARE = "11111111-1111-4111-8111-111111111111"
OTHER_HARDWARE = "22222222-2222-4222-8222-222222222222"
START = datetime(2026, 11, 22, 4, 0, tzinfo=timezone.utc)


def test_unpaired_pc_is_locked_out_and_a_session_unlocks_it(db) -> None:
    seed(db)
    with staff_client(db, "MANAGER", "agent-manager") as client:
        missing = client.post("/agent/heartbeat", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert missing.status_code == 404

        paired = client.post(
            "/stations/PC-01/agent",
            json={"mac_address": "AA-BB-CC-DD-EE-01", "hardware_uuid": HARDWARE.upper()},
        )
        assert paired.status_code == 201, paired.text
        assert paired.json()["mac_address"] == MAC

        locked = client.post("/agent/heartbeat", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert locked.status_code == 200, locked.text
        assert locked.json()["station_code"] == "PC-01"
        assert locked.json()["desired"] == "LOCK"
        assert locked.json()["session_id"] is None

        cashier = create_user(
            db,
            username="agent-cashier",
            password=TEST_PASSWORD,
            display_name="Desk",
            role_name="CASHIER",
            actor=None,
        )
        play = start_session(
            db,
            station_code="PC-01",
            staff=cashier,
            billing_mode=BillingMode.POSTPAID,
            guest_label="Agent guest",
            now=START,
        )
        unlocked = client.post("/agent/heartbeat", json={"mac_address": MAC, "hardware_uuid": HARDWARE, "desired": "LOCK"})
        assert unlocked.status_code == 200, unlocked.text
        assert unlocked.json()["desired"] == "UNLOCK"
        assert unlocked.json()["session_id"] == str(play.id)

        end_session(db, session_id=str(play.id), staff=cashier, payment_method=PaymentMethod.CASH, now=START + timedelta(minutes=1))
        locked_again = client.post("/agent/heartbeat", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert locked_again.json()["desired"] == "LOCK"

        floor = client.get("/stations")
        pc = next(item for item in floor.json() if item["code"] == "PC-01")
        assert pc["agent_desired"] == "LOCK"
        assert pc["last_heartbeat_at"] is not None
        ps5 = next(item for item in floor.json() if item["code"] == "PS5-01")
        assert ps5["agent_desired"] is None


def test_cashier_cannot_pair_and_other_devices_cannot_run_an_agent(db) -> None:
    seed(db)
    with staff_client(db, "CASHIER", "agent-desk") as client:
        denied = client.post("/stations/PC-02/agent", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert denied.status_code == 403
    with staff_client(db, "MANAGER", "agent-manager-2") as client:
        rejected = client.post("/stations/PS5-01/agent", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert rejected.status_code == 422
        cashier = client.post("/stations/CASHIER-01/agent", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert cashier.status_code == 422


def test_mac_and_hardware_must_stay_a_pair(db) -> None:
    seed(db)
    with staff_client(db, "MANAGER", "agent-manager-3") as client:
        first = client.post("/stations/PC-03/agent", json={"mac_address": MAC, "hardware_uuid": HARDWARE})
        assert first.status_code == 201, first.text
        second = client.post("/stations/PC-04/agent", json={"mac_address": OTHER_MAC, "hardware_uuid": OTHER_HARDWARE})
        assert second.status_code == 201, second.text
        stolen = client.post("/stations/PC-05/agent", json={"mac_address": MAC, "hardware_uuid": OTHER_HARDWARE})
        assert stolen.status_code == 409
        mismatch = client.post("/agent/heartbeat", json={"mac_address": MAC, "hardware_uuid": OTHER_HARDWARE})
        assert mismatch.status_code == 409
        unknown = client.post(
            "/agent/heartbeat",
            json={"mac_address": "aa:bb:cc:dd:ee:99", "hardware_uuid": "33333333-3333-4333-8333-333333333333"},
        )
        assert unknown.status_code == 404


def test_customer_token_cannot_pair_a_pc(db) -> None:
    seed(db)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        registered = client.post(
            "/customers/register",
            json={
                "username": "no.agent",
                "password": "player-pass-1",
                "display_name": "No Agent",
                "mobile": "9876522222",
            },
        )
        token = registered.json()["access_token"]
        denied = client.post(
            "/stations/PC-06/agent",
            headers={"Authorization": f"Bearer {token}"},
            json={"mac_address": MAC, "hardware_uuid": HARDWARE},
        )
    finally:
        app.dependency_overrides.clear()
    assert denied.status_code == 401
