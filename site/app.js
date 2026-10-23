/* HCD Letter Tracker: reads data/*.json (scripts/build_site_data.py) and search/ (scripts/build_search_index.py) and draws six tabs. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const fmt = d3.format(',');
  const pct = d3.format('.0%');
  const parse = d3.utcParse('%Y-%m-%d');
  const fdate = (s) => (s ? d3.utcFormat('%b %-d, %Y')(parse(s)) : '—');
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const STATEWIDE = new Set(['generalapplicability', 'na', '']);
  let REPO = 'betterleg/hcd-letters';
  let KW_VARIANTS = {};
  const gh = (path) => `https://github.com/${REPO}/blob/main/${path.split('/').map(encodeURIComponent).join('/')}`;

  // ---------- helpers ----------
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v; else n.setAttribute(k, v);
    }
    for (const k of kids) if (k != null) n.append(k instanceof Node ? k : document.createTextNode(String(k)));
    return n;
  };
  const link = (href, text) => (href ? el('a', { href, target: '_blank', rel: 'noopener' }, text) : null);
  const readCell = (r) => el('td', { class: 'read' }, link(r.text && gh(r.text), 'Text'), link(r.pdf || (r.req && gh(r.req)), 'PDF'),
    r.hePdf ? link(r.hePdf, 'Element') : null,
    r.req ? el('span', { class: 'src', title: 'Not posted by HCD; obtained by request and kept in this repo' }, 'Requested') : null,
    !r.text && !r.pdf && !r.req ? el('span', { class: 'src' }, r.contact ? 'Request from HCD' : 'No copy') : null);
  const pill = (s) => {
    const k = /enforcement|out/i.test(s) ? 'out' : /review/i.test(s) ? 'rev' : /^in$/i.test(s) ? 'in' : 'na';
    return el('span', { class: `pill ${k}` }, s || 'Not listed');
  };
  const quarter = (d) => `${d.slice(0, 4)}-Q${Math.floor((+d.slice(5, 7) - 1) / 3) + 1}`;
  const tip = $('#tip');
  const showTip = (ev, head, lines) => {
    tip.replaceChildren(el('div', { class: 'h' }, head), ...lines.map((l) => el('div', {}, l)));
    tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
    if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
    tip.style.left = `${Math.max(8, x)}px`; tip.style.top = `${Math.max(8, y)}px`;
  };
  const hideTip = () => { tip.hidden = true; };
  const legend = (node, items) => node.replaceChildren(...items.map(([name, color]) => el('span', {}, Object.assign(el('i'), { style: `background:${color}` }), name)));

  // ---------- data ----------
  async function load() {
    const get = (n) => fetch(`data/${n}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    const [hau, he, comp, cit, meta] = await Promise.all(['hau', 'he', 'compliance', 'citations', 'meta'].map(get));
    if (meta?.repo) REPO = meta.repo;
    const CD = cit?.dict || [];
    const H = (hau?.rows || []).map((r, idx) => {
      const [date, jur, type, laws, statutes, keywords, pdf, text, cs, task, req, cites] = r;
      const t = hau.dict.type[type];
      return { src: 'HAU', idx, date, year: date.slice(0, 4), jur: hau.dict.jur[jur], key: hau.jurKey[jur], type: t, group: hau.typeGroup[t],
        laws: laws.map((i) => hau.dict.law[i]), statutes: statutes.map((i) => hau.dict.statute[i]),
        keywords: keywords.map((i) => hau.dict.keyword[i]), pdf, text, cs, task, req, contact: !pdf && !req, cites: (cites || []).map((i) => CD[i]) };
    });
    const E = (he?.rows || []).map((r, idx) => {
      const [date, jur, county, type, cycle, finding, submittal, days, pdf, text, hePdf, heType, contact, req, cites] = r;
      return { src: 'HE', idx, date, year: date.slice(0, 4), jur: he.dict.jur[jur], key: he.jurKey[jur], county: he.dict.county[county],
        type: he.dict.type[type], group: 'Housing element review', cycle, finding, submittal, days, pdf, text, hePdf, heType: he.dict.heType[heType], req,
        contact: contact === 'contact', statutes: [], keywords: [], laws: [], cites: (cites || []).map((i) => CD[i]) };
    });
    KW_VARIANTS = hau?.keywordVariants || {};
    const C = (comp?.rows || []).map(([county, jurisdiction, cycle, recordType, reviewStatus, received, reviewed, status, key]) =>
      ({ county, jur: jurisdiction, cycle, recordType, reviewStatus, received, reviewed, status, key }));
    return { H, E, C, meta, A: H.concat(E) };
  }

  // ---------- chart primitives ----------
  function axisStyle(g) { g.select('.domain').remove(); g.selectAll('.tick line').attr('stroke', css('--rule')); }

  /** Stacked bars over a band of categories (x), keys stacked bottom-up. */
  function stackedBars(node, { cats, keys, colors, value, tickEvery = 1, label, height = 260, percent = false, totals }) {
    node.replaceChildren();
    const W = Math.max(320, node.clientWidth), m = { t: 12, r: 8, b: 26, l: percent ? 40 : 44 };
    const data = cats.map((c) => Object.fromEntries([['cat', c], ...keys.map((k) => [k, value(c, k)])]));
    if (percent) data.forEach((d) => { const s = d3.sum(keys, (k) => d[k]) || 1; d._n = s; keys.forEach((k) => { d[k] /= s; }); });
    const series = d3.stack().keys(keys)(data);
    const x = d3.scaleBand(cats, [m.l, W - m.r]).padding(0.18);
    const ymax = percent ? 1 : d3.max(data, (d) => d3.sum(keys, (k) => d[k])) || 1;
    const y = d3.scaleLinear([0, ymax], [height - m.b, m.t]).nice();
    const svg = d3.select(node).append('svg').attr('viewBox', `0 0 ${W} ${height}`).attr('role', 'img').attr('aria-label', label || '');
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(percent ? pct : fmt)).call(axisStyle);
    const isQ = /-Q\d$/.test(cats[0] || '');
    const room = Math.max(1, Math.floor((W - m.l - m.r) / (isQ ? 48 : 40)));
    let every = Math.max(tickEvery, Math.ceil(cats.length / room));
    if (isQ) every = Math.ceil(every / 4) * 4;
    const shown = cats.filter((c, i) => (isQ ? c.endsWith('Q1') && ((+c.slice(0, 4)) % (every / 4) === 0) : i % every === 0));
    svg.append('g').attr('transform', `translate(0,${height - m.b})`)
      .call(d3.axisBottom(x).tickValues(shown).tickFormat((c) => (isQ ? c.slice(0, 4) : c)).tickSizeOuter(0)).call(axisStyle);
    svg.append('g').selectAll('g').data(series).join('g').attr('fill', (s) => colors[s.key])
      .selectAll('rect').data((s) => s.map((d) => Object.assign(d, { key: s.key }))).join('rect')
      .attr('x', (d) => x(d.data.cat)).attr('width', x.bandwidth()).attr('y', (d) => y(d[1])).attr('height', (d) => Math.max(0, y(d[0]) - y(d[1])))
      .on('mousemove', (ev, d) => {
        const lines = keys.filter((k) => d.data[k]).map((k) => `${k}: ${percent ? pct(d.data[k]) : fmt(d.data[k])}`);
        if (percent) lines.push(`${fmt(d.data._n)} letters`); else lines.push(`Total: ${fmt(d3.sum(keys, (k) => d.data[k]))}`);
        showTip(ev, d.data.cat, lines);
      }).on('mouseleave', hideTip);
    if (totals) {
      svg.append('g').selectAll('text').data(data).join('text').attr('x', (d) => x(d.cat) + x.bandwidth() / 2).attr('y', m.t - 2)
        .attr('text-anchor', 'middle').text((d) => (d._n ? fmt(d._n) : ''));
    }
    return svg;
  }

  function sparkline(values, max) {
    const W = 120, H = 22, n = values.length;
    const svg = d3.create('svg').attr('class', 'spark').attr('width', W).attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
    const x = d3.scaleBand(d3.range(n), [0, W]).padding(0.15), y = d3.scaleLinear([0, max || 1], [H, 1]);
    svg.selectAll('rect').data(values).join('rect').attr('x', (_, i) => x(i)).attr('width', x.bandwidth())
      .attr('y', (v) => y(v)).attr('height', (v) => H - y(v)).attr('fill', css('--accent'));
    return svg.node();
  }

  // ---------- tabs ----------
  const drawn = {};
  function show(hash) {
    let [tab, query] = (hash || '').split('?');
    if (!$$('.panel').some((p) => p.id === tab)) tab = 'overview';
    $$('.panel').forEach((p) => { p.hidden = p.id !== tab; });
    $$('.tabs a').forEach((a) => a.setAttribute('aria-selected', String(a.dataset.tab === tab)));
    if (!drawn[tab] && DATA) { DRAW[tab](); drawn[tab] = true; }
    if (tab === 'search' && DATA) SEARCH.fromQuery(query || '');
  }

  let DATA = null;
  const DRAW = {};
  const lawsAll = () => [...new Set(DATA.H.flatMap((r) => r.laws))].sort();
  const groupColors = () => ({ 'Technical assistance': css('--s1'), Enforcement: css('--out'), 'Ordinance review': css('--s2'), 'Resolution & support': css('--s4'), Other: css('--s5'), 'Housing element review': css('--s3') });
  const GROUPS = ['Enforcement', 'Technical assistance', 'Ordinance review', 'Resolution & support', 'Other'];
  const quarters = (from, to) => { const out = []; for (let y = +from; y <= +to; y++) for (let q = 1; q <= 4; q++) out.push(`${y}-Q${q}`); return out; };
  const lastQ = () => quarter(d3.max(DATA.H.concat(DATA.E), (r) => r.date) || '2026-01-01');

  // Overview
  DRAW.overview = () => {
    const { H, E, C } = DATA;
    const maxDate = d3.max(H.concat(E), (r) => r.date);
    const since = (days) => d3.utcFormat('%Y-%m-%d')(d3.utcDay.offset(parse(maxDate), -days));
    const recent90 = H.filter((r) => r.date >= since(90)).length;
    const outNow = C.filter((c) => /out/i.test(c.status));
    const recentDays = E.filter((r) => r.date >= since(365) && r.days != null).map((r) => r.days);
    const kpi = (label, value, sub, alert) => el('div', { class: `kpi${alert ? ' alert' : ''}` }, el('span', { class: 'label' }, label), el('span', { class: 'value' }, value), el('span', { class: 'sub' }, sub));
    $('#kpis').replaceChildren(
      kpi('HAU letters', fmt(H.length), `${fmt(recent90)} in the last 90 days`),
      kpi('Housing element review letters', fmt(E.length), `${fmt(E.filter((r) => r.text).length)} with full text`
        + (H.concat(E).some((r) => r.req) ? `; ${fmt(H.concat(E).filter((r) => r.req).length)} letters requested from HCD` : '')),
      kpi('Out of compliance now', fmt(outNow.length), `of ${fmt(C.length)} jurisdictions on HCD's report`, true),
      kpi('Median review time', recentDays.length ? `${d3.median(recentDays)} days` : '—', 'submittal to HCD letter, last 12 months'),
    );
    const latest = H.concat(E).filter((r) => r.date).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 25);
    $('#latest tbody').replaceChildren(...latest.map((r) => el('tr', {},
      el('td', { class: 'd' }, fdate(r.date)),
      el('td', {}, el('button', { type: 'button', class: 'link', 'data-go': r.jur }, STATEWIDE.has(r.key) ? 'Statewide' : r.jur)),
      el('td', {}, r.src === 'HAU' ? r.type : `${r.type}${r.finding ? ` · ${r.finding}` : ''}`),
      el('td', {}, el('span', { class: 'src' }, r.src === 'HAU' ? 'HAU' : 'HE review')),
      readCell(r))));
    const qs = quarters(2019, lastQ().slice(0, 4)).filter((q) => q <= lastQ());
    const cnt = d3.rollup(H, (v) => v.length, (r) => quarter(r.date), (r) => r.group);
    const colors = groupColors();
    stackedBars($('#ov-chart'), { cats: qs, keys: GROUPS, colors, value: (q, k) => cnt.get(q)?.get(k) || 0, tickEvery: 4, label: 'HAU letters per quarter' });
  };

  // Trends
  DRAW.trends = () => {
    const sel = $('#tr-law');
    if (sel.options.length < 2) for (const l of lawsAll()) sel.append(el('option', { value: l }, l));
    const colors = groupColors();
    legend($('#tr-hau-legend'), GROUPS.map((g) => [g, colors[g]]));
    const drawHau = () => {
      const law = sel.value;
      const rows = DATA.H.filter((r) => r.date && (!law || r.laws.includes(law)));
      const qs = quarters(2018, lastQ().slice(0, 4)).filter((q) => q >= '2018-Q2' && q <= lastQ());
      const cnt = d3.rollup(rows, (v) => v.length, (r) => quarter(r.date), (r) => r.group);
      stackedBars($('#tr-hau'), { cats: qs, keys: GROUPS, colors, value: (q, k) => cnt.get(q)?.get(k) || 0, tickEvery: 4, height: 300, label: 'HAU letters per quarter' });
    };
    sel.onchange = drawHau;
    drawHau();

    const fc = { Out: css('--out'), In: css('--in'), 'No finding': css('--muted') };
    legend($('#tr-he-legend'), Object.entries(fc));
    const cyc = $('#tr-cycle');
    const drawHe = () => {
      const c = cyc.value;
      const rows = DATA.E.filter((r) => r.date >= '2018' && (!c || r.cycle === c));
      const qs = quarters(2018, lastQ().slice(0, 4)).filter((q) => q <= lastQ());
      const cnt = d3.rollup(rows, (v) => v.length, (r) => quarter(r.date), (r) => r.finding || 'No finding');
      stackedBars($('#tr-he'), { cats: qs, keys: ['Out', 'In', 'No finding'], colors: fc, value: (q, k) => cnt.get(q)?.get(k) || 0, tickEvery: 4, height: 300, label: 'Review letters per quarter' });
    };
    cyc.onchange = drawHe;
    drawHe();

    // law x year heat table
    const years = [...new Set(DATA.H.map((r) => r.year).filter((y) => /^\d{4}$/.test(y)))].sort();
    const byLaw = d3.rollup(DATA.H.flatMap((r) => r.laws.map((l) => ({ l, y: r.year }))), (v) => v.length, (d) => d.l, (d) => d.y);
    const laws = [...byLaw.keys()].sort((a, b) => d3.sum(byLaw.get(b).values()) - d3.sum(byLaw.get(a).values()));
    const max = d3.max(laws, (l) => d3.max(byLaw.get(l).values()));
    const shade = d3.scaleSequential([0, max], d3.interpolateRgb(css('--panel'), css('--accent')));
    const t = $('#tr-laws');
    t.replaceChildren(el('thead', {}, el('tr', {}, el('th', {}, 'Housing law'), ...years.map((y) => el('th', { class: 'num' }, y)), el('th', { class: 'num' }, 'Total'))),
      el('tbody', {}, ...laws.map((l) => el('tr', {}, el('td', {}, l), ...years.map((y) => {
        const v = byLaw.get(l).get(y) || 0;
        const td = el('td', { class: 'v' }, v ? fmt(v) : '');
        if (v) { td.style.background = shade(v); if (v > max * 0.55) td.style.color = css('--panel'); }
        return td;
      }), el('td', { class: 'num' }, fmt(d3.sum(byLaw.get(l).values())))))));
  };

  // Statutes & keywords
  const ADU_LABEL = 'ADU Law (66310–66342)';
  const secNum = (c) => { const m = /^(\d{3,6}(?:\.\d+)?)/.exec(c); return m ? +m[1] : null; };
  const isAdu = (c) => { const n = secNum(c); return n != null && n >= 66310 && n < 66343; };
  /** "65583(c)(10)(A)" at depth 0 -> "65583", 1 -> "65583(c)"; prefixes like "HSC " are kept. */
  const citeLevel = (c, depth) => {
    if (depth >= 9) return c;
    const m = /^((?:[A-Z]{2,4} )?[\d.]+(?:-[\d.]+)?)((?:\([^)]+\))*)/.exec(c);
    if (!m) return c;
    return m[1] + (m[2].match(/\([^)]+\)/g) || []).slice(0, depth).join('');
  };
  const codeQuery = (tag) => tag.replace(/^ADU Law.*$/, '66310-66342');
  DRAW.statutes = () => {
    let kind = 'statutes', picked = null;
    const years = d3.range(2018, +d3.max(DATA.A, (r) => r.year) + 1).map(String);
    const maxDate = d3.max(DATA.A, (r) => r.date);
    const yearAgo = d3.utcFormat('%Y-%m-%d')(d3.utcDay.offset(parse(maxDate), -365));
    const NOTES = {
      statutes: 'The Statutory Reference tags HCD assigns to each HAU letter on its dashboard. Click a row for its letters.',
      cites: 'Every statute citation found in the text of the letters, standardized (e.g. Gov. Code, § 65915, subd. (o)(8) → 65915(o)(8); other codes prefixed, e.g. HSC 17021.5). Housing element review letters have no HCD tags, so this is the only statute view for them.',
      keywords: 'The keywords HCD assigns to each HAU letter, with spelling variants grouped (e.g. "LOI" with "letter of inquiry"). Hover a keyword to see the variants it groups.',
    };
    const tagsOf = (r) => {
      const depth = +$('#st-depth').value, adu = $('#st-adu').checked;
      let t = kind === 'cites' ? r.cites.map((c) => citeLevel(c, depth)) : r[kind];
      if (adu && kind !== 'keywords') t = t.map((c) => (isAdu(c) ? ADU_LABEL : c));
      return [...new Set(t)];
    };
    const pool = () => {
      if (kind !== 'cites') return DATA.H;
      const src = $('#st-src').value;
      return src === 'HAU' ? DATA.H : src === 'HE' ? DATA.E : DATA.A;
    };
    const table = () => {
      const q = $('#st-q').value.trim().toLowerCase();
      $('#st-src-l').hidden = $('#st-depth-l').hidden = kind !== 'cites';
      $('#st-adu-l').hidden = kind === 'keywords';
      $('#st-note').textContent = NOTES[kind];
      const m = new Map();
      for (const r of pool().filter((x) => x.date)) for (const tag of tagsOf(r)) {
        if (!m.has(tag)) m.set(tag, []);
        m.get(tag).push(r);
      }
      let rows = [...m].map(([tag, rs]) => ({ tag, rs, n: rs.length, recent: rs.filter((r) => r.date >= yearAgo).length,
        first: d3.min(rs, (r) => r.date), last: d3.max(rs, (r) => r.date), byYear: years.map((y) => rs.filter((r) => r.year === y).length) }));
      if (q) rows = rows.filter((r) => r.tag.toLowerCase().includes(q) || (KW_VARIANTS[r.tag] || []).some((v) => v.toLowerCase().includes(q)));
      rows.sort((a, b) => b.n - a.n || a.tag.localeCompare(b.tag));
      const total = rows.length;
      rows = rows.slice(0, 200);
      const smax = d3.max(rows, (r) => d3.max(r.byYear));
      $('#st-title').textContent = { statutes: 'Most-cited statutes, HCD tags', cites: 'Statutes cited in the letters', keywords: 'Most-used keywords' }[kind]
        + (total > rows.length ? ` (top ${rows.length} of ${fmt(total)})` : '');
      $('#st-table tbody').replaceChildren(...rows.map((r) => {
        const vars = KW_VARIANTS[r.tag];
        const tr = el('tr', { class: `click${picked === r.tag ? ' sel' : ''}`, tabindex: '0' },
          el('td', { class: kind === 'keywords' ? '' : 'code', title: vars ? `Groups: ${vars.join('; ')}` : null }, r.tag),
          el('td', { class: 'num' }, fmt(r.n)), el('td', { class: 'num' }, r.recent ? fmt(r.recent) : ''),
          el('td', { title: `${years[0]}–${years.at(-1)}` }, sparkline(r.byYear, smax)), el('td', {}, r.first?.slice(0, 4) || ''), el('td', {}, fdate(r.last)));
        const open = () => { picked = r.tag; detail(r); table(); };
        tr.addEventListener('click', open);
        tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
        return tr;
      }));
    };
    const detail = (r) => {
      $('#st-detail').hidden = false;
      $('#st-d-title').textContent = kind === 'keywords' ? `Keyword: ${r.tag}` : r.tag === ADU_LABEL ? r.tag : `§ ${r.tag}`;
      const laws = d3.rollups(r.rs.flatMap((x) => x.laws), (v) => v.length, (d) => d).sort((a, b) => b[1] - a[1]).slice(0, 3);
      const nHe = r.rs.filter((x) => x.src === 'HE').length;
      $('#st-d-note').textContent = `${fmt(r.n)} letters${nHe && nHe < r.n ? ` (${fmt(r.n - nHe)} HAU, ${fmt(nHe)} review)` : ''}, ${r.first?.slice(0, 4)}–${r.last?.slice(0, 4)}.`
        + (laws.length ? ` Most often with ${laws.map(([l, n]) => `${l} (${n})`).join(', ')}.` : '')
        + (KW_VARIANTS[r.tag] ? ` Groups HCD's keywords: ${KW_VARIANTS[r.tag].join('; ')}.` : '');
      const p = new URLSearchParams(kind === 'keywords' ? { keyword: r.tag } : { code: codeQuery(r.tag) });
      if (kind === 'cites' && $('#st-src').value) p.set('src', $('#st-src').value);
      if (kind === 'statutes') p.set('src', 'HAU');
      $('#st-d-search').href = `#search?${p}`;
      const keys = GROUPS.concat(nHe ? ['Housing element review'] : []);
      const cnt = d3.rollup(r.rs, (v) => v.length, (x) => x.year, (x) => x.group);
      stackedBars($('#st-d-chart'), { cats: years, keys, colors: groupColors(), value: (y, k) => cnt.get(y)?.get(k) || 0, label: `Letters citing ${r.tag} per year` });
      $('#st-d-table tbody').replaceChildren(...[...r.rs].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 500).map((x) => el('tr', {},
        el('td', { class: 'd' }, fdate(x.date)), el('td', {}, el('button', { type: 'button', class: 'link', 'data-go': x.jur }, STATEWIDE.has(x.key) ? 'Statewide' : x.jur)),
        el('td', {}, x.src === 'HAU' ? x.type : `Review · ${x.type}${x.finding ? ` · ${x.finding}` : ''}`), readCell(x))));
      $('#st-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
    $$('#statutes .seg button').forEach((b) => { b.onclick = () => {
      kind = b.dataset.kind; picked = null; $('#st-detail').hidden = true;
      $$('#statutes .seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      $('#st-q').placeholder = kind === 'keywords' ? 'Filter, e.g. parking or density' : 'Filter, e.g. 65915 or 66300';
      table();
    }; });
    $('#st-q').oninput = table;
    for (const id of ['#st-src', '#st-depth', '#st-adu']) $(id).onchange = () => { picked = null; $('#st-detail').hidden = true; table(); };
    $('#st-d-close').onclick = () => { picked = null; $('#st-detail').hidden = true; table(); };
    table();
  };

  // Compliance
  DRAW.compliance = () => {
    const { C, E } = DATA;
    const status = d3.rollup(C, (v) => v.length, (c) => c.status);
    const inReview = C.filter((c) => /review/i.test(c.reviewStatus)).length;
    const box = (label, n, cls) => el('div', { class: `kpi${cls === 'out' ? ' alert' : ''}` }, el('span', { class: 'label' }, label), el('span', { class: 'value' }, fmt(n)));
    $('#co-status').replaceChildren(box('In compliance', status.get('In') || 0), box('Out of compliance', status.get('Out') || 0, 'out'),
      box('Enforcement out', status.get('Enforcement Out') || 0, 'out'), box('Under HCD review now', inReview), box('Not listed', status.get('Not listed') || 0));

    const fc = { Out: css('--out'), In: css('--in') };
    legend($('#co-find-legend'), Object.entries(fc));
    const six = E.filter((r) => r.cycle === '6' && r.finding && r.year >= '2019');
    const ys = [...new Set(six.map((r) => r.year))].sort().filter((y) => six.filter((r) => r.year === y).length >= 10);
    const cnt = d3.rollup(six, (v) => v.length, (r) => r.year, (r) => r.finding);
    stackedBars($('#co-find'), { cats: ys, keys: ['Out', 'In'], colors: fc, value: (y, k) => cnt.get(y)?.get(k) || 0, percent: true, totals: true, label: 'Share of 6th cycle review letters in or out' });

    const drawDays = () => {
      const t = $('#co-type').value;
      const rows = E.filter((r) => r.date >= '2023' && r.days != null && r.days >= 0 && (!t || r.type === t));
      const node = $('#co-days');
      node.replaceChildren();
      const W = Math.max(320, node.clientWidth), H = 240, m = { t: 14, r: 8, b: 28, l: 40 };
      const bins = d3.range(0, 190, 10).map((b) => ({ b, n: rows.filter((r) => (b === 180 ? r.days >= 180 : r.days >= b && r.days < b + 10)).length }));
      const x = d3.scaleLinear([0, 190], [m.l, W - m.r]), y = d3.scaleLinear([0, d3.max(bins, (d) => d.n) || 1], [H - m.b, m.t]).nice();
      const svg = d3.select(node).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', 'Review days distribution');
      svg.append('g').attr('class', 'grid').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)).tickFormat(fmt)).call(axisStyle);
      svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues([0, 30, 60, 90, 120, 150, 180]).tickFormat((d) => (d === 180 ? '180+' : d)).tickSizeOuter(0)).call(axisStyle);
      svg.append('g').selectAll('rect').data(bins).join('rect').attr('x', (d) => x(d.b) + 1).attr('width', (d) => x(d.b + 10) - x(d.b) - 2)
        .attr('y', (d) => y(d.n)).attr('height', (d) => y(0) - y(d.n)).attr('rx', 2)
        .attr('fill', (d) => (d.b >= 90 ? css('--out') : d.b >= 60 ? css('--s2') : css('--s1')))
        .on('mousemove', (ev, d) => showTip(ev, d.b === 180 ? '180 days or more' : `${d.b}–${d.b + 9} days`, [`${fmt(d.n)} letters`])).on('mouseleave', hideTip);
      for (const ref of [60, 90]) {
        svg.append('line').attr('class', 'ref').attr('x1', x(ref)).attr('x2', x(ref)).attr('y1', m.t - 4).attr('y2', H - m.b);
        svg.append('text').attr('x', x(ref) + 4).attr('y', m.t + 2).text(`${ref} days`);
      }
      const d = rows.map((r) => r.days);
      $('#co-days-note').textContent = d.length ? `${fmt(d.length)} letters. Median ${d3.median(d)} days; ${pct(d.filter((v) => v > 60).length / d.length)} took more than 60 days and ${pct(d.filter((v) => v > 90).length / d.length)} more than 90.` : 'No letters with a submittal date for this type.';
    };
    $('#co-type').onchange = drawDays;
    drawDays();

    const out = C.filter((c) => /out/i.test(c.status)).sort((a, b) => a.county.localeCompare(b.county) || a.jur.localeCompare(b.jur));
    $('#co-out tbody').replaceChildren(...out.map((c) => el('tr', {},
      el('td', {}, el('button', { type: 'button', class: 'link', 'data-go': c.jur }, c.jur)), el('td', {}, c.county), el('td', {}, c.cycle),
      el('td', {}, pill(c.status)), el('td', {}, `${c.recordType} (${c.reviewStatus})`), el('td', {}, fdate(c.received)), el('td', {}, fdate(c.reviewed)))));
  };

  // Jurisdiction lookup
  let placeIndex = null;
  DRAW.place = () => {
    placeIndex = new Map();
    const add = (key, name, county) => {
      if (!key || STATEWIDE.has(key)) return;
      if (!placeIndex.has(key)) placeIndex.set(key, { key, names: new Set(), county: '' });
      const p = placeIndex.get(key); p.names.add(name); if (county && !p.county) p.county = county;
    };
    DATA.E.forEach((r) => add(r.key, r.jur, r.county));
    DATA.H.forEach((r) => add(r.key, r.jur));
    DATA.C.forEach((c) => add(c.key, c.jur, c.county));
    const label = (p) => [...p.names].find((n) => n !== n.toUpperCase()) || [...p.names][0];
    const byName = new Map();
    for (const p of placeIndex.values()) {
      byName.set(p.key, p);
      for (const n of p.names) byName.set(n.toLowerCase().replace(/^(city|town) of /, '').replace(/[^a-z]/g, ''), p);
    }
    $('#pl-list').replaceChildren(...[...placeIndex.values()].map((p) => el('option', { value: label(p) })).sort((a, b) => a.value.localeCompare(b.value)));
    const q = $('#pl-q');
    const go = () => {
      const p = byName.get(q.value.toLowerCase().replace(/^(city|town) of /, '').replace(/[^a-z]/g, ''));
      if (p) renderPlace(p, label(p));
    };
    q.onchange = go;
    q.oninput = go;
  };
  function renderPlace(p, name) {
    const hau = DATA.H.filter((r) => r.key === p.key), he = DATA.E.filter((r) => r.key === p.key);
    const c = DATA.C.find((x) => x.key === p.key);
    const all = hau.concat(he).sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    const findings = he.filter((r) => r.finding);
    const head = el('div', { class: 'place-head' }, el('h3', {}, name), c ? pill(c.status) : null);
    const facts = el('p', { class: 'facts' },
      p.county ? el('span', {}, 'County ', el('b', {}, p.county)) : null,
      c ? el('span', {}, `${c.cycle}: `, el('b', {}, `${c.recordType}, ${c.reviewStatus}`), c.reviewed ? ` (reviewed ${fdate(c.reviewed)})` : '') : null,
      el('span', {}, el('b', {}, fmt(hau.length)), ' HAU letters'),
      el('span', {}, el('b', {}, fmt(he.length)), ' review letters', findings.length ? ` (${findings.filter((r) => r.finding === 'Out').length} out, ${findings.filter((r) => r.finding === 'In').length} in)` : ''));
    const tbody = el('tbody', {}, ...all.map((r) => el('tr', {},
      el('td', { class: 'd' }, fdate(r.date)), el('td', {}, el('span', { class: 'src' }, r.src === 'HAU' ? 'HAU' : 'HE review')),
      el('td', {}, r.type),
      el('td', { class: 'hide-sm' }, r.src === 'HAU' ? [r.laws.join('; '), r.statutes.length ? ` · ${r.statutes.slice(0, 6).join(', ')}${r.statutes.length > 6 ? '…' : ''}` : ''].join('')
        : [r.cycle ? `Cycle ${r.cycle}` : '', r.finding ? ` · ${r.finding}` : '', r.days != null ? ` · ${r.days} days` : ''].join('')),
      readCell(r))));
    const table = el('div', { class: 'tablebox tall' }, el('table', { class: 't' },
      el('thead', {}, el('tr', {}, el('th', {}, 'Date'), el('th', {}, 'Source'), el('th', {}, 'Letter'), el('th', { class: 'hide-sm' }, 'Details'), el('th', {}, 'Read'))), tbody));
    $('#pl-body').replaceChildren(head, facts, all.length ? table : el('p', { class: 'empty' }, 'No letters on file.'));
  }
  function goPlace(name) {
    location.hash = '#place';
    show('place');
    $('#pl-q').value = name;
    $('#pl-q').dispatchEvent(new Event('change'));
  }

  // ---------- search ----------
  /* Full-text index: site/search/ (scripts/build_search_index.py). Tokenizer and hash must match it. */
  const TOKEN = /[a-z0-9]+(?:['.][a-z0-9]+)*/g;
  const toks = (s) => (s || '').toLowerCase().replace(/[‘’]/g, "'").match(TOKEN) || [];
  const fnv1a = (s) => { let h = 0x811c9dc5; for (const b of new TextEncoder().encode(s)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; } return h; };
  const INDEX = { meta: null, docs: null, shards: new Map(), fail: false };
  async function indexReady() {
    if (!INDEX.meta && !INDEX.fail) {
      try {
        [INDEX.meta, INDEX.docs] = await Promise.all(['meta', 'docs'].map((n) => fetch(`search/${n}.json`).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })));
      } catch { INDEX.fail = true; }
    }
    return !INDEX.fail;
  }
  async function postings(term) {
    const n = fnv1a(term) % INDEX.meta.shards;
    if (!INDEX.shards.has(n)) INDEX.shards.set(n, fetch(`search/s/${n}.json`).then((r) => r.json()).catch(() => ({})));
    const raw = (await INDEX.shards.get(n))[term];
    if (!raw) return { ids: [], tf: null };
    const [idp, tfp] = raw.split('|');
    let prev = 0;
    const ids = idp.split(',').map((x) => (prev += parseInt(x, 36)));
    return { ids, tf: tfp ? [...tfp].map((c) => parseInt(c, 36)) : null };
  }
  /** Parse 'a "b c" -d multi-family' -> words [a], phrases [[b,c],[multi,family]], minus [d]. */
  function parseQuery(q) {
    const words = [], phrases = [], minus = [];
    const rest = (q || '').replace(/"([^"]*)"?/g, (_, p) => { const t = toks(p); if (t.length > 1) phrases.push(t); else words.push(...t); return ' '; });
    for (const chunk of rest.split(/\s+/).filter(Boolean)) {
      const neg = chunk.startsWith('-') && chunk.length > 1;
      const t = toks(neg ? chunk.slice(1) : chunk);
      if (neg) minus.push(...t); else if (t.length > 1) phrases.push(t); else words.push(...t);
    }
    return { words: [...new Set(words)], phrases, minus };
  }
  /** -> Map(docId -> score), or null when the query has no words. */
  async function textSearch(q) {
    const { words, phrases, minus } = parseQuery(q);
    if (!words.length && !phrases.length) return null;
    if (!(await indexReady())) throw new Error('The search index is not built yet.');
    const N = INDEX.meta.docs;
    const need = [...words.map((w) => ({ term: w, w: 1 })), ...phrases.flatMap((p) => p.slice(1).map((t, i) => ({ term: `${p[i]} ${t}`, w: 1.5 })))];
    const lists = await Promise.all(need.map((n) => postings(n.term)));
    const negs = await Promise.all(minus.map((m) => postings(m)));
    let score = null;
    lists.forEach(({ ids, tf }, k) => {
      const idf = Math.log(1 + N / Math.max(1, ids.length)) * need[k].w;
      const m = new Map(ids.map((d, i) => [d, idf * (tf ? 1 + Math.log(tf[i]) : 1)]));
      if (score === null) score = m;
      else { for (const d of [...score.keys()]) { if (m.has(d)) score.set(d, score.get(d) + m.get(d)); else score.delete(d); } }
    });
    for (const { ids } of negs) for (const d of ids) score.delete(d);
    return score;
  }
  /** Code query "65915(o)", "HSC 17021.5", "66310-66342" -> predicate on a normalized citation or HCD tag. */
  function codeMatcher(q) {
    let s = (q || '').trim();
    if (!s) return null;
    s = s.replace(/gov(ernment|'t|\.)?\s*code,?/i, '').replace(/§+/g, '').replace(/\bsect?(ion)?s?\.?/i, '')
      .replace(/subd(ivision)?s?\.?|para(graph)?\.?/gi, '').replace(/,/g, '').trim();
    const pre = /^(HSC|PRC|CIV|CCP|RTC|WIC|EVID|FAM|PEN|WAT)\s*/i.exec(s);
    const code = pre ? `${pre[1].toUpperCase()} ` : '';
    s = s.slice(pre ? pre[0].length : 0).replace(/\s+/g, '');
    const range = /^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$/.exec(s);
    if (range) {
      const lo = +range[1], hi = +range[2];
      return (c) => { if (code ? !c.startsWith(code) : /^[A-Z]/.test(c)) return false; const n = secNum(c.replace(/^[A-Z]+ /, '')); return n != null && n >= lo && n <= hi; };
    }
    const want = code + s;
    return (c) => c === want || c.startsWith(`${want}(`) || c.startsWith(`${want}-`);
  }

  let PLACES = null;
  function places() {
    if (PLACES) return PLACES;
    const byKey = new Map(), byName = new Map(), counties = new Map();
    const norm = (n) => (n || '').toLowerCase().replace(/^(city|town) of /, '').replace(/[^a-z]/g, '');
    const add = (key, name, county) => {
      if (!key || STATEWIDE.has(key)) return;
      if (!byKey.has(key)) byKey.set(key, { key, names: new Set(), county: '' });
      const p = byKey.get(key); p.names.add(name); if (county && !p.county) p.county = county;
    };
    DATA.E.forEach((r) => add(r.key, r.jur, r.county));
    DATA.H.forEach((r) => add(r.key, r.jur));
    DATA.C.forEach((c) => add(c.key, c.jur, c.county));
    const label = (p) => [...p.names].find((n) => n !== n.toUpperCase()) || [...p.names][0];
    for (const p of byKey.values()) {
      byName.set(p.key, p);
      for (const n of p.names) byName.set(norm(n), p);
      if (p.county) { const k = norm(p.county); if (!counties.has(k)) counties.set(k, { name: p.county, keys: new Set() }); counties.get(k).keys.add(p.key); }
    }
    for (const c of counties.values()) { const own = byName.get(norm(`${c.name} County`)); if (own) c.keys.add(own.key); }
    PLACES = { byKey, byName, counties, norm, label };
    return PLACES;
  }

  const SEARCH = (() => {
    const F = ['q', 'code', 'jur', 'src', 'type', 'law', 'keyword', 'cycle', 'finding', 'from', 'to', 'sort', 'text'];
    const field = { q: '#sr-q', code: '#sr-code', jur: '#sr-jur', src: '#sr-src', type: '#sr-type', law: '#sr-law', keyword: '#sr-kw',
      cycle: '#sr-cycle', finding: '#sr-finding', from: '#sr-from', to: '#sr-to', sort: '#sr-sort', text: '#sr-text' };
    let results = [], shown = 0, lastHash = '', runId = 0, current = {};
    const TEXT = new Map();
    const getText = (path) => {
      if (!TEXT.has(path)) {
        TEXT.set(path, fetch(`https://raw.githubusercontent.com/${REPO}/main/${path.split('/').map(encodeURIComponent).join('/')}`)
          .then((r) => (r.ok ? r.text() : '')).catch(() => ''));
      }
      return TEXT.get(path);
    };
    const read = () => Object.fromEntries(F.map((k) => {
      const n = $(field[k]);
      return [k, n.type === 'checkbox' ? (n.checked ? '1' : '') : n.value.trim()];
    }).filter(([, v]) => v));
    const write = (p) => F.forEach((k) => { const n = $(field[k]); if (n.type === 'checkbox') n.checked = !!p[k]; else n.value = p[k] || ''; });

    function fill() {
      const types = [...GROUPS.map((g) => [`HAU:${g}`, `HAU · ${g}`]),
        ...[...new Set(DATA.E.map((r) => r.type).filter(Boolean))].sort().map((t) => [`HE:${t}`, `Review · ${t}`])];
      $('#sr-type').append(...types.map(([v, l]) => el('option', { value: v }, l)));
      $('#sr-law').append(...lawsAll().map((l) => el('option', { value: l }, l)));
      const kws = d3.rollups(DATA.H.flatMap((r) => r.keywords), (v) => v.length, (k) => k).filter(([, n]) => n >= 2).sort((a, b) => a[0].localeCompare(b[0]));
      $('#sr-kw').append(...kws.map(([k, n]) => el('option', { value: k }, `${k} (${n})`)));
      const P = places();
      const names = [...P.byKey.values()].map(P.label).concat([...P.counties.values()].map((c) => `${c.name} County`));
      $('#sr-jurs').replaceChildren(...[...new Set(names)].sort().map((n) => el('option', { value: n })));
    }

    async function run(p) {
      const id = ++runId;
      current = p;
      const out = $('#sr-out');
      const has = Object.keys(p).some((k) => k !== 'sort');
      $('#sr-help').hidden = has;
      if (!has) { out.hidden = true; return; }
      out.hidden = false;
      $('#sr-count').textContent = 'Searching…';
      $('#sr-note').textContent = '';
      $('#sr-table tbody').replaceChildren();
      $('#sr-more').hidden = true;
      let scores = null;
      try { scores = await textSearch(p.q); } catch (e) { $('#sr-count').textContent = e.message; return; }
      if (id !== runId) return;
      const cm = codeMatcher(p.code);
      let jurKeys = null;
      if (p.jur) {
        const P = places(), k = P.norm(p.jur), cty = P.counties.get(k.replace(/county$/, ''));
        if (/county$/i.test(p.jur.trim()) && cty) jurKeys = cty.keys;
        else if (P.byName.get(k)) jurKeys = new Set([P.byName.get(k).key]);
        else if (cty) jurKeys = cty.keys;
        else jurKeys = new Set([...P.byKey.values()].filter((x) => [...x.names].some((n) => P.norm(n).includes(k))).map((x) => x.key));
      }
      let pool = p.src === 'HAU' ? DATA.H : p.src === 'HE' ? DATA.E : DATA.A;
      const textScore = new Map();
      if (scores) {
        const docs = INDEX.docs;
        for (const [d, sc] of scores) { const [s, i] = docs[d]; textScore.set(s ? DATA.E[i] : DATA.H[i], sc); }
        pool = pool.filter((r) => textScore.has(r));
      }
      const [tSrc, tVal] = (p.type || '').split(/:(.*)/s);
      results = pool.filter((r) => (!p.text || r.text) && (!jurKeys || jurKeys.has(r.key))
        && (!p.type || (r.src === tSrc && (tSrc === 'HAU' ? r.group === tVal : r.type === tVal)))
        && (!p.law || r.laws.includes(p.law)) && (!p.keyword || r.keywords.includes(p.keyword))
        && (!p.cycle || r.cycle === p.cycle) && (!p.finding || r.finding === p.finding)
        && (!p.from || (r.date && r.date >= p.from)) && (!p.to || (r.date && r.date <= p.to)))
        .map((r) => ({ r, score: textScore.get(r) || 0, codes: cm ? [...new Set(r.cites.filter(cm).concat(r.statutes.filter(cm).map((s) => `${s} (tag)`)))] : r.cites.slice(0, 4) }))
        .filter((x) => !cm || x.codes.length);
      const sort = p.sort || (scores ? '' : 'new');
      results.sort(sort === 'old' ? (a, b) => (a.r.date || '').localeCompare(b.r.date || '')
        : sort === 'new' ? (a, b) => (b.r.date || '').localeCompare(a.r.date || '')
          : (a, b) => b.score - a.score || (b.r.date || '').localeCompare(a.r.date || ''));
      const nH = results.filter((x) => x.r.src === 'HAU').length;
      $('#sr-count').textContent = `${fmt(results.length)} letter${results.length === 1 ? '' : 's'}`;
      $('#sr-note').textContent = results.length ? `${fmt(nH)} HAU, ${fmt(results.length - nH)} housing element review.`
        + (scores ? ' Text matches cover letters with a public or requested copy only.' : '') : 'Nothing matched. Try fewer words or filters.';
      shown = 0;
      more();
    }

    function more() {
      const p = current, terms = parseQuery(p.q);
      const tbody = $('#sr-table tbody');
      const batch = results.slice(shown, shown + 50);
      shown += batch.length;
      for (const { r, codes } of batch) {
        const what = r.src === 'HAU' ? `HAU · ${r.type}` : `Review · ${r.type}${r.cycle ? ` · cycle ${r.cycle}` : ''}${r.finding ? ` · ${r.finding}` : ''}`;
        tbody.append(el('tr', { class: 'hit' },
          el('td', { class: 'd' }, fdate(r.date)),
          el('td', {}, el('button', { type: 'button', class: 'link', 'data-go': r.jur }, STATEWIDE.has(r.key) ? 'Statewide' : r.jur), r.county ? el('div', { class: 'src' }, r.county) : null),
          el('td', {}, what, r.laws.length ? el('div', { class: 'src' }, r.laws.join('; ')) : null),
          el('td', { class: 'hide-sm' }, el('div', { class: 'codes code' }, ...codes.slice(0, 6).map((c) => el('span', {}, c)), codes.length > 6 ? el('span', {}, `+${codes.length - 6}`) : null)),
          readCell(r)));
        if ((p.q || p.code) && r.text) {
          const td = el('td', { colspan: '5' }, el('span', { class: 'busy' }, '…'));
          tbody.append(el('tr', { class: 'snip' }, td));
          getText(r.text).then((t) => td.replaceChildren(...snippet(t, terms, p.code ? codes : [])));
        }
      }
      $('#sr-more').hidden = shown >= results.length;
      $('#sr-more').textContent = `Show more (${fmt(results.length - shown)} left)`;
    }

    /** ~280 characters around the first match, with every query term marked. */
    function snippet(text, { words, phrases }, codes) {
      if (!text) return [el('span', { class: 'busy' }, 'Text could not be loaded.')];
      const flat = text.replace(/\s+/g, ' ');
      const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const pats = [...phrases.map((p) => p.map(esc).join("[^a-z0-9.']+")), ...words.map((w) => `${esc(w)}`)];
      const secs = codes.map((c) => c.replace(/ \(tag\)$/, '').replace(/^[A-Z]+ /, '').match(/^[\d.]+/)?.[0]).filter(Boolean);
      pats.push(...[...new Set(secs)].map(esc));
      if (!pats.length) return [flat.slice(0, 200) + '…'];
      const rx = new RegExp(`(?<![a-z0-9])(${pats.join('|')})(?![a-z0-9])`, 'gi');
      // center on the first exact phrase if there is one, else the first match of anything
      const lead = phrases.length ? new RegExp(`(?<![a-z0-9])(${pats[0]})(?![a-z0-9])`, 'i').exec(flat) : null;
      const first = lead || rx.exec(flat);
      const at = first ? first.index : 0;
      let a = Math.max(0, at - 120), b = Math.min(flat.length, at + 160);
      while (a > 0 && flat[a] !== ' ') a--;
      while (b < flat.length && flat[b] !== ' ') b++;
      const part = flat.slice(a, b);
      const nodes = [a > 0 ? '…' : ''];
      let last = 0;
      rx.lastIndex = 0;
      for (const m of part.matchAll(rx)) { nodes.push(part.slice(last, m.index), el('mark', {}, m[0])); last = m.index + m[0].length; }
      nodes.push(part.slice(last), b < flat.length ? '…' : '');
      return nodes;
    }

    function csv() {
      const head = ['date', 'jurisdiction', 'county', 'source', 'letter_type', 'cycle', 'finding', 'housing_laws', 'code_sections', 'pdf', 'text'];
      const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
      const lines = [head.join(',')].concat(results.map(({ r, codes }) => [r.date, r.jur, r.county || places().byKey.get(r.key)?.county || '', r.src === 'HAU' ? 'HAU' : 'HE review',
        r.type, r.cycle || '', r.finding || '', r.laws.join('; '), codes.join('; '), r.pdf || (r.req ? gh(r.req) : ''), r.text ? gh(r.text) : ''].map(q).join(',')));
      const a = el('a', { href: URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })), download: `hcd-letters-search-${new Date().toISOString().slice(0, 10)}.csv` });
      document.body.append(a); a.click(); a.remove();
    }

    function go(p) {
      const qs = new URLSearchParams(p).toString();
      lastHash = `#search${qs ? `?${qs}` : ''}`;
      if (location.hash !== lastHash) history.replaceState(null, '', lastHash);
      run(p);
    }
    return {
      init() {
        fill();
        $('#sr-form').addEventListener('submit', (e) => { e.preventDefault(); go(read()); });
        for (const k of ['src', 'type', 'law', 'keyword', 'cycle', 'finding', 'from', 'to', 'sort', 'text']) $(field[k]).addEventListener('change', () => go(read()));
        $('#sr-clear').onclick = () => { write({}); go({}); };
        $('#sr-more').onclick = more;
        $('#sr-csv').onclick = csv;
      },
      fromQuery(qs) {
        const p = Object.fromEntries(new URLSearchParams(qs));
        write(p);
        if (p.q) $('#qs-q').value = p.q;
        go(read());
      },
      ownHash: () => location.hash === lastHash,
    };
  })();
  DRAW.search = () => SEARCH.init();

  // ---------- boot ----------
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-go]');
    if (b) { e.preventDefault(); goPlace(b.dataset.go); }
    const sb = e.target.closest('[data-search]');
    if (sb) { e.preventDefault(); location.hash = `#search?${sb.dataset.search}`; }
  });
  addEventListener('hashchange', () => { if (!SEARCH.ownHash()) show(location.hash.slice(1)); });
  let resizeT, lastW = innerWidth;
  addEventListener('resize', () => {
    if (innerWidth === lastW) return;  // ignore mobile address-bar height changes
    lastW = innerWidth;
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      const tab = (location.hash.slice(1) || 'overview').split('?')[0];
      Object.keys(drawn).filter((k) => k !== 'search').forEach((k) => delete drawn[k]);
      if (tab !== 'search') show(tab);
    }, 250);
  });
  $('#qs').addEventListener('submit', (e) => {
    e.preventDefault();
    const v = $('#qs-q').value.trim();
    location.hash = `#search?${new URLSearchParams(v ? { q: v } : {})}`;
  });

  load().then((d) => {
    DATA = d;
    $('#repo-link').href = `https://github.com/${REPO}`;
    $('#stamp').textContent = d.meta ? `Updated ${fdate(d.meta.built.slice(0, 10))} · ${fmt(d.H.length)} HAU and ${fmt(d.E.length)} review letters` : 'Data not built yet';
    show(location.hash.slice(1) || 'overview');
  }).catch((err) => { $('#stamp').textContent = `Could not load data: ${err.message}`; });
})();
