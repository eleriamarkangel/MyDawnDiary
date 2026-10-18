# Next checkpoint

## Account and authentication

- [ ] Fix the live verification form regression: on a first sign-in with an unverified account, the password can still appear in the verification-code field. This was reported after the `6fe26e9` frontend fix. Reproduce the sign-in-to-verification transition and check browser autofill as well as React input reuse. Verify that the code field is empty and that a password is never displayed as plain text, including after refresh.
- [ ] Add **Forgot password** with an email reset flow, short-lived single-use credentials, rate limiting, and responses that do not reveal whether an address has an account.
- [ ] Add **Change password** in Account Settings using the existing backend endpoint. Require the current password and invalidate existing sessions as appropriate.
- [ ] Add self-service **Delete account**, with clear confirmation and removal of the account's private data so the email address can be used again. Ensure an unverified registration does not permanently occupy one of the user's limited email addresses.

These are deferred to the next checkpoint; no production account deletion or credential changes are part of this note.
