#!/usr/bin/env python3
"""Group benchmark rows by the machine that produced them.

A fleet spans machines. Ranking every model in one table is actively
misleading, because tok/s is only comparable within one box: the Studio's
151 tok/s and the MBP's 16 tok/s for the same task say nothing about which
model is better, only about which silicon it ran on. Each machine also has a
different roster, so a combined table implies comparisons that do not exist.

Grouping key is the `endpoint` column the CSVs already carry -- measured fact,
not a guess from the model-id prefix. endpoints.json supplies the friendly
machine name and is consulted second, so a model that never appears in a CSV
(the model-config entries with no benchmark rows) can still be placed.
"""
import json
import os
from collections import OrderedDict

DEFAULT_REGISTRY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "endpoints.json")


def _host_label(entry):
    """Turn a registry entry's host string into a short machine name."""
    host = (entry.get("host") or entry.get("name") or "?").strip()
    # 'MacBook Pro M5 over tailnet' / 'Mac Studio M3 Ultra (local)' -> first phrase
    host = host.split(" over ")[0].split(" (")[0].strip()
    return host


def load_machines(registry=DEFAULT_REGISTRY):
    """Return [(machine_name, endpoint_url)] from endpoints.json, in file order.

    Only entries that declare an id_prefix describe a served MODEL ROSTER, so
    they are the ones worth grouping by. oMLX and friends expose no prefix and
    are excluded.
    """
    try:
        with open(registry) as f:
            entries = json.load(f)["endpoints"]
    except (OSError, ValueError, KeyError):
        return []
    out = OrderedDict()
    for e in entries:
        url = e.get("url")
        prefix = e.get("id_prefix")
        if not url or not prefix:
            continue
        name = _host_label(e)
        # A tailnet URL and its loopback twin are the same box; keep the first
        # name seen so both spellings do not become two machines.
        out.setdefault(url, (name, prefix))
    return list(out.items())


def machine_for_endpoint(endpoint, machines=None):
    """Exact URL match first, then host:port, then None."""
    machines = machines if machines is not None else load_machines()
    if not endpoint:
        return None
    ep = endpoint.rstrip("/")
    for url, (name, prefix) in machines:
        if url.rstrip("/") == ep:
            return name
    # Fall back to host:port so a URL that differs only by scheme/hostname
    # (localhost vs 127.0.0.1) still groups with its registry entry.
    def hostport(u):
        u = u.split("://", 1)[-1]
        return u.split("/")[0]
    hp = hostport(ep)
    for url, (name, prefix) in machines:
        if hostport(url) == hp:
            return name
    return None


def machine_for_model(name, machines=None):
    """Prefix match, for rows that lack an endpoint (model-config entries)."""
    machines = machines if machines is not None else load_machines()
    best = None
    for url, (mname, prefix) in machines:
        if name.startswith(prefix):
            if best is None or len(prefix) > len(best[1]):
                best = (mname, prefix)
    return best[0] if best else None


def group_rows(rows, key="model", machines=None):
    """Ordered {machine: [rows]} plus an 'unassigned' bucket for anything unknown.

    Order follows endpoints.json so output is stable run to run.
    """
    machines = machines if machines is not None else load_machines()
    order = [name for name, _ in machines]
    groups = OrderedDict((n, []) for n in order)
    for r in rows:
        m = (machine_for_endpoint(r.get("endpoint"), machines)
             or machine_for_model(r.get(key, ""), machines)
             or "unassigned")
        groups.setdefault(m, []).append(r)
    return OrderedDict((k, v) for k, v in groups.items() if v)


def machine_of_model(name, machines=None):
    """Public helper: which machine serves this model id."""
    return machine_for_model(name, machines)