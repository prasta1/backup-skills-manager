# Extracting Claude Design Artifacts

## Context

Claude Design exports self-contained HTML files with all assets embedded as base64 in a `__bundler/manifest` script tag. This is not editable as normal HTML.

## Extraction Method

1. Parse the `__bundler/manifest` JSON to get asset list
2. Parse the `__bundler/template` JSON string to get the actual HTML
3. Decode each asset: uncompressed is base64-only, compressed uses gzip
4. Write assets to files with extensions matching their MIME type:
   - `image/png` -> `.png`
   - `image/jpeg` -> `.jpg`
   - `font/woff2` -> `.woff2`
   - `text/javascript` -> `.js`
5. Replace UUID references in template with real filenames
6. Write extracted `index.html`

## Key Details

- Compressed assets use gzip, not zlib raw deflate
- Template is stored as a JSON string literal inside the script tag
- Image slots use `<image-slot>` tags that must be replaced with real `<img>` tags
- External resources (React/ReactDOM from CDN) may be in `__bundler/ext_resources`

## Replacement Pattern

To replace an image slot after extraction:
1. Save new image as `headshot.jpg` in the site directory
2. In `index.html`, replace `<image-slot id="headshot" ...></image-slot>` with `<img src="headshot.jpg" alt="..." style="...">`
