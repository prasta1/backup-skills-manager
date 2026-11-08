# Himalaya Gmail Configuration Reference

This file documents the specific configuration needed for Gmail with Himalaya, including the required folder aliases that prevent duplicate emails.

## Complete Gmail Configuration

```toml
[accounts.gmail]
email = "ruster.patrick@gmail.com"
display-name = "Patrick A Ruster"
default = true

# IMAP backend for reading emails
backend.type = "imap"
backend.host = "imap.gmail.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "ruster.patrick@gmail.com"
backend.auth.type = "password"
backend.auth.cmd = "pass show google/app-password"

# SMTP backend for sending emails
message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "ruster.patrick@gmail.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "pass show google/app-password"

# Gmail folder mapping. Without these, save-to-Sent fails after
# SMTP delivery succeeds (Gmail's Sent folder is `[Gmail]/Sent Mail`,
# not `Sent`), and `himalaya message send` exits non-zero. Any
# caller (agent, script, user) that retries on that error
# code will re-run SMTP — duplicate emails to recipients.
# Always include this block for Gmail.
folder.aliases.inbox = "INBOX"
folder.aliases.sent = "[Gmail]/Sent Mail"
folder.aliases.drafts = "[Gmail]/Drafts"
folder.aliases.trash = "[Gmail]/Trash"
```

## Important Notes

### Folder Aliases Required
Himalaya v1.2.0+ requires folder aliases for Gmail because:
- Gmail's "Sent" folder is actually named `[Gmail]/Sent Mail`
- Without aliases, `himalaya message send` exits non-zero after SMTP succeeds
- This causes duplicate email delivery when retry logic is applied

### App Password Setup
If 2FA is enabled on the Gmail account:
1. Go to Google Account settings
2. Security → 2-Step Verification → App passwords  
3. Create a new app password for "Mail"
4. Store it with `pass insert google/app-password`

### Password Storage Options
- **Pass**: `pass show google/app-password`
- **Keychain**: `security find-generic-password -a ruster.patrick@gmail.com -s gmail-imap -w`