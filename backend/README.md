# MyDawnDiary API

Python API for the first backend phase. It models accounts, one diary per user-local day, conversations, immutable finalized transcript entries, optional conversation-linked notes, editable summaries, a three-day recycle bin, private social post drafts, and a 30-day activity report.

## Run locally

Use Python 3.11 or newer and PostgreSQL for the intended server deployment. SQLite is available for local development and tests.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
$env:JWT_SECRET = "a-long-random-secret-of-at-least-32-characters"
$env:DATABASE_URL = "sqlite:///./mydawndiary.db"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn mydawndiary.main:app --reload
```

The API serves interactive documentation at `/docs`. Set `DATABASE_URL` to a PostgreSQL `postgresql+psycopg://...` URL for the server. Keep `JWT_SECRET` and database credentials in the server environment; `.env` is ignored by Git.

## Current API flow

1. Register with email, password, and an IANA time zone; sign in for a bearer token. The owner can update their profile or change their password with the current password. Changing the password or calling `POST /auth/sign-out-all` revokes existing access tokens.
2. Start a conversation with `POST /records`. A diary for the chosen user-local date is created if needed. New content can be assigned only to today or yesterday.
3. Append finalized transcript and AI response turns with `POST /records/{id}/entries`. Entries cannot be edited after submission. Correct speech recognition before sending an entry.
4. Complete the conversation with `POST /records/{id}/complete`, supplying the AI-generated summary. A conversation crossing midnight remains one record and may be assigned to yesterday or today at completion. A draft resumed after several days must be explicitly assigned to today or yesterday.
5. Edit only the displayed summary with `PATCH /records/{id}/summary`; the AI original remains available.
6. Add a note with `POST /notes`, optionally linking it to a conversation in the same daily diary. Notes and summaries in older diaries remain editable.
7. Store an AI-generated combined daily entry with `PUT /diaries/{date}/ai-entry`; edit the displayed version with `PATCH /diaries/{date}/entry`.
8. Prepare private social copy with `POST /social-drafts`, then edit and explicitly approve it. Approval only marks it ready; it never publishes to an external platform.
9. Read activity counts by user-local diary date with `GET /reviews/activity`. The report covers today and the previous 29 days and excludes incomplete or trashed conversations and trashed notes.

Records and notes have private paginated list endpoints, `GET /records` and `GET /notes`. Filter conversations that can be resumed with `GET /records?status=draft`, then fetch the full transcript with `GET /records/{id}`.

Records and notes move to `/trash` for three days when deleted. A restore endpoint is available for each. Run `python -m mydawndiary.purge` on a server schedule to permanently remove expired items. Purging a conversation leaves its linked notes in the daily diary and clears their conversation link.

## Integration boundaries

The API **does not yet connect to an AI model, microphone, speech-to-text service, wake-word detector, or email sender**. The conversation-complete and daily-entry endpoints store text supplied by a future AI integration; they do not generate it. Email OTP, password recovery, social publishing, and AI-written personality review remain pending. Social drafts are private snapshots; approving one does not authorize or initiate publication. Publishing will require a separate provider integration and explicit user action.

The combined daily entry is marked stale when source content changes. Deleting a conversation or note clears both versions of that daily entry because they might contain deleted content. A later AI integration must regenerate it.
Regenerating an entry with a user edit returns a conflict unless the caller explicitly sets `replace_user_edit` to true.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover account isolation, the midnight date choice, immutable completed transcripts, older-diary editing, recycle-bin restoration and purging, preservation of original summaries, social draft approval, and private 30-day activity counts.
