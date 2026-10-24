from datetime import timedelta
from sqlalchemy import select
from conftest import register_and_login
from mydawndiary import auth
from mydawndiary.models import User
from mydawndiary.email_delivery import EmailDeliveryError


def setup_reset(client, monkeypatch):
    headers = register_and_login(client, 'reset@example.com')
    sent = []
    monkeypatch.setattr(auth, 'send_password_reset_email', lambda address, code: sent.append((address, code)))
    assert client.post('/auth/forgot-password', json={'email': 'reset@example.com'}).status_code == 202
    return headers, sent


def reset(client, code, password='a-new-password-12345'):
    return client.post('/auth/reset-password', json={'email': 'reset@example.com', 'code': code, 'new_password': password})


def test_reset_is_single_use_revokes_sessions_and_preserves_notes(api, monkeypatch):
    client, factory = api
    headers, sent = setup_reset(client, monkeypatch)
    note = client.post('/notes', headers=headers, json={'content': 'Keep this memory'}).json()
    code = sent[-1][1]
    with factory() as db:
        user = db.scalar(select(User).where(User.email == 'reset@example.com'))
        assert user.reset_code_hash != code
        assert len(user.reset_code_hash) == 64
    assert reset(client, code, 'short').status_code == 422
    assert reset(client, code).status_code == 204
    assert reset(client, code).status_code == 400
    assert client.get('/auth/me', headers=headers).status_code == 401
    assert client.post('/auth/login', json={'email': 'reset@example.com', 'password': 'long-test-password-123'}).status_code == 401
    token = client.post('/auth/login', json={'email': 'reset@example.com', 'password': 'a-new-password-12345'}).json()['access_token']
    assert client.get('/notes/' + note['id'], headers={'Authorization': 'Bearer ' + token}).status_code == 200


def test_reset_limits_expiry_and_resend(api, monkeypatch):
    client, _ = api
    _, sent = setup_reset(client, monkeypatch)
    first = sent[-1][1]
    wrong = '000000' if first != '000000' else '111111'
    for _ in range(5):
        assert reset(client, wrong).status_code == 400
    assert reset(client, first).status_code == 400
    client.post('/auth/forgot-password', json={'email': 'reset@example.com'})
    assert len(sent) == 1
    start = auth.utc_now()
    for index in range(1, 6):
        monkeypatch.setattr(auth, 'utc_now', lambda index=index: start + timedelta(minutes=index * 5))
        client.post('/auth/forgot-password', json={'email': 'reset@example.com'})
    assert len(sent) == 5
    assert reset(client, first).status_code == 400
    monkeypatch.setattr(auth, 'utc_now', lambda: start + timedelta(minutes=40))
    assert reset(client, sent[-1][1]).status_code == 400
    monkeypatch.setattr(auth, 'utc_now', lambda: start + timedelta(minutes=61))
    client.post('/auth/forgot-password', json={'email': 'reset@example.com'})
    assert len(sent) == 6
    assert reset(client, sent[-1][1]).status_code == 204


def test_reset_generic_responses_and_delivery_failure(api, monkeypatch):
    client, _ = api
    _, sent = setup_reset(client, monkeypatch)
    code = sent[-1][1]
    known = client.post('/auth/forgot-password', json={'email': 'reset@example.com'})
    unknown = client.post('/auth/forgot-password', json={'email': 'unknown@example.com'})
    assert (known.status_code, known.content) == (unknown.status_code, unknown.content)
    assert len(sent) == 1
    start = auth.utc_now()
    monkeypatch.setattr(auth, 'utc_now', lambda: start + timedelta(minutes=6))
    def fail(address, code):
        raise EmailDeliveryError('simulated failure')
    monkeypatch.setattr(auth, 'send_password_reset_email', fail)
    failed = client.post('/auth/forgot-password', json={'email': 'reset@example.com'})
    assert (failed.status_code, failed.content) == (unknown.status_code, unknown.content)
    assert reset(client, code).status_code == 204


def test_verification_code_cannot_reset_password_and_password_change_invalidates_reset(api, monkeypatch):
    client, _ = api
    headers, sent = setup_reset(client, monkeypatch)
    assert reset(client, client.sent_verification_emails[-1][1]).status_code == 400
    assert client.post('/auth/change-password', headers=headers, json={'current_password': 'long-test-password-123', 'new_password': 'another-password-123'}).status_code == 204
    assert reset(client, sent[-1][1]).status_code == 400
