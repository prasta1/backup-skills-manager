#!/usr/bin/env python3
"""Convert a ComfyUI editor-format workflow JSON to API format.

Editor format = top-level `nodes` + `links` arrays (blueprints/, civitai
files, shared workflows). API format = one dict per node id keyed by
`class_type` with resolved named `inputs` — required by POST /prompt and by
the comfyui skill's run_workflow.py.

Usage:
  python3 comfy_editor_to_api.py INPUT.json --host http://127.0.0.1:8188 [-o OUT.json]

Schemas come from the live server's /object_info (authoritative slot names).
Handles BOTH link encodings: legacy array links
`[id, from_node, from_slot, to_node, to_slot, type]` and newer dict links
`{id, origin_id, origin_slot, target_id, target_slot, type}`, plus graphs
wrapped inside `definitions.subgraphs` (single wrapper node) as shipped in
ComfyUI blueprints. Reroute nodes resolve through their incoming link;
Primitive-style nodes pass widgets_values[0] through; Note/MarkdownText are
dropped. Missing values are reported as warnings, never guessed.
Stdlib only. Verified against ComfyUI 0.37.x (macOS, MPS) by running a
converted blueprint end-to-end.
"""
import argparse, json, sys, urllib.request

DROP = {"Note", "MarkdownText", "ConvertToJson", "ShowText|pysssss"}

def fetch_object_info(host):
    with urllib.request.urlopen(host.rstrip("/") + "/object_info", timeout=30) as r:
        info = json.load(r)
    out = {}
    for name, d in info.items():
        order, combo = [], {}
        for section in ("required", "optional"):
            for slot, spec in (d.get("input") or {}).items():
                kinds = spec[0] if isinstance(spec, (list, tuple)) and spec else None
                combo[slot] = isinstance(kinds, list)
                order.append(slot)
        out[name] = {"slots": order, "combo": combo}
    return out

def normalize_links(links):
    """-> list of (link_id, from_id(str), from_slot, to_id(str), to_slot)"""
    out = []
    for l in links:
        if isinstance(l, dict):
            out.append((l["id"], str(l["origin_id"]), l["origin_slot"],
                        str(l["target_id"]), l["target_slot"]))
        else:
            out.append((l[0], str(l[1]), l[2], str(l[3]), l[4]))
    return out

def input_names(node):
    """Slot names in display order from the node's own `inputs` array
    (link slots AND widget slots, in graph order). None if absent."""
    ins = node.get("inputs")
    if not ins:
        return None
    return [i.get("name") for i in ins]

def flatten(doc, exposed, out_src):
    nodes = list(doc.get("nodes", []))
    links = list(doc.get("links", []))
    subs = {sg.get("id"): sg for sg in (doc.get("definitions") or {}).get("subgraphs", [])}
    wrapper = [n for n in nodes if n.get("type") in subs]
    if len(wrapper) == 1 and len(subs) >= 1:
        sg = subs[wrapper[0]["type"]]
        nodes, links = list(sg.get("nodes", [])), list(sg.get("links", []))
        exposed.append(str(wrapper[0]["id"]))
        # inject subgraph-exposed defaults into the target node slots
        for o in sg.get("outputs", []):
            if o.get("name") == "IMAGE" or o.get("localized_name") == "IMAGE":
                for lid in o.get("linkIds") or []:
                    for l in links:
                        if (l["id"] if isinstance(l, dict) else l[0]) == lid:
                            fid = str(l["origin_id"] if isinstance(l, dict) else l[1])
                            fslot = l["origin_slot"] if isinstance(l, dict) else l[2]
                            out_src.append((fid, fslot))
        for sin in sg.get("inputs", []):
            dflt = sin.get("defaultValue", sin.get("widget_value"))
            if dflt is None:
                continue
            for lid in sin.get("linkIds") or []:
                for l in links:
                    if (l["id"] if isinstance(l, dict) else l[0]) != lid:
                        continue
                    tgt = str(l["target_id"] if isinstance(l, dict) else l[3])
                    tslot = l["target_slot"] if isinstance(l, dict) else l[4]
                    tnode = next((n for n in nodes if str(n["id"]) == tgt), None)
                    names = input_names(tnode) if tnode else None
                    if tnode and names and tslot < len(names):
                        tnode.setdefault("_injected", {})[names[tslot]] = dflt
    return nodes, links

def convert(doc, info):
    exposed, out_src = [], []
    doc_nodes, raw_links = flatten(doc, exposed, out_src)
    wrapper_ids = set(exposed)
    links = normalize_links(raw_links)
    nodes = {str(n["id"]): n for n in doc_nodes}
    # by_target keyed by SLOT NAME; also a positional fallback map
    by_target_named, by_target_pos = {}, {}
    for lid, fn, fs, tn, ts in links:
        tnode = nodes.get(tn)
        names = input_names(tnode) if tnode else None
        if names and ts < len(names):
            by_target_named[(tn, names[ts])] = (fn, fs)
        by_target_pos[(tn, ts)] = (fn, fs)
    out, warns = {}, []
    for nid, n in nodes.items():
        ct = n.get("type") or n.get("class_type")
        if ct in DROP:
            continue
        if ct == "Reroute":
            src = next(((fn, fs) for (tn, key), (fn, fs) in by_target_named.items() if tn == nid), None)
            if src is None:
                src = next(((fn, fs) for (tn, p), (fn, fs) in by_target_pos.items() if tn == nid), None)
            if src is None:
                warns.append(f"{nid}: Reroute with no incoming link"); continue
            for key, (fn, fs) in list(by_target_named.items()):
                if fn == nid: by_target_named[key] = src
            for key, (fn, fs) in list(by_target_pos.items()):
                if fn == nid: by_target_pos[key] = src
            continue
        if ct not in info:
            if "Primitive" in str(ct):
                val = (n.get("widgets_values") or [None])[0]
                for key, (fn, fs) in list(by_target_named.items()):
                    if fn == nid: by_target_named[key] = ("PRIM", val)
                continue
            warns.append(f"{nid}: class '{ct}' unknown to server — skipped")
            continue
        schema = info[ct]
        inputs, wv, injected = {}, list(n.get("widgets_values") or []), n.get("_injected") or {}
        names = input_names(n)
        if names:
            # widget position i corresponds to slot names[len(names)-len(wv)+i]
            # when widgets trail link inputs (litegraph display order).
            off = len(names) - len(wv)
            for i, val in enumerate(wv):
                if 0 <= off + i < len(names):
                    inputs.setdefault(names[off + i], val)
            pos = 0
            for slot in names:
                ref = by_target_named.get((nid, slot)) or by_target_pos.get((nid, pos))
                if ref:
                    inputs[slot] = ref[1] if ref[0] == "PRIM" else [ref[0], ref[1]]
                pos += 1
        else:
            wi = 0
            for slot in schema["slots"]:
                if slot in injected:
                    inputs[slot] = injected[slot]
                elif wi < len(wv):
                    inputs[slot] = wv[wi]; wi += 1
            if wi < len(wv):
                warns.append(f"{nid}.{ct}: {len(wv)-wi} widget values beyond schema slots")
        # links onto slots not covered above
        for (tn, slot), ref in by_target_named.items():
            if tn == nid and slot not in inputs:
                inputs[slot] = ref[1] if ref[0] == "PRIM" else [ref[0], ref[1]]
        unresolved = {}
        for slot, val in list(inputs.items()):
            if isinstance(val, list) and val[0] not in nodes:
                unresolved[slot] = val[1]
                del inputs[slot]
        for slot in schema["slots"]:
            if slot not in inputs and (schema["combo"].get(slot) or slot in unresolved):
                warns.append(f"{nid}.{ct}: slot '{slot}' exposed by the blueprint — pass --set {slot}=VALUE")
        out[nid] = {"class_type": ct, "inputs": inputs, "_exposed": unresolved}
    out = {k: v for k, v in out.items() if v["class_type"] in info}
    if out_src and not any(v["class_type"] in ("SaveImage", "SaveImageAdvanced",
                                               "SaveAnimatedWEBP", "PreviewImage")
                           for v in out.values()):
        fid, fslot = out_src[0]
        if fid in out:
            out["900"] = {"class_type": "SaveImage",
                          "inputs": {"images": [fid, fslot], "filename_prefix": "localgen"}}
            warns.append("added SaveImage node 900 (blueprint exposed IMAGE with no save node)")
    return out, warns

def apply_sets(out, sets):
    """Fill exposed slots by name across all nodes. Values parse as JSON
    when possible (numbers, lists), else stay strings."""
    for raw in sets:
        name, _, val = raw.partition("=")
        try:
            v = json.loads(val)
        except Exception:
            v = val
        hit = 0
        for nid, node in out.items():
            if name in node.get("_exposed", {}):
                node["inputs"][name] = v; hit += 1
        if hit == 0:
            print(f"WARN: --set {name}: no exposed slot of that name", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("-o", "--output")
    ap.add_argument("--host", required=True, help="running ComfyUI, e.g. http://127.0.0.1:8188")
    ap.add_argument("--raw", action="store_true",
                    help="emit bare node map; default emits the ready-to-POST body {'prompt': ...}")
    ap.add_argument("--set", action="append", default=[], metavar="SLOT=VALUE",
                    help="fill a blueprint-exposed slot, e.g. --set unet_name=z_image_turbo_bf16.safetensors")
    ap.add_argument("--schema-out", metavar="FILE",
                    help="write a run_workflow.py-compatible schema sidecar for exposed slots")
    a = ap.parse_args()
    doc = json.load(open(a.input))
    if "nodes" not in doc:
        print("input looks like API format already", file=sys.stderr); sys.exit(1)
    info = fetch_object_info(a.host)
    api, warns = convert(doc, info)
    if a.set:
        apply_sets(api, a.set)
    wrapped = {"prompt": api} if not a.raw else api
    if a.schema_out:
        # sidecar schema so comfyui run_workflow.py --args can inject the
        # blueprint's exposed slots (empty combo slots aren't auto-detected)
        params = {}
        for nid, node in api.items():
            slots = info.get(node["class_type"], {}).get("slots", [])
            for slot in node.get("_exposed", {}):
                key = slot if slot not in params else f"{slot}_{nid}"
                params[key] = {"node_id": nid, "field": slot, "type": "string"}
        json.dump({"parameters": params}, open(a.schema_out, "w"), indent=2)
        print(f"wrote schema {a.schema_out} ({len(params)} exposed params)")
    for v in api.values():
        v.pop("_exposed", None)
    txt = json.dumps(wrapped, indent=2)
    if a.output:
        open(a.output, "w").write(txt); print(f"wrote {a.output} ({len(api)} nodes)")
    else:
        print(txt)
    for w in warns: print("WARN:", w, file=sys.stderr)

if __name__ == "__main__":
    main()
