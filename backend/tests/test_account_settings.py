from sqlalchemy import select

from conftest import register_and_login
from mydawndiary.models import User, DailyDiary, Note, Record, ConversationEntry, SocialDraft


def test_theme_is_validated_persisted_and_private(api):
    client, _ = api
    owner = register_and_login(client, "theme@example.com")
    other = register_and_login(client, "other@example.com")
    assert client.get("/auth/me", headers=owner).json()["theme"] == "orange-yellow"
    for theme in ("blue-yellow", "green-yellow", "orange-yellow"):
        response = client.patch("/auth/me", headers=owner, json={"theme": theme})
        assert response.status_code == 200
        assert client.get("/auth/me", headers=owner).json()["theme"] == theme
    for invalid in (None, "unknown"):
        assert client.patch("/auth/me", headers=owner, json={"theme": invalid}).status_code == 422
    assert client.patch("/auth/me", json={"theme": "blue-yellow"}).status_code == 401
    assert client.get("/auth/me", headers=other).json()["theme"] == "orange-yellow"


def test_account_deletion_removes_all_content_and_releases_email(api):
    client, factory = api
    owner = register_and_login(client, "delete@example.com")
    other = register_and_login(client, "keep@example.com")
    user_id = client.get("/auth/me", headers=owner).json()["id"]
    record = client.post("/records", headers=owner, json={}).json()
    entry = client.post(f"/records/{record['id']}/entries", headers=owner,
                        json={"speaker": "user", "content": "Private conversation"}).json()
    note = client.post("/notes", headers=owner, json={"content": "Linked note", "record_id": record["id"]}).json()
    trashed = client.post("/notes", headers=owner, json={"content": "Deleted note"}).json()
    assert client.delete(f"/notes/{trashed['id']}", headers=owner).status_code == 204
    keep = client.post("/notes", headers=other, json={"content": "Keep me"}).json()
    with factory() as db:
        draft = SocialDraft(user_id=user_id, content="Private draft")
        db.add(draft)
        db.commit()
        draft_id = draft.id
    body = {"current_password": "long-test-password-123"}
    assert client.request("DELETE", "/auth/me", json=body).status_code == 401
    assert client.request("DELETE", "/auth/me", headers=owner, json={"current_password": "wrong"}).status_code == 403
    assert client.get(f"/notes/{note['id']}", headers=owner).status_code == 200
    assert client.request("DELETE", "/auth/me", headers=owner, json=body).status_code == 204
    assert client.get("/auth/me", headers=owner).status_code == 401
    assert client.get("/notes", headers=owner).status_code == 401
    with factory() as db:
        for model, identifier in ((User, user_id), (Record, record["id"]), (ConversationEntry, entry["id"]),
                                  (Note, note["id"]), (Note, trashed["id"]), (SocialDraft, draft_id)):
            assert db.get(model, identifier) is None
        assert db.scalar(select(DailyDiary).where(DailyDiary.user_id == user_id)) is None
    assert client.get(f"/notes/{keep['id']}", headers=other).status_code == 200
    replacement = register_and_login(client, "delete@example.com")
    assert client.get("/auth/me", headers=replacement).json()["id"] != user_id
    assert client.get("/notes", headers=replacement).json() == []
    assert client.get("/auth/me", headers=owner).status_code == 401
