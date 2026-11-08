# Himalaya Configuration

Configuration file at `~/.config/himalaya/config.toml`.

## Gmail Setup

1. Generate an App Password in Google Account settings
2. Configure with the template: `templates/gmail-configuration.toml`
3. Alias Gmail's non-standard folders ([Gmail]/Sent Mail -> Sent, etc.)

Folder aliases use `folder.aliases.X` (plural) syntax in v1.2.0+.

## IMAP/SMTP Authentication

Himalaya supports both IMAP and SMTP authentication. For Gmail, use App Passwords.

## Commands

- `himalaya envelope list` — list messages
- `himalaya message read` — read message
- `himalaya template send` — pipe stdin for non-interactive sending

**Full reference:** `references/himalaya-gmail-setup.md` (absorbed from `himalaya-gmail-setup`)