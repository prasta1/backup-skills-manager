# Model Memory Settings — Code Traces (2026-08-14)

Session: Unsloth Studio config review on MacBook Pro (desktop app install).

## Files traced

### 1. `model_memory_settings.py` (6680 chars)
Path: `studio/backend/utils/model_memory_settings.py`

Key constants:
- `KEEP_RESIDENT_SETTING_KEY = "model_memory_keep_resident"`
- `NO_RAM_RESERVE_SETTING_KEY = "model_memory_no_ram_reserve"`
- `DEFAULT_KEEP_RESIDENT = False`
- `DEFAULT_NO_RAM_RESERVE = False`
- `_CACHE_TTL_S = 2.0` (reads cached for 2s, write-invalidate on change)

Key functions:
- `get_keep_resident()` → reads DB, returns bool (default False)
- `get_no_ram_reserve()` → reads DB, returns bool (default False)
- `should_mlock()` → `keep_resident and not no_ram_reserve` — emits `--mlock` only when both conditions hold
- `get_model_memory_settings()` → returns `(keep_resident, no_ram_reserve)` as one coherent snapshot (generation-based cache to avoid reading a stale pair)

Critical detail: settings are read from `storage.studio_db.get_app_setting()` — a SQLite table `app_settings` with columns `(key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT)`. If a key is absent from the DB, the default (False) is applied.

### 2. `llama_server_args.py` (954 lines)
Path: `studio/backend/core/inference/llama_server_args.py`

Key constants:
- `VALID_GPU_MEMORY_MODES = frozenset({"auto", "manual"})`
- `gpu_layers = -1` means "Auto" (llama.cpp `--fit` handles sizing)
- Only `>= 0` is stored (Manual mode with a specific layer count)

### 3. `llama_cpp.py` (18,007 lines)
Path: `studio/backend/core/inference/llama_cpp.py`

Apple Silicon VRAM budget (line 5359):
- Query `mlx.core.mx.device_info()["max_recommended_working_set_size"]`
- Fallback to `psutil.virtual_memory().total` (full RAM)
- Multiply by `_APPLE_UNIFIED_MEMORY_FRACTION = 0.85`

GPU selection at load (line 11788):
- **Auto mode** (default): if model fits VRAM budget → emits `-ngl -1 --fit off` (full GPU). If not → emits `--fit on` (auto-sizes offload).
- **Manual mode** with gpu_layers >= 0: emits `--gpu-layers N --fit off`.

The `-ngl -1 --fit off` path prevents llama.cpp's default `--fit on` from second-guessing when the model provably fits.

### 4. `openai_auto_switch_settings.py` (827 lines)
Defaults: auto_switch=False, idle_seconds=0 (off), keep_kv=True.
`get_auto_unload_idle_seconds()`: gated on auto_switch being on; additionally vetted by `keep_resident` (if True, returns 0 regardless).
Env var `UNSLOTH_MODEL_IDLE_TTL` is a standalone startup default.

The residency veto is the single most misread piece of this module. Verified 2026-10-04 against the live install:
- `_residency_vetoes_unload()` at **line 174** — returns `bool(get_keep_resident())`.
- `get_auto_unload_idle_seconds()` at **line 183** — checks the veto **first**, before the stored value, and returns 0.
- `get_media_auto_unload_idle_seconds()` at **line 197** — same veto, separate stored setting, does NOT inherit the chat TTL.
- `idle_unload_is_configured()` at **line 204** — intentionally ignores the veto so saved-state discard decisions are not corrupted by it.
- `_apply_idle_floor()` at **line 61** — `<= 0` → 0, otherwise `max(MIN_AUTO_UNLOAD_IDLE_SECONDS, seconds)`. UI enforces the same floor on write; a direct sqlite write does not.

## Live state

### 2026-10-04 (Mac Studio, server reinstall) — differs from the fresh-install defaults
- `model_memory_keep_resident`: **true**
- `openai_api_auto_switch_model`: **true**
- `openai_api_auto_unload_idle_seconds`: **3600**
- `openai_api_auto_switch_overrides`: `{}`
- absent → defaults: `model_memory_no_ram_reserve` false, `openai_api_auto_download_model` false, `openai_api_auto_unload_keep_kv` true, `openai_api_auto_unload_api_only` false

**Read the code before calling these three rows self-contradictory.** `keep_resident=true` triggers `_residency_vetoes_unload()` (`openai_auto_switch_settings.py:174`), which forces the effective idle TTL to **0** regardless of the stored 3600 — so the config is coherent and needs no change. The stored 3600 is dormant and returns if residency is turned off. Reasoning from the raw rows alone produced a confidently wrong "these contradict, zero the timer" conclusion on 2026-10-04; the correction is to query the effective value or read the veto, never to compare rows.

### 2026-08-14 (MacBook Pro, desktop install) — the fresh-install default state
- model_memory_keep_resident: NOT IN DB → default False
- model_memory_no_ram_reserve: NOT IN DB → default False
- openai_api_auto_switch_model: NOT IN DB → default False
- openai_api_auto_unload_idle_seconds: NOT IN DB → default 0 (off)
- openai_api_auto_switch_overrides: `{}` (empty)

Running process: `llama-server ... --fit off -ngl -1` on bge-small-en (110MB) — correct for a small model in auto mode.

User setup: MacBook Pro M5, 64GB RAM. Qwen3.6-27B Q4_K_M = 14GB file. Apple VRAM budget ~54GB → fits → `-ngl -1 --fit off`. llama.cpp 10360.