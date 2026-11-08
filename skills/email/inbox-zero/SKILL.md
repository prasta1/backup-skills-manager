---
name: inbox-zero
description: "Use when clearing the Gmail inbox by sender. Builds a local widget that bulk-deletes via himalaya."
version: 1.0.0
author: Ionga, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [email, gmail, inbox, triage, widget, delete, himalaya]
    related_skills: [email-triage, himalaya]
---

# Inbox Zero

Build a sender-grouped, in-browser widget of the Gmail inbox that lets Patrick bulk-delete
emails directly in the interface (double-click to confirm), to drive the inbox to zero.
The widget runs on the MacBook; a small delete server on the MacBook performs the actual
himalaya deletes against Gmail.

## When to Use

- "Help me get to inbox zero" / "bulk evaluate my inbox"
- "I want to delete a bunch of emails by sender"
- "Build me the inbox widget again"

Don't use for: single-email triage or drafting replies (use `email-triage`), or reading one
known message (use `himalaya`).

## Prerequisites

- Himalaya on the **MacBook** with the Gmail account (account name `personal`,
  `ruster.patrick@gmail.com`, password via `pass show google/app-password`).
- The MacBook is reachable from the Studio via `ssh macbook`.
- The Studio has the Gmail app password in `~/.hermes/.env` as `GMAIL_APP_PASSWORD`
  (used only to enumerate the inbox from the Studio; deletes run on the MacBook).

## How to Run

```bash
# 0. One token per session, shared by the widget AND the server. The builder mints its
#    own if you omit this, and then every action the widget sends is a 401.
export TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")

# 1. Enumerate the inbox from the Studio and build the widget
INBOX_DELETE_TOKEN="$TOKEN" python3 ~/.hermes/skills/email/inbox-zero/scripts/build_inbox_widget.py \
  --out /tmp/inbox-sender-widget.html

# 2. Copy widget + delete server to the MacBook, and lock the widget down
scp /tmp/inbox-sender-widget.html macbook:/tmp/inbox-sender-widget.html
scp ~/.hermes/skills/email/inbox-zero/scripts/inbox-delete-server.py macbook:/tmp/
ssh macbook "chmod 600 /tmp/inbox-sender-widget.html"   # the file embeds the token

# 3. (Re)start the delete server on the MacBook. Binds 127.0.0.1 by default.
ssh macbook "pkill -f inbox-delete-server.py; sleep 1; \
  nohup python3 /tmp/inbox-delete-server.py --port 8644 --token '$TOKEN' \
  > /tmp/inbox-delete-server.log 2>&1 &"

# 4. Open the widget. It renders on the MacBook's display, not the Studio's.
ssh macbook "open /tmp/inbox-sender-widget.html"

# 5. Teardown
ssh macbook "pkill -f inbox-delete-server.py; rm -f /tmp/inbox-sender-widget.html"
rm -f /tmp/inbox-sender-widget.html /tmp/inbox-token.txt
```

## Procedure

1. **Enumerate the inbox** from the Studio: `himalaya envelope list -a gmail -m INBOX -p <n> -s 250`
   (the Studio account is `gmail`; the MacBook's is `personal`). Parse the `│`/`┆` table.
   `-p/--page` exists — page until a page comes back short; never assume one page is the
   whole mailbox. Cross-check the total against IMAP `SELECT INBOX` (EXISTS) when it matters.
2. **Build the widget** with `build_inbox_widget.py`. It embeds every email (id, subject,
   date, unread) grouped by sender: a pill per sender at or above `PILL_MIN` emails, plus a
   single `All other senders` bucket pill holding every lower-count sender, sub-headed per
   sender. Every email must be reachable from the UI — see the reachability pitfall below.
3. **Copy to the MacBook** and start the delete server there (localhost — the Studio's
   application firewall silently drops inbound to a new Python process, so the server
   must run on the MacBook where the widget lives).
4. **Open the widget** on the MacBook. The widget POSTs to `http://127.0.0.1:8644/` with a
   bearer token; the server runs `himalaya message delete -a personal -m INBOX <ids>`.
5. **Act:** expand a sender (or **All other senders**), uncheck anything to keep, then
   **Delete**, **Archive** or **Mark as read**. The first click arms the button for 3
   seconds, the second fires. Delete moves mail to trash (recoverable ~30 days); Archive
   moves it to `[Gmail]/All Mail`, which drops the Inbox label.
   The widget opens with **All other senders** already expanded and *nothing selected*, so
   an empty pane never reads as broken. A pill is a select-all toggle whose open state
   follows the selection: clicking an unselected pill selects that whole sender and expands
   it; clicking a fully-selected one clears and collapses it. Never make the default-open
   state reuse the pill click, or the widget arms a hundred-email delete on load.
   **Count / Name / Date** reorder the pills, the sender sections and the bucket sub-groups
   together, each with its own default direction.

## Pitfalls

- **The Studio's application firewall drops inbound to a new Python process** even when the
  binary is "permitted" — the TCP handshake completes but the request never reaches the
  handler. Run the delete server on the MacBook (localhost), not the Studio.
- **Never treat one himalaya page as the whole mailbox.** `envelope list` paginates via
  `-p`; a page size that exceeds today's count silently truncates at tomorrow's. Page until
  short, and treat IMAP `SELECT INBOX` (EXISTS) as ground truth for the total. The Gmail
  browser count counts All Mail / categories, not INBOX, so it will not match.
- **A per-sender pill threshold alone makes inbox zero unreachable.** Sections ship
  `display:none`, and `togglePill()` — reachable only from a pill — is the sole code path
  that sets `display:block`. Give every sub-threshold sender a route into the bucket pill,
  or most of the inbox sits loaded but unclickable, the same pills reappear every run, and
  the count never reaches zero.
- **The MacBook himalaya account is `personal`; the Studio's is `gmail`.** Pass `--account`
  to the server rather than editing the file.
- **himalaya exits 0 when it acted on nothing.** `message delete` prints "Successfully moved
  0 message(s)" and `move` prints "No message moved: no id matched", both with exit code 0.
  Never report the number of ids you sent as the number affected: parse the count himalaya
  prints, and treat a printed 0 as a failure so a stale widget cannot fake success.
- **The two counts are worded differently.** Delete says `Successfully moved N message(s) to
  the trash`; archive says `N message successfully moved`. A regex tuned to only the first
  silently leaves archive on the unconfirmed path, so match `(\d+)\s+message` and cover both.
- **`flag add` prints no count**, only "Successfully added flags: seen". Its result cannot be
  verified from output, so the server marks it `confirmed: false` and the widget says the
  number is what was requested, not what was confirmed.
- **himalaya's FLAGS column renders `*` for unseen and blank for seen.** It is not a list of
  IMAP flags and the two other markers (`!`, `R`) are not unread. `unread` is `"*" in flags`;
  treating a blank column as unread inverts the signal and badges the read mail.
- **Escape sender and subject before interpolating into the widget.** Both are attacker
  controlled and the page holds the bearer token for a destructive endpoint, so unescaped
  markup is script execution against it. A plain `"` in a display name also breaks
  `data-sender="..."` and makes that sender permanently unopenable.
- **A stale widget silently desyncs from the mailbox.** Ids are a snapshot; anything deleted
  elsewhere no longer matches. The server reports `requested` and `deleted` separately and
  the widget refuses to remove rows when they differ. Rebuild after a partial result.
- **The delete server is a background process** — it does not survive a MacBook reboot.
  Re-launch it (or wire a LaunchAgent) before a session.
- **The widget embeds the auth token** in the HTML, so the builder chmods it `600`. It lands
  in `/tmp` on both machines; delete both copies on teardown, commit neither.
- **The server binds `127.0.0.1` by default.** It previously bound `0.0.0.0`, which put a
  token-gated delete endpoint on the LAN for no reason. Don't widen it unless the widget
  genuinely runs on another host.
- **Double-click to confirm is intentional** — a single click arms the button (3s window),
  a second fires. This prevents accidental deletes.

## Verification

- `ssh macbook "lsof -iTCP:8644 -sTCP:LISTEN -P"` shows the server listening.
- `curl -s -X POST http://127.0.0.1:8644/ -H 'Authorization: Bearer $TOKEN' -d '{"ids":[]}'`
  returns `{"ok": true, "deleted": 0, "detail": "no ids"}`.
- After a delete, the email is gone from INBOX and present in `[Gmail]/Trash`.
- Reachability (check on every build): each `data-id` appears exactly once in the widget,
  and every sender below `PILL_MIN` sits inside the `All other senders` bucket section.
- Counts (check on every build): the builder prints its email and unread totals. The email
  total must equal IMAP `SELECT INBOX` (EXISTS) and the unread total must equal `UID SEARCH
  UNSEEN`. Measure both against the same snapshot or the numbers race live deletions.
- Stale-id honesty: `-d '{"ids":[999999999],"action":"delete"}'` must return `"ok": false`
  with "no ids matched", never `"ok": true` with `"deleted": 1`.
- Archive (verified working): after archiving, the UID is absent from INBOX, present in
  `[Gmail]/All Mail` (matched by Message-ID — UIDs are per-mailbox), and absent from
  `[Gmail]/Trash`. A user label such as `\Important` correctly survives; only `\Inbox` drops.
  Note `[Gmail]/All Mail` contains a space, and imaplib needs it quoted: `select('"[Gmail]/All Mail"')`.
