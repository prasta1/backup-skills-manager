# Unsloth version-aliasing trap — diagnostic sequence

## Symptom
User ran `pip install -U unsloth` (or `==2026.8.8`) and reports "still 2026.8.5" or
"the upgrade didn't take." `import unsloth` prints a number lower than what pip claims is installed.

## Why
`unsloth/__init__.py` contains:
```python
__version__ = unsloth_zoo.__version__
```
So the package's *reported* version is the **zoo's** version, not the core's. When the
Unsloth core releases ahead of `unsloth_zoo` on PyPI, the core installs at the new number
but the import still echoes the older zoo number.

## Confirm it's NOT broken (run on the Studio host)
```bash
VENV=~/.unsloth/studio/unsloth_studio
SP="$VENV/lib/python3.13/site-packages"

# 1. What pip THINKS is installed (core)
"$VENV/bin/pip" show unsloth | grep -E "^Version"        # -> 2026.8.8

# 2. What the import reports (zoo-aliased)
"$VENV/bin/python" -c "import unsloth; print(unsloth.__version__)"   # -> 2026.8.5

# 3. Does a matching zoo exist on PyPI? (dry)
"$VENV/bin/pip" index versions unsloth_zoo               # latest = 2026.8.5

# 4. PROOF the running process is on the new core: read the dist-info the venv ships
grep -m1 "^Version:" "$SP"/unsloth-2026.8.8.dist-info/METADATA      # -> 2026.8.8
grep -m1 "^Version:" "$SP"/unsloth_zoo-2026.8.5.dist-info/METADATA  # -> 2026.8.5

# 5. Confirm the live server PID maps to this venv (not a second install)
ps -o pid,command -p 1022 | grep -o "unsloth_studio/bin/python"
```

## Resolution
- Nothing to coercively fix. Wait for the matching `unsloth_zoo==<ver>` to publish, then
  `~/.unsloth/studio/unsloth_studio/bin/pip install -U unsloth` flips the reported version.
- NEVER hand-edit `__version__` in `unsloth/__init__.py` or `_gpu_init.py` — masks the real
  zoo version and can fool future upgrade logic.
- Never `pip install -U unsloth` against system pip — it won't touch the bundled venv
  (system `pip show unsloth` → "not found" is expected for this Studio install).
- Watch the torch pin: `torch<2.12.0` (venv carries 2.10.0). An upgrade that pulls a newer
  torch can break the running server.

## Mismatch that IS real (different failure)
If `pip show unsloth` says the OLD version (e.g. 2026.8.5) AND the dist-info is old too,
then the upgrade genuinely didn't apply — check you used the **bundled venv's** pip, and
that the server's venv path is the one you upgraded.
