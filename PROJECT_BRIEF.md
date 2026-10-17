# MyDawnDiary — working brief

## Name

**MyDawnDiary** is the chosen app name. “Dawn” represents new hope as the sun shines; “Diary” describes the personal record. The name also nods to the Tagalog word *talaarawan* (diary).

## Goal

Create a full-stack application called **MyDawnDiary** that records a person's conversations with AI models, lets them post selected content to social media, and provides a review of their personality and activity over the past 30 days.

Each user has one diary per calendar day. That diary groups multiple AI conversations and notes. A note may link to a conversation or remain unlinked within the day's diary.
The diary also includes one AI-written combined entry based on that day's conversations and notes. Users may edit this daily entry while the original AI version and full source items remain available for review.
Diary dates follow the user's chosen time zone. New content may be saved to today or yesterday, never a future day. A conversation crossing midnight remains one record; its day can be chosen at completion. Existing older summaries and notes remain editable.

This document captures the product direction and decisions made so far. A Python API and relational data model are in `backend/`; AI and speech integrations will be discussed after the backend layer. Private social drafts and 30-day activity counts are implemented; external posting and personality review remain open.

## Initial deployment scope

- Plan for the application and its data to run in the cloud.
- Use the existing user-owned server for the initial deployment, with light workloads only.
- Initial capacity target: no more than 10 users using the application at the same time.
- The backend uses Python, FastAPI, SQLAlchemy, and Alembic. PostgreSQL is planned for the server; SQLite is used for local development and tests.
- Planned application directory on the server: `/srv/app/mydawndiary`, separate from the existing website in `/srv/app/www` and the landing-page project in `/srv/app/mbe-landpage`.
- Use the development account for application files. Reserve administrator access for system configuration when needed.

## Capabilities to define

1. **Conversation records:** With the microphone ready, “Dear Diary” activates an AI conversation. Speech-to-text produces an autosaved draft transcript. When the conversation ends, the AI creates an editable summary and the one-conversation record is completed. Pauses do not end it. Finalized transcript entries cannot be edited; raw audio is not saved.
2. **Personal notes:** Users can save primarily manual text notes independently of AI conversations and may optionally link a note to a record. Only the owning account can see or change a note.
3. **Social posting:** Which platforms are in scope? What content may be shared, and what review and approval should happen before a post is published?
4. **30-day review:** What does “personality” mean in this product? Which activity measures and time window should the review use, and how should conclusions be explained?
5. **Accounts and privacy:** Who can access the diary? What consent, retention, export, and deletion controls are needed for potentially sensitive conversations and notes?

Email and password sign-in is planned. Email OTP is optional if a free sending allowance works for the app. Deleted records and notes go to a recycle bin and are permanently removed after three days.

## Decisions still open

- Intended users and the main problem the app should solve for them.
- Whether importing conversations from other AI apps will be supported later; the first-release flow starts inside MyDawnDiary.
- How the app detects “Dear Diary,” distinguishes a true conversation ending from a pause, and lets the user choose between a conversation and a note.
- Whether optional email OTP will be used, and whether it verifies an email, supports sign-in, or adds a second factor.
- Whether the diary is private by default and whether any sharing beyond social posts is needed.
- Whether posting is manual, scheduled, or automated.
- Whether the review is a reflective summary, a set of metrics, or something else.
- Existing server specifications and operating system; database, platforms, integrations, regions, and devices to support.
- Success criteria for an initial release.

## Working approach

We will clarify one area at a time. This brief records the agreed requirements alongside the Phase 1 backend baseline; later integrations will build on it.
