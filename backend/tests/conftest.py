import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-longer-than-thirty-two-characters")
os.environ.setdefault("REQUESTS_PER_MINUTE", "10000")
os.environ.setdefault("AUTH_REQUESTS_PER_MINUTE", "10000")
os.environ.setdefault("ALERT_REQUESTS_PER_MINUTE", "20000")

from mydawndiary.database import Base, get_db  # noqa: E402
from mydawndiary.main import app  # noqa: E402


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def test_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def register_and_login(client: TestClient, email: str, time_zone: str = "Asia/Manila") -> dict[str, str]:
    password = "long-test-password-123"
    registered = client.post("/auth/register", json={"email": email, "password": password, "time_zone": time_zone})
    assert registered.status_code == 201, registered.text
    logged_in = client.post("/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200, logged_in.text
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
