# NPM Nanoid Override Safety

**Absorbed from:** `npm-nanoid-override-safety` skill

## Problem

`npm install` in the `web` workspace can drop the `nanoid@3.3.18` override from root `package.json`, re-introducing [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) (high severity) in `sanitize-html` → `postcss` and `vite`.

## Fix

```bash
cd /Users/macstudio/.hermes/hermes-agent

# 1. Ensure override exists in root package.json
grep -q '"nanoid@^3": "3.3.18"' package.json || \
  hermes config set overrides.nanoid@^3 3.3.18

# 2. Install + fix vulnerabilities
npm install
npm audit fix

# 3. Verify — expect "found 0 vulnerabilities"
npm audit --workspaces web
```

## When to Run

After any `npm install` in the `web` workspace, or whenever `npm audit` shows vulnerabilities in the `sanitize-html` → `postcss` → `nanoid` dependency chain.
