#!/usr/bin/env python3
"""
image-gen interactive picker — model menu + settings dialog.

Reads config.yaml (same directory by default), presents a numbered menu of
models grouped by machine/backend, collects the prompt (+ optional negative),
then runs a settings dialog with sensible defaults and validation. Emits a
request object matching request-schema.json (same directory) to stdout.

Contract (config.yaml header):
  - Only models with availability == verified are selectable. Unverified
    models are listed but greyed out / not offered.
  - Promptable settings come from the model's `settings` map. Backend-
    unsupported keys are never prompted (the map already omits them).
  - Cross-field rules enforced: ComfyUI Qwen-Image-2.1-int8 width == height
    (single resolution param); Unsloth area width*height <= 4300800.
  - Emitted settings follow the schema/examples: width, height, steps, seed
    always; cfg_scale only when the model pins it (ComfyUI); n for Unsloth.
    sampler/scheduler/denoise/strength are omitted — the executor applies
    the model's config defaults.

Usage:
  python3 picker.py                      # interactive (menu + dialogs)
  python3 picker.py --model <id> --prompt "..." [--defaults] [-o req.json]
  python3 picker.py --json-only --model <id> --prompt "..."
  python3 picker.py --help

Scripted mode: with --model + --prompt + --defaults the run is fully
non-interactive (negative prompt defaults to None; settings all defaults).
Library mode: import picker; picker.run(picker.parse_args([...])) returns the
request dict directly.

Interactive tips:
  - At any settings prompt: Enter = accept the default; 'd' = accept ALL
    remaining defaults; Ctrl-C aborts cleanly (no partial JSON emitted).
  - Menu: pick by number, 'q' to quit.
"""

import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("picker.py requires PyYAML (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

SCHEMA_VERSION = 1

# ComfyUI-only settings whose default is pinned and applied by the executor.
EXECUTOR_DEFAULTS = ("sampler", "scheduler", "denoise", "strength")


class PickError(Exception):
    """User-level abort (quit, EOF, interrupt). Exit codes below."""


def err_print(*a, **kw):
    """All interactive text goes to stderr so stdout stays pure JSON."""
    print(*a, file=sys.stderr, **kw)


def ask(prompt, default="", allow_d=False):
    """Read one line from stdin; prompt text goes to stderr. Returns str.

    'd' -> accept-all-defaults shortcut; callers treat lower-cased 'q' as
    quit where it makes sense.
    """
    suffix = ""
    if default != "":
        suffix = f" [default: {default}]"
    hint = " ('d' = all defaults)"
    if allow_d:
        suffix += hint
    err_print(f"{prompt}{suffix}: ", end="")
    try:
        line = input()
    except EOFError as e:
        raise PickError("input ended (EOF) — aborting") from e
    return line.strip()


def parse_int(text, label):
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{label} must be an integer, got {text!r}")


def parse_float(text, label):
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{label} must be a number, got {text!r}")


def load_config(path):
    if not os.path.isfile(path):
        raise PickError(f"config not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict) or "machines" not in cfg or "models" not in cfg:
        raise PickError(f"config {path} is missing 'machines'/'models'")
    if "defaults" not in cfg or "output_dir" not in cfg.get("defaults", {}):
        raise PickError(f"config {path} is missing defaults.output_dir")
    return cfg


def build_model_index(cfg):
    """Return ordered [(machine, backend, model), ...] with live/info flags."""
    machines = cfg.get("machines", {})
    models = cfg.get("models", [])
    index = []
    for m in models:
        mid = m.get("id", "")
        machine = machines.get(m.get("machine"))
        backend = (machine or {}).get("backends", {}).get(m.get("backend"))
        if machine is None or backend is None:
            err_print(f"warning: model {mid} references unknown machine/backend; skipping")
            continue
        index.append((machine, backend, m))
    return index


def print_menu(index):
    """Numbered menu grouped by machine -> backend. Returns {num: (item)}."""
    err_print("")
    err_print("Image generation — pick a model")
    err_print("=" * 58)
    mapping = {}
    num = 1

    # Group machines in config order
    seen_machines = []
    for machine, backend, model in index:
        key = (machine.get("id"), machine.get("name"))
        if key not in seen_machines:
            seen_machines.append(key)

    for mac_id, mac_name in seen_machines:
        err_print(f"\n[{mac_name}]")
        mac_models = [it for it in index if it[0].get("id") == mac_id]
        seen_backends = []
        for machine, backend, model in mac_models:
            bk = backend.get("id")
            if bk not in seen_backends:
                seen_backends.append(bk)
        for bk in seen_backends:
            err_print(f"  {bk}:")
            for machine, backend, model in mac_models:
                if backend.get("id") != bk:
                    continue
                avail = model.get("availability")
                if avail != "verified":
                    err_print(f"    - {model.get('display')}  (unverified — not offered)")
                    continue
                err_print(f"    {num}) {model.get('display')}  [{model.get('id')}]")
                mapping[num] = (machine, backend, model)
                num += 1
    err_print("")
    return mapping


def pick_model(mapping):
    """Let the user pick a model by number; 'q' quits."""
    while True:
        raw = ask("Pick model number", allow_d=False)
        if raw.lower() == "q":
            raise PickError("quit")
        try:
            choice = int(raw)
        except ValueError:
            err_print(f"  not a number: {raw!r}")
            continue
        if choice in mapping:
            return mapping[choice]
        err_print(f"  {choice} is not an offered model (1-{len(mapping)})")


def collect_prompt():
    """Prompt text is required (schema minLength 1)."""
    while True:
        text = ask("Prompt", default="")
        if text:
            if len(text) > 4000:
                err_print("  prompt too long (max 4000 chars)")
                continue
            return text
        err_print("  prompt is required")


def collect_negative():
    text = ask("Negative prompt (Enter for none)", default="")
    if not text:
        return None
    if len(text) > 4000:
        err_print("  negative prompt too long (max 4000 chars); truncated")
        text = text[:4000]
    return text


def settings_spec(model):
    """Return ordered list of (key, spec) promptable for this model.

    - skips keys the backend doesn't control (absent from the settings map)
    - skips keys the executor applies from config defaults (sampler/scheduler/
      denoise/strength)
    - cfg_scale is emitted but only when the model pins it (ComfyUI); pinned
      -> no interactive prompt, value included silently.
    """
    out = []
    for key, spec in (model.get("settings") or {}).items():
        if key in EXECUTOR_DEFAULTS:
            continue
        out.append((key, spec))
    return out


def validate_dim(value, spec, label, model):
    """Single-dimension bounds incl. multiple_of; cross-field checks later."""
    vmin = spec.get("min")
    vmax = spec.get("max")
    if vmin is not None and value < vmin:
        raise ValueError(f"{label} too small (min {vmin})")
    if vmax is not None and value > vmax:
        raise ValueError(f"{label} too large (max {vmax})")
    mult = spec.get("multiple_of")
    if mult and value % mult != 0:
        raise ValueError(f"{label} must be a multiple of {mult} (got {value})")
    return value


def check_cross_field(width, height, model, backend):
    """Model/backend-specific relation between dimensions."""
    bids = []
    if isinstance(backend, dict):
        bids.append(backend.get("id"))
    mid = model.get("id", "")
    # ComfyUI Qwen-Image-2.1-int8: single resolution param -> width == height
    if "comfyui" in bids and "qwen-image-2.1-int8" in mid:
        if width != height:
            raise ValueError(
                f"Qwen-Image-2.1-int8 uses a single resolution param: "
                f"width must equal height (got {width}x{height})"
            )
    # Unsloth: area rule from server_limits / area_rule
    limits = model.get("server_limits") or {}
    max_px = limits.get("max_output_pixels")
    if max_px and width * height > max_px:
        raise ValueError(
            f"Unsloth area limit exceeded: {width}x{height}={width*height} > {max_px}"
        )
    max_side = limits.get("max_output_side")
    if max_side:
        for v, label in ((width, "width"), (height, "height")):
            if v > max_side:
                raise ValueError(f"{label} exceeds Unsloth side limit {max_side}")
    return True


def prompt_int(key, spec, model, backend, current):
    """One integer/float setting with default + bounds; value or 'd'/'q'."""
    default = current if current is not None else spec.get("default")
    label = key
    note = spec.get("note", "")

    def fmt(v):
        return str(v) if v is not None else "random"

    while True:
        raw = ask(f"{key} (min {spec.get('min')}, max {spec.get('max')})"
                  f"{' , multiple of ' + str(spec.get('multiple_of')) if spec.get('multiple_of') else ''}"
                  f"{' — ' + note if note else ''}",
                  default=fmt(default))
        if raw.lower() == "d":
            return "d"
        if raw.lower() == "q":
            raise PickError("quit")
        if raw == "":
            return default  # accept default (may be None for seed)
        try:
            if isinstance(spec.get("default"), float) or isinstance(spec.get("min"), float):
                value = parse_float(raw, label)
            else:
                value = parse_int(raw, label)
        except ValueError as e:
            err_print(f"  {e}")
            continue
        try:
            vmin = spec.get("min")
            vmax = spec.get("max")
            if vmin is not None and value < vmin:
                raise ValueError(f"{label} too small (min {vmin})")
            if vmax is not None and value > vmax:
                raise ValueError(f"{label} too large (max {vmax})")
            mult = spec.get("multiple_of")
            if mult and value % mult != 0:
                raise ValueError(f"{label} must be a multiple of {mult} (got {value})")
            return value
        except ValueError as e:
            err_print(f"  {e}")


def prompt_settings(model, backend, defaults_only=False):
    """Run the settings dialog; returns settings dict (schema-aligned).

    'd' shortcut at any prompt accepts all remaining defaults.
    Cross-field rules (width==height for qwen int8, Unsloth area) validated.
    """
    settings = {}
    specs = settings_spec(model)
    dims = {}
    use_defaults = defaults_only

    for key, spec in specs:
        # cfg_scale pinned (min==max): include silently, no prompt.
        if key in ("cfg_scale",):
            vmin, vmax = spec.get("min"), spec.get("max")
            if vmin is not None and vmax is not None and vmin == vmax:
                settings[key] = vmin
                continue
        if use_defaults:
            val = spec.get("default")
            if key == "seed" and val is None:
                settings[key] = None
            elif val is not None:
                settings[key] = val
            continue

        if key in ("width", "height"):
            # seed-like default: None not allowed for dims; config default always set
            default = spec.get("default")
            while True:
                raw = ask(f"{key} (min {spec.get('min')}, max {spec.get('max')}"
                          f"{', multiple of ' + str(spec.get('multiple_of')) if spec.get('multiple_of') else ''})",
                          default=default)
                if raw.lower() == "d":
                    use_defaults = True
                    val = default
                elif raw.lower() == "q":
                    raise PickError("quit")
                elif raw == "":
                    val = default
                else:
                    try:
                        val = parse_int(raw, key)
                    except ValueError as e:
                        err_print(f"  {e}")
                        continue
                try:
                    validate_dim(val, spec, key, model)
                    # cross-field after both dims known
                    dims[key] = val
                    if len(dims) == 2:
                        check_cross_field(dims["width"], dims["height"], model, backend)
                    settings[key] = val
                    break
                except ValueError as e:
                    err_print(f"  {e}")
            continue

        # steps, seed, n
        res = prompt_int(key, spec, model, backend, settings.get(key))
        if res == "d":
            use_defaults = True
            settings[key] = spec.get("default")
            continue
        settings[key] = res

    # Fill remaining defaults if 'd' was hit mid-dialog.
    for key, spec in specs:
        if key in settings:
            continue
        if key == "cfg_scale":
            vmin, vmax = spec.get("min"), spec.get("max")
            if vmin is not None and vmax is not None and vmin == vmax:
                settings[key] = vmin
            continue
        val = spec.get("default")
        if key == "seed":
            settings[key] = None if val is None else val
        elif val is not None:
            settings[key] = val

    return settings


def validate_against_config(request, model, backend):
    """Enforce per-model bounds from config (the real contract)."""
    mid = request.get("model_id")
    if mid != model.get("id"):
        raise PickError(f"model_id mismatch: {mid} != {model.get('id')}")
    settings = request.get("settings", {})
    specs = model.get("settings") or {}
    allowed = set(specs.keys())
    # Emitted set vs allowed: cfg_scale allowed for comfyui; n for unsloth
    unknown = set(settings.keys()) - allowed
    if unknown:
        raise PickError(f"settings not in model map: {sorted(unknown)}")
    for key, spec in specs.items():
        if key not in settings:
            continue
        val = settings[key]
        if val is None:
            continue
        s_min, s_max = spec.get("min"), spec.get("max")
        if key in ("steps", "width", "height", "n") and not isinstance(val, int):
            raise PickError(f"{key} must be an integer, got {val!r}")
        if key == "cfg_scale" and not isinstance(val, (int, float)):
            raise PickError(f"{key} must be numeric, got {val!r}")
        if s_min is not None and val < s_min:
            raise PickError(f"{key} {val} < min {s_min}")
        if s_max is not None and val > s_max:
            raise PickError(f"{key} {val} > max {s_max}")
        mult = spec.get("multiple_of")
        if mult and val % mult != 0:
            raise PickError(f"{key} {val} not multiple of {mult}")
        choices = spec.get("choices")
        if choices and val not in choices:
            raise PickError(f"{key} {val} not in choices {choices}")
    # Cross-field (same as dialog)
    if "width" in settings and "height" in settings:
        try:
            check_cross_field(settings["width"], settings["height"], model, backend)
        except ValueError as e:
            raise PickError(str(e))
    # Unsloth area server limit (advisory vs verified both applied)
    limits = model.get("server_limits") or {}
    max_px = limits.get("max_output_pixels")
    if max_px and "width" in settings and "height" in settings:
        if settings["width"] * settings["height"] > max_px:
            raise PickError(
                f"area {settings['width']}x{settings['height']} exceeds {max_px}"
            )
    return True


def validate_schema_envelope(request, schema):
    """Manual schema-envelope check (jsonschema may be unavailable).

    Real per-model truth lives in config.yaml; this is the generic envelope
    from request-schema.json: required keys, types, string lengths, and the
    settings key allowlist.
    """
    req = set(request.keys())
    missing = set(schema.get("required", [])) - req
    if missing:
        raise PickError(f"missing required keys: {sorted(missing)}")
    extra = req - set(schema.get("properties", {}).keys())
    if extra:
        raise PickError(f"unknown top-level keys: {sorted(extra)}")
    if request.get("schema_version") != schema["properties"]["schema_version"].get("const", SCHEMA_VERSION):
        raise PickError("schema_version mismatch")
    pattern = schema["properties"]["model_id"].get("pattern")
    if pattern and not re.match(pattern, request.get("model_id", "")):
        raise PickError(f"model_id {request.get('model_id')!r} does not match {pattern}")
    prompt = request.get("prompt", "")
    if not isinstance(prompt, str) or not (1 <= len(prompt) <= 4000):
        raise PickError("prompt must be a string of 1-4000 chars")
    neg = request.get("negative_prompt")
    if neg is not None and (not isinstance(neg, str) or len(neg) > 4000):
        raise PickError("negative_prompt must be null or a string <= 4000 chars")
    settings = request.get("settings", {})
    sprops = schema["properties"]["settings"]["properties"]
    unknown = set(settings.keys()) - set(sprops.keys())
    if unknown:
        raise PickError(f"settings keys not in schema: {sorted(unknown)}")
    for key, val in settings.items():
        if val is None:
            continue
        spec = sprops[key]
        stype = spec.get("type")
        types = stype if isinstance(stype, list) else [stype]
        if "integer" in types and not isinstance(val, int):
            raise PickError(f"settings.{key} must be an integer (or null)")
        if "number" in types and not isinstance(val, (int, float)):
            raise PickError(f"settings.{key} must be a number (or null)")
        if "string" in types and not isinstance(val, str):
            raise PickError(f"settings.{key} must be a string (or null)")
        if "integer" not in types and "number" not in types and "string" not in types:
            raise PickError(f"settings.{key}: unsupported schema type {stype!r}")
        lo, hi = spec.get("minimum"), spec.get("maximum")
        if lo is not None and val < lo:
            raise PickError(f"settings.{key} {val} < schema minimum {lo}")
        if hi is not None and val > hi:
            raise PickError(f"settings.{key} {val} > schema maximum {hi}")
    out = request.get("output", {})
    if not isinstance(out, dict):
        raise PickError("output must be an object")
    oprops = schema["properties"]["output"]["properties"]
    unknown_out = set(out.keys()) - set(oprops.keys())
    if unknown_out:
        raise PickError(f"output keys not in schema: {sorted(unknown_out)}")
    return True


def try_jsonschema_validate(request, schema_path):
    """Validate with jsonschema if importable; return None if unavailable."""
    try:
        import jsonschema
    except ImportError:
        return None
    try:
        with open(schema_path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        jsonschema.validate(instance=request, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        raise PickError(f"schema validation failed: {e.message}") from e


def build_request(model, machine, backend, cfg, prompt, negative, settings,
                  output_dir, filename_template=None):
    request = {
        "schema_version": SCHEMA_VERSION,
        "model_id": model["id"],
        "prompt": prompt,
        "settings": settings,
    }
    if negative:
        request["negative_prompt"] = negative
    out = {"dir": output_dir}
    if filename_template:
        out["filename_template"] = filename_template
    request["output"] = out
    return request


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Interactive image-gen model picker + settings dialog",
        epilog="Prompts go to stderr; the request JSON is printed to stdout.",
    )
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--config", default=os.path.join(here, "config.yaml"),
                    help="config.yaml path (default: same dir as picker.py)")
    ap.add_argument("--schema", default=os.path.join(here, "request-schema.json"),
                    help="request-schema.json path (default: same dir)")
    ap.add_argument("--model", help="skip the menu and use this model id")
    ap.add_argument("--prompt", help="prompt text (skip interactive ask)")
    ap.add_argument("--negative", help="negative prompt (skip interactive ask)")
    ap.add_argument("--defaults", action="store_true",
                    help="accept all settings defaults without prompting "
                         "(implied by --json-only)")
    ap.add_argument("--output-dir", help="override output.dir "
                                         "(default from config defaults.output_dir)")
    ap.add_argument("--filename-template", help="output.filename_template")
    ap.add_argument("-o", "--output", help="also write the JSON to this file")
    ap.add_argument("--no-validate", action="store_true", help="skip validation")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress all prompts; only print JSON (requires "
                         "--model and --prompt)")
    return ap.parse_args(argv)


def run(args):
    """Build a validated request object for the selected model + settings.

    Returns the request dict matching request-schema.json. Raises PickError
    on user abort (quit/EOF) or validation failure, KeyboardInterrupt on
    Ctrl-C. `args` may be argparse Namespace or None (parses sys.argv).
    """
    if args is None:
        args = parse_args()
    cfg = load_config(args.config)
    index = build_model_index(cfg)

    # Resolve model
    if args.model:
        target = next((it for it in index if it[2].get("id") == args.model), None)
        if target is None:
            raise PickError(f"model {args.model!r} not found in config")
        machine, backend, model = target
        if model.get("availability") != "verified":
            raise PickError(f"model {args.model!r} is unverified (not runnable)")
    else:
        mapping = print_menu(index)
        if not mapping:
            raise PickError("no verified models available")
        machine, backend, model = pick_model(mapping)

    # Prompt text
    if args.prompt is not None:
        prompt = args.prompt
        if not (1 <= len(prompt) <= 4000):
            raise PickError("--prompt must be 1-4000 chars")
    elif args.json_only:
        raise PickError("--json-only requires --prompt")
    else:
        prompt = collect_prompt()

    # Negative prompt
    # Scripted mode (all inputs provided or defaults) skips the ask:
    # --negative given -> use it; else json_only/defaults -> None; else ask.
    scripted = args.json_only or (
        args.defaults and args.model and args.prompt is not None
    )
    if args.negative is not None:
        negative = args.negative or None
    elif scripted:
        negative = None
    else:
        negative = collect_negative()

    # Settings
    settings = prompt_settings(model, backend,
                               defaults_only=args.defaults or args.json_only)

    # Output dir
    output_dir = args.output_dir or cfg["defaults"]["output_dir"]

    request = build_request(model, machine, backend, cfg, prompt, negative,
                            settings, output_dir,
                            filename_template=args.filename_template)

    # Validate
    if not args.no_validate:
        validate_against_config(request, model, backend)
        validate_schema_envelope(request, json.load(open(args.schema)))
        js = try_jsonschema_validate(request, args.schema)
        if js is None:
            err_print("(jsonschema not installed — used config-bounds + "
                      "envelope validation)")
        else:
            err_print("(validated against request-schema.json)")

    return request


def main(argv=None):
    code = 0
    try:
        args = parse_args(argv)
        request = run(args)
        payload = json.dumps(request, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
            err_print(f"request written to {args.output}")

        err_print("\nRequest JSON (pipe to the executor or save with -o):")
        print(payload)
    except KeyboardInterrupt:
        err_print("\ninterrupted — no request emitted")
        code = 130
    except PickError as e:
        err_print(f"error: {e}")
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
