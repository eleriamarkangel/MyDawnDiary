from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from mydawndiary import auth as auth_routes
from mydawndiary import email_delivery
from mydawndiary.email_delivery import EmailDeliveryError
from mydawndiary.models import User


def _register(client, email="verify@example.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "long-test-password-123", "time_zone": "Asia/Manila"},
    )


def test_registration_requires_email_verification_and_does_not_store_plain_code(api):
    client, factory = api
    response = _register(client)
    assert response.status_code == 201, response.text
    assert response.json()["email_verified_at"] is None
    code = client.sent_verification_emails[-1][1]
    assert len(code) == 6 and code.isdigit()

    with factory() as db:
        user = db.get(User, response.json()["id"])
        assert user.email_otp_hash != code

    login = {"email": "verify@example.com", "password": "long-test-password-123"}
    assert client.post("/auth/login", json=login).status_code == 403
    assert client.post("/auth/verify-email", json={"email": login["email"], "code": code}).status_code == 204
    assert client.post("/auth/login", json=login).status_code == 200
    assert client.post("/auth/verify-email", json={"email": login["email"], "code": code}).status_code == 400


def test_resend_invalidates_previous_code_and_limits_frequency(api, monkeypatch):
    client, _ = api
    start = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start)
    assert _register(client).status_code == 201
    first_code = client.sent_verification_emails[-1][1]

    body = {"email": "verify@example.com"}
    assert client.post("/auth/resend-verification", json=body).status_code == 202
    assert len(client.sent_verification_emails) == 1
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start + timedelta(minutes=4, seconds=59))
    assert client.post("/auth/resend-verification", json=body).status_code == 202
    assert len(client.sent_verification_emails) == 1
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start + timedelta(minutes=5))
    assert client.post("/auth/resend-verification", json=body).status_code == 202
    second_code = client.sent_verification_emails[-1][1]
    assert len(client.sent_verification_emails) == 2
    assert client.post("/auth/verify-email", json={**body, "code": first_code}).status_code == 400
    assert client.post("/auth/verify-email", json={**body, "code": second_code}).status_code == 204
    assert client.post("/auth/resend-verification", json=body).status_code == 202
    assert len(client.sent_verification_emails) == 2


def test_expired_code_and_attempt_limit(api, monkeypatch):
    client, _ = api
    start = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start)
    assert _register(client).status_code == 201
    code = client.sent_verification_emails[-1][1]
    wrong = "000000" if code != "000000" else "111111"
    body = {"email": "verify@example.com"}
    for _ in range(5):
        assert client.post("/auth/verify-email", json={**body, "code": wrong}).status_code == 400
    assert client.post("/auth/verify-email", json={**body, "code": code}).status_code == 400

    monkeypatch.setattr(auth_routes, "utc_now", lambda: start + timedelta(minutes=11))
    assert client.post("/auth/resend-verification", json=body).status_code == 202
    fresh_code = client.sent_verification_emails[-1][1]
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start + timedelta(minutes=22))
    assert client.post("/auth/verify-email", json={**body, "code": fresh_code}).status_code == 400


def test_delivery_failure_rolls_back_registration_and_resend(api, monkeypatch):
    client, factory = api

    def fail_send(address, code):
        raise EmailDeliveryError("simulated failure")

    monkeypatch.setattr(auth_routes, "send_verification_email", fail_send)
    assert _register(client).status_code == 503
    with factory() as db:
        assert db.query(User).count() == 0

    sent_codes = client.sent_verification_emails
    monkeypatch.setattr(auth_routes, "send_verification_email", lambda address, code: sent_codes.append((address, code)))
    assert _register(client).status_code == 201
    original_code = sent_codes[-1][1]
    monkeypatch.setattr(auth_routes, "utc_now", lambda: datetime.now(timezone.utc) + timedelta(minutes=6))
    monkeypatch.setattr(auth_routes, "send_verification_email", fail_send)
    assert client.post("/auth/resend-verification", json={"email": "verify@example.com"}).status_code == 202
    assert client.post("/auth/verify-email", json={"email": "verify@example.com", "code": original_code}).status_code == 204


def test_hourly_send_limit(api, monkeypatch):
    client, _ = api
    start = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start)
    assert _register(client).status_code == 201
    for number in range(1, 6):
        monkeypatch.setattr(auth_routes, "utc_now", lambda number=number: start + timedelta(minutes=5 * number))
        assert client.post("/auth/resend-verification", json={"email": "verify@example.com"}).status_code == 202
    assert len(client.sent_verification_emails) == 5
    monkeypatch.setattr(auth_routes, "utc_now", lambda: start + timedelta(hours=1, seconds=1))
    assert client.post("/auth/resend-verification", json={"email": "verify@example.com"}).status_code == 202
    assert len(client.sent_verification_emails) == 6


def test_resend_request_uses_configured_sender_without_logging_key(monkeypatch):
    sent = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        email_delivery,
        "get_settings",
        lambda: SimpleNamespace(resend_api_key="test-key", resend_from_email="Verify <verify@example.com>"),
    )
    monkeypatch.setattr(email_delivery, "urlopen", lambda request, timeout: sent.append((request, timeout)) or FakeResponse())
    email_delivery.send_verification_email("person@example.com", "123456")
    request, timeout = sent[0]
    payload = json.loads(request.data)
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer test-key"
    assert request.get_header("User-agent") == "MyDawnDiary/0.1"
    assert payload["from"] == "Verify <verify@example.com>"
    assert payload["to"] == ["person@example.com"]
    assert "123456" in payload["html"]
    assert timeout == 10


def test_resend_error_shows_reason_without_exposing_key_or_code(monkeypatch):
    monkeypatch.setattr(
        email_delivery,
        "get_settings",
        lambda: SimpleNamespace(resend_api_key="test-secret-key", resend_from_email="verify@example.com"),
    )

    def reject(request, timeout):
        body = json.dumps({"message": "Domain is not verified; test-secret-key 123456"}).encode()
        raise HTTPError(request.full_url, 403, "Forbidden", {}, BytesIO(body))

    monkeypatch.setattr(email_delivery, "urlopen", reject)
    with pytest.raises(EmailDeliveryError) as error:
        email_delivery.send_verification_email("person@example.com", "123456")
    assert "HTTP 403" in str(error.value)
    assert "Domain is not verified" in str(error.value)
    assert "test-secret-key" not in str(error.value)
    assert "123456" not in str(error.value)
