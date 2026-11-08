#!/usr/bin/env python3
"""Which model ids can still be SERVED by some host.

THE rule the sinks follow: a measurement is published only if its model can still
be loaded by this box or the other one. Nothing is stored, so nothing can go
stale -- which is the whole point. The flag this replaces (`deleted`, surfaced as
`Retired`) was computed once at merge time and then frozen into four places: each
run's own model-config.json, the fleet model-config.json, and the two sinks. They
froze at different times and disagreed, so rows described models no host could
load -- 12 of them, 10 of which were sitting on a chart, including 3 of the 19
points on the MacBook "Current fleet" scatter.

    loadable(m) = m in this host's llama-swap config
               or m in the peer's llama-swap config (read over ssh)

FAIL-SAFE, and it is load-bearing in both directions. An unreachable peer is
UNKNOWN, never empty: an id the local config does not declare but the peer might
own is treated as loadable, so a sleeping laptop can never delete laptop rows
from the review surface. An unreadable LOCAL config is unknown too, and unknown
means publish everything -- the opposite reading would wipe the table on the
first bad path.

Usage:
    python3 scripts/loadability.py --list                  # the resolved sets
    python3 scripts/loadability.py --check ID [ID ...]     # verdict per id
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_model_config import config_model_keys, prefix_map  # noqa: E402

STUDIO_CONFIG = os.path.expanduser("~/.hermes/llama-swap/config.yaml")
PEER_CONFIG = "~/.hermes/llama-swap/config.yaml"
REGISTRY = os.path.join(ROOT, "references", "endpoints.json")
PEER_SSH = os.environ.get("BENCH_MBP_SSH", "macbook")

# Piped over ssh, so nothing has to be installed on the far side beyond python3.
# Same shape as model_family.remote_arch_map, including the BatchMode+timeout, so
# a box that is asleep returns fast instead of hanging a push. Kept as its own
# copy rather than importing the arch map: that one answers a different question
# and would drag the GGUF reader along with it.
_PEER_SNIPPET = r"""
import json, os, re, sys
path = os.path.expanduser(sys.argv[1])
keys, inside = set(), False
for line in open(path).read().splitlines():
    if re.match(r'^models:\s*$', line):
        inside = True
        continue
    if inside:
        if line and not line.startswith((' ', '\t', '#')):
            break
        m = re.match(r'^  ([a-zA-Z0-9_.\-]+):\s*$', line)
        if m:
            keys.add(m.group(1))
print(json.dumps(sorted(keys)))
"""


def local_ids(config=STUDIO_CONFIG):
    """Ids this host declares, or None if the config cannot be read at all."""
    if not os.path.exists(config):
        return None
    keys = config_model_keys(config)
    return keys or None          # an empty models block is a read failure, not a fact


def peer_ids(ssh_host=PEER_SSH, config=PEER_CONFIG, timeout=60):
    """Ids the peer declares, or None when the peer cannot be reached."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", ssh_host,
           "/usr/bin/python3", "-", config]
    try:
        proc = subprocess.run(cmd, input=_PEER_SNIPPET.encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout)
        if proc.returncode != 0:
            return None
        keys = set(json.loads(proc.stdout.decode() or "[]"))
        return keys or None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def remote_prefixes(config=STUDIO_CONFIG, registry=REGISTRY):
    """Prefixes whose rosters live on another box, derived from the config itself.

    `prefix_map` decides locality by asking which prefixes THIS config actually
    declares -- never from the URL, because the registry lists the MacBook's
    loopback endpoint as 127.0.0.1 with prefix mb-, so a loopback-means-local test
    would call the whole laptop roster local.
    """
    _, remote = prefix_map(config, registry)
    return remote


_RESOLVER = None


def resolver(verbose=True):
    """Cached predicate: is this model loadable by some host right now?"""
    global _RESOLVER
    if _RESOLVER is not None:
        return _RESOLVER
    local = local_ids()
    peer = peer_ids()
    remote = remote_prefixes()

    def is_loadable(model):
        if not model:
            return False
        if local is None:
            return True                    # this host's config is unreadable: do not prune
        if model in local:
            return True
        if peer is not None and model in peer:
            return True
        if peer is None and any(model.startswith(p) for p in remote):
            return True                    # peer unknown, its roster is not our call
        return False

    if verbose:
        print(f"  loadability: {len(local) if local is not None else 'UNKNOWN'} "
              f"local id(s), "
              + (f"{len(peer)} peer id(s)" if peer is not None
                 else "peer UNKNOWN (unreachable -> its roster is kept)")
              + (f", remote prefixes {sorted(remote)}" if remote else ""))
    _RESOLVER = is_loadable
    return is_loadable


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", nargs="+", metavar="ID")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.check:
        f = resolver()
        for i in args.check:
            print(f"  {'LOADABLE ' if f(i) else 'not loadable'}  {i}")
        return 0

    local, peer = local_ids(), peer_ids()
    remote = remote_prefixes()
    print(f"local config ({STUDIO_CONFIG}): "
          + (f"{len(local)} ids" if local is not None else "UNREADABLE"))
    if args.list and local:
        for i in sorted(local):
            print(f"    {i}")
    print(f"peer {PEER_SSH}:{PEER_CONFIG}: "
          + (f"{len(peer)} ids" if peer is not None else "UNREACHABLE (unknown)"))
    if args.list and peer:
        for i in sorted(peer):
            print(f"    {i}")
    print(f"remote prefixes: {sorted(remote)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
