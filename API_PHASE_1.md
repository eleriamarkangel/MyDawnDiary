# MyDawnDiary — Phase 1 API task list

This is a planning draft for the first backend phase. No endpoints, database schema, or framework have been implemented or finalized. Commit the Markdown planning files after the data model is agreed, as requested.

## Working resource model

- **User account:** owns private diary data.
- **Record:** one saved AI conversation started inside the app by a user in the first release.
- **Conversation entry:** a message or turn belonging to a record, with its speaker and order preserved.
- **Note:** a standalone, user-written text entry that does not require a conversation record.

The one-record-to-one-conversation relationship is confirmed. Endpoint and table names remain open.

## Task breakdown

### 1. User accounts and access

- Define the minimum information required to create an account.
- Define sign-in, sign-out, and account recovery behavior.
- Use email and password for the first sign-in method. Define an optional email OTP flow only if a free sending allowance meets the app's needs.
- Define how a user views and updates their own account.
- Define how account deletion affects owned records and conversation entries.
- Ensure every private-data operation checks the signed-in user's ownership.

### 2. Records API

- Create a record for the signed-in user.
- Autosave an in-progress record and its finalized text entries during the AI conversation.
- Complete the record and generate its summary when the conversation ends, without treating ordinary pauses as an ending.
- Let the owner edit the summary, while keeping finalized conversation entries immutable.
- List the user's records with ordering and pagination.
- Read one record and its basic metadata.
- Update a record's editable metadata.
- Move a deleted record to a recycle bin, allow recovery, and permanently purge it after three days.

### 3. Conversation API

- Add a conversation entry to a record.
- List entries in conversation order.
- Read entries in order; finalized entries cannot be edited by the user.
- Support correction of a misheard word during live speech-to-text capture, before the entry becomes final.
- Preserve source information such as AI provider/model when available.
- Support an AI interaction activated by “Dear Diary” once the microphone is ready.
- Handle speech-to-text entries and AI responses during the conversation.
- Define how an interrupted in-progress interaction is resumed.

### 4. Notes API

- Create a standalone text note for the signed-in user.
- Support primarily manual note entry after the “Dear Diary” activation and allow an optional link to a conversation record.
- List, read, and update the user's notes.
- Move a deleted note to a recycle bin, allow recovery, and permanently purge it after three days.
- Require the signed-in account to own a note before it can be listed, read, updated, or deleted. Other accounts cannot access it.

### 5. Shared API behavior

- Decide request and response formats, validation rules, error responses, and pagination.
- Define authentication and authorization rules across all endpoints.
- Decide whether deleted data can be restored and how export will work.
- Document the API and verify the key account-to-record-to-conversation flow.

## Later API areas to define

- Social post drafts and publishing.
- Thirty-day activity and personality review.

## Open decisions before implementation

- Which account fields and sign-in method should be supported first?
- Where is the “Dear Diary” phrase detected, and how is accidental activation handled?
- How does the app distinguish a true conversation ending from a pause?
- How does the user choose between conversation recording and note creation?
- What role would an optional free-tier email OTP serve?
- Which database and Python API framework should be used on the existing server?
