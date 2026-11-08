# Provider Organization in Hermes Codebase

## How Providers Are Structured

Hermes organizes model providers at multiple levels, without explicit "category" names for providers themselves.

### 1. Provider Groups (Display-Level Folding)

**File:** `hermes_cli/models.py` (lines 1101-1119)

Groups fold related slugs into one top-level row in interactive pickers. This is purely a display affordance — every member slug remains individually addressable.

```python
PROVIDER_GROUPS: dict[str, tuple[str, str, list[str]]] = {
    "kimi":     ("Kimi / Moonshot", "Coding Plan, Moonshot global & China endpoints", ["kimi-coding", "kimi-coding-cn"]),
    "minimax":  ("MiniMax",         "Global, OAuth Coding Plan & China endpoints",      ["minimax", "minimax-oauth", "minimax-cn"]),
    "xai":      ("xAI Grok",        "Direct API or SuperGrok / Premium+ OAuth",         ["xai", "xai-oauth"]),
    "google":   ("Google Gemini",   "Google AI Studio (API key)",                       ["gemini"]),
    "openai":   ("OpenAI",          "Codex CLI or direct OpenAI API",                 ["openai-codex", "openai-api"]),
    ...
}
```

Structure: `group_id -> (display_label, group_description, [member_slug, ...])`

### 2. Canonical Provider Registry

**File:** `hermes_cli/models.py` (lines 1012-1053)

Single source of truth for provider identity. Used by all picker surfaces.

```python
class ProviderEntry(NamedTuple):
    slug: str      # internal provider ID (used in config.yaml, --provider flag)
    label: str     # short display name
    tui_desc: str  # longer description for interactive picker

CANONICAL_PROVIDERS: list[ProviderEntry] = [
    ProviderEntry("nous",           "Nous Portal",              "Nous Portal (300+ models with bundled tool use)"),
    ProviderEntry("openrouter",     "OpenRouter",               "OpenRouter (Pay-per-use API aggregator)"),
    ...
]
```

### 3. Provider Profiles (Rich Metadata)

**File:** `providers/base.py`

Provider plugins register `ProviderProfile` instances with optional metadata:

```python
@dataclass
class ProviderProfile:
    # Identity
    name: str
    aliases: tuple = ()

    # Human-readable metadata (display only)
    display_name: str = ""   # e.g., "Z.AI (GLM)" — shown in picker
    description: str = ""    # e.g., "Z.AI / GLM — Zhipu AI models" — picker subtitle
    signup_url: str = ""     # shown during setup

    # Auth & endpoints
    env_vars: tuple = ()
    base_url: str = ""
    auth_type: str = "api_key"

    # Model catalog
    fallback_models: tuple = ()  # used when live fetch fails
```

Located in:
- Bundled: `plugins/model-providers/<name>/__init__.py`
- User: `$HERMES_HOME/plugins/model-providers/<name>/__init__.py`

### 4. Model-Level Families (NOT Provider Categories)

**File:** `agent/models_dev.py`

The `family` field categorizes models, not providers:

```python
model_family = entry.get("family", "")  # e.g., "claude-opus", "qwen3"
```

This comes from the models.dev registry and is used for capability detection and timeout heuristics.

### 5. Provider-to-models.dev Mapping

**File:** `agent/models_dev.py` (lines 142-180)

Maps Hermes provider slugs to models.dev IDs for capability lookups:

```python
PROVIDER_TO_MODELS_DEV: Dict[str, str] = {
    "openrouter": "openrouter",
    "anthropic": "anthropic",
    "openai-codex": "openai",
    "qwen-oauth": "alibaba",
    "xai-oauth": "xai",  # OAuth uses same catalog as direct API
    ...
}
```

## Key Files for Provider Configuration

| File | Purpose |
|------|---------|
| `hermes_cli/models.py` | Canonical provider list, groups, aliases |
| `providers/base.py` | ProviderProfile dataclass definition |
| `providers/__init__.py` | Plugin discovery and registration |
| `agent/models_dev.py` | Capability metadata from models.dev API |
| `plugins/model-providers/` | Bundled provider plugins |
| `scripts/build_model_catalog.py` | Generates JSON manifest for runtime fetch |

## No Provider Categories

Unlike skills (which have categories), providers do NOT have a `category` field. Organization happens through:

1. **Groups** - display folding in pickers
2. **Aliases** - alternative names mapping to canonical slug
3. **Provider ID mapping** - multiple auth variants (global/China/OAuth) map to same models.dev catalog

To add a new provider category, use `PROVIDER_GROUPS` to fold related slugs together in the UI.