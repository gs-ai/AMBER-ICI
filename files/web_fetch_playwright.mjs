/**
 * Playwright-based web page fetcher for AMBER ICI.
 * Usage: node web_fetch_playwright.mjs '{"url":"https://...","timeout":18000}'
 * Returns JSON: {ok, url, content, title} or {ok:false, error}
 */
import process from 'node:process';
import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

chromium.use(StealthPlugin());

const DEFAULT_TIMEOUT = 18000;
const MAX_CONTENT_CHARS = 24000;

function normalizeText(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trim();
}

async function main() {
  const payload = JSON.parse(process.argv[2] || '{}');
  const url = String(payload.url || '').trim();
  const timeout = parseInt(payload.timeout) || DEFAULT_TIMEOUT;

  if (!url || !/^https?:\/\//i.test(url)) {
    process.stdout.write(JSON.stringify({ ok: false, error: 'valid http(s) url is required' }));
    process.exitCode = 1;
    return;
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: 'en-US',
    timezoneId: 'America/Chicago',
    viewport: { width: 1365, height: 768 },
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
  });

  const page = await context.newPage();
  try {
    // Try networkidle first for JS-heavy sites; fall back to domcontentloaded on timeout
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: Math.min(timeout, 22000) });
    } catch {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout }).catch(() => {});
    }
    // Give JS-rendered content extra time to appear
    await page.waitForTimeout(3000);

    const data = await page.evaluate(() => {
      // Strip only purely decorative/structural noise that never has article text
      const junk = ['script', 'style', 'noscript', 'iframe',
        '[class*="cookie-banner"]', '[id*="cookie-banner"]',
        '[class*="cookie-notice"]', '[class*="gdpr"]',
        '[class*="consent"]', '[aria-label="Advertisement"]'];
      junk.forEach(sel => {
        try { document.querySelectorAll(sel).forEach(el => el.remove()); } catch {}
      });
      return {
        title: document.title || '',
        text: document.body ? document.body.innerText : '',
      };
    });

    const content = normalizeText(`${data.title}\n\n${data.text}`).slice(0, MAX_CONTENT_CHARS);

    process.stdout.write(
      JSON.stringify({ ok: true, url, title: normalizeText(data.title), content }),
    );
  } catch (err) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(err.message || err) }));
    process.exitCode = 1;
  } finally {
    await page.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

main().catch((err) => {
  process.stdout.write(JSON.stringify({ ok: false, error: String(err.message || err) }));
  process.exitCode = 1;
});
