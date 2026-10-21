/**
 * Stage 1: pull a table from an HCD Power BI report by replaying its saved query.
 * No browser needed for a normal run.
 *
 *   node scrape_report.js --report letters      # review letters  -> letters_raw.json
 *   node scrape_report.js --report compliance   # compliance table -> compliance_raw.json
 *
 * Reports
 *   letters     Housing Element Download Tool, page 2 "Housing Element Review Letter Download
 *               Tool" (the "Click to Access Review Letters" button). One row per HCD review
 *               letter: county, jurisdiction, type, cycle, reviewed, linktext, weblink.
 *   housing_elements  Housing Element Download Tool, page 1: every housing element document
 *               submitted to HCD (county, jurisdiction, planning period, received date, type,
 *               PDF link). Used to match each letter to the submittal it reviewed.
 *   compliance  Housing Element Review and Compliance Report, page 3. One row per
 *               jurisdiction with current compliance status.
 *
 * Re-capture (needs `npm install puppeteer`) when HCD republishes a report and the saved
 * template stops working:
 *   node scrape_report.js --report letters --capture
 *   node scrape_report.js --report letters --capture --list    # just list the queries
 *
 * Flags
 *   --report <name>    letters | housing_elements | compliance (default letters)
 *   --template <file>  saved query (default <report>_template.json); written by --capture
 *   --out <prefix>     output prefix (default <report>) -> <prefix>_raw.json
 *   --page-size <n>    rows per request (default 500)
 *   --capture          open the report in headless Chrome and capture the query
 *   --url <url>        report link or an HCD page that embeds it
 *   --next-pages <n>   times to click the Next Page arrow before capturing
 *   --visual <regex>   pick the captured query whose column names match
 *   --query <n>        pick capture #n from --list
 *   --list             only list captured queries
 *   --keep-filters     keep slicer filters present at capture time (default: drop them)
 *   --wait <sec>       wait after each click (default 8)
 */

const fs = require('fs');

const PRESETS = {
  letters: {
    url: 'https://app.powerbigov.us/view?r=eyJrIjoiM2MxM2E3YTQtZmYzMC00MWJkLWE5MzEtNGI1NDRiNGQyMTczIiwidCI6IjJiODI4NjQ2LWIwMzctNGZlNy04NDE1LWU5MzVjZDM0Y2Y5NiJ9',
    nextPages: 1,
    visual: 'weblink',
  },
  housing_elements: {
    url: 'https://app.powerbigov.us/view?r=eyJrIjoiM2MxM2E3YTQtZmYzMC00MWJkLWE5MzEtNGI1NDRiNGQyMTczIiwidCI6IjJiODI4NjQ2LWIwMzctNGZlNy04NDE1LWU5MzVjZDM0Y2Y5NiJ9',
    nextPages: 0,
    accept: 'accept and view',
    visual: 'View Link',
    keepFilters: true, // the table's own "has a document" filter, not a user slicer
    labels: ['county', 'jurisdiction', 'planning_period', 'received_date', 'type', 'link_text', 'pdf_url'],
  },
  compliance: {
    url: 'https://app.powerbigov.us/view?r=eyJrIjoiMDk3NDZlN2QtNjdiNy00MTZmLWExNzctNmNjMDAxNTBhYzI1IiwidCI6IjJiODI4NjQ2LWIwMzctNGZlNy04NDE1LWU5MzVjZDM0Y2Y5NiJ9',
    nextPages: 2,
    visual: 'Compliance Status',
  },
};

function parseArgs(argv) {
  const a = { report: 'letters', pageSize: 500, wait: 8 };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    const v = () => argv[++i];
    if (k === '--report') a.report = v();
    else if (k === '--template') a.template = v();
    else if (k === '--out') a.out = v();
    else if (k === '--page-size') a.pageSize = parseInt(v(), 10);
    else if (k === '--capture') a.capture = true;
    else if (k === '--url') a.url = v();
    else if (k === '--next-pages') a.nextPages = parseInt(v(), 10);
    else if (k === '--visual') a.visual = v();
    else if (k === '--query') a.query = parseInt(v(), 10);
    else if (k === '--list') a.list = true;
    else if (k === '--keep-filters') a.keepFilters = true;
    else if (k === '--wait') a.wait = parseFloat(v());
    else if (k === '-h' || k === '--help') { console.log(fs.readFileSync(__filename, 'utf8').split('*/')[0]); process.exit(0); }
    else { console.error(`Unknown flag ${k}`); process.exit(2); }
  }
  const p = PRESETS[a.report];
  if (!p) { console.error(`--report must be one of: ${Object.keys(PRESETS).join(', ')}`); process.exit(2); }
  a.template = a.template || `${a.report}_template.json`;
  a.out = a.out || a.report;
  a.url = a.url || p.url;
  if (!Number.isInteger(a.nextPages)) a.nextPages = p.nextPages;
  if (!a.visual && !Number.isInteger(a.query)) a.visual = p.visual;
  if (p.keepFilters) a.keepFilters = true;
  a.preset = p;
  return a;
}
const args = parseArgs(process.argv);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const MAX_PAGES = 100; // 50,000 rows; letters needs ~12 pages, compliance 2
const cmdOf = (body) => body.queries[0].Query.Commands[0].SemanticQueryDataShapeCommand;
const selectOf = (body) => cmdOf(body).Query.Select || [];
const resourceKeyFromUrl = (u) => {
  try { return JSON.parse(Buffer.from(new URL(u).searchParams.get('r'), 'base64').toString()).k; } catch { return null; }
};

// ---------------- replay ----------------
async function fetchPage(tpl, restartTokens) {
  const body = JSON.parse(JSON.stringify(tpl.body));
  const dr = cmdOf(body).Binding.DataReduction || (cmdOf(body).Binding.DataReduction = {});
  dr.Primary = { Window: { Count: args.pageSize } };
  if (restartTokens) dr.Primary.Window.RestartTokens = restartTokens;
  let res;
  for (let attempt = 1; ; attempt++) {
    try {
      res = await fetch(tpl.url, {
        method: 'POST',
        headers: { 'content-type': 'application/json;charset=UTF-8', 'X-PowerBI-ResourceKey': tpl.resourceKey },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60_000), // never wait forever on one request
      });
      break;
    } catch (e) {
      if (attempt >= 3) throw new Error(`Request failed 3 times (${e.name}: ${e.message})`);
      console.log(`  request ${e.name === 'TimeoutError' ? 'timed out' : 'failed'}; retrying (${attempt}/3)...`);
      await sleep(3000 * attempt);
    }
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 500)}`);
  const j = await res.json();
  if (!j.results || !j.results[0].result.data) {
    throw new Error(`Unexpected response (template may be stale; re-run with --capture): ${JSON.stringify(j).slice(0, 500)}`);
  }
  return j;
}

async function replay(tpl) {
  const pages = [];
  let tokens = null;
  let total = 0;
  for (;;) {
    const resp = await fetchPage(tpl, tokens);
    pages.push(resp);
    const ds = resp.results[0].result.data.dsr.DS[0];
    const got = (ds.PH || []).reduce((n, ph) => n + (ph.DM0 || []).length, 0);
    total += got;
    console.log(`  page ${pages.length}: ${got} rows (running total ${total})`);
    if (!ds.RT || got < args.pageSize) break;
    if (JSON.stringify(ds.RT) === JSON.stringify(tokens)) {
      throw new Error('Power BI returned the same restart token twice (paging is not advancing). Re-capture the template with --capture.');
    }
    if (pages.length >= MAX_PAGES) {
      throw new Error(`Stopped after ${MAX_PAGES} pages (${total} rows) - far more than expected. Re-capture the template with --capture.`);
    }
    tokens = ds.RT;
    await sleep(500);
  }
  const labels = tpl.labels || selectOf(tpl.body).map((s) => s.NativeReferenceName || s.Name);
  const out = `${args.out}_raw.json`;
  fs.writeFileSync(out, JSON.stringify({
    meta: { report_url: tpl.report_url, columns: selectOf(tpl.body).map((s) => s.Name), labels, scraped_at: new Date().toISOString() },
    pages,
  }));
  console.log(`Wrote ${out}. Next: node decode_report.js --in ${out}`);
}

// ---------------- capture ----------------
async function clickNextPage(page) {
  const box = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button[aria-label]')].find((e) => /^next page$/i.test(e.getAttribute('aria-label')));
    if (!b) return null;
    const r = b.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  if (!box) throw new Error('Next Page button not found.');
  // Power BI ignores element.click(); use real mouse events.
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await sleep(80);
  await page.mouse.up();
}

async function capture() {
  let puppeteer;
  try { puppeteer = require('puppeteer'); } catch { throw new Error('--capture needs puppeteer: npm install puppeteer'); }
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'], defaultViewport: { width: 1600, height: 1000 } });
  let url = args.url;
  if (!/powerbigov\.us|powerbi\.com/.test(url)) {
    const p = await browser.newPage();
    await p.goto(url, { waitUntil: 'networkidle2', timeout: 120_000 });
    url = await p.evaluate(() => ([...document.querySelectorAll('iframe')].map((f) => f.src).find((s) => /powerbigov\.us|powerbi\.com/.test(s)) || null));
    await p.close();
    if (!url) throw new Error('No Power BI iframe found on that page; pass the app.powerbigov.us link with --url.');
  }
  const page = await browser.newPage();
  const caps = [];
  let step = 'page1';
  page.on('request', (req) => {
    if (req.method() === 'POST' && req.url().includes('querydata')) caps.push({ url: req.url(), headers: req.headers(), body: req.postData(), step });
  });
  console.log('Loading report...');
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 120_000 });
  await page.waitForSelector('.visualContainer', { timeout: 60_000 });
  await sleep(args.wait * 1000);
  if (args.preset.accept) {
    step = 'accepted';
    const box = await page.evaluate((src) => {
      const v = [...document.querySelectorAll('.visualContainer')].find((e) => new RegExp(src, 'i').test(e.innerText || ''));
      if (!v) return null;
      const r = v.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
    }, args.preset.accept);
    if (!box) throw new Error('Disclaimer button not found.');
    await page.mouse.move(box.x, box.y); await page.mouse.down(); await sleep(80); await page.mouse.up();
    await sleep(args.wait * 1000);
  }
  for (let i = 0; i < args.nextPages; i++) {
    step = `page${i + 2}`;
    await clickNextPage(page);
    await sleep(args.wait * 1000);
  }
  await browser.close();

  // Only queries fired on the final page, one candidate per query.
  const cands = [];
  for (const c of caps.filter((x) => x.step === step)) {
    let body;
    try { body = JSON.parse(c.body); } catch { continue; }
    for (const q of body.queries || []) {
      const single = { ...body, queries: [q] };
      const cols = selectOf(single).map((s) => s.Name);
      if (cols.length) cands.push({ c, body: single, cols });
    }
  }
  console.log(`\n${cands.length} queries on ${step}:`);
  cands.forEach((x, i) => console.log(`  [${i}] ${x.cols.length} cols: ${x.cols.join(' | ').slice(0, 200)}`));
  if (args.list) return null;
  if (!cands.length) throw new Error('No queries captured; try --wait 15 or check --next-pages.');

  let pick;
  if (Number.isInteger(args.query)) pick = cands[args.query];
  else if (args.visual) pick = cands.filter((x) => new RegExp(args.visual, 'i').test(x.cols.join(' | '))).sort((a, b) => b.cols.length - a.cols.length)[0];
  else pick = [...cands].sort((a, b) => b.cols.length - a.cols.length)[0]; // widest table
  if (!pick) throw new Error('No matching query. Run with --list.');

  const cmd = cmdOf(pick.body);
  if (cmd.Query.Where && !args.keepFilters) {
    console.log('Dropping slicer filters present at capture time (use --keep-filters to keep).');
    delete cmd.Query.Where;
  }
  const hdr = Object.fromEntries(Object.entries(pick.c.headers).map(([k, v]) => [k.toLowerCase(), v]));
  const tpl = {
    report_url: url,
    captured: new Date().toISOString().slice(0, 10),
    url: pick.c.url,
    resourceKey: hdr['x-powerbi-resourcekey'] || resourceKeyFromUrl(url),
    labels: args.preset.labels && args.preset.labels.length === selectOf(pick.body).length
      ? args.preset.labels
      : selectOf(pick.body).map((s) => (s.NativeReferenceName || s.Name).replace(/\d+$/, '')),
    body: pick.body,
  };
  fs.writeFileSync(args.template, JSON.stringify(tpl, null, 2));
  console.log(`Saved template [${cands.indexOf(pick)}] -> ${args.template}: ${tpl.labels.join(', ')}`);
  return tpl;
}

async function main() {
  let tpl;
  if (args.capture) {
    tpl = await capture();
    if (!tpl) return;
  } else {
    if (!fs.existsSync(args.template)) throw new Error(`${args.template} not found; run with --capture.`);
    tpl = JSON.parse(fs.readFileSync(args.template, 'utf8'));
  }
  console.log(`Querying ${tpl.labels ? tpl.labels.join(', ') : 'table'}...`);
  await replay(tpl);
}

main()
  .then(() => process.exit(0)) // don't let open keep-alive sockets or a stray browser hold the process open
  .catch((e) => { console.error(e.message || e); process.exit(1); });
