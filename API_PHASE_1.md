# MyDawnDiary — Phase 1 API task list

This is the task list for the first backend phase. The account, daily diary, conversation, note, recycle-bin, private social-draft, and 30-day activity endpoints and database schema are implemented in `backend/`. This is the Phase 1 backend baseline on `main`. AI, speech-to-text, wake-word, email, external social publishing, and AI-written personality review remain open. AI integration will be discussed after the backend layer.

## Working resource model

- **User account:** owns private diary data.
- **Daily diary:** the user's single diary for a calendar day, containing that day's conversations and notes.
- **Record:** one saved AI conversation started inside the app by a user in the first release.
- **Conversation entry:** a message or turn belonging to a record, with its speaker and order preserved.
- **Note:** a user-written text entry in a daily diary, optionally linked to a conversation. An unlinked note does not require a conversation record.

The one-record-to-one-conversation relationship is confirmed. Endpoint and table names remain open.

## Task breakdown

### 1. User accounts and access

- Define the minimum information required to create an account.
- Define sign-in, sign-out, and account recovery behavior.
- Use email and password for sign-in. Verify the address after registration with an email OTP delivered by Resend.
- Define how a user views and updates their own account.
- Define how account deletion affects owned records and conversation entries.
- Ensure every private-data operation checks the signed-in user's ownership.

### 2. Daily diary API

- Get or create the signed-in user's diary for a local calendar day without creating duplicates.
- List diary days and show the conversations and notes belonging to one day.
- Generate and read one AI-written combined entry from that day's conversations and notes, while keeping the source items available separately.
- Let the owner edit the combined entry while preserving the original AI-written version.
- Define when to generate or refresh that entry as more items arrive during the day.

### 3. Records API

- Create a record for the signed-in user.
- Autosave an in-progress record and its finalized text entries during the AI conversation.
- Complete the record and generate its summary when the conversation ends, without treating ordinary pauses as an ending.
- Let the owner edit the summary, while keeping finalized conversation entries immutable.
- List the user's records with ordering and pagination.
- Read one record and its basic metadata.
- Update a record's editable metadata.
- Move a deleted record to a recycle bin, allow recovery, and permanently purge it after three days.

### 4. Conversation API

- Add a conversation entry to a record.
- List entries in conversation order.
- Read entries in order; finalized entries cannot be edited by the user.
- Support correction of a misheard word during live speech-to-text capture, before the entry becomes final.
- Preserve source information such as AI provider/model when available.
- Support an AI interaction activated by “Dear Diary” once the microphone is ready.
- Handle speech-to-text entries and AI responses during the conversation.
- Define how an interrupted in-progress interaction is resumed.

### 5. Notes API

- Create a standalone text note for the signed-in user.
- Support primarily manual note entry after the “Dear Diary” activation and allow an optional link to a conversation record in the daily diary.
- Keep unlinked notes in that day's diary. If a linked conversation is permanently deleted, retain the note and clear its link.
- List, read, and update the user's notes.
- Move a deleted note to a recycle bin, allow recovery, and permanently purge it after three days.
- Require the signed-in account to own a note before it can be listed, read, updated, or deleted. Other accounts cannot access it.

### 6. Shared API behavior

- Decide request and response formats, validation rules, error responses, and pagination.
- Define authentication and authorization rules across all endpoints.
- Decide whether deleted data can be restored and how export will work.
- Document the API and verify the key account-to-record-to-conversation flow.

## Additional backend areas

- Private social post drafts and explicit approval are implemented. External publication needs a platform integration and remains open.
- Thirty-day activity counts are implemented. AI-written personality reflections remain open until AI integration is discussed.

## Open decisions before implementation

- Which account fields and sign-in method should be supported first?
- Where is the “Dear Diary” phrase detected, and how is accidental activation handled?
- How does the app distinguish a true conversation ending from a pause?
- How does the user choose between conversation recording and note creation?
- Use the account's IANA time zone for diary dates. Permit today or yesterday for new conversations and final conversation placement, allow any past date for new notes, and allow edits to older diaries. Reject future dates.
- When should the combined daily entry be generated or refreshed?
- Email OTP verifies the address after registration; Resend provides delivery.
- Which database and Python API framework should be used on the existing server?
