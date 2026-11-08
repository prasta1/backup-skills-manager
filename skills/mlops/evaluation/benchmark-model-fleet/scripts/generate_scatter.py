#!/usr/bin/env python3
"""Generate scatter plots from benchmark CSV results — dark dramatic edition.

Design:
  - Near-black paper, generous negative space, crisp grid.
  - Uniform marker size across all active models (no size encoding → clean comparison).
  - Type encoded by shape + colour only: square / triangle / circle / diamond.
  - The verdict is drawn, not left to the reader: a dashed staircase traces the
    Pareto frontier (models nothing else beats on BOTH axes) and shades the
    beaten region beneath it. Frontier models stay bright; beaten ones recede.
  - oMLX models get a subtle accent ring so the new benchmark run reads at a glance.
  - Annotations placed with side-biased nudging to avoid overlap; hairline leaders.
  - Deleted models: dim grey ×, no leader, label set back.

Usage:
    python3 generate_scatter.py --results-dir ~/.hermes/benchmark_results
                                 --model-config references/model-config.json
                                 --label Coding

Output:
    One PNG per plot, plus a multipage PDF collecting them in the same order
    (scatter_plots.pdf). Each PDF page is the same live figure the PNG was saved
    from, so the two artifacts can never disagree. Suppress with --no-pdf.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from adjustText import adjust_text
import csv
import glob
import os
import sys
import json
import argparse
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_final_report import pareto

# ---------------------------------------------------------------------------
# Palette — dark paper, high-contrast data, one accent for the new run.
# ---------------------------------------------------------------------------
BG        = '#14141A'   # near-black with blue undertone
PANEL     = '#181820'   # slightly lighter plot floor
INK       = '#F0EDE6'   # warm off-white text
MUTED     = '#8A8A94'   # axis labels, tick labels, secondary
GRID      = '#26262E'   # subtle warm grid
LEADER    = '#484852'   # hairline leader

# Data colours — muted but distinct on dark ground
COLORS = {
    "MoE":        '#6B9BD6',   # soft blue
    "Vision":     '#E0A565',   # warm amber
    "Standard":   '#D97A6B',   # muted brick
    "Embeddings": '#6E6E76',   # neutral grey
}

MARKERS = {
    "MoE":        's',
    "Vision":     '^',
    "Standard":   'o',
    "Embeddings": 'D',
}

DELETED_COLOR = '#4A4A52'

# oMLX accent — a single saturated highlight that reads as "newly benchmarked"
OMLX_ACCENT     = '#F2C14E'   # warm gold
OMLX_GLOW_ALPHA = 0.35
OMLX_GLOW_SCALE = 1.22

# Beaten (off-frontier) models keep their colour but step back.
BEATEN_ALPHA = 0.38

# Chart paper. Every PDF page uses it, front matter included, so the document
# has one page size and prints at one scale.
CHART_W, CHART_H = 15.5, 10.5

# Uniform marker size for every active model — no size encoding
MARKER_SIZE = 185
MARKER_EDGE = 1.4

# ---------------------------------------------------------------------------
# Legend — only what this plot actually shows
# ---------------------------------------------------------------------------
def _legend(ax, rows, frontier):
    present = {m['type'] for m, _x, _y in rows if not m['deleted']}
    handles = [
        Line2D([0], [0], marker=MARKERS[t], color='w', markerfacecolor=COLORS[t],
               markersize=10 if t == 'Embeddings' else 12, label=t,
               markeredgecolor='#FFFFFF', markeredgewidth=0.9, linestyle='None')
        for t in COLORS if t in present
    ]
    if frontier:
        handles.append(Line2D([0], [0], color=INK, alpha=0.6, lw=1.2,
                              linestyle=(0, (4, 3)),
                              label='Frontier  (unbeaten on both axes)'))
    if any(m['deleted'] for m, _x, _y in rows):
        handles.append(Line2D([0], [0], marker='x', color='w', markersize=13,
                              label='Deleted', markeredgecolor=DELETED_COLOR,
                              markeredgewidth=2.4, linestyle='None'))
    # One row above the plot, opposite the subtitle. Inside the axes it sat on
    # the top-left corner -- exactly where a high-quality slow model plots.
    ax.legend(
        handles=handles,
        loc='lower right',
        bbox_to_anchor=(1.0, 1.008),
        ncol=len(handles),
        borderaxespad=0,
        fontsize=10.5,
        frameon=False,
        labelcolor=INK,
        handletextpad=0.5,
        columnspacing=1.6,
        handlelength=1.5,
    )

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
def _style_figure(fig, ax, title, subtitle):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)

    ax.set_title(title, fontsize=16, fontweight='600', color=INK,
                 pad=44, loc='left', family='DejaVu Sans')
    # Subtitle carries the run summary and the reading rule, so nobody has to
    # work out which corner of the chart is "good".
    ax.text(0, 1.018, subtitle, transform=ax.transAxes, ha='left', va='bottom',
            fontsize=11, color=MUTED, family='DejaVu Sans')

    ax.set_xlabel('', fontsize=1, labelpad=1)
    ax.set_ylabel('', fontsize=1, labelpad=1)

    ax.tick_params(colors=MUTED, labelsize=10.5, length=0, pad=8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRID)
        ax.spines[spine].set_linewidth(1.0)

    ax.yaxis.grid(True, color=GRID, linewidth=0.9, alpha=0.9, zorder=0)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    return fig, ax

def _subtitle(rows, keep):
    """'14 models  ·  4 on the frontier  ·  2 Oct 2026' for the plot header."""
    n = sum(1 for m, _x, _y in rows if not m['deleted'])
    parts = [f"{n} model{'s' if n != 1 else ''}"]
    if keep is not None:
        parts.append(f"{len(keep)} on the frontier")
    parts.append(date.today().strftime('%-d %b %Y'))
    parts.append('up and to the right wins ↗')
    return '  ·  '.join(parts)

def _place_axis_labels(ax, xlabel, ylabel):
    ax.text(
        0.5, -0.108, xlabel,
        transform=ax.transAxes,
        ha='center', va='top',
        fontsize=11.5, color=MUTED, fontweight='500',
        family='DejaVu Sans',
    )
    ax.text(
        -0.098, 0.5, ylabel,
        transform=ax.transAxes,
        ha='center', va='center',
        fontsize=11.5, color=MUTED, fontweight='500',
        rotation=90,
        family='DejaVu Sans',
    )

# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------
def _stamp_marker(ax, x, y, color, marker, size=MARKER_SIZE,
                  edge='white', edge_width=MARKER_EDGE, alpha=0.95, z=6):
    ax.scatter(x, y, s=size, c=color, marker=marker,
               alpha=alpha, edgecolors=edge, linewidths=edge_width, zorder=z)

DPI = 150
# If a stray artist still escapes after _resolve_labels' clamp, bbox_inches
# 'tight' would balloon the canvas. Cap the padding so the saved image can never
# exceed a sane size, and fail loudly rather than writing a 100 MB PNG.
MAX_PAD_IN = 1.0


def _savefig(path):
    plt.savefig(path, dpi=DPI, bbox_inches='tight', facecolor=BG,
                pad_inches=MAX_PAD_IN)


PDF_PAGES = 0


def _emit(fig, output_path, pdf=None, quiet=False):
    """Save the figure as a PNG and, when a PdfPages is supplied, add the SAME
    live figure as a PDF page.

    Both artifacts come from one figure object, so the PDF cannot drift from the
    PNGs the way a separate render pass would. Native PDF pages (not embedded
    bitmaps) keep the text vector-crisp and the file small. Closes the figure.

    Returns True when a PDF page was actually added, so the caller can register
    it in the table of contents.
    """
    global PDF_PAGES
    _savefig(output_path)
    added = False
    if pdf is not None:
        # Fixed page, not bbox 'tight': a tight bbox gives every chart its own
        # page size. tight_layout in _finish already fits the content.
        pdf.savefig(fig, dpi=DPI, facecolor=BG)
        PDF_PAGES += 1
        added = True
    plt.close(fig)
    if not quiet:
        print(f"  Saved: {os.path.basename(output_path)}")
    return added


def _resolve_labels(ax, labels, pts_x, pts_y):
    """De-overlap annotations with adjustText; markers act as keep-out zones."""
    if len(labels) < 2:
        return
    # Snapshot the intended viewport. adjust_text can push a label arbitrarily
    # far when the axes are crowded, and every savefig uses bbox_inches='tight'
    # -- which GROWS the canvas to enclose whatever ended up drawn. One escaped
    # label turned a 15.5x10.5in figure into 66x12,440in and a 116 MB PNG that
    # never finished writing.
    x_lo, x_hi = ax.get_xlim()
    y_lo, y_hi = ax.get_ylim()
    x_frac = (x_hi - x_lo) * 0.01 if x_hi > x_lo else 0.0
    y_frac = (y_hi - y_lo) * 0.01 if y_hi > y_lo else 0.0

    # adjustText 1.x keyword names. The 0.x ones (expand_points, lim,
    # precision, autoalign) are silently swallowed by 1.x, which left labels
    # sitting on top of each other. x/y make every marker a keep-out zone.
    adjust_text(
        labels,
        x=pts_x,
        y=pts_y,
        ax=ax,
        expand=(1.15, 1.6),
        force_text=(0.3, 0.6),
        force_static=(0.3, 0.6),
        ensure_inside_axes=True,
        iter_lim=1000,
    )

    for ann, ax_x, ax_y in zip(labels, pts_x, pts_y):
        tx, ty = ann.get_position()
        if x_lo <= tx <= x_hi and y_lo <= ty <= y_hi:
            continue  # already fine -- leave the de-overlap layout alone
        # Escaped the axes. Put it just outside its OWN marker, on whichever
        # side keeps it inside the viewport. Snapping every escaped label to the
        # nearest edge instead stacks them all in one unreadable corner.
        left_room = ax_x < (x_lo + x_hi) / 2
        cy = min(max(ty, y_lo + y_frac), y_hi - y_frac)
        cx = (ax_x - x_frac) if left_room else (ax_x + x_frac)
        cx = min(max(cx, x_lo + x_frac), x_hi - x_frac)
        ann.set_position((cx, cy))

def _annotate_active(ax, name, x, y, xytext, extra='', accent=False,
                     marker='o', color=None, labels=None, beaten=False):
    """Active model marker + label with hairline leader; appended to labels for adjustText.

    xytext is in DATA coordinates (not offset points) so adjustText can
    reposition labels relative to markers. beaten=True draws an off-frontier
    model: same colour and shape, but receded so the frontier reads first.
    """
    label = f"{name}   ·   {extra}" if extra else name

    if accent:
        _stamp_marker(ax, x, y, 'none', marker,
                      size=int(MARKER_SIZE * OMLX_GLOW_SCALE),
                      edge=OMLX_ACCENT, edge_width=1.8,
                      alpha=OMLX_GLOW_ALPHA, z=4)

    if color is None:
        color = COLORS.get('Standard', '#FFFFFF')
    if beaten:
        _stamp_marker(ax, x, y, color, marker, edge=MUTED, edge_width=0.9,
                      alpha=BEATEN_ALPHA, z=5)
    else:
        _stamp_marker(ax, x, y, color, marker, edge='#FFFFFF', z=6)

    ann = ax.annotate(
        label,
        (x, y),
        xytext=xytext,
        textcoords='data',
        fontsize=10,
        fontweight='400' if beaten else '600',
        color=MUTED if beaten else INK,
        ha='left' if xytext[0] > x else 'right',
        va='center',
        arrowprops=dict(
            arrowstyle='-',
            color=LEADER,
            alpha=0.5 if beaten else 0.85,
            lw=0.8,
            shrinkA=2,
            shrinkB=4,
        ),
        zorder=11 if beaten else 12,
    )
    if labels is not None:
        labels.append(ann)
    return ann

def _annotate_deleted(ax, name, x, y):
    """Deleted-model label — offset-points, not routed through adjustText."""
    ax.scatter(x, y, s=90, c=DELETED_COLOR, marker='x',
               alpha=0.65, zorder=3, linewidths=2.2)
    ax.annotate(
        name,
        (x, y),
        xytext=(6, -10),
        textcoords='offset points',
        fontsize=9,
        color=MUTED,
        ha='left',
        va='center',
        fontstyle='italic',
        zorder=9,
    )

def _draw_frontier(ax, pts, y_floor):
    """Dashed staircase through frontier points, beaten region shaded beneath.

    pts are (x, y) frontier points. Every model inside the shaded region has at
    least one frontier model that is both faster and better, which is the whole
    right-sizing question answered in one shape.
    """
    pts = sorted(pts)  # x ascending -> y descending on a frontier
    xs, ys = [0], [pts[0][1]]
    for i, (x, y) in enumerate(pts):
        xs += [x, x]
        ys += [y, pts[i + 1][1] if i + 1 < len(pts) else y_floor]
    ax.fill(xs + [0], ys + [y_floor], color=INK, alpha=0.035, lw=0, zorder=1)
    ax.plot(xs, ys, color=INK, alpha=0.5, lw=1.2, linestyle=(0, (4, 3)),
            solid_capstyle='butt', zorder=2)

def _plot_rows(ax, rows, extra, use_frontier, y_floor, y_pad):
    """Draw every row, the frontier when asked, and de-overlap the labels.

    rows are (model, x, y); extra(model, x, y) returns the label suffix.
    Returns the frontier name set, or None when no frontier was drawn.
    """
    active = [(m['name'], x, y) for m, x, y in rows if not m['deleted']]
    keep = set(pareto(active)) if use_frontier and active else None
    if keep:
        _draw_frontier(ax, [(x, y) for n, x, y in active if n in keep], y_floor)

    x_max = ax.get_xlim()[1]
    labels, pts_x, pts_y = [], [], []
    # oMLX last so its accent ring sits on top
    for m, x, y in sorted(rows, key=lambda r: r[0].get('source') == 'omlx'):
        if m['deleted']:
            _annotate_deleted(ax, m['name'], x, y)
            continue
        accent = m.get('source') == 'omlx'
        suffix = '  ·  '.join(s for s in (extra(m, x, y), 'oMLX' if accent else '') if s)
        tx = x + x_max * 0.05 if x < x_max * 0.76 else x - x_max * 0.05
        _annotate_active(ax, m['name'], x, y, (tx, y + y_pad), extra=suffix,
                         accent=accent,
                         marker=MARKERS.get(m['type'], 'o'),
                         color=COLORS.get(m['type'], COLORS['Standard']),
                         labels=labels,
                         beaten=keep is not None and m['name'] not in keep)
        pts_x.append(x)
        pts_y.append(y)

    _resolve_labels(ax, labels, pts_x, pts_y)
    return keep

def _size_extra(m, _x, _y):
    """'15.4 GB', or nothing when the size is unknown (never 'None GB')."""
    return f"{m['size_gb']} GB" if m.get('size_gb') else ''

def _finish(fig, ax, rows, keep, title, output_path, pdf):
    _style_figure(fig, ax, title, _subtitle(rows, keep))
    _legend(ax, rows, keep is not None)
    plt.tight_layout(rect=(0.0, 0.0, 1.0, 1.0), pad=2.5)
    return _emit(fig, output_path, pdf)

def _empty(fig, ax, title, what, hint, output_path):
    """Report that there is nothing to plot, and write NO file.

    This used to emit a placeholder PNG so that callers globbing `scatter_*.png`
    always found something. That promise was the bug. The placeholder is an
    error screen, not an artifact, and downstream it behaved like one: it got
    uploaded into Notion as a frontier chart, and filed beside real charts in
    the run report dirs. Seven of them accumulated and had to be found by hand
    and deleted.

    Callers now find nothing, which is the truth. The hint still prints, so the
    operator can see how to produce the missing data.
    """
    plt.close(fig)
    print(f'  skipped {os.path.basename(output_path)}: no {what} results for '
          f'these models.  To produce some:\n      {hint}')
    return False


# ---------------------------------------------------------------------------
# Plot 1 — Coding Speed × Quality
# ---------------------------------------------------------------------------
def plot_coding_speed_quality(models, output_path, label='Coding',
                              scope='Model Fleet', frontier=True, pdf=None):
    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
    title = f'{scope}   ·   {label} Speed × Quality'
    _place_axis_labels(ax,
                       'Coding Speed  (tokens / sec)',
                       'Quality Score  (0 – 1)')

    rows = [(m, m['coding_spd'], m.get('quality') or 0) for m in models
            if m.get('coding_spd') is not None]
    if not rows:
        return _empty(fig, ax, title, 'coding',
                      'python3 scripts/benchmark.py --models <id> ...', output_path)

    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    # Floor follows the data. A fixed 0.55 floor silently dropped every model
    # scoring below it off the chart -- the very models a fleet audit cuts.
    y_lo = max(0.0, min(0.55, min(ys) - 0.05))
    ax.set_xlim(0, max(xs) * 1.15)
    ax.set_ylim(y_lo, max(ys) * 1.08)

    keep = _plot_rows(ax, rows, _size_extra, frontier, y_lo, y_pad=0.022)
    return _finish(fig, ax, rows, keep, title, output_path, pdf)


# ---------------------------------------------------------------------------
# Plot 2 — Vision Speed × Output Detail
# ---------------------------------------------------------------------------
def plot_vision_speed_detail(models, output_path, scope='Model Fleet',
                             frontier=True, pdf=None):
    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
    # Y is the RUBRIC SCORE, not character count. A char count rewards padding
    # and invention -- exactly what the grounded vision rubrics exist to
    # measure -- and the skill's own guidance is that the quality axis is the
    # only trustworthy part of a vision run. build_model_config.py writes
    # vision_quality when vision scores are present; fall back to chars only
    # for a config that predates it.
    graded = any(m.get('vision_quality') is not None for m in models)
    ykey = 'vision_quality' if graded else 'vision_chars'
    title = (f'{scope}   ·   Vision Speed × '
             + ('Grounded Quality' if graded else 'Output Detail'))
    _place_axis_labels(ax,
                       'Vision Speed  (tokens / sec)',
                       'Grounded Vision Quality  (0 - 1)' if graded
                       else 'Output Detail  (characters)')

    rows = [(m, m['vision_spd'], m.get(ykey) or 0)
            for m in models if m.get('vision_spd') is not None]
    if not rows:
        return _empty(fig, ax, title, 'vision',
                      'python3 scripts/benchmark.py --vision --prompts-file prompts/vision_user.py\n'
                      '    --image-path scripts/test_image_user.png --models <id> ...',
                      output_path)

    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    # Quality lives in 0-1; pad the top so labels have room.
    y_max = (max(ys) * 1.35 if ys and max(ys) > 1.5 else 1.15)

    ax.set_xlim(0, max(xs) * 1.15)
    ax.set_ylim(0, y_max)
    if graded:
        ax.axhline(1.0, color=BG, lw=0.8, alpha=0.25, zorder=0)

    # A frontier on character count would crown the most verbose model, which
    # is the failure the rubric exists to catch. Only draw it on graded runs.
    keep = _plot_rows(ax, rows, _size_extra, frontier and graded, 0,
                      y_pad=max(y_max * 0.025, 0.02))
    return _finish(fig, ax, rows, keep, title, output_path, pdf)


# ---------------------------------------------------------------------------
# Plot 3 — Speed × Efficiency (tok/s per GB)
# ---------------------------------------------------------------------------
def plot_speed_efficiency(models, output_path, label='Coding',
                          scope='Model Fleet', pdf=None):
    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H))
    title = f'{scope}   ·   {label} Speed × Efficiency'
    _place_axis_labels(ax,
                       'Speed  (tokens / sec)',
                       'Efficiency  (tokens / sec per GB)')

    rows = []
    for m in models:
        spd = m.get('coding_spd')
        sz = m.get('size_gb')
        if spd is None or not sz:
            continue
        rows.append((m, spd, spd / sz))

    if not rows:
        return _empty(fig, ax, title, 'efficiency',
                      'efficiency needs size_gb — rebuild model-config.json with\n'
                      'python3 scripts/build_model_config.py', output_path)

    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    y_max = max(ys) * 1.18 if ys else 60

    ax.set_xlim(0, max(xs) * 1.15)
    ax.set_ylim(0, y_max)

    # No frontier here: tok/s/GB grows with tok/s, so the fastest small model
    # beats everything and the rest would all be dimmed for no information.
    keep = _plot_rows(ax, rows, lambda m, x, y: f"{y:.1f} tok/s/GB",
                      False, 0, y_pad=max(0.5, y_max * 0.04))
    return _finish(fig, ax, rows, keep, title, output_path, pdf)


# ---------------------------------------------------------------------------
# PDF assembly
# ---------------------------------------------------------------------------
def _open_pdf(output_dir, enabled, results_dir):
    """Open a PdfPages for the run, or return (None, None) when disabled.

    Returns (pdf, path). The caller owns the context manager so the PDF is
    finalised after every plot has been added.
    """
    if not enabled:
        return None, None
    path = os.path.join(output_dir or results_dir, 'scatter_plots.pdf')
    return PdfPages(path), path


# ---------------------------------------------------------------------------
# Front matter — cover, contents, summary
# ---------------------------------------------------------------------------
PDF_W, PDF_H = CHART_W, CHART_H     # same paper as the charts
# Text pages are laid out in an 8.27in column (A4 width, what the x positions
# below were drawn for), placed so x=0.10 lines up with the chart titles.
COL_W = 8.27 / PDF_W
COL_X = 0.103 - 0.10 * COL_W


def _new_text_page():
    """A blank page on the same dark paper and size as the plots.

    Returns an axes spanning the text column, with 0-1 coordinates in both
    directions, so callers position text as fractions of the column.
    """
    fig = plt.figure(figsize=(PDF_W, PDF_H))
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([COL_X, 0, COL_W, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    return fig, ax


def _cover_page(pdf, label, model_count, machine_count, generated):
    """Page 1 — what this document is."""
    fig, ax = _new_text_page()

    ax.text(0.10, 0.80, 'Model Fleet Benchmark', fontsize=34,
            fontweight='600', color=INK, va='top', ha='left',
            family='DejaVu Sans')
    ax.text(0.10, 0.725, f'{label} Speed × Quality', fontsize=19,
            color=COLORS['Vision'], va='top', ha='left', family='DejaVu Sans')

    ax.plot([0.10, 0.90], [0.685, 0.685], color=GRID, lw=1.2)

    ax.text(0.10, 0.640, generated, fontsize=13, color=INK,
            va='top', ha='left', family='DejaVu Sans')
    ax.text(0.10, 0.600,
            f'{model_count} models across {machine_count} machines',
            fontsize=13, color=MUTED, va='top', ha='left',
            family='DejaVu Sans')

    # The one methodological caveat that matters, stated up front.
    ax.text(0.10, 0.500, 'How to read this', fontsize=13, fontweight='600',
            color=INK, va='top', ha='left', family='DejaVu Sans')
    body = [
        'Speed is only comparable within one machine. tok/s is a fact about the',
        'hardware as much as the model, so each machine gets its own section and',
        'its own ranking. Quality is comparable everywhere: it comes from',
        'deterministic pattern matchers, not from a judge model.',
        '',
        'The cross-machine comparison, where it exists, is the only honest way to',
        'see what quantization and runtime do to the same weights.',
    ]
    yy = 0.460
    for line in body:
        ax.text(0.10, yy, line, fontsize=11, color=MUTED, va='top', ha='left',
                family='DejaVu Sans')
        yy -= 0.026

    ax.text(0.10, 0.10,
            'Generated by benchmark-model-fleet  ·  generate_scatter.py',
            fontsize=9, color=MUTED, va='bottom', ha='left',
            family='DejaVu Sans')

    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def _contents_page(pdf, entries):
    """Page 2 — table of contents with dotted leaders.

    entries: list of (level, text, page_number); level 0 is a machine heading.
    """
    fig, ax = _new_text_page()
    ax.text(0.10, 0.90, 'Contents', fontsize=24, fontweight='600', color=INK,
            va='top', ha='left', family='DejaVu Sans')
    ax.plot([0.10, 0.90], [0.855, 0.855], color=GRID, lw=1.0)

    y = 0.815
    for level, text, page in entries:
        if level == 0:
            if y < 0.815 - 0.001:      # a little air before each section
                y -= 0.022
            ax.text(0.10, y, text, fontsize=12.5, fontweight='600', color=INK,
                    va='top', ha='left', family='DejaVu Sans')
            y -= 0.034
        else:
            ax.text(0.145, y, text, fontsize=10.5, color=MUTED, va='top',
                    ha='left', family='DejaVu Sans')
            # Dotted leader from the end of the text to the page number.
            ax.plot([0.145 + min(len(text) * 0.0052 + 0.02, 0.55), 0.865],
                    [y - 0.007, y - 0.007],
                    color=GRID, lw=0.9, linestyle=(0, (1, 3)))
            ax.text(0.90, y, str(page), fontsize=10.5, color=INK, va='top',
                    ha='right', family='DejaVu Sans')
            y -= 0.028

    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def _machine_stats(subset):
    """Per-machine summary numbers, computed the same way the plots read them."""
    coding = [m for m in subset if m.get('coding_spd') is not None]
    vision = [m for m in subset if m.get('vision_spd') is not None]
    sized = [m for m in subset
             if m.get('coding_spd') is not None and m.get('size_gb')]
    scored = [m for m in coding if m.get('quality') is not None]
    top_q = max((m['quality'] for m in scored), default=None)
    # Same rows the speed x quality chart feeds to pareto(), so the summary and
    # the chart always name the same frontier.
    live = [(m['name'], m['coding_spd'], m.get('quality') or 0)
            for m in coding if not m['deleted']]
    by_name = {m['name']: m for m in coding}

    return {
        'n': len(subset),
        'n_coding': len(coding),
        'n_vision': len(vision),
        'n_sized': len(sized),
        'frontier': sorted((by_name[n] for n in pareto(live)),
                           key=lambda m: (-(m.get('quality') or 0), m['name'])),
        # Every model tied for the top score, not whichever max() met first.
        'best_q': sorted((m for m in scored if m['quality'] == top_q),
                         key=lambda m: m['name']),
        'best_eff': (max(sized, key=lambda m: m['coding_spd'] / m['size_gb'])
                     if sized else None),
        'total_gb': sum(m.get('size_gb') or 0 for m in sized) or None,
        'avg_spd': (sum(m['coding_spd'] for m in coding) / len(coding)
                    if coding else None),
        'avg_q': (sum(m['quality'] for m in scored) / len(scored)
                  if scored else None),
    }


def _summary_page(pdf, buckets, label, mixed_titles=()):
    """Page 3 — the verdict, per machine, before any chart.

    Single-machine groups list their coding frontier (the models nothing else
    beats on both speed and quality -- the keep list) and the best tok/s per GB.

    mixed_titles: groups that span more than one machine. Every speed-derived
    line is suppressed for them -- mean tok/s, the frontier, best tok/s/GB --
    because comparing speed across hardware is exactly what the per-machine
    split exists to prevent. Only quality, which is hardware-neutral, is ranked.
    The disk total is reported with the count of models actually measured,
    since a group can mix machines whose sizes were only readable on one host.
    """
    fig, ax = _new_text_page()
    ax.text(0.10, 0.90, 'Summary', fontsize=24, fontweight='600', color=INK,
            va='top', ha='left', family='DejaVu Sans')
    ax.plot([0.10, 0.90], [0.855, 0.855], color=GRID, lw=1.0)

    # Build every row first, then space them to fit the page: the frontier
    # makes each machine's block a variable height.
    STEP = {'machine': 0.030, 'head': 0.030, 'note': 0.026, 'row': 0.026,
            'gap': 0.022}
    rows = []
    for machine, subset in buckets.items():
        if not subset:
            continue
        s = _machine_stats(subset)
        mixed = machine in mixed_titles
        rows.append(('machine', machine))

        head = f"{s['n']} models"
        if s['total_gb']:
            # Never present a partial total as if it covered the whole group.
            if s['n_sized'] < s['n']:
                head += f"  ·  {s['total_gb']:.1f} GB across {s['n_sized']} sized"
            else:
                head += f"  ·  {s['total_gb']:.1f} GB on disk"
        if s['avg_spd'] is not None and not mixed:
            head += f"  ·  mean {s['avg_spd']:.1f} tok/s"
        if s['avg_q'] is not None:
            head += f"  ·  mean quality {s['avg_q']:.2f}"
        rows.append(('head', head))

        if mixed:
            rows.append(('note', 'speed not compared — spans multiple machines'))
            if s['best_q']:
                names = [m['name'] for m in s['best_q']]
                who = (', '.join(names) if len(names) <= 2
                       else f"{names[0]} and {len(names) - 1} more")
                rows.append(('row', 'Best quality',
                             f"{who}  (q {s['best_q'][0]['quality']:.2f})"))
        else:
            for i, m in enumerate(s['frontier']):
                rows.append(('row', 'Frontier' if i == 0 else '',
                             f"◆ {m['name']}   q {m.get('quality') or 0:.2f}  ·  "
                             f"{m['coding_spd']:.1f} tok/s"))
            m = s['best_eff']
            if m is not None:
                rows.append(('row', 'Best efficiency',
                             f"{m['name']}  ({m['coding_spd'] / m['size_gb']:.1f} tok/s/GB)"))
        rows.append(('gap',))

    top, floor = 0.805, 0.135
    need = sum(STEP[r[0]] for r in rows)
    k = min(1.0, (top - floor) / need) if need else 1.0

    y = top
    for r in rows:
        kind = r[0]
        if kind == 'machine':
            ax.text(0.10, y, r[1], fontsize=14, fontweight='600', color=INK,
                    va='top', ha='left', family='DejaVu Sans')
        elif kind == 'head':
            ax.text(0.10, y, r[1], fontsize=10.5, color=MUTED, va='top',
                    ha='left', family='DejaVu Sans')
        elif kind == 'note':
            ax.text(0.145, y, r[1], fontsize=9.5, color=MUTED, va='top',
                    ha='left', style='italic', family='DejaVu Sans')
        elif kind == 'row':
            ax.text(0.145, y, r[1], fontsize=10.5, color=MUTED, va='top',
                    ha='left', family='DejaVu Sans')
            ax.text(0.33, y, r[2], fontsize=10.5, color=INK, va='top',
                    ha='left', family='DejaVu Sans')
        y -= STEP[kind] * k

    ax.text(0.10, 0.10,
            'Quality is a deterministic rubric score, 0–1. The frontier is every '
            'model no other model on that machine beats on both speed and quality.',
            fontsize=9, color=MUTED, va='bottom', ha='left',
            family='DejaVu Sans')

    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def _has_coding(ms):
    return any(m.get('coding_spd') is not None for m in ms)


def _has_vision(ms):
    return any(m.get('vision_spd') is not None for m in ms)


def _has_efficiency(ms):
    return any(m.get('coding_spd') is not None and m.get('size_gb') for m in ms)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys as _sys
    from collections import OrderedDict as _OrderedDict
    import machines as M
    parser = argparse.ArgumentParser(
        description='Generate scatter plots — dark dramatic edition')
    parser.add_argument('--results-dir',
                        default=os.path.expanduser('~/.hermes/benchmark_results'))
    parser.add_argument('--output-dir', default=None)
    parser.add_argument('--model-config', default=None,
                        help='JSON file with model metadata (name, size_gb, type, deleted)')
    parser.add_argument('--label', default='Coding',
                        help='Task family shown in plot titles and filenames')
    parser.add_argument('--per-machine', action='store_true',
                        help='Also emit one set of plots per machine '
                             '(scatter_<label>_studio.png etc). tok/s is not '
                             'comparable across hardware, so a combined speed '
                             'axis mixes the machines into one ranking.')
    parser.add_argument('--combined-only', action='store_true',
                        help='Suppress the all-machines plots (implied by --per-machine '
                             'unless you want both).')
    parser.add_argument('--no-pdf', action='store_true',
                        help='Write only the individual PNGs; skip the multipage '
                             'scatter_plots.pdf. PDF is on by default.')
    parser.add_argument('--preview-pages', default=None, metavar='DIR',
                        help='Render the PDF front matter (cover, contents, '
                             'summary) to numbered PNGs in DIR and exit without '
                             'drawing charts. Layout check on a box with no PDF '
                             'renderer: text overlap and page-number drift are '
                             'invisible in the .pdf itself.')
    args = parser.parse_args()

    output_dir = args.output_dir or args.results_dir
    os.makedirs(output_dir, exist_ok=True)

    config_path = args.model_config or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'references',
        'model-config.json')
    models = []
    if os.path.exists(config_path):
        with open(config_path) as f:
            models = json.load(f)
    else:
        print(f'WARNING: model config not found at {config_path} — plots will be empty')

    registry = M.load_machines()
    # Machine identity comes from the `endpoint` column the CSVs already carry
    # (measured fact), falling back to the registry's id_prefix only for entries
    # that have no benchmark rows. Prefix-only grouping silently invents a
    # phantom machine: `sushi` carries no `ms-` prefix on purpose (user's call),
    # so it matched no prefix and the Studio's biggest model was plotted under
    # an "Unassigned models" group that is not a box. machines.group_rows() has
    # always resolved by endpoint; this makes the plots agree with the report.
    endpoint_of = {}
    for csv_path in sorted(glob.glob(os.path.join(args.results_dir, '*_bench_*.csv'))):
        try:
            with open(csv_path, newline='') as fh:
                for r in csv.DictReader(fh):
                    if r.get('model') and r.get('endpoint'):
                        endpoint_of.setdefault(r['model'], r['endpoint'])
        except OSError:
            continue
    buckets = _OrderedDict()
    for m in models:
        name = (M.machine_for_endpoint(endpoint_of.get(m['name']), registry)
                or M.machine_for_model(m['name'], registry) or 'unassigned')
        buckets.setdefault(name, []).append(m)
    # A frontier across machines would rank the hardware, not the models, so
    # the combined plots only get one when a single machine is involved. The
    # same test decides whether the summary page may average tok/s.
    one_box = len(buckets) <= 1
    # Real machines only: not the combined group, not the unassigned bucket.
    n_machines = sum(1 for b in buckets if b != 'unassigned')

    slug = args.label.lower().replace(' ', '_')
    PDF_PAGES = 0
    pdf, pdf_path = _open_pdf(output_dir, not args.no_pdf, args.results_dir)

    # ---------------------------------------------------------------- plan
    # Build the chart plan up front so the table of contents can carry real
    # page numbers. Page order: 1 cover, 2 contents, 3 summary, then charts.
    COMBINED = 'All Machines  ·  combined'
    groups = []
    if not args.combined_only:
        groups.append({'title': COMBINED, 'tag': '', 'subset': models,
                       'scope': 'Model Fleet', 'frontier': one_box})

    if args.per_machine:
        for machine, subset in buckets.items():
            if not subset:
                continue
            scope = 'Unassigned models' if machine == 'unassigned' else machine
            groups.append({
                'title': scope,
                'tag': machine.lower().replace(' ', '_').replace('.', ''),
                'subset': subset,
                # Machine name leads the chart title: PDF pages carry no
                # filename, so a bare "Speed x Quality" would be ambiguous.
                'scope': scope,
                'frontier': True,
            })

    # Assign page numbers, skipping axes a group has no data for.
    page = 4                       # 1 cover + 2 contents + 3 summary
    for g in groups:
        g['charts'] = []
        if _has_coding(g['subset']):
            g['charts'].append(('coding', page)); page += 1
        if _has_vision(g['subset']):
            g['charts'].append(('vision', page)); page += 1
        if _has_efficiency(g['subset']):
            g['charts'].append(('efficiency', page)); page += 1

    # Any group spanning machines -- not only when --per-machine is passed.
    mixed = {COMBINED} if not one_box else set()
    buckets_od = _OrderedDict((g['title'], g['subset']) for g in groups)

    def _toc_entries():
        ent = []
        for g in groups:
            ent.append((0, g['title'], None))
            # Must match plot_vision_speed_detail's own title, which falls back
            # to Output Detail when the config carries no rubric scores.
            graded = any(m.get('vision_quality') is not None for m in g['subset'])
            for kind, pg in g['charts']:
                ent.append((1, {
                    'coding': f"{args.label} Speed × Quality",
                    'vision': 'Vision Speed × '
                              + ('Grounded Quality' if graded else 'Output Detail'),
                    'efficiency': f"{args.label} Speed × Efficiency",
                }[kind], pg))
        return ent

    # ------------------------------------------------------------- preview
    # Same plan, same page functions, PNG sink instead of PdfPages -- so what
    # is inspected is what the PDF will contain.
    if args.preview_pages:
        os.makedirs(args.preview_pages, exist_ok=True)

        class _PngSink:
            def __init__(self, d):
                self.d, self.n = d, 0

            def savefig(self, fig, **kw):
                self.n += 1
                p = os.path.join(self.d, f'page{self.n}.png')
                fig.savefig(p, dpi=DPI, facecolor=BG)
                plt.close(fig)
                print(f'  wrote {p}')

        sink = _PngSink(args.preview_pages)
        _cover_page(sink, args.label, len(models), n_machines,
                    datetime.now().strftime('%d %B %Y, %H:%M'))
        _contents_page(sink, _toc_entries())
        _summary_page(sink, buckets_od, args.label, mixed)
        print(f'\nFront matter previewed to {args.preview_pages}/ '
              f'(charts would run to page {page - 1})')
        _sys.exit(0)

    print('Generating dark plots…')
    try:
        if pdf is not None:
            _cover_page(pdf, args.label, len(models), n_machines,
                        datetime.now().strftime('%d %B %Y, %H:%M'))
            # Contents is written before the charts but needs their page
            # numbers, which the plan above already fixed.
            _contents_page(pdf, _toc_entries())
            _summary_page(pdf, buckets_od, args.label, mixed)

        for g in groups:
            if g['tag']:
                print(f"\nPer-machine: {g['title']} ({len(g['subset'])} models)")
            subset, scope = g['subset'], g['scope']
            stem = f"_{g['tag']}" if g['tag'] else ''
            plot_coding_speed_quality(
                subset, os.path.join(output_dir, f'scatter_{slug}{stem}.png'),
                args.label, scope=scope, frontier=g['frontier'], pdf=pdf)
            plot_vision_speed_detail(
                subset, os.path.join(output_dir, f'scatter_vision{stem}.png'),
                scope=scope, frontier=g['frontier'], pdf=pdf)
            plot_speed_efficiency(
                subset,
                os.path.join(output_dir, f'scatter_{slug}_efficiency{stem}.png'),
                args.label, scope=scope, pdf=pdf)
    finally:
        if pdf is not None:
            pdf.close()
            print(f"\nPDF: scatter_plots.pdf ({PDF_PAGES + 3} pages: "
                  f"3 front matter + {PDF_PAGES} charts)")

    print('\nAll plots generated.')
