const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const [input, output, preferencesPath] = process.argv.slice(2);
  if (!input || !output || !preferencesPath) {
    throw new Error('Usage: node scripts/render_pdf.cjs INPUT.html OUTPUT.pdf PREFERENCES.json');
  }
  if (fs.existsSync(output)) throw new Error('Output exists; use a new revision filename.');
  const preferences = JSON.parse(fs.readFileSync(preferencesPath, 'utf8').replace(/^\uFEFF/, ''));
  if (!['A4', 'Letter'].includes(preferences.paper_size)) throw new Error('Choose A4 or Letter in preferences.');
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({ path: output, format: preferences.paper_size, printBackground: true,
      preferCSSPageSize: false, margin: { top: '0.5in', right: '0.5in', bottom: '0.5in', left: '0.5in' } });
    console.log(`PDF written: ${path.resolve(output)}`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
