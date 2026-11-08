# Duplicate "default" Profiles in Hermes Web UI

## Symptom

Profile selector shows two entries named `default`, even though there is only one `~/.hermes/profiles/default` directory on disk.

## Root cause family

Backend list construction in `~/projects/hermes-webui/api/profiles.py` separately emits:
- a synthetic base-home row labeled `default`, and
- an enumerated `profiles/default` row.

Result: two visually identical entries.

## Diagnostic steps

1. Confirm on-disk duplication does not exist:
   ```bash
   find ~/.hermes -maxdepth 2 -type d -name 'default' | sort
   ```
2. Inspect API rows in `api/profiles.py` rather than the filesystem alone.
3. Trace `list_profiles_api` and `_build_profile_rows_fast` for redundant base-home emission.

## Fix bounds

- Fix belongs in `_build_profile_rows_fast` or `list_profiles_api`: collapse rows when both `home == default_home` and `name == 'default'`.
- Do not create symlinks, rename directories, or delete candidate directories until the backend cause is confirmed.

## Test verification

After fixing the backend dedupe, refresh `/api/profiles` in browser dev tools and confirm the JSON array contains at most one entry with `"name": "default"` and `"is_default": true`.
