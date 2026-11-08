#!/usr/bin/env python3
"""mtop_dashboard.py — live terminal dashboard for Apple Silicon resource consumption.

Streams one JSON sample per line from macmon `pipe` and renders a live,
resize-safe dashboard with ANSI meters. No third-party Python deps beyond
macmon itself (Apple Silicon only).

Usage:
    /opt/homebrew/bin/python3.14 mtop_dashboard.py

Exit: Ctrl-C.
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import time

MACMON = "/opt/homebrew/bin/macmon"
WIDTH = 44  # bar column width (chars), independent of terminal width


def _read_samples(proc: subprocess.Popen):
    """Yield parsed JSON objects, one per line, from macmon pipe."""
    for line in proc.stdout:  # type: ignore[union-attr]
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _fmt_gigs(b: int) -> float:
    return b / (1024 ** 3)


def render(o: dict) -> list[str]:
    gpu_usage = o.get("gpu_usage") or [0, 0.0]
    gpu_ratio = float(gpu_usage[1]) if len(gpu_usage) >= 2 else 0.0
    mem = o.get("memory") or {}
    fans = o.get("fans") or []

    mem_used = _fmt_gigs(int(mem.get("ram_usage", 0)))
    mem_total = _fmt_gigs(int(mem.get("ram_total", 0)))
    mem_pct = (mem_used / mem_total * 100) if mem_total else 0.0

    swap_used = _fmt_gigs(int(mem.get("swap_usage", 0)))
    swap_total = _fmt_gigs(int(mem.get("swap_total", 0)))
    swap_pct = (swap_used / swap_total * 100) if swap_total else 0.0

    cpu_ratio = float(o.get("cpu_scaled_ratio", 0.0))

    lines = []
    lines.append(f"  GPU    {gpu_ratio*100:5.1f}%        {float(o.get('gpu_power',0)):5.1f}W     {int(o.get('gpu_freq_mhz',0))} MHz")
    g = int(gpu_ratio * WIDTH)
    lines.append("        " + "\u2588"*g + "\u25a1"*(WIDTH - g))

    lines.append(f"  CPU    {cpu_ratio*100:5.1f}%        {float(o.get('cpu_power',0)):5.1f}W     P:{int(o.get('pcpu_freq_mhz',0))} E:{int(o.get('ecpu_freq_mhz',0))} MHz")
    c = int(cpu_ratio * WIDTH)
    lines.append("        " + "\u2588"*c + "\u25a1"*(WIDTH - c))

    lines.append(f"  MEM    {mem_used:6.1f} / {mem_total:.0f} GiB  ({mem_pct:.1f}%)")
    mb = int(mem_pct / 100 * WIDTH)
    lines.append("        " + "\u2588"*mb + "\u25a1"*(WIDTH - mb))

    if swap_total:
        lines.append(f"  SWAP   {swap_used:6.1f} / {swap_total:.0f} GiB  ({swap_pct:.1f}%)")
        sb = int(swap_pct / 100 * WIDTH)
        lines.append("        " + "\u2588"*sb + "\u25a1"*(WIDTH - sb))

    if fans:
        fan_strs = [f"{f.get('name','fan'+str(i))}:{f.get('rpm',0)}/{f.get('max_rpm',0)}"
                    for i, f in enumerate(fans)]
        lines.append("  FAN    " + "   ".join(fan_strs))

    all_power = float(o.get("all_power", 0.0))
    ane_power = float(o.get("ane_power", 0.0))
    lines.append(f"  PKG    {all_power:5.1f}W total   (ANE {ane_power:.1f}W)")
    lines.append("")
    lines.append("  \u2500\u2500 mtop: live macmon feed \u00b7 Ctrl-C to exit \u2500\u2500")
    return lines


def main() -> int:
    proc = subprocess.Popen(
        [MACMON, "pipe", "-i", "1000"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )

    # Clean Ctrl-C exit without stack trace
    def _quit(signum, frame):  # noqa: ARG001
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
        sys.exit(0)
    signal.signal(signal.SIGINT, _quit)

    sys.stdout.write("\033[?25l")  # hide cursor
    sys.stdout.flush()

    for o in _read_samples(proc):
        sys.stdout.write("\033[2J\033[H")  # clear screen, home cursor
        for ln in render(o):
            print(ln)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
