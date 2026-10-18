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

The API serves interactive documentation at `/docs`. Set `DATABASE_URL` to a PostgreSQL `postgresql+psycopg://...` URL for the server. Keep `JWT_SECRET` and database credentials in the server environment. A `.env` file is ignored by Git but is not loaded automatically; supply the variables through the service configuration or load the file explicitly when launching the API.

## Traffic protection and alerts

The API counts requests and emits one aggregate log line per minute with the request, throttle, and server-error counts. It does not log diary text, request bodies, tokens, or email addresses. With the default settings it returns HTTP 429 after 120 requests per minute from one direct client address, or after 10 requests per minute to `/auth/*` from that address. The response includes `Retry-After: 60`. Set `REQUESTS_PER_MINUTE` and `AUTH_REQUESTS_PER_MINUTE` to tune the limits.

At 300 requests in a minute, it writes a warning and can send one email alert. Set `RESEND_API_KEY`, `ALERT_EMAIL_FROM`, and `ALERT_EMAIL_TO` to use Resend. The sender must use a domain verified in Resend. Alternatively, set the `ALERT_SMTP_*` fields with the same sender and recipients to use SMTP STARTTLS on port 587. `ALERT_EMAIL_TO` accepts comma-separated recipients. `ALERT_COOLDOWN_MINUTES` defaults to 15, so a sustained spike does not flood the inbox. Mail failures are logged and do not interrupt API requests. These are request-volume alerts, not CPU or memory alarms.

The counters are in memory **per API worker**. For a deployment with multiple workers or public traffic, configure shared rate limits at the reverse proxy as well. Ensure the proxy passes the real client address only from a trusted proxy; otherwise the API may treat all visitors as one address. Uvicorn access logging is also available for individual HTTP requests. This repository does not contain an active MyDawnDiary server deployment, so these protections start when this API version is deployed and the optional email settings are supplied.

## Web frontend

The responsive React, Vite, and TypeScript app lives in `../frontend/`. Start the API on port 8000, then in a second PowerShell window run:

```powershell
cd ..\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/app/`. Vite forwards account, note, and diary requests to the local API. For a production build, run `npm run build`; when `frontend/dist/` exists, FastAPI serves it at `/app/`. For a non-editable backend install, set `FRONTEND_DIST_DIR` to the absolute path of that build directory. The central color palette is in `frontend/src/theme.css`.

The current UI handles registration, email verification, sign-in, and manual note creation and editing. Its diary page navigates today and 30 previous days; All Notes keeps older notes available and links directly to their diary dates. Trash shows recoverable deleted notes and conversations. Voice capture and AI conversations are planned later.

For registration verification, also set `RESEND_API_KEY` in the server environment and set `RESEND_FROM_EMAIL` to a sender at a domain verified in Resend, such as `MyDawnDiary <verify@your-domain.example>`. Do not put the API key in source files. Restart the API after changing these variables. Registration returns 503 and creates no account when delivery fails or Resend is not configured.

If registration reports that the Resend API key or sender is missing, stop the API and check `[bool]$env:RESEND_API_KEY` and `[bool]$env:RESEND_FROM_EMAIL` in the same PowerShell window that starts it. Set any missing value there, then restart the API. The settings are read at startup.

## Current API flow

1. Register with email, password, and an IANA time zone. Registration sends a six-digit email code. Submit the email and code to `POST /auth/verify-email`, then sign in for a bearer token. Use `POST /auth/resend-verification` with the email address to request another code. The owner can update their profile or change their password with the current password. Changing the password or calling `POST /auth/sign-out-all` revokes existing access tokens.
2. Start a conversation with `POST /records`. A diary for the chosen user-local date is created if needed. New conversations can be assigned only to today or yesterday.
3. Append finalized transcript and AI response turns with `POST /records/{id}/entries`. Entries cannot be edited after submission. Correct speech recognition before sending an entry.
4. Complete the conversation with `POST /records/{id}/complete`, supplying the AI-generated summary. A conversation crossing midnight remains one record and may be assigned to yesterday or today at completion. A draft resumed after several days must be explicitly assigned to today or yesterday.
5. Edit only the displayed summary with `PATCH /records/{id}/summary`; the AI original remains available.
6. Add a note with `POST /notes`, optionally linking it to a conversation in the same daily diary. Notes can be assigned to today or any past date, never a future date. Notes and summaries in older diaries remain editable.
7. Store an AI-generated combined daily entry with `PUT /diaries/{date}/ai-entry`; edit the displayed version with `PATCH /diaries/{date}/entry`.
8. Prepare private social copy with `POST /social-drafts`, then edit and explicitly approve it. Approval only marks it ready; it never publishes to an external platform.
9. Read activity counts by user-local diary date with `GET /reviews/activity`. The report covers today and the previous 29 days and excludes incomplete or trashed conversations and trashed notes.

Records and notes have private paginated list endpoints, `GET /records` and `GET /notes`. Filter conversations that can be resumed with `GET /records?status=draft`, then fetch the full transcript with `GET /records/{id}`.

Records and notes move to `/trash` for three days when deleted. A restore endpoint is available for each. Run `python -m mydawndiary.purge` on a server schedule to permanently remove expired items. Purging a conversation leaves its linked notes in the daily diary and clears their conversation link.

## Integration boundaries

The API **does not yet connect to an AI model, microphone, speech-to-text service, or wake-word detector**. The conversation-complete and daily-entry endpoints store text supplied by a future AI integration; they do not generate it. Email verification uses Resend; password recovery, social publishing, and AI-written personality review remain pending. Social drafts are private snapshots; approving one does not authorize or initiate publication. Publishing will require a separate provider integration and explicit user action.

Verification codes expire after 10 minutes. At most five wrong guesses are allowed per code, with a five-minute resend wait and five sends per hour. The UI should disable its resend button for five minutes after requesting a code; the API also enforces the wait. Resending replaces the previous code. Unknown and already verified addresses get the same 202 response from the resend endpoint. Existing accounts are marked verified when the migration is applied.

The combined daily entry is marked stale when source content changes. Deleting a conversation or note clears both versions of that daily entry because they might contain deleted content. A later AI integration must regenerate it.
Regenerating an entry with a user edit returns a conflict unless the caller explicitly sets `replace_user_edit` to true.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests cover account isolation, the midnight date choice, immutable completed transcripts, older-diary editing, recycle-bin restoration and purging, preservation of original summaries, social draft approval, and private 30-day activity counts.
