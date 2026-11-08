## Status (triage 2026-10-01)

Reviewed with Patrick, see `docs/superpowers/plans/2026-10-01-mbp-skills-archive-triage.md`. Codes: `promoted` = copied into `skills/` (10), `folded` = a few lines lifted into hermes-infrastructure or embedding-path-audit (3 + 1 duplicate), `postponed` = still in the archive dir awaiting a decision (1), `discarded` = removed from the working tree; recover from git history at the commit that deleted the archive (157).

## Contents

### apple (4)

- `apple/macos-app-launcher` `discarded` — Create clickable macOS application bundles (.app) that launch CLI tools, servers, or dashboar...
- `apple/macos-display-control` `discarded` — DDC/CI monitor control on macOS via m1ddc.
- `apple/macos-launch-agents` `discarded` — Set up macOS Launch Agents for persistent background services — auto-start on login, auto-res...
- `apple/macos-local-ocr` `discarded` — Use when vision_analyze fails; OCR images locally on macOS.

### autonomous-ai-agents (9)

- `autonomous-ai-agents/claude-code` `discarded` — Delegate coding to Claude Code CLI (features, PRs).
- `autonomous-ai-agents/codex` `discarded` — Delegate coding to OpenAI Codex CLI (features, PRs).
- `autonomous-ai-agents/computer-use` `discarded` — Drive the desktop in the background without stealing focus.
- `autonomous-ai-agents/hermes-agent` `discarded` — Use, configure, theme, extend, and orchestrate Hermes Agent.
- `autonomous-ai-agents/hermes-memory-hygiene` `discarded` — Audit and maintain Hermes memory layers: native identity files, Hindsight/Honcho config, hono...
- `autonomous-ai-agents/hermes-memory-providers` `discarded` — >
- `autonomous-ai-agents/hermes-model-picker` `folded` — Hide provider/model rows from Hermes model pickers.
- `autonomous-ai-agents/kanban-codex-lane` `discarded` — Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane whi...
- `autonomous-ai-agents/opencode` `discarded` — Delegate coding to OpenCode CLI (features, PR review).

### business (2)

- `business/indagate-strategy` `postponed` — Run indigate.ai-specific strategy and BD workflows.
- `business/venture-target-profiles` `discarded` — Build target customer profiles for venture evaluation.

### creative (16)

- `creative/architecture-diagram` `discarded` — Dark-themed SVG architecture/cloud/infra diagrams as HTML.
- `creative/ascii-art` `discarded` — ASCII art: pyfiglet, cowsay, boxes, image-to-ascii.
- `creative/ascii-video` `discarded` — ASCII video: convert video/audio to colored ASCII MP4/GIF.
- `creative/baoyu-infographic` `discarded` — Infographics: 21 layouts x 21 styles (信息图, 可视化).
- `creative/claude-design` `discarded` — Design one-off HTML artifacts (landing, deck, prototype).
- `creative/design-md` `discarded` — Author/validate/export Google's DESIGN.md token spec files.
- `creative/excalidraw` `discarded` — Hand-drawn Excalidraw JSON diagrams (arch, flow, seq).
- `creative/html-artifact` `discarded` — Build self-contained HTML files to explain, plan, or review.
- `creative/humanizer` `discarded` — Humanize text: strip AI-isms and add real voice.
- `creative/manim-video` `discarded` — Manim CE animations: 3Blue1Brown math/algo videos.
- `creative/p5js` `discarded` — p5.js sketches: gen art, shaders, interactive, 3D.
- `creative/popular-web-designs` `discarded` — 54 real design systems (Stripe, Linear, Vercel) as HTML/CSS.
- `creative/pretext` `discarded` — Build creative browser demos with DOM-free text layout.
- `creative/sketch` `discarded` — Throwaway HTML mockups: 2-3 design variants to compare.
- `creative/songwriting-and-ai-music` `discarded` — Songwriting craft and Suno AI music prompts.
- `creative/touchdesigner-mcp` `discarded` — Control TouchDesigner via twozero MCP.

### devops (23)

- `devops/cloudflare-pages` `discarded` — Cloudflare Pages static site deployment and troubleshooting.
- `devops/cloudflare-pages-deploy` `discarded` — Deploy static sites to Cloudflare Pages from HTML or GitHub.
- `devops/cloudflare-pages-deployment` `promoted` — Deploy static sites to Cloudflare Pages.
- `devops/config-file-forensics` `discarded` — Identify an unknown config's owning tool and live state.
- `devops/cron-jobs` `discarded` — Schedule Hermes cron jobs with multi-platform delivery — model selection, testing, troublesho...
- `devops/data-archive-restructuring` `discarded` — Safely restructure git-tracked data archive repos.
- `devops/ddc-monitor-control` `discarded` — Control monitors via DDC/CI from the macOS command line.
- `devops/docker-compose-gpu-vendors` `discarded` — Multiple GPU vendor Docker Compose deployment patterns.
- `devops/docker-services-on-synology` `promoted` — Deploy and manage Docker-based services on Synology NAS — setup, file transfer, Container Man...
- `devops/git-repo-remote-management` `discarded` — Manage git remotes: rename repos, update URLs, sync forks. Also covers backing up git repos o...
- `devops/git-stash-cleanup` `discarded` — Use when cleaning stale git stashes or autostash debris.
- `devops/global-cli-recovery` `discarded` — Use when a CLI vanished from PATH but its state survived.
- `devops/go-local-services` `discarded` — Run repo-built Go binaries as macOS Launch Agents.
- `devops/lms-provider-setup` `discarded` — Wire multiple LM Studio instances into Hermes as providers with consistent naming. Each machi...
- `devops/local-inference` `discarded` — Local LLM inference: serve, providers, multi-machine, diag.
- `devops/local-studio-controller` `discarded` — Manage Local Studio controller: provider API and lifecycle.
- `devops/macos-ddc` `discarded` — DDC/VCP display control on macOS Apple Silicon.
- `devops/monorepo-npm-audit-remediation` `discarded` — Fix npm audit vulnerabilities in monorepos when fix crashes.
- `devops/multi-machine-inference-setup` `discarded` — Complete workflow for deploying Hermes across multiple machines — inference failover, gateway...
- `devops/open-webui-management` `discarded` — Audit, configure, and troubleshoot Open WebUI installations — pip/venv, launchd, SQLite DB, e...
- `devops/sdlc-review` `discarded` — Review Kanban handoffs and route verified outcomes.
- `devops/tool-evaluation` `promoted` — Use when Patrick asks how a tool compares to what we have.
- `devops/unsloth-studio-ops` `promoted` — Audit/upgrade Unsloth Studio on the Mac Studio. Use on update/review/config asks.

### education (1)

- `education/ccb-edu` `discarded` — Workshop design for non-technical public audiences.

### email (3)

- `email/email-inbox-triage` `discarded` — Triage an inbox: prioritize threads, draft replies safely.
- `email/himalaya` `discarded` — Himalaya CLI: IMAP/SMTP email from terminal (v2.0.0+).
- `email/himalaya-email-setup` `discarded` — Himalaya email setup with pass and GPG, including v2 config format and decryption failure rec...

### finance (1)

- `finance/financial-export` `promoted` — Convert OFX/QFX exports to analysis-ready CSVs.

### github (7)

- `github/github-auth` `discarded` — GitHub auth setup: HTTPS tokens, SSH keys, gh CLI login.
- `github/github-code-review` `discarded` — Review PRs: diffs, inline comments via gh or REST.
- `github/github-issue-to-pr` `discarded` — Carry a GitHub issue to a verified PR with honest CI state.
- `github/github-issues` `discarded` — Create, triage, label, assign GitHub issues via gh or REST.
- `github/github-pr-workflow` `discarded` — GitHub PR lifecycle: branch, commit, open, CI, merge.
- `github/github-repo-audit` `discarded` — Scan local git checkouts against GitHub state and fix drift.
- `github/github-repo-management` `discarded` — Clone/create/fork repos; manage remotes, releases.

### hermes (1)

- `hermes/hermes-model-picker-filtering` `folded` — Suppress providers from the Hermes model picker UI.

### macos (5)

- `macos/homebrew-maintenance` `discarded` — Audit, clean, and maintain Homebrew taps and packages.
- `macos/macos-dotfolder-triage` `discarded` — Triage a stray macOS dotfolder for deletion, move, or keep.
- `macos/macos-filesystem-search` `discarded` — search_files times out on big macOS dirs. Use find -prune.
- `macos/non-brew-software-audit` `discarded` — Find installed software that Homebrew could manage instead.
- `macos/package-manager-cli-recovery` `discarded` — Recover a CLI whose package-manager scope was wiped.

### mcp (2)

- `mcp/mcp-server-installation` `discarded` — Install and wire self-hosted / npm MCP servers into Hermes.
- `mcp/native-mcp` `discarded` — MCP client: connect servers, register tools (stdio/HTTP).

### media (3)

- `media/gif-search` `discarded` — Search/download GIFs from Tenor via curl + jq.
- `media/songsee` `discarded` — Audio spectrograms/features (mel, chroma, MFCC) via CLI.
- `media/youtube-content` `discarded` — YouTube transcripts to summaries, threads, blogs.

### mlops (11)

- `mlops/evaluation/evaluating-llms-harness` `discarded` — lm-eval-harness: benchmark LLMs (MMLU, GSM8K, etc.).
- `mlops/evaluation/weights-and-biases` `discarded` — W&B: log ML experiments, sweeps, model registry, dashboards.
- `mlops/huggingface-hub` `promoted` — HuggingFace hf CLI: search/download/upload models, datasets.
- `mlops/inference/llama-cpp` `discarded` — llama.cpp local GGUF inference + HF Hub model discovery.
- `mlops/inference/obliteratus` `discarded` — OBLITERATUS: abliterate LLM refusals (diff-in-means).
- `mlops/inference/serving-llms-vllm` `discarded` — vLLM: high-throughput LLM serving, OpenAI API, quantization.
- `mlops/local-inference-serving` `folded` — Diagnose live llama-swap server: running, dashboard, caller. Also covers local-vs-OpenRouter ...
- `mlops/open-webui-admin` `discarded` — Configure and maintain Open WebUI — multi-endpoint connections, RAG, web search, naming, and ...
- `mlops/open-webui-ui-customization` `discarded` — Hide or remove Open WebUI UI elements via CSS.
- `mlops/research/dspy` `discarded` — DSPy: declarative LM programs, auto-optimize prompts, RAG.
- `mlops/self-hosted-llm-frontend` `discarded` — >-

### note-taking (1)

- `note-taking/obsidian` `discarded` — Read, search, create, and edit notes in the Obsidian vault.

### productivity (24)

- `productivity/airtable` `discarded` — Airtable REST API via curl. Records CRUD, filters, upserts.
- `productivity/box` `discarded` — Box manages cloud files, sharing, search, and metadata.
- `productivity/collective-wisdom-install` `discarded` — Browse, install, or share team skills with consent.
- `productivity/data-pipeline` `discarded` — Ingest LinkedIn connections CSV exports into an Obsidian vault as structured markdown contact...
- `productivity/document-to-action-items` `discarded` — Extract cited obligations, deadlines, tasks from documents.
- `productivity/docx` `discarded` — Create, read, edit, template, and review Word .docx files.
- `productivity/finance-export-converters` `discarded` — Convert OFX/QFX financial exports to CSV for analysis.
- `productivity/ghostty` `discarded` — Configure Ghostty terminal emulator on macOS. Use when setting font size, theme, shell option...
- `productivity/google-workspace` `discarded` — Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python.
- `productivity/investment-export-converter` `discarded` — Convert OFX/QFX/QBO investment exports to CSV. One sentence.
- `productivity/job-search-pipeline` `promoted` — Scan, rank, and review career-ops pipeline results.
- `productivity/job-search-warm-outreach` `promoted` — Draft warm outreach to former customers for intro requests.
- `productivity/linear` `discarded` — Linear: manage issues, projects, teams via GraphQL + curl.
- `productivity/maps` `discarded` — Geocode, POIs, routes, timezones via OpenStreetMap/OSRM.
- `productivity/meeting-action-items` `discarded` — Turn meeting notes into cited decisions, owners, tickets.
- `productivity/notion` `discarded` — Notion API + ntn CLI: pages, databases, markdown, Workers.
- `productivity/ocr-and-documents` `discarded` — Extract text from PDFs/scans (pymupdf, marker-pdf).
- `productivity/pdf` `discarded` — PDF files: create, read, merge, fill, OCR, edit text.
- `productivity/powerpoint` `discarded` — Create, read, edit .pptx decks with python-pptx.
- `productivity/product-price-monitor` `discarded` — Watch product, flight, or listing prices; alert on target.
- `productivity/session-librarian` `discarded` — Organize sessions by prompt: find, rename, archive, prune.
- `productivity/teams-meeting-pipeline` `discarded` — Teams meeting summaries, job replay, Graph subscriptions.
- `productivity/weekly-review-planning` `discarded` — Weekly reset: commitments, stalled work, next-week plan.
- `productivity/xlsx` `discarded` — Create, read, edit Excel .xlsx workbooks and CSVs.

### python (1)

- `python/python-cli-web-wrapper` `discarded` — Wrap a Python CLI framework in a Streamlit web UI.

### reference (1)

- `reference/patrick-infra` `discarded` — Reference for Patrick's personal infra: detailed project context, migration history, and date...

### research (6)

- `research/arxiv` `discarded` — Search arXiv papers by keyword, author, category, or ID.
- `research/competitor-news-monitor` `discarded` — Watch named companies for material news; cited digests.
- `research/grounded-citations` `discarded` — Ground answers and documents in cited, verifiable sources.
- `research/linkedin-profile-finder` `discarded` — Find and verify LinkedIn profile URLs for individuals.
- `research/llm-wiki` `discarded` — Karpathy's LLM Wiki: build/query interlinked markdown KB.
- `research/market-intel` `discarded` — Research companies, markets, or competitive landscapes and return structured, source-backed m...

### software-development (37)

- `software-development/codebase-inspection` `discarded` — Inspect codebases w/ pygount: LOC, languages, ratios.
- `software-development/codebase-orientation` `discarded` — Summarize what an unfamiliar codebase does and how it works.
- `software-development/debugging-hermes-tui-commands` `discarded` — Debug Hermes TUI slash commands: Python, gateway, Ink UI.
- `software-development/debugging-performance-metrics` `discarded` — Debugging performance metrics when measurements lie — server-reported telemetry vs actual beh...
- `software-development/debugging-strategies` `discarded` — Master systematic debugging techniques, profiling tools, and root cause analysis to efficient...
- `software-development/documentation-writer` `discarded` — Diátaxis Documentation Expert. An expert technical writer specializing in creating high-quali...
- `software-development/dogfood` `discarded` — Exploratory QA of web apps: find bugs, evidence, reports.
- `software-development/firebase-security-rules-auditor` `discarded` — A skill to evaluate how secure Firestore security rules are. Use this when Firestore security...
- `software-development/git-commit` `discarded` — Execute git commit with conventional commit message analysis, intelligent staging, and messag...
- `software-development/github-actions-docs` `discarded` — Use when users ask how to write, explain, customize, migrate, secure, or troubleshoot GitHub ...
- `software-development/github-cross-fork-contribution` `discarded` — Create PRs against upstream from a fork.
- `software-development/hermes-acp-editors` `discarded` — Use when wiring Hermes into an ACP editor.
- `software-development/hermes-agent-skill-authoring` `discarded` — Author in-repo SKILL.md files: frontmatter and structure.
- `software-development/hermes-config-management` `folded` — Configure Hermes Agent settings — model, providers, MoA presets, display, platforms, and othe...
- `software-development/hermes-desktop-troubleshooting` `promoted` — Diagnose Hermes desktop app initialization failures, startup errors, and connection issues — ...
- `software-development/hermes-s6-container-supervision` `discarded` — Modify, debug, or extend the s6-overlay supervision tree inside the Hermes Agent Docker image...
- `software-development/inspecting-hermes-desktop-dom` `discarded` — Read the live Hermes desktop DOM/CSS over CDP.
- `software-development/local-inference-ops` `discarded` — Triage local LLM OOM and migrate to llama.cpp.
- `software-development/local-inference-providers` `discarded` — Add and verify local inference endpoints as Hermes providers — exo, Ollama, LM Studio, vLLM, ...
- `software-development/local-inspect-watchers` `discarded` — Build inspect-only watchers that emit mrmr-style events.
- `software-development/macos-security-audit` `discarded` — Comprehensive macOS security audit skill for SSH, firewall, and system hardening
- `software-development/mcp-config-troubleshooting` `discarded` — Use when MCP servers fail in Warp/Zed/Codex/Claude.
- `software-development/node-inspect-debugger` `discarded` — Debug Node.js via --inspect + Chrome DevTools Protocol CLI.
- `software-development/python-debugpy` `discarded` — Debug Python: pdb REPL + debugpy remote (DAP).
- `software-development/python-performance-optimization` `discarded` — Profile and optimize Python code using cProfile, memory profilers, and performance best pract...
- `software-development/python-testing-patterns` `discarded` — Implement comprehensive testing strategies with pytest, fixtures, mocking, and test-driven de...
- `software-development/requesting-code-review` `discarded` — Pre-commit review: security scan, quality gates, auto-fix.
- `software-development/simplify-code` `discarded` — Parallel 4-agent cleanup of recent code changes.
- `software-development/skill-library-curation` `discarded` — Audit, summarize, and prune skills that don't match the user's actual workflow. Dead weight i...
- `software-development/spike` `discarded` — Throwaway experiments to validate an idea before build.
- `software-development/subagent-driven-development` `discarded` — Execute plans via delegate_task subagents (2-stage review).
- `software-development/swiftui-code-audit` `discarded` — SwiftUI audits using axiom-swiftui inlined auditors.
- `software-development/systematic-debugging` `discarded` — 4-phase root cause debugging: understand bugs before fixing.
- `software-development/test-driven-development` `discarded` — TDD: enforce RED-GREEN-REFACTOR, tests before code.
- `software-development/typescript-advanced-types` `discarded` — Master TypeScript's advanced type system including generics, conditional types, mapped types,...
- `software-development/webapp-testing` `discarded` — Toolkit for interacting with and testing local web applications using Playwright. Supports ve...
- `software-development/writing-plans` `discarded` — Write implementation plans: bite-sized tasks, paths, code.

### teaching (1)

- `teaching/community-tech-sessions` `promoted` — Design community workshops for non-technical learners.

### web (1)

- `web/blocked-page-recovery` `discarded` — Use when a fetch fails: 403/429, paywall, WAF, bot wall.

### webops (1)

- `webops/static-site-deploy` `discarded` — Deploy static sites to Cloudflare Pages.

### (top level) (10)

- `debugging-hermes-skill-loading` `discarded` — Fix Hermes skills that load invisible or fail silently.
- `github-workflow` `discarded` — GitHub operations: auth, repos, PRs, issues, review, audit.
- `hermes-desktop-plugins` `discarded` — Write desktop app plugins that add UI panes and commands.
- `hermes-themes` `discarded` — Author a Hermes color theme that skins every surface.
- `macos-dotfiles-backup` `discarded` — >
- `macos-swiftdata-navigation` `discarded` — macOS SwiftUI NavigationSplitView route side-effects.
- `mcp` `discarded` — MCP: connect, install, auth, troubleshoot servers.
- `mcp-bearer-auth` `discarded` — Replace expiring OAuth MCP with Bearer token and direct API.
- `swift-planning` `discarded` — Swift plans: bridging types, SwiftUI pitfalls, SwiftData.
- `voice-mode` `discarded` — Setup voice mode and TTS across CLI, TUI, Desktop.
