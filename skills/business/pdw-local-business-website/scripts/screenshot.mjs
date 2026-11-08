// Screenshot one page at the four review viewports (full-page PNGs).
// Usage: node screenshot.mjs <url> [outDir]   (requires: npm i playwright && npx playwright install chromium)
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';

const [url, outDir = 'qa-shots'] = process.argv.slice(2);
if (!url) {
  console.error('usage: node screenshot.mjs <url> [outDir]');
  process.exit(1);
}

const viewports = [
  ['mobile', 390, 844],
  ['tablet', 768, 1024],
  ['desktop', 1440, 900],
  ['wide', 1920, 1080],
];

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
for (const [name, width, height] of viewports) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
  await page.close();
  console.log(`${outDir}/${name}.png`);
}
await browser.close();
