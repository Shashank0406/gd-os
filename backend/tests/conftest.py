import os

os.environ["JWT_SECRET"] = "test-only-jwt-secret-0123456789abcdef"
os.environ["GD_OS_ADMIN_PASSWORD"] = "change-me"

from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _test_database_url() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    _load_env(repo_root / ".env")
    configured = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://gdos:change-me@localhost:5432/gdos",
    )
    url = make_url(configured)
    if url.host in {None, "postgres"}:
        url = url.set(host="localhost")
    return url.set(database="gdos_test").render_as_string(hide_password=False)


@pytest.fixture(autouse=True)
def _clear_login_limiter() -> Generator[None, None, None]:
    from app.core.login_limit import login_limiter

    login_limiter.clear()
    yield
    login_limiter.clear()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _test_database_url()
    admin = make_url(url).set(database="postgres")
    connection = psycopg.connect(
        host=admin.host or "localhost",
        port=admin.port or 5432,
        user=admin.username,
        password=admin.password,
        dbname="postgres",
        autocommit=True,
    )
    try:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            ("gdos_test",),
        ).fetchone()
        if exists is None:
            connection.execute("CREATE DATABASE gdos_test")
    finally:
        connection.close()
    return url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    previous = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
        else:
            os.environ["ALEMBIC_DATABASE_URL"] = previous
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
