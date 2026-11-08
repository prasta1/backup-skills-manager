#!/usr/bin/env python3
"""
convert_workflow.py — Convert a ComfyUI *editor-format* workflow JSON to
*API format* for direct submission to /api/prompt.

Why this exists
---------------
ComfyUI saves workflow files in editor format (top-level `nodes` and `links`
arrays). The skill's scripts (run_workflow.py, check_deps.py, extract_schema.py)
all require API format (a flat `node_id -> {class_type, inputs}` map). Exporting
via the UI is manual and not always available (agent runs). This script fills
the gap: parse editor format, resolve links, map widget values positionally
against known node schemas, and emit API JSON.

What it handles
---------------
- Standard node classes (core ComfyUI 0.37 set used by the skill's workflows)
- Dotted widget keys kept literal (`format.bit_depth`, `format.input_color_space`)
- Container inputs (`images.image_1` -> `images: {"image_1": [...]}`)
- Reroute bypass (rewires references to the Reroute's source)
- Note/MarkdownNote and *detached* LoadImage nodes (safe to drop)
- UI-only widgets (`control_after_generate`, `upload`) dropped automatically

What it refuses
---------------
- ComfyUI 0.37 *subgraph template nodes* (a node whose `type` is a UUID,
  defined in `definitions.subgraphs`) — packed graphs, not convertible here.
- Unknown node classes (fail loudly rather than emit a broken workflow;
  add the class to WIDGET_FIELDS if it's legitimately convertible).

Usage
-----
    python3 scripts/convert_workflow.py editor_workflow.json
    python3 scripts/convert_workflow.py editor_workflow.json --out api.json
    python3 scripts/convert_workflow.py editor_workflow.json --pretty --dry-run

Output defaults to `<input>.api.json` next to the source file.

Stdlib-only. Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# =============================================================================
# Known widget field order per node class
# =============================================================================
# Positional map of editor `widgets_values` -> API input field names.
# Fields suffixed `(UI-ONLY)` exist in the editor widget list but are NOT
# part of the API schema — they're dropped during conversion.
# Schema source: ComfyUI 0.37.0 core source (nodes.py, comfy_extras/*).
# -----------------------------------------------------------------------------

WIDGET_FIELDS: dict[str, list[str]] = {
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "VAELoader": ["vae_name"],
    "ModelSamplingAuraFlow": ["shift", "sampling"],
    "CLIPTextEncode": ["text"],
    "ConditioningZeroOut": [],
    "EmptyLatentImage": ["width", "height", "batch_size"],
    "EmptySD3LatentImage": ["width", "height", "batch_size"],
    "KSampler": [
        "seed",
        "control_after_generate(UI-ONLY)",
        "steps",
        "cfg",
        "sampler_name",
        "scheduler",
        "denoise",
    ],
    "KSamplerAdvanced": [
        "add_noise",
        "noise_seed",
        "control_after_generate(UI-ONLY)",
        "steps",
        "cfg",
        "sampler_name",
        "scheduler",
        "start_at_step",
        "end_at_step",
        "return_with_leftover_noise",
    ],
    "VAEDecode": [],
    "VAEEncode": [],
    "VAEEncodeForInpaint": ["grow_mask_by"],
    "SaveImage": ["filename_prefix"],
    "SaveImageAdvanced": [
        "filename_prefix",
        "format",
        "format.bit_depth",
        "format.input_color_space",
    ],
    "LoadImage": ["image", "upload(UI-ONLY)"],
    "ImageScaleToTotalPixels": ["upscale_method", "megapixels", "resolution_steps"],
    "GrowMask": ["expand", "tapered_corners"],
    "SetLatentNoiseMask": [],
    "ImagePadForOutpaint": ["left", "top", "right", "bottom", "feathering"],
    "LatentUpscaleBy": ["upscale_method", "scale_by"],
    "TextEncodeQwenImage21": ["prompt", "negative_prompt", "resolution"],
    "QwenImage21Cache": ["device", "dtype"],
}

# Link-type inputs (tensors/models) that appear in the editor `inputs` array
# with `link: null` but must never be mistaken for widgets.
LINK_ONLY_FIELDS: dict[str, set[str]] = {
    "UNETLoader": set(),
    "CLIPLoader": set(),
    "VAELoader": set(),
    "ModelSamplingAuraFlow": {"model"},
    "CLIPTextEncode": {"clip"},
    "ConditioningZeroOut": {"conditioning"},
    "EmptyLatentImage": set(),
    "EmptySD3LatentImage": set(),
    "KSampler": {"model", "positive", "negative", "latent_image"},
    "KSamplerAdvanced": {"model", "positive", "negative", "latent_image"},
    "VAEDecode": {"samples", "vae"},
    "VAEEncode": {"pixels", "vae"},
    "VAEEncodeForInpaint": {"pixels", "vae", "mask"},
    "SaveImage": {"images"},
    "SaveImageAdvanced": {"images"},
    "LoadImage": set(),
    "ImageScaleToTotalPixels": {"image"},
    "GrowMask": {"mask"},
    "SetLatentNoiseMask": {"samples", "mask"},
    "ImagePadForOutpaint": {"image"},
    "LatentUpscaleBy": {"samples"},
    "TextEncodeQwenImage21": {"clip", "vae"},
    "QwenImage21Cache": {"model"},
}


# =============================================================================
# Conversion
# =============================================================================

def _editor_links(data: dict) -> dict[int, list]:
    """Build link_id -> [id, origin_id, origin_slot, target_id, target_slot, type]."""
    links: dict[int, list] = {}
    for l in data.get("links", []):
        if isinstance(l, list) and l:
            links[int(l[0])] = l
    return links


def _link_ref(link: list) -> list[Any]:
    """[origin_id, origin_slot] -> API reference [str(origin_id), origin_slot]."""
    return [str(link[1]), int(link[2])]


def _node_connected(node: dict, links: dict[int, list]) -> bool:
    """True if any link references this node as origin or target."""
    nid = node.get("id")
    for l in links.values():
        if l[1] == nid or l[3] == nid:
            return True
    return False


def _resolve_reroute(node_id: int, links: dict[int, list], nodes_by_id: dict[int, dict],
                     visited: set[int] | None = None) -> list | None:
    """Follow a chain of Reroute nodes to the real source link.

    Returns the API link reference [source_node_id, slot] of the eventual
    origin (skipping Reroutes), or None if the chain dead-ends.
    """
    visited = visited or set()
    if node_id in visited:
        return None
    visited.add(node_id)
    node = nodes_by_id.get(node_id)
    if node is None:
        return None
    for inp in node.get("inputs", []):
        link_id = inp.get("link")
        if link_id is None:
            continue
        l = links.get(int(link_id))
        if l is None:
            continue
        origin_id = l[1]
        origin_node = nodes_by_id.get(origin_id)
        if origin_node is not None and origin_node.get("type") == "Reroute":
            return _resolve_reroute(origin_id, links, nodes_by_id, visited)
        return _link_ref(l)
    return None


def convert_editor(data: dict) -> tuple[dict, list[tuple]]:
    """Convert editor-format dict to API-format dict.

    Returns (api_workflow, warnings) where warnings is a list of
    (node_id, node_type, message) tuples.
    """
    if "nodes" not in data or "links" not in data:
        raise ValueError("Not editor format: missing top-level 'nodes'/'links' arrays")

    links = _editor_links(data)
    nodes_by_id = {n.get("id"): n for n in data.get("nodes", [])}
    out: dict[str, dict] = {}
    warnings: list[tuple] = []

    for node in data.get("nodes", []):
        nid = node.get("id")
        cls = node.get("type", "")
        title = node.get("title")

        # --- Skip decorative / detached nodes ---------------------------------
        if cls in ("Note", "MarkdownNote"):
            warnings.append((nid, cls, "skipped (decorative)"))
            continue
        if cls == "Reroute":
            warnings.append((nid, cls, "bypassed (references rewired to source)"))
            continue
        if cls == "LoadImage" and not _node_connected(node, links):
            warnings.append((nid, cls, "skipped (detached LoadImage)"))
            continue

        # --- Refuse subgraph template nodes -----------------------------------
        if cls not in WIDGET_FIELDS:
            # UUID-type nodes = packed subgraph templates (ComfyUI 0.37)
            if len(cls) == 36 and cls.count("-") == 4:
                raise ValueError(
                    f"Node {nid} is a subgraph template node (UUID type '{cls}'). "
                    "Packed subgraphs are not convertible by this script. "
                    "Use the flat graph instead (e.g. the skill's qwen-image-2.1-simple workflow)."
                )
            raise ValueError(
                f"Node {nid} has unknown class_type '{cls}'. "
                "Add it to WIDGET_FIELDS to convert, or export from the UI "
                "('Workflow -> Export (API)')."
            )

        inputs: dict[str, Any] = {}
        containers: dict[str, dict[str, Any]] = {}

        # --- Resolve linked inputs --------------------------------------------
        for inp in node.get("inputs", []) or []:
            name = inp.get("name", "")
            link_id = inp.get("link")
            if link_id is None:
                continue  # widget input -> filled positionally below
            l = links.get(int(link_id))
            if l is None:
                raise ValueError(f"Node {nid} input '{name}' references missing link {link_id}")
            origin_id = l[1]
            origin_node = nodes_by_id.get(origin_id)
            if origin_node is not None and origin_node.get("type") == "Reroute":
                ref = _resolve_reroute(origin_id, links, nodes_by_id)
                if ref is not None:
                    if "." in name:
                        container, member = name.split(".", 1)
                        containers.setdefault(container, {})[member] = ref
                    else:
                        inputs[name] = ref
            else:
                ref = _link_ref(l)
                if "." in name:
                    container, member = name.split(".", 1)
                    containers.setdefault(container, {})[member] = ref
                else:
                    inputs[name] = ref

        # --- Merge container inputs (images.image_1 -> images: {...}) ----------
        for container, members in containers.items():
            inputs[container] = members

        # --- Map widget values positionally ------------------------------------
        widgets = node.get("widgets_values") or []
        fields = WIDGET_FIELDS[cls]
        if len(widgets) > len(fields):
            warnings.append((nid, cls, f"widgets_values ({len(widgets)}) longer than schema ({len(fields)}); extra ignored"))
        for field, value in zip(fields, widgets):
            if field.endswith("(UI-ONLY)"):
                continue
            inputs[field] = value

        node_out: dict[str, Any] = {"class_type": cls, "inputs": inputs}
        if title:
            node_out["_meta"] = {"title": title}

        out[str(nid)] = node_out

    return out, warnings


# =============================================================================
# CLI
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert a ComfyUI editor-format workflow to API format")
    p.add_argument("workflow", help="Path to editor-format workflow JSON")
    p.add_argument("--out", "-o", help="Output path (default: <input>.api.json)")
    p.add_argument("--pretty", action="store_true", help="Pretty-print the JSON (default: compact)")
    p.add_argument("--dry-run", action="store_true", help="Print the converted workflow to stdout, don't write")
    args = p.parse_args(argv)

    wf_path = Path(args.workflow).expanduser()
    if not wf_path.exists():
        print(f"Error: {wf_path} not found", file=sys.stderr)
        return 1

    try:
        with wf_path.open(encoding="utf-8-sig") as f:
            data = json.load(f)
        api, warnings = convert_editor(data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if warnings:
        print("Warnings:", file=sys.stderr)
        for nid, cls, msg in warnings:
            print(f"  - node {nid} ({cls}): {msg}", file=sys.stderr)

    text = json.dumps(api, indent=2 if args.pretty else None)

    if args.dry_run:
        print(text)
        return 0

    out_path = Path(args.out) if args.out else wf_path.with_name(wf_path.stem + ".api.json")
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"Converted: {wf_path} -> {out_path}", file=sys.stderr)
    print(f"Nodes: {len(api)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())