# MyDawnDiary — data model draft

This is a discussion draft for the first backend phase. It describes concepts and relationships, not a finalized database schema. No database or API code has been created.

## Core relationships

```mermaid
erDiagram
    USER ||--o{ DAILY_DIARY : owns
    DAILY_DIARY ||--o{ RECORD : contains
    DAILY_DIARY ||--o{ NOTE : contains
    RECORD ||--o{ CONVERSATION_ENTRY : contains
    RECORD o|--o{ NOTE : optionally_links
```

**Confirmed:** one record represents exactly one saved AI conversation. A user can own many records, and each record contains that conversation's entries in order.

**Confirmed:** a user can also save a freeform text note independently of any AI conversation. A note does not require a record.

**Confirmed:** personal notes are private to their owner. Other user accounts cannot view or change them.

**Confirmed:** records and notes enter a recycle bin when deleted and are permanently removed three days later.

**Confirmed:** each user has at most one diary for a calendar day. That daily diary can contain multiple conversation records and multiple notes. A note may be linked to one conversation or remain unlinked. An unlinked note still belongs to its day's diary; no placeholder conversation is needed.

**Confirmed:** the daily diary includes one AI-written combined entry drawn from that day's conversations and notes. The user may edit the displayed daily entry while the original AI version is preserved. The complete conversations and notes remain available separately; a “Read more” control may expand long content in the interface without shortening the stored text.

## First-release conversation flow

1. The user enables the microphone. Saying **“Dear Diary”** activates the AI interaction.
2. The user speaks with the AI. Speech-to-text produces ordered text entries. The in-progress record is autosaved so an interruption does not lose the conversation. The user may correct a misheard word during live capture before that entry is finalized.
3. When the conversation actually ends, the AI creates a summary and the record is marked complete. Ordinary pauses do not end the conversation or trigger a summary. The user may edit the summary, but cannot edit finalized conversation entries.

The same activation should also let the user create a personal note. Notes are primarily entered manually and may optionally link to a record. Only the transcript is retained; raw audio is not saved. How the app detects the activation phrase and a true end of conversation remains open.

## Core entities

### User

The person who owns private diary content.

| Candidate field | Purpose | Status |
| --- | --- | --- |
| `id` | Stable internal identity | Proposed |
| `email` | Sign-in and account contact | Confirmed |
| `password_hash` | Password verification without storing the password | Confirmed |
| `display_name` | Name shown in the app | Optional |
| `created_at` | Account creation time | Proposed |
| `time_zone` | Determines the user's local diary date | Proposed |

Authentication credentials should be handled separately from diary content. Email and password sign-in is confirmed. Email OTP may be added within a free sending allowance; its exact role (email verification, sign-in, or second factor) is still open.

### Daily diary

The one diary belonging to a user for a calendar day. It groups all of that day's conversations and notes and has one AI-written combined entry. A unique constraint on `user_id` and `diary_date` prevents duplicate diaries for the same day.

| Candidate field | Purpose | Status |
| --- | --- | --- |
| `id` | Stable daily-diary identity | Proposed |
| `user_id` | Owner | Confirmed concept |
| `diary_date` | The day in the user's chosen time zone | Confirmed concept; time zone choice open |
| `ai_combined_entry` | Original AI-written daily entry based on that day's conversations and notes | Confirmed concept |
| `edited_combined_entry` | User-edited version, if changed | Confirmed concept |
| `combined_entry_generated_at`, `combined_entry_edited_at` | Generation and last edit times | Proposed |
| `created_at`, `updated_at` | When the daily diary was created and changed | Proposed |

The combined entry adds a readable account of the day; it does not replace the source conversations or notes. When it is first generated and whether later additions regenerate it are open decisions.

### Record

One saved AI conversation belonging to one daily diary, and therefore owned by that diary's user.

| Candidate field | Purpose | Status |
| --- | --- | --- |
| `id` | Stable record identity | Proposed |
| `diary_id` | Parent daily diary | Confirmed concept |
| `title` | User-facing label | Proposed |
| `status` | In progress, complete, or in recycle bin | Confirmed concept |
| `source` | Origin; first-release conversations start in this app | Optional |
| `started_at` | When the interaction began | Proposed |
| `ended_at` | When the conversation actually ended | Proposed |
| `ai_summary` | Original AI-generated summary, preserved after user edits | Confirmed concept |
| `edited_summary` | User-edited version, if changed | Confirmed concept |
| `summary_generated_at`, `summary_updated_at` | Summary creation and last edit times | Proposed |
| `deleted_at` | When moved to recycle bin; permanent purge follows after three days | Confirmed concept |
| `created_at`, `updated_at` | When the record was saved and changed | Proposed |

### Conversation entry

One turn or message inside a record.

| Candidate field | Purpose | Status |
| --- | --- | --- |
| `id` | Stable entry identity | Proposed |
| `record_id` | Parent record | Proposed |
| `position` | Order within the conversation | Proposed |
| `speaker` | User or AI assistant | Proposed |
| `content` | Finalized message text, including speech-to-text output for spoken user turns | Proposed |
| `model` | AI model, if known | Optional |
| `occurred_at` | Original message time, if known | Optional |
| `created_at` | Time saved in MyDawnDiary | Proposed |

Finalized entries are immutable. Corrections to speech recognition happen during live capture, before an entry is finalized. No raw audio field is needed in the first-release model.

### Note

A standalone text entry written by a user, separate from AI conversation records.

| Candidate field | Purpose | Status |
| --- | --- | --- |
| `id` | Stable note identity | Proposed |
| `diary_id` | Parent daily diary and route to its owner | Confirmed concept |
| `record_id` | Optional link to one conversation record; empty means unlinked | Confirmed concept |
| `title` | Optional label | Optional |
| `content` | Primarily manually entered, user-written note text | Confirmed concept |
| `deleted_at` | When moved to recycle bin; permanent purge follows after three days | Confirmed concept |
| `created_at`, `updated_at` | When the note was saved and changed | Proposed |

## Rules to settle

- Each record and its entries are private to their owner unless the user explicitly chooses to publish content.
- Only the note owner can read, edit, or delete that note.
- Define when a live speech-to-text entry becomes final and how a user corrects a misheard word before then.
- Define how the app distinguishes an ended conversation from a pause.
- Define how to resume an interrupted in-progress record.
- Decide whether deleting a record also removes its entries and what happens to linked notes, reviews, and social drafts when the three-day recycle-bin period ends.
- Preserve notes when a linked conversation is permanently deleted; clear the link so those notes become unlinked.
- Define whether a note can link to a conversation from another diary day.
- Define the user's time zone, and whether a conversation crossing midnight belongs to its start day or end day.
- Decide whether an empty daily diary is created each day or created when the first conversation or note arrives.
- Decide when the combined entry is first generated and how it is updated when another conversation or note is added that day.
- Define whether the 30-day review uses original conversation times, save times, or both.
- Define how to handle missing provider, model, and timestamp information if import is added later.
- Define the role of email OTP if a free sending service is selected.

## Later entities

Social post drafts/publications and 30-day reviews will be modeled after their behavior is agreed. They should reference the user's content without making private entries public by default.

## Confirmed decision

**One record = one AI conversation.** A record does not group multiple conversations.
