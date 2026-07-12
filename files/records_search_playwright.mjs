import process from 'node:process';
import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';

chromium.use(StealthPlugin());

const MAX_QUERIES = 8;
const MAX_RESULTS_PER_QUERY = 10;
const MAX_PAGES = 32;
const PAGE_TIMEOUT_MS = 18000;

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function tokenSet(value) {
  return new Set(
    normalizeText(value)
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(Boolean),
  );
}

function includesAll(haystack, tokens) {
  return tokens.every((token) => haystack.includes(token));
}

function corroboratedWindow(text, subjectTokens, locationTokens) {
  const lower = text.toLowerCase();
  const anchors = subjectTokens
    .map((token) => lower.indexOf(token))
    .filter((idx) => idx >= 0)
    .sort((a, b) => a - b);
  for (const anchor of anchors) {
    const start = Math.max(0, anchor - 700);
    const window = lower.slice(start, anchor + 1800);
    if (includesAll(window, subjectTokens) && includesAll(window, locationTokens)) {
      return { start, text: text.slice(start, anchor + 1800) };
    }
  }
  return null;
}

function locationAlternatives(location) {
  const normalized = normalizeText(location);
  const tokens = [...tokenSet(normalized)];
  const variants = [{ label: normalized, tokens }];
  const withoutCounty = tokens.filter((token) => token !== 'county');
  if (withoutCounty.length !== tokens.length) {
    variants.push({ label: normalized, tokens: withoutCounty });
  }
  if (tokens.includes('kansas')) {
    variants.push({ label: normalized, tokens: tokens.map((token) => (token === 'kansas' ? 'ks' : token)) });
  }
  return variants.filter((variant) => variant.tokens.length);
}

function buildQueries(subject, locations) {
  const safeSubject = normalizeText(subject);
  const baseLocations = locations.length ? locations : ['Kansas'];
  const queries = [];
  for (const location of baseLocations) {
    const loc = normalizeText(location);
    queries.push(`"${safeSubject}" "${loc}"`);
    queries.push(`"${safeSubject}" ${loc}`);
    queries.push(`"${safeSubject}" "${loc}" records`);
    queries.push(`"${safeSubject}" "${loc}" news`);
  }
  return [...new Set(queries)].slice(0, MAX_QUERIES);
}

function classify(url, title, text) {
  const blob = `${url} ${title} ${text}`.toLowerCase();
  if (/\b(news|newspaper|times|press|post|journal|article)\b/.test(blob)) return 'news';
  if (/court|sheriff|police|inmate|booking|arrest|jail|records|register|deeds|property|case/.test(blob)) {
    return 'record';
  }
  return 'data';
}

function snippetAround(text, subjectTokens, locationTokens) {
  const window = corroboratedWindow(text, subjectTokens, locationTokens);
  if (window) return normalizeText(window.text.slice(0, 620));
  return normalizeText(text.slice(0, 560));
}

function isSearchUrl(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    return ['duckduckgo.com', 'google.com', 'bing.com', 'yahoo.com'].some((d) => host.endsWith(d));
  } catch {
    return true;
  }
}

function parseName(fullName) {
  const parts = normalizeText(fullName).split(/\s+/);
  if (parts.length === 1) return { first: '', last: parts[0] };
  return { first: parts.slice(0, -1).join(' '), last: parts[parts.length - 1] };
}

function isKansasSearch(locations) {
  const kw = ['kansas', 'ks', 'leavenworth', 'lansing', 'topeka', 'wichita', 'overland park'];
  const normalized = locations.map((l) => l.toLowerCase());
  return normalized.length === 0 || normalized.some((l) => kw.some((k) => l.includes(k)));
}

/**
 * Direct scrape of the Kansas District Court Public Access Portal.
 * URL: https://casesearch.kscourts.gov/
 * Requires: accept terms, select county, select Party Name search, enter name.
 */
async function searchKansasEcourt(context, subject, county = 'Leavenworth') {
  const { first, last } = parseName(subject);
  const page = await context.newPage();
  const results = [];
  try {
    await page.goto('https://casesearch.kscourts.gov/', { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT_MS });
    await page.waitForTimeout(1200);

    // Accept terms & conditions
    const acceptBtn = page.locator('button:has-text("Accept"), input[value="Accept"], a:has-text("Accept")');
    if (await acceptBtn.count() > 0) {
      await acceptBtn.first().click();
      await page.waitForTimeout(1200);
    }

    // Select county from dropdown
    const countySelects = page.locator('select');
    const countyCount = await countySelects.count();
    for (let i = 0; i < countyCount; i++) {
      const opts = await countySelects.nth(i).locator('option').allInnerTexts();
      if (opts.some((o) => o.toLowerCase().includes('leavenworth') || o.toLowerCase().includes('county'))) {
        await countySelects.nth(i).selectOption({ label: new RegExp(county, 'i') }).catch(() => {});
        await page.waitForTimeout(600);
        break;
      }
    }

    // Pick "Party Name" search type if a search type selector is visible
    const allSelects = page.locator('select');
    const total = await allSelects.count();
    for (let i = 0; i < total; i++) {
      const opts = await allSelects.nth(i).locator('option').allInnerTexts();
      if (opts.some((o) => /party\s*name/i.test(o))) {
        await allSelects.nth(i).selectOption({ label: /party\s*name/i }).catch(() => {});
        await page.waitForTimeout(600);
        break;
      }
    }

    // Fill last name
    const lastInput = page.locator(
      'input[name*="last" i], input[id*="last" i], input[placeholder*="last" i]',
    );
    if (await lastInput.count() > 0) await lastInput.first().fill(last);

    // Fill first name
    const firstInput = page.locator(
      'input[name*="first" i], input[id*="first" i], input[placeholder*="first" i]',
    );
    if (await firstInput.count() > 0 && first) await firstInput.first().fill(first);

    // Submit search
    const searchBtn = page.locator(
      'button[type="submit"], input[type="submit"], button:has-text("Search")',
    );
    if (await searchBtn.count() > 0) {
      await searchBtn.first().click();
    } else {
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(4000);

    const pageUrl = page.url();
    const pageText = normalizeText(
      await page.evaluate(() => (document.body ? document.body.innerText : '')),
    );

    // Extract table rows that contain the subject last name
    const rows = await page.evaluate((lastName) => {
      return [...document.querySelectorAll('table tr')]
        .map((r) => r.innerText.replace(/\s+/g, ' ').trim())
        .filter((t) => t.length > 5 && t.toLowerCase().includes(lastName.toLowerCase()));
    }, last);

    if (rows.length > 0) {
      for (const row of rows.slice(0, 30)) {
        results.push({
          title: `Kansas eCourt — ${subject} (${county} County)`,
          url: pageUrl,
          type: 'record',
          matched_location: `${county} County, Kansas`,
          snippet: row.slice(0, 620),
        });
      }
    } else if (pageText.toLowerCase().includes(last.toLowerCase())) {
      results.push({
        title: `Kansas eCourt — ${subject} (${county} County)`,
        url: pageUrl,
        type: 'record',
        matched_location: `${county} County, Kansas`,
        snippet: pageText.slice(0, 620),
      });
    } else {
      // Return the raw page text so the analyst can see what the portal returned
      results.push({
        title: `Kansas eCourt — search executed (no name match found)`,
        url: pageUrl,
        type: 'record',
        matched_location: `${county} County, Kansas`,
        snippet: pageText.slice(0, 620),
      });
    }
  } catch (err) {
    results.push({
      title: 'Kansas eCourt — scrape error',
      url: 'https://casesearch.kscourts.gov/',
      type: 'record',
      matched_location: `${county} County, Kansas`,
      snippet: String(err.message || err).slice(0, 300),
    });
  } finally {
    await page.close().catch(() => {});
  }
  return results;
}

/**
 * Kansas DOC Offender Search.
 * URL: https://www.doc.ks.gov/offender-search
 */
async function searchKansasDOC(context, subject) {
  const { first, last } = parseName(subject);
  const page = await context.newPage();
  const results = [];
  try {
    await page.goto('https://www.doc.ks.gov/offender-search', {
      waitUntil: 'domcontentloaded',
      timeout: PAGE_TIMEOUT_MS,
    });
    await page.waitForTimeout(1000);

    const lastInput = page.locator('input[name*="last" i], input[id*="last" i], input[placeholder*="last" i]');
    if (await lastInput.count() > 0) await lastInput.first().fill(last);

    const firstInput = page.locator('input[name*="first" i], input[id*="first" i], input[placeholder*="first" i]');
    if (await firstInput.count() > 0 && first) await firstInput.first().fill(first);

    const searchBtn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Search")');
    if (await searchBtn.count() > 0) {
      await searchBtn.first().click();
    } else {
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(3500);

    const pageUrl = page.url();
    const pageText = normalizeText(
      await page.evaluate(() => (document.body ? document.body.innerText : '')),
    );

    const rows = await page.evaluate((lastName) => {
      return [...document.querySelectorAll('table tr, .view-row, .views-row')]
        .map((r) => r.innerText.replace(/\s+/g, ' ').trim())
        .filter((t) => t.length > 5 && t.toLowerCase().includes(lastName.toLowerCase()));
    }, last);

    if (rows.length > 0) {
      for (const row of rows.slice(0, 20)) {
        results.push({
          title: `Kansas DOC Offender Search — ${subject}`,
          url: pageUrl,
          type: 'record',
          matched_location: 'Kansas',
          snippet: row.slice(0, 620),
        });
      }
    } else if (pageText.toLowerCase().includes(last.toLowerCase())) {
      results.push({
        title: `Kansas DOC Offender Search — ${subject}`,
        url: pageUrl,
        type: 'record',
        matched_location: 'Kansas',
        snippet: pageText.slice(0, 620),
      });
    } else {
      results.push({
        title: 'Kansas DOC Offender Search — no match found',
        url: pageUrl,
        type: 'record',
        matched_location: 'Kansas',
        snippet: pageText.slice(0, 400),
      });
    }
  } catch (err) {
    results.push({
      title: 'Kansas DOC — scrape error',
      url: 'https://www.doc.ks.gov/offender-search',
      type: 'record',
      matched_location: 'Kansas',
      snippet: String(err.message || err).slice(0, 300),
    });
  } finally {
    await page.close().catch(() => {});
  }
  return results;
}

/**
 * Kansas Sex Offender Registry (KBI).
 * URL: https://www.kbi.ks.gov/registeredoffender/
 */
async function searchKansasSOR(context, subject) {
  const { first, last } = parseName(subject);
  const page = await context.newPage();
  const results = [];
  try {
    await page.goto('https://www.kbi.ks.gov/registeredoffender/', {
      waitUntil: 'domcontentloaded',
      timeout: PAGE_TIMEOUT_MS,
    });
    await page.waitForTimeout(1000);

    const lastInput = page.locator('input[name*="last" i], input[id*="last" i], input[placeholder*="last" i], #lastName');
    if (await lastInput.count() > 0) await lastInput.first().fill(last);

    const firstInput = page.locator('input[name*="first" i], input[id*="first" i], input[placeholder*="first" i], #firstName');
    if (await firstInput.count() > 0 && first) await firstInput.first().fill(first);

    const searchBtn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Search")');
    if (await searchBtn.count() > 0) {
      await searchBtn.first().click();
    } else {
      await page.keyboard.press('Enter');
    }
    await page.waitForTimeout(3500);

    const pageUrl = page.url();
    const pageText = normalizeText(
      await page.evaluate(() => (document.body ? document.body.innerText : '')),
    );

    const rows = await page.evaluate((lastName) => {
      return [...document.querySelectorAll('table tr, .offender-row, .result-item')]
        .map((r) => r.innerText.replace(/\s+/g, ' ').trim())
        .filter((t) => t.length > 5 && t.toLowerCase().includes(lastName.toLowerCase()));
    }, last);

    if (rows.length > 0) {
      for (const row of rows.slice(0, 20)) {
        results.push({
          title: `Kansas Sex Offender Registry — ${subject}`,
          url: pageUrl,
          type: 'record',
          matched_location: 'Kansas',
          snippet: row.slice(0, 620),
        });
      }
    } else {
      results.push({
        title: 'Kansas Sex Offender Registry — no match found',
        url: pageUrl,
        type: 'record',
        matched_location: 'Kansas',
        snippet: pageText.slice(0, 400),
      });
    }
  } catch (err) {
    results.push({
      title: 'Kansas SOR — scrape error',
      url: 'https://www.kbi.ks.gov/registeredoffender/',
      type: 'record',
      matched_location: 'Kansas',
      snippet: String(err.message || err).slice(0, 300),
    });
  } finally {
    await page.close().catch(() => {});
  }
  return results;
}

async function collectResultLinks(page, query) {
  const url = `https://duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT_MS });
  await page.waitForTimeout(900);
  return page.evaluate((limit) => {
    const anchors = [...document.querySelectorAll('a.result__a, a[href]')];
    return anchors
      .map((a) => ({ title: a.textContent.trim(), url: a.href }))
      .filter((r) => r.title && /^https?:\/\//.test(r.url))
      .map((r) => {
        try {
          const u = new URL(r.url);
          const uddg = u.searchParams.get('uddg');
          return { title: r.title, url: uddg ? decodeURIComponent(uddg) : r.url };
        } catch {
          return r;
        }
      })
      .filter((r) => /^https?:\/\//.test(r.url))
      .slice(0, limit);
  }, MAX_RESULTS_PER_QUERY);
}

async function collectBraveLinks(page, query) {
  const url = `https://search.brave.com/search?q=${encodeURIComponent(query)}&source=web`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT_MS });
  await page.waitForTimeout(900);
  return page.evaluate((limit) => {
    return [...document.querySelectorAll('a[href]')]
      .map((a) => ({ title: a.textContent.trim(), url: a.href }))
      .filter((r) => r.title && /^https?:\/\//.test(r.url))
      .filter((r) => !r.url.includes('search.brave.com/'))
      .slice(0, limit);
  }, MAX_RESULTS_PER_QUERY);
}

async function readCandidate(context, candidate, subjectTokens, locationTokenSets) {
  if (isSearchUrl(candidate.url)) return null;
  const page = await context.newPage();
  try {
    await page.goto(candidate.url, { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT_MS });
    await page.waitForTimeout(500);
    const data = await page.evaluate(() => ({
      title: document.title || '',
      text: document.body ? document.body.innerText : '',
    }));
    const text = normalizeText(`${candidate.title} ${data.title} ${data.text}`);
    const lower = text.toLowerCase();
    const hasSubject = includesAll(lower, subjectTokens);
    const matchedLocation = locationTokenSets.find((loc) => corroboratedWindow(text, subjectTokens, loc.tokens));
    if (!hasSubject || !matchedLocation) return null;
    return {
      title: normalizeText(data.title || candidate.title),
      url: candidate.url,
      type: classify(candidate.url, data.title, text),
      matched_location: matchedLocation.label,
      snippet: snippetAround(text, subjectTokens, matchedLocation.tokens),
    };
  } catch (error) {
    return null;
  } finally {
    await page.close().catch(() => {});
  }
}

async function main() {
  const payload = JSON.parse(process.argv[2] || '{}');
  const subject = normalizeText(payload.subject || payload.name || payload.query || '');
  const locations = Array.isArray(payload.locations)
    ? payload.locations.map(normalizeText).filter(Boolean)
    : [];
  if (!subject) throw new Error('subject is required');

  const subjectTokens = [...tokenSet(subject)];
  const locationTokenSets = (locations.length ? locations : ['Kansas']).flatMap(locationAlternatives);
  const queries = buildQueries(subject, locations);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    locale: 'en-US',
    timezoneId: 'America/Chicago',
    viewport: { width: 1365, height: 768 },
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
  });

  const searchPage = await context.newPage();
  const seen = new Set();
  const candidates = [];
  for (const query of queries) {
    const links = [
      ...(await collectResultLinks(searchPage, query).catch(() => [])),
      ...(await collectBraveLinks(searchPage, query).catch(() => [])),
    ];
    for (const link of links) {
      if (seen.has(link.url)) continue;
      seen.add(link.url);
      candidates.push(link);
    }
  }
  await searchPage.close().catch(() => {});

  const matches = [];
  for (const candidate of candidates.slice(0, MAX_PAGES)) {
    const match = await readCandidate(context, candidate, subjectTokens, locationTokenSets);
    if (match) matches.push(match);
  }

  // Direct targeted database searches for Kansas locations
  if (isKansasSearch(locations)) {
    // Determine county — default Leavenworth when specified or when no location given
    const countyHint = locations.find((l) => /leavenworth/i.test(l)) ? 'Leavenworth' : 'Leavenworth';

    const [ecourt, doc, sor] = await Promise.all([
      searchKansasEcourt(context, subject, countyHint),
      searchKansasDOC(context, subject),
      searchKansasSOR(context, subject),
    ]);

    matches.push(...ecourt, ...doc, ...sor);
  }

  await browser.close();

  process.stdout.write(JSON.stringify({
    ok: true,
    subject,
    locations,
    searched_at: new Date().toISOString(),
    queries,
    matches,
  }));
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({ ok: false, error: error.message || String(error) }));
  process.exitCode = 1;
});
