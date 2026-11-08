---
name: credential-vault-refresh
description: "Refresh this machine's Hermes credentials into the shared Bitwarden item, and verify an encrypted backup can actually be restored. Covers secrets-to-bitwarden.sh, the machine-distinct attachment naming rule, the openssl-cms backup key pair, and the bw CLI gotchas."
---

# Credential Vault Refresh

`~/.hermes/.env`, `config.yaml` and `auth.json` hold live credentials and are excluded from every
git backup by design. Their off-machine copy lives as **attachments on one shared Bitwarden item**,
and a separate encrypted bundle (`secrets.tar.gz.cms`) rides along in the git backup.

## When to use this skill

- After rotating any API key, so the vault copy stops drifting from reality.
- When asked whether a backup is actually restorable (as opposed to merely present).
- When adding a machine to the backup scheme.
- When `secrets.tar.gz.cms` or `backup-cert.pem` needs explaining.

## Refreshing the vault

```bash
export BW_SESSION=$(bw unlock --raw)     # the script never sees the master password
~/.hermes/scripts/secrets-to-bitwarden.sh
```

`DRY_RUN=1` prints the plan and touches nothing (works without a session). `BW_ITEM_ID` overrides
the target item; `BW_BIN` overrides the `bw` path.

The script reads `~/.hermes/scripts/secrets-files.txt` (`source|vault-attachment-name` per line),
uploads each file under its mapped name, confirms the upload landed, and only then deletes the
superseded attachment. It aborts without deleting if the upload does not appear. Plaintext transits
a temp file (an attachment's name comes from the file's basename) and is `rm -P` shredded on every
exit path.

## RULE: attachment names must be machine-distinct

All machines share **one** Bitwarden item, so generic names make one machine silently overwrite
another's credentials — discovered only during a restore, i.e. the worst possible moment.

| Machine | Vault names |
| -- | -- |
| Mac Studio | `hermes.env`, `hermes-config.yaml`, `hermes-auth.json` |
| MacBook Pro | `macbook-hermes.env`, `macbook-hermes-config.yaml`, `macbook-hermes-auth.json` |

Never copy one machine's `secrets-files.txt` to another without re-prefixing the names.

## The encrypted bundle and its key pair

`hermes-git-backup.sh` tars the same three files and encrypts them with
`openssl cms -encrypt` to `~/.hermes/backup-cert.pem`. **Encrypting needs only the certificate**, so
each machine can write its own backup but cannot read it back — that is the property that makes an
unattended job safe. The private keys live only in Bitwarden:

| Key | Cert subject | Cert modulus sha256 (first 16) |
| -- | -- | -- |
| `studio-backup-key.pem` | `CN=hermes-studio-backup` | `c717f5321e3b8ba8` |
| `macbook-backup-key.pem` | `CN=hermes-macbook-backup` | `835ce692bd8b243a` |

## Verifying a restore actually works

A present backup is not a proven backup. To prove one end to end:

```bash
export BW_SESSION=$(bw unlock --raw)
export I=<bitwarden item id>
cd /tmp
bw get attachment macbook --itemid $I --output v.pem       # or 'studio'
openssl rsa -in v.pem -noout -modulus | shasum -a 256      # compare to the table above
openssl cms -decrypt -inform DER -in ~/.hermes/secrets.tar.gz.cms -inkey v.pem | tar -tz
rm -P v.pem
```

The decisive check is content, not listing: extract one file and compare hashes with the live one.

```bash
openssl cms -decrypt -inform DER -in ~/.hermes/secrets.tar.gz.cms -inkey v.pem \
  | tar -xzO .hermes/.env | shasum -a 256
shasum -a 256 ~/.hermes/.env
```

Matching hashes mean the key from the vault opens the bundle from the git remote and reproduces the
real file. Anything less is an assumption.

## bw CLI gotchas (v2026.9.0)

- **Attachments cannot be renamed.** The name comes from the uploaded file's basename, so rename the
  file *before* upload. To fix a bad name: upload the correctly-named copy, then
  `bw delete attachment <attachmentid> --itemid <itemid>`.
- `bw get attachment <name-or-search> --itemid <id> --output <path>` — a bare filename in `--output`
  is written **relative to the shell's cwd**, which is easy to lose track of. A search fragment
  (`macbook`) works in place of the full name.
- **Stored attachment sizes are ~57 bytes larger than plaintext** (IV+HMAC). Two different keys both
  showing 3,329 bytes is expected, not a duplicate upload.
- Unlock inline as `BW_SESSION=$(bw unlock --raw) <cmd>` so the token is never echoed.
- **`bw` is not on the non-login ssh PATH** on either Mac (`/opt/homebrew/bin` is absent). Scripts
  must resolve it explicitly; `command -v bw` fails over ssh even though bw is installed.
- An error of `too many arguments` or `missing required argument 'id'` almost always means a shell
  variable was empty: an empty `--itemid` value makes the flag swallow the next flag.

## Traps

- **Exported shell variables are easily lost between terminal tabs**, and long pasted commands get
  broken into separate lines around 60-80 characters — which silently drops a `cp` destination or a
  `--itemid` argument. Keep pasted commands short or set variables first.
- `~/.hermes/config.yaml` is gitignored because it embeds live `api_key` values; only
  `snapshot/config.redacted.yaml` is tracked. Never print `config.yaml` wholesale — reading it to
  screen has leaked a key before. Report a key as `prefix...suffix` plus a sha256 fingerprint.
- `*.bak.<timestamp>` files in `~/.hermes` get pruned by the disk-cleanup plugin. Use the
  `*.bak-<timestamp>` hyphen form for backups you intend to keep.
