from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from mydawndiary import notes as note_routes, records as record_routes, reviews as review_routes
from mydawndiary import purge
from mydawndiary.models import Note, Record

from conftest import register_and_login


def test_private_conversation_and_note_access(api):
    client, _ = api
    owner = register_and_login(client, "owner@example.com")
    stranger = register_and_login(client, "stranger@example.com")
    record = client.post("/records", headers=owner, json={"title": "Morning"}).json()
    note = client.post("/notes", headers=owner, json={"content": "My private note", "record_id": record["id"]}).json()

    assert client.get(f"/records/{record['id']}", headers=stranger).status_code == 404
    assert client.get(f"/notes/{note['id']}", headers=stranger).status_code == 404
    assert client.get(f"/diaries/{datetime.now(ZoneInfo('Asia/Manila')).date()}", headers=stranger).status_code == 404
    assert client.patch(f"/notes/{note['id']}", headers=stranger, json={"content": "Changed"}).status_code == 404


def test_cross_midnight_conversation_is_one_record_and_transcript_is_immutable(api, monkeypatch):
    client, _ = api
    headers = register_and_login(client, "midnight@example.com")
    before = datetime(2026, 10, 17, 15, 50, tzinfo=timezone.utc)  # 11:50 PM in Manila
    after = datetime(2026, 10, 17, 17, 10, tzinfo=timezone.utc)  # 1:10 AM next day
    monkeypatch.setattr(record_routes, "utc_now", lambda: before)
    record_response = client.post("/records", headers=headers, json={})
    assert record_response.status_code == 201, record_response.text
    record = record_response.json()
    assert client.get("/diaries/2026-10-17", headers=headers).status_code == 200

    first = client.post(f"/records/{record['id']}/entries", headers=headers, json={"speaker": "user", "content": "I have a meeting."})
    second = client.post(f"/records/{record['id']}/entries", headers=headers, json={"speaker": "assistant", "content": "Tell me more."})
    assert [first.json()["position"], second.json()["position"]] == [1, 2]

    monkeypatch.setattr(record_routes, "utc_now", lambda: after)
    completed = client.post(f"/records/{record['id']}/complete", headers=headers, json={"ai_summary": "A meeting was discussed.", "diary_date": "2026-10-18"})
    assert completed.status_code == 200, completed.text
    assert completed.json()["ai_summary"] == "A meeting was discussed."
    assert client.get("/diaries/2026-10-18", headers=headers).json()["records"][0]["id"] == record["id"]
    assert client.get("/diaries/2026-10-17", headers=headers).json()["records"] == []

    edited = client.patch(f"/records/{record['id']}/summary", headers=headers, json={"text": "My edited summary."})
    assert edited.json()["ai_summary"] == "A meeting was discussed."
    assert edited.json()["edited_summary"] == "My edited summary."
    assert client.post(f"/records/{record['id']}/entries", headers=headers, json={"speaker": "user", "content": "Late addition"}).status_code == 409
    assert client.patch(f"/records/{record['id']}/entries/{first.json()['id']}", headers=headers, json={"content": "Changed"}).status_code == 404


def test_yesterday_today_limit_and_older_edits(api, monkeypatch):
    client, _ = api
    headers = register_and_login(client, "dates@example.com")
    fixed = datetime(2026, 10, 17, 17, 10, tzinfo=timezone.utc)
    monkeypatch.setattr(record_routes, "utc_now", lambda: fixed)
    monkeypatch.setattr(note_routes, "utc_now", lambda: fixed)

    assert client.post("/records", headers=headers, json={"diary_date": "2026-10-19"}).status_code == 422
    assert client.post("/notes", headers=headers, json={"diary_date": "2026-10-16", "content": "Too old"}).status_code == 422
    yesterday_note = client.post("/notes", headers=headers, json={"diary_date": "2026-10-17", "content": "Yesterday"})
    assert yesterday_note.status_code == 201

    later = fixed + timedelta(days=5)
    monkeypatch.setattr(note_routes, "utc_now", lambda: later)
    note_id = yesterday_note.json()["id"]
    assert client.patch(f"/notes/{note_id}", headers=headers, json={"content": "Edited later"}).json()["content"] == "Edited later"
    assert client.post("/notes", headers=headers, json={"diary_date": "2026-10-17", "content": "New old item"}).status_code == 422


def test_resumed_draft_must_be_assigned_to_today_or_yesterday(api, monkeypatch):
    client, _ = api
    headers = register_and_login(client, "resume@example.com")
    started = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(record_routes, "utc_now", lambda: started)
    record = client.post("/records", headers=headers, json={}).json()
    client.post(f"/records/{record['id']}/entries", headers=headers, json={"speaker": "user", "content": "I started earlier."})

    monkeypatch.setattr(record_routes, "utc_now", lambda: started + timedelta(days=5))
    assert client.post(f"/records/{record['id']}/complete", headers=headers, json={"ai_summary": "Earlier."}).status_code == 422
    completed = client.post(f"/records/{record['id']}/complete", headers=headers, json={"ai_summary": "Earlier.", "diary_date": "2026-10-22"})
    assert completed.status_code == 200, completed.text
    assert completed.json()["diary_date"] == "2026-10-22"


def test_recycle_bin_keeps_linked_note_then_unlinks_on_purge(api, monkeypatch):
    client, factory = api
    headers = register_and_login(client, "trash@example.com")
    record = client.post("/records", headers=headers, json={}).json()
    linked = client.post("/notes", headers=headers, json={"content": "Keep me", "record_id": record["id"]}).json()
    standalone = client.post("/notes", headers=headers, json={"content": "Also keep me"}).json()

    assert client.delete(f"/records/{record['id']}", headers=headers).status_code == 204
    assert client.get(f"/notes/{linked['id']}", headers=headers).json()["record_id"] == record["id"]
    assert len(client.get("/trash", headers=headers).json()["records"]) == 1
    assert client.post(f"/records/{record['id']}/restore", headers=headers).status_code == 200

    assert client.delete(f"/records/{record['id']}", headers=headers).status_code == 204
    with factory() as db:
        item = db.get(Record, record["id"])
        item.purge_after = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(purge, "session_factory", lambda: factory)
    assert purge.purge_expired() == (1, 0)
    assert client.get(f"/notes/{linked['id']}", headers=headers).json()["record_id"] is None
    assert client.get(f"/notes/{standalone['id']}", headers=headers).status_code == 200


def test_combined_entry_keeps_original_and_clears_deleted_source(api):
    client, _ = api
    headers = register_and_login(client, "combined@example.com")
    note = client.post("/notes", headers=headers, json={"content": "A good day"}).json()
    date = datetime.now(ZoneInfo("Asia/Manila")).date().isoformat()
    ai = client.put(f"/diaries/{date}/ai-entry", headers=headers, json={"text": "The day went well."})
    assert ai.status_code == 200, ai.text
    edited = client.patch(f"/diaries/{date}/entry", headers=headers, json={"text": "I felt good today."})
    assert edited.json()["ai_combined_entry"] == "The day went well."
    assert edited.json()["edited_combined_entry"] == "I felt good today."
    assert client.put(f"/diaries/{date}/ai-entry", headers=headers, json={"text": "A new draft."}).status_code == 409
    assert client.delete(f"/notes/{note['id']}", headers=headers).status_code == 204
    diary = client.get(f"/diaries/{date}", headers=headers).json()
    assert diary["ai_combined_entry"] is None
    assert diary["edited_combined_entry"] is None


def test_social_drafts_require_owned_sources_and_explicit_approval(api):
    client, _ = api
    owner = register_and_login(client, "poster@example.com")
    stranger = register_and_login(client, "other-poster@example.com")
    note = client.post("/notes", headers=owner, json={"content": "Private source"}).json()

    assert client.post("/social-drafts", headers=stranger, json={"content": "Stolen", "source_kind": "note", "source_id": note["id"]}).status_code == 404
    assert client.post("/social-drafts", headers=owner, json={"content": "Missing ID", "source_kind": "note"}).status_code == 422
    created = client.post("/social-drafts", headers=owner, json={"content": "A post I choose to share", "platform": "example", "source_kind": "note", "source_id": note["id"]})
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "draft"
    assert client.get(f"/social-drafts/{draft['id']}", headers=stranger).status_code == 404
    assert client.get("/social-drafts", headers=stranger).json() == []
    assert client.patch(f"/social-drafts/{draft['id']}", headers=owner, json={"content": "Final copy"}).json()["content"] == "Final copy"
    assert client.post(f"/social-drafts/{draft['id']}/approve", headers=owner).json()["status"] == "approved"
    assert client.patch(f"/social-drafts/{draft['id']}", headers=owner, json={"content": "Changed"}).status_code == 409
    assert client.delete(f"/social-drafts/{draft['id']}", headers=owner).status_code == 204


def test_activity_review_counts_only_active_items_in_last_30_days(api, monkeypatch):
    client, _ = api
    owner = register_and_login(client, "reviewer@example.com")
    stranger = register_and_login(client, "other-reviewer@example.com")
    fixed = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(record_routes, "utc_now", lambda: fixed)
    monkeypatch.setattr(note_routes, "utc_now", lambda: fixed)
    monkeypatch.setattr(review_routes, "utc_now", lambda: fixed)

    record = client.post("/records", headers=owner, json={"diary_date": "2026-10-16"}).json()
    client.post(f"/records/{record['id']}/entries", headers=owner, json={"speaker": "user", "content": "Hello"})
    client.post(f"/records/{record['id']}/entries", headers=owner, json={"speaker": "assistant", "content": "Hi"})
    client.post(f"/records/{record['id']}/complete", headers=owner, json={"ai_summary": "A greeting"})
    current_note = client.post("/notes", headers=owner, json={"content": "Today"}).json()
    deleted_note = client.post("/notes", headers=owner, json={"content": "Deleted"}).json()
    client.delete(f"/notes/{deleted_note['id']}", headers=owner)
    client.post("/notes", headers=stranger, json={"content": "Not mine"})

    report = client.get("/reviews/activity", headers=owner)
    assert report.status_code == 200, report.text
    data = report.json()
    assert (data["start_date"], data["end_date"], data["active_days"]) == ("2026-09-18", "2026-10-17", 2)
    assert (data["conversations"], data["notes"], data["messages"]) == (1, 1, 2)
    assert len(data["days"]) == 30
    assert client.get(f"/notes/{current_note['id']}", headers=owner).status_code == 200


def test_account_password_change_and_private_paginated_lists(api):
    client, _ = api
    owner = register_and_login(client, "lists@example.com")
    stranger = register_and_login(client, "other-lists@example.com")
    first = client.post("/records", headers=owner, json={}).json()
    second = client.post("/records", headers=owner, json={}).json()
    note = client.post("/notes", headers=owner, json={"content": "Mine"}).json()
    client.post("/records", headers=stranger, json={})
    client.post("/notes", headers=stranger, json={"content": "Theirs"})

    assert {row["id"] for row in client.get("/records", headers=owner).json()} == {first["id"], second["id"]}
    assert len(client.get("/records?limit=1", headers=owner).json()) == 1
    assert {row["id"] for row in client.get("/records?status=draft", headers=owner).json()} == {first["id"], second["id"]}
    assert [row["id"] for row in client.get("/notes", headers=owner).json()] == [note["id"]]
    assert client.post("/auth/change-password", headers=owner, json={"current_password": "wrong", "new_password": "new-long-password-456"}).status_code == 401
    assert client.post("/auth/change-password", headers=owner, json={"current_password": "long-test-password-123", "new_password": "new-long-password-456"}).status_code == 204
    assert client.get("/auth/me", headers=owner).status_code == 401
    assert client.post("/auth/login", json={"email": "lists@example.com", "password": "long-test-password-123"}).status_code == 401
    fresh = client.post("/auth/login", json={"email": "lists@example.com", "password": "new-long-password-456"})
    assert fresh.status_code == 200
    fresh_headers = {"Authorization": f"Bearer {fresh.json()['access_token']}"}
    assert client.post("/auth/sign-out-all", headers=fresh_headers).status_code == 204
    assert client.get("/auth/me", headers=fresh_headers).status_code == 401
