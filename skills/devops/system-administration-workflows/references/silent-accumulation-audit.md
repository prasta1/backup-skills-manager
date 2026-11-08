# Silent Accumulation Audit

Directories that grow without being asked, on both hosts. Use this when
"things keep piling up" or before any disk-pressure investigation — these are
the first places to look, because each one accumulates by design and none of
them ever self-reports.

## The rule

**Both the MacBook (prasta) and the Mac Studio (macstudio) are candidates for
cruft investigation.** Check the same list on each. Paths below are written
per-host; substitute the other home dir when checking the other box. Audit
locally on each machine (the Studio's paths are not visible from the MacBook
and vice versa — run the audit via `ssh macbook` for the MBP side).

## Known accumulating directories

### Hermes desktop app (MacBook side — `/Users/prasta/Library/Application Support/Hermes/`)

| Directory | What accumulates | Audit |
|---|---|---|
| `composer-images/` | A snapshot of every `::preview` render in chat. One session that iterated on a widget 6 times left 6 near-identical HTML/PNG copies. | `ls -lat | head` — look for runs of same-sized files with timestamps minutes apart |
| `composer-pastes/` | Every paste made into chat (`.txt`). | `ls -lat | wc -l`, `du -sh` |

### Hermes runtime (both hosts — `~/.hermes/`)

| Directory | What accumulates | Audit |
|---|---|---|
| `cache/scratch/` | Temp files and probes. Auto-pruned after 24h — if this is large, something recent leaked. | `du -sh` |
| `logs/` | llama-swap, agent, gateway and update logs. **Rotation is partial:** the eight logs named in `/etc/newsyslog.d/hermes.conf` size-rotate at 5 MB / keep 3 / gzip. Cron run logs, clef-serve stdout+stderr and launchd agent output are NOT covered — hand-rotate those. | `du -sh`; `ls -lat | head` for stale giants; read `/etc/newsyslog.d/hermes.conf` for what's covered |
| `benchmark_results/` | Every bench run's CSVs, PNGs, PDFs. | `du -sh`; count run dirs |
| `backups/` | Dated archives (certifi bumps, hindsight dump, etc.). Only grows. | `ls -lat | head`; check age of oldest |
| `benchy/` | Per-run JSON/MD results from llama-benchy. | `du -sh` |
| `outputs/` | **LEGACY since 2026-11-01** — the canonical spot is now iCloud `Hermes/<category>/`. Still holds ~1.5 GB of older artifacts plus hardcoded Ionga render/QC scripts. Not cruft; review before deleting. | `du -sh`; `ls -lat` |

### Third-party caches (both hosts)

| Directory | What accumulates | Audit |
|---|---|---|
| `~/.cache/huggingface/hub` | **The real HF cache** (~150 GB on the Studio). Has its own skill (`hf-cache-hygiene`); `hf cache prune` handles it. `~/.hf/hub` also exists but is vestigial — one whisper repo, ~1.5 GB — so don't mistake it for the main store. | `hf cache list`; `du -sh` |
| `~/.cache/llama-benchy/` | Sherlock Holmes corpus + cached slices, keyed by URL/tokenizer. | `du -sh` |
| `~/Library/Caches/` | General macOS/app caches. Usually handled by the OS, but worth a `du -sh` glance on disk pressure. | `du -sh ~/Library/Caches` |

## Audit procedure (diagnose, don't act)

1. **Pick a host.** Run the audit on the Studio for its paths, `ssh macbook` for the MBP's.
2. **For each directory above**, run the audit command. Report total size and,
   for file-pile dirs (composer-images, composer-pastes, benchmark_results),
   the count and a `ls -lat | head` sample so the buildup is visible.
3. **Flag runs of near-duplicates** — same size, timestamps minutes apart,
   same stem. That's the signature of iteration snapshots (the composer-images
   case: 6 copies of one evolving widget).
4. **Stop and report.** Build the candidate list with sizes and what each item
   is for. Do not delete anything without explicit confirmation.

## Cleanup workflow (after confirmation)

Same shape as `hf-cache-hygiene` — audit, dry-run, confirm, prune, verify.

1. **Report what would be deleted** (paths, sizes, why it's safe: e.g. the live
   widget file lives in iCloud `Hermes/<category>/`, so composer-images copies
   are stale history).
2. **Get explicit OK** before `rm` / emptying a dir. Nothing here is
   irreversible-friendly: these are the app's own snapshots, not scratch.
3. **Prefer the smallest reversible step** — e.g. keep only the newest
   composer-image per session rather than nuking the whole dir, or move to a
   dated archive folder before deleting.
4. **Verify after** — confirm the live artifact (e.g. `fleet-inventory.html`
   in iCloud `Hermes/<category>/`) is untouched and still renders, and that
   the cleared dir is back to expected size.

## Pitfalls

- **Composer snapshots are not the source of truth.** The live widget/file in
  iCloud `Hermes/<category>/` (Studio) is authoritative; `composer-images` on
  the MacBook is the desktop app's render history. Deleting the snapshots never
  breaks the live file — verify the live path exists before deleting its
  copies.
- **Cross-host confusion.** The Studio has its own `~/.hermes` and the MacBook
  has its own. A path that exists on one may not on the other; a directory
  that's huge on one may be empty on the other. Audit per-host, never assume
  the two look alike.
- **`~/.hermes/outputs/` is LEGACY, not canonical.** Since 2026-11-01 the
  canonical spot for project output is iCloud `Hermes/<category>/`. The dir
  still holds ~1.5 GB of older artifacts and some hardcoded Ionga render/QC
  scripts, so it isn't cruft — review before deleting, but send new output to
  iCloud. Its own `README.md` still calls itself canonical; that header is
  stale.
- **Scratch auto-prunes, but only after 24h.** A large scratch dir means
  something recent was left there deliberately — check what it is before
  assuming it's stale.
- **logs/ rotation is partial.** `/etc/newsyslog.d/hermes.conf` size-rotates
  llama-swap.out.log, gateway*.log, agent.log, errors.log, mcp-stderr.log and
  gui.log at 5 MB / keep 3 / gzip. The uncovered logs — cron runs, clef-serve
  stdout+stderr, launchd agent output — still grow unbounded and need hand
  rotation. Still the first place to reclaim space with zero risk. (Splash logs
  no longer exist; that engine was retired 2026-11-05.)
