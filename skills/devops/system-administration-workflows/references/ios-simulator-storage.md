# iOS Simulator storage management (DEV-381, 2026-10-22)

Simulator cruft is a MacBook (prasta) problem, never the Studio. Tool: `~/bin/simulator-space.sh` (MacBook), weekly LaunchAgent `local.simulator-space.prune` (Sunday 07:30, prune mode). Config mirrors to backup-dotfiles-macbook via daily sync.

## Key facts

- **Measuring runtime sizes:** runtime volumes under `/Library/Developer/CoreSimulator/Volumes/*` are sealed read-only APFS mounts — `du -sh` reports LOGICAL size and overstates. Use `diskutil info <vol>` → Volume Used Space for real host allocation, or `df` on the Data volume before/after.
- **Registered disk images vs installed runtimes:** `xcrun simctl runtime list` shows only registered *disk images* (downloads / staged bundles) in the secure storage area; `xcrun simctl list runtimes` shows *installed* runtimes (what the simulator can boot). `simctl runtime delete <id>` operates ONLY on registered disk images. A legacy-installed runtime whose image was consumed at install cannot be deleted via CLI — `runtime delete` returns "No runtime disk images or bundles found matching…" even with the right bundle identifier / bundlePath / `--outdated` / `--notUsedSinceDays`.
- **Removing a legacy installed runtime (no CLI path):** Xcode → Settings → Components → remove, OR manual: `sudo diskutil unmount diskN` for the runtime volume and its SimRuntimeBundle cryptex volume, `sudo rm -rf` the now-empty mountpoint dir and the cryptex bundle dir (`/Library/Developer/CoreSimulator/Cryptex/Images/bundle/SimRuntimeBundle-<UUID>`), then `launchctl kickstart -k gui/$(id -u)/com.apple.CoreSimulator.CoreSimulatorService`. No passwordless sudo on the MacBook — a manual step for Patrick.
- **What the prune covers:** runtimes older than the newest installed major (only when a registered disk image exists), `simctl delete unavailable` (orphan stubs), DerivedData entries >30 days (full sweep via `--force`). Never touches the newest runtime. Logs to `~/Library/Logs/simulator-space.log` + `.launchd.log`.

## Numbers seen 2026-10-22 (MacBook)

- iOS 18.6: 20.2 GB runtime volume + 8.2 GB cryptex bundle (~29 GB, removed manually by Patrick)
- iOS 27.0: 18.0 GB (current, keep)
- Device data: 3.4 GB in one heavy sim (erase via `simctl erase <uuid>` keeps device, wipes data)
- DerivedData / Archives / CodingAssistant: 5.0 / 1.4 / 1.7 GB
- Prevention rule: one runtime per major max; delete the previous major the day a new Xcode/iOS cycle drops.
