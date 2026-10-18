from threading import Event
import logging
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mydawndiary import operations


def test_throttling_aggregate_log_and_single_spike_email(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger=operations.logger.name)
    clock = [10.0]
    monkeypatch.setattr(operations, "monotonic", lambda: clock[0])
    sent = []
    delivered = Event()

    def fake_send(config, count):
        sent.append(count)
        delivered.set()

    monkeypatch.setattr(operations, "send_spike_email", fake_send)
    config = operations.TrafficConfig(
        requests_per_minute=3,
        auth_requests_per_minute=2,
        alert_requests_per_minute=4,
        smtp_host="smtp.example.com",
        smtp_username="alerts",
        smtp_password="test-password",
        mail_from="alerts@example.com",
        mail_to=("owner@example.com",),
    )
    app = FastAPI()
    app.add_middleware(operations.TrafficMiddleware, config=config)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app) as client:
        assert [client.get("/ping").status_code for _ in range(3)] == [200, 200, 200]
        blocked = client.get("/ping")
        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"] == "60"
        assert delivered.wait(1)
        assert sent == [4]
        assert client.get("/ping").status_code == 429
        assert sent == [4]
        clock[0] = 70.0
        assert client.get("/ping").status_code == 200

    assert "requests=5 throttled=2 server_errors=0" in caplog.text
    assert "test-password" not in caplog.text
    assert "owner@example.com" not in caplog.text


def test_auth_limit_is_stricter(monkeypatch):
    monkeypatch.setattr(operations, "monotonic", lambda: 10.0)
    app = FastAPI()
    app.add_middleware(
        operations.TrafficMiddleware,
        config=operations.TrafficConfig(requests_per_minute=10, auth_requests_per_minute=2),
    )

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    with TestClient(app) as client:
        assert [client.post("/auth/login").status_code for _ in range(3)] == [200, 200, 429]


def test_resend_alert_uses_key_and_recipients(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(operations, "urlopen", fake_urlopen)
    config = operations.TrafficConfig(
        resend_api_key="test-key",
        mail_from="alerts@example.com",
        mail_to=("first@example.com", "second@example.com"),
    )
    operations.send_spike_email(config, 300)

    request, timeout = calls[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer test-key"
    assert json.loads(request.data)["to"] == ["first@example.com", "second@example.com"]
    assert timeout == 5
