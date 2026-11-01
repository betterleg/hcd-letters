/**
 * Stage 2: decode <prefix>_raw.json from scrape_report.js into a CSV.
 *
 *   node decode_report.js --in compliance_raw.json --out compliance.csv
 *
 * Headers use the visual's own column labels (NativeReferenceName, e.g. "Date Reviewed"),
 * snake_cased: county, jurisdiction, planning_period, record_type, review_status,
 * date_received, date_reviewed, compliance_status.
 *
 * Power BI row encoding handled here:
 *   S   schema (first row of each response); DN = value-dictionary name, T 7 = datetime
 *   C   the values for columns that are not repeated or null, in column order
 *   R   bitmask: column repeats the previous row's value
 *   Ø   bitmask: column is null (shown as "(Blank)" in the report)
 *   RF  restart row: the first row of a continuation page repeats the last row of the
 *       previous page; it is decoded (to seed R) but not emitted
 * Value dictionaries are per response page. A value missing from the page's dictionary is
 * sent as a literal string. Datetimes are wall-clock times encoded as UTC epoch ms, so the
 * UTC date is the date the report shows.
 */

function cleanName(n) {
  let s = String(n || '');
  const inner = s.match(/\(([^()]*)\)/);
  if (inner) s = inner[1];
  if (s.includes('.')) s = s.slice(s.lastIndexOf('.') + 1);
  s = s.replace(/\d+$/, ''); // "Record Type1" -> "Record Type"
  return s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'col';
}

function decode(raw) {
  const pages = Array.isArray(raw) ? raw : raw.pages; // also accepts old housing_elements_raw.json
  const meta = raw.meta || {};
  const labels = meta.labels || meta.columns || [];
  const rows = [];
  let header = null;
  let restartSkipped = 0;
  let nested = false;

  pages.forEach((page, pi) => {
    const data = page.results[0].result.data;
    const ds = data.dsr.DS[0];
    const dicts = ds.ValueDicts || {};
    const byG = {};
    ((data.descriptor && data.descriptor.Select) || []).forEach((s, i) => { byG[s.Value] = labels[i] || s.Name; });
    let schema = null;
    let prev = null;
    for (const ph of ds.PH || []) {
      if (ph.DM1) nested = true;
      for (const row of ph.DM0 || []) {
        if (row.S) {
          schema = row.S;
          prev = new Array(schema.length).fill(null);
          if (!header) {
            const seen = {};
            header = schema.map((s, i) => cleanName(byG[s.N] || labels[i] || s.N))
              .map((h) => ((seen[h] = (seen[h] || 0) + 1) > 1 ? `${h}_${seen[h]}` : h));
          }
        }
        if (!schema) continue;
        const rMask = row.R || 0;
        const nMask = row['Ø'] || 0;
        const c = row.C || [];
        let ci = 0;
        const vals = [];
        for (let col = 0; col < schema.length; col++) {
          let v;
          if (nMask & (1 << col)) v = null;
          else if (rMask & (1 << col)) v = prev[col];
          else {
            const x = c[ci++];
            const s = schema[col];
            if (s.DN && typeof x === 'number') v = dicts[s.DN][x];
            else if (s.T === 7 && typeof x === 'number') v = new Date(x).toISOString().slice(0, 10);
            else v = x;
          }
          vals.push(v);
        }
        if (ci !== c.length) throw new Error(`Row decode mismatch on page ${pi}: used ${ci} of ${c.length} values`);
        prev = vals;
        if (row.RF && pi > 0) { restartSkipped++; continue; }
        rows.push(vals);
      }
    }
  });
  if (!header) throw new Error('No rows found.');

  const seen = new Set();
  let exactDupes = 0;
  const out = rows.filter((r) => { const k = JSON.stringify(r); if (seen.has(k)) { exactDupes++; return false; } seen.add(k); return true; });
  return { header, rows: out, restartSkipped, exactDupes, nested };
}

function csvEscape(v) {
  if (v == null) return '';
  const s = String(v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
const toCsv = (r) => [r.header.join(','), ...r.rows.map((x) => x.map(csvEscape).join(','))].join('\n');

function summary(r) {
  const lines = [`${r.rows.length} rows; columns: ${r.header.join(', ')}`];
  if (r.restartSkipped) lines.push(`  ${r.restartSkipped} page-boundary repeat row(s) skipped`);
  if (r.exactDupes) lines.push(`  ${r.exactDupes} exact duplicate row(s) dropped`);
  if (r.nested) lines.push('  WARNING: nested (matrix) data present; only flat rows decoded');
  for (const h of ['planning_period', 'compliance_status', 'review_status', 'record_type']) {
    const i = r.header.indexOf(h);
    if (i < 0) continue;
    const counts = {};
    r.rows.forEach((x) => { const k = x[i] == null ? '(Blank)' : x[i]; counts[k] = (counts[k] || 0) + 1; });
    lines.push(`  ${h}: ${Object.entries(counts).map(([k, n]) => `${k} ${n}`).join(', ')}`);
  }
  const isLink = (v) => typeof v === 'string' && (/^https?:\/\//i.test(v) || /\.pdf(\?|$)/i.test(v));
  const links = r.header.filter((h, i) => r.rows.some((x) => isLink(x[i])));
  lines.push(links.length ? `  link columns: ${links.join(', ')}` : '  no document-link columns');
  return lines.join('\n');
}

if (typeof module !== 'undefined') module.exports = { decode, toCsv, summary, cleanName };

if (typeof require !== 'undefined' && require.main === module) {
  const fs = require('fs');
  const argv = process.argv.slice(2);
  const flag = (n, d) => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : d; };
  const input = flag('--in', 'compliance_raw.json');
  const output = flag('--out', input.replace(/_raw\.json$/, '').replace(/\.json$/, '') + '.csv');
  const r = decode(JSON.parse(fs.readFileSync(input, 'utf8')));
  fs.writeFileSync(output, toCsv(r), 'utf8');
  console.log(`-> ${output}\n${summary(r)}`);
}
