# QC tooling: how to invoke it without tripping the archive and env traps

Three traps on this stack. Any one of them makes a QC script look broken when the
tooling is fine, and two of them are silent: the script dies before reading a
frame, or it runs and grades the wrong thing.

## 1. `limb_sweep.py` resolves its imports only with `archive/scripts` on the path

It imports `limb_rules` and `qc_bakeoff`, and both live in `archive/scripts/`
because the session-script archive swept them in along with the throwaway batch
files. Archive by role, not by filename: `qc_bakeoff.py` is both a session
script and a library, and `limb_sweep.py` reuses its `call(model, image)` helper.

- Put BOTH the Ionga root and `archive/scripts` on `sys.path` (the script does
  this now). Do not copy the modules back to the root: one copy, one place to
  fix, or the next archive pass breaks it again.
- It has no `--help` and no `__main__` guard. Running it starts the sweep
  immediately, and it grades the ROOT flat keepers (`^\d{2}_\d{4}_` filenames),
  not a run directory. Use it to re-grade filed keepers.

## 2. `qc_pipeline.py` builds its prompts out of an archived session script

Two helpers read `archive/scripts/batch_session9b_yolo.py` and AST-parse out the
`NEG` and `POSES` constants (path now resolved through an `ARCH` constant).
The path is fixed; the CONTENT is still stale, so it would grade a brand-new
batch against session-9b's prompts and poses.

- Repoint those two helpers at the current batch script before trusting
  `qc_pipeline.py` on a new run.
- `qc_pointer.py <run_dir>` has no such dependency and is the default per-run
  pointer. Prefer it.

## 3. A leaked `PYTHONPATH` shadows Pillow across interpreters

If the shell carries `PYTHONPATH=<venv>/lib/python3.14/site-packages`, then
`from PIL import Image` fails on every other interpreter with
`ImportError: cannot import name '_imaging'`: that site-packages wins on the
path, but its compiled `_imaging.cpython-314-*.so` cannot load under Homebrew
3.15 or system 3.9. Nothing is corrupt and the venv's own Pillow is intact.

- Run QC scripts as `env -u PYTHONPATH <python> <script>`.
- Never diagnose "Pillow is broken" before checking `PYTHONPATH`. Check the env
  var first, then the interpreter.
- `batch_render.py` is stdlib-only, so renders are unaffected by this trap. It
  hits the PIL-based QC tools only, which is why a whole batch can render
  cleanly and every QC script on the same shell can still fail.

## Verified invocations

```
# per-run pointer, location hints only -> <run_dir>/qc/pointer.jsonl
cd <run_dir>
env -u PYTHONPATH /opt/homebrew/bin/python3 \
  ~/.hermes/outputs/Ionga/qc_pointer.py <run_dir> ms-qwen3-vl-8b

# keeper re-grade, executes on invocation, no --help
env -u PYTHONPATH /opt/homebrew/bin/python3 \
  ~/.hermes/outputs/Ionga/limb_sweep.py ms-qwen3-vl-8b
```

Interpreter: `/opt/homebrew/bin/python3` with `PYTHONPATH` stripped, or the
venv's own interpreter (its Pillow is intact). The system 3.9 python works too,
drawing Pillow from the user site-packages.
