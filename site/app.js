/* HCD Letter Tracker: reads data/*.json (built by scripts/build_site_data.py) and draws five tabs. */
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
    const [hau, he, comp, meta] = await Promise.all(['hau', 'he', 'compliance', 'meta'].map(get));
    if (meta?.repo) REPO = meta.repo;
    const H = (hau?.rows || []).map((r) => {
      const [date, jur, type, laws, statutes, keywords, pdf, text, cs, task, req] = r;
      const t = hau.dict.type[type];
      return { src: 'HAU', date, year: date.slice(0, 4), jur: hau.dict.jur[jur], key: hau.jurKey[jur], type: t, group: hau.typeGroup[t],
        laws: laws.map((i) => hau.dict.law[i]), statutes: statutes.map((i) => hau.dict.statute[i]),
        keywords: keywords.map((i) => hau.dict.keyword[i]), pdf, text, cs, task, req, contact: !pdf && !req };
    });
    const E = (he?.rows || []).map((r) => {
      const [date, jur, county, type, cycle, finding, submittal, days, pdf, text, hePdf, heType, contact, req] = r;
      return { src: 'HE', date, year: date.slice(0, 4), jur: he.dict.jur[jur], key: he.jurKey[jur], county: he.dict.county[county],
        type: he.dict.type[type], cycle, finding, submittal, days, pdf, text, hePdf, heType: he.dict.heType[heType], req, contact: contact === 'contact' };
    });
    const C = (comp?.rows || []).map(([county, jurisdiction, cycle, recordType, reviewStatus, received, reviewed, status, key]) =>
      ({ county, jur: jurisdiction, cycle, recordType, reviewStatus, received, reviewed, status, key }));
    return { H, E, C, meta };
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
  function show(tab) {
    if (!$$('.panel').some((p) => p.id === tab)) tab = 'overview';
    $$('.panel').forEach((p) => { p.hidden = p.id !== tab; });
    $$('.tabs a').forEach((a) => a.setAttribute('aria-selected', String(a.dataset.tab === tab)));
    if (!drawn[tab] && DATA) { DRAW[tab](); drawn[tab] = true; }
  }

  let DATA = null;
  const DRAW = {};
  const lawsAll = () => [...new Set(DATA.H.flatMap((r) => r.laws))].sort();
  const groupColors = () => ({ 'Technical assistance': css('--s1'), Enforcement: css('--out'), 'Ordinance review': css('--s2'), 'Resolution & support': css('--s4'), Other: css('--s5') });
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
  DRAW.statutes = () => {
    let kind = 'statutes', picked = null;
    const years = d3.range(2018, +d3.max(DATA.H, (r) => r.year) + 1).map(String);
    const maxDate = d3.max(DATA.H, (r) => r.date);
    const yearAgo = d3.utcFormat('%Y-%m-%d')(d3.utcDay.offset(parse(maxDate), -365));
    const table = () => {
      const q = $('#st-q').value.trim().toLowerCase();
      const m = new Map();
      for (const r of DATA.H.filter((x) => x.date)) for (const tag of r[kind]) {
        if (!m.has(tag)) m.set(tag, []);
        m.get(tag).push(r);
      }
      let rows = [...m].map(([tag, rs]) => ({ tag, rs, n: rs.length, recent: rs.filter((r) => r.date >= yearAgo).length,
        first: d3.min(rs, (r) => r.date), last: d3.max(rs, (r) => r.date), byYear: years.map((y) => rs.filter((r) => r.year === y).length) }));
      if (q) rows = rows.filter((r) => r.tag.toLowerCase().includes(q));
      rows.sort((a, b) => b.n - a.n || a.tag.localeCompare(b.tag));
      rows = rows.slice(0, 150);
      const smax = d3.max(rows, (r) => d3.max(r.byYear));
      $('#st-title').textContent = kind === 'statutes' ? 'Most-cited statutes' : 'Most-used keywords';
      $('#st-table tbody').replaceChildren(...rows.map((r) => {
        const tr = el('tr', { class: `click${picked === r.tag ? ' sel' : ''}`, tabindex: '0' },
          el('td', { class: kind === 'statutes' ? 'code' : '' }, r.tag), el('td', { class: 'num' }, fmt(r.n)), el('td', { class: 'num' }, r.recent ? fmt(r.recent) : ''),
          el('td', { title: `${years[0]}–${years.at(-1)}` }, sparkline(r.byYear, smax)), el('td', {}, r.first?.slice(0, 4) || ''), el('td', {}, fdate(r.last)));
        const open = () => { picked = r.tag; detail(r); table(); };
        tr.addEventListener('click', open);
        tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(); });
        return tr;
      }));
    };
    const detail = (r) => {
      $('#st-detail').hidden = false;
      $('#st-d-title').textContent = kind === 'statutes' ? `§ ${r.tag}` : `Keyword: ${r.tag}`;
      const laws = d3.rollups(r.rs.flatMap((x) => x.laws), (v) => v.length, (d) => d).sort((a, b) => b[1] - a[1]).slice(0, 3);
      $('#st-d-note').textContent = `${fmt(r.n)} letters, ${r.first?.slice(0, 4)}–${r.last?.slice(0, 4)}. Most often with ${laws.map(([l, n]) => `${l} (${n})`).join(', ')}.`;
      const cnt = d3.rollup(r.rs, (v) => v.length, (x) => x.year, (x) => x.group);
      stackedBars($('#st-d-chart'), { cats: years, keys: GROUPS, colors: groupColors(), value: (y, k) => cnt.get(y)?.get(k) || 0, label: `Letters citing ${r.tag} per year` });
      $('#st-d-table tbody').replaceChildren(...[...r.rs].sort((a, b) => b.date.localeCompare(a.date)).map((x) => el('tr', {},
        el('td', { class: 'd' }, fdate(x.date)), el('td', {}, el('button', { type: 'button', class: 'link', 'data-go': x.jur }, STATEWIDE.has(x.key) ? 'Statewide' : x.jur)),
        el('td', {}, x.type), readCell(x))));
      $('#st-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
    $$('#statutes .seg button').forEach((b) => { b.onclick = () => {
      kind = b.dataset.kind; picked = null; $('#st-detail').hidden = true;
      $$('#statutes .seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      $('#st-q').placeholder = kind === 'statutes' ? 'Filter, e.g. 65915 or 66300' : 'Filter, e.g. parking or density';
      table();
    }; });
    $('#st-q').oninput = table;
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

  // ---------- boot ----------
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-go]');
    if (b) { e.preventDefault(); goPlace(b.dataset.go); }
  });
  addEventListener('hashchange', () => show(location.hash.slice(1)));
  let resizeT;
  addEventListener('resize', () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => { const tab = location.hash.slice(1) || 'overview'; Object.keys(drawn).forEach((k) => delete drawn[k]); show(tab); }, 250);
  });

  load().then((d) => {
    DATA = d;
    $('#repo-link').href = `https://github.com/${REPO}`;
    $('#stamp').textContent = d.meta ? `Updated ${fdate(d.meta.built.slice(0, 10))} · ${fmt(d.H.length)} HAU and ${fmt(d.E.length)} review letters` : 'Data not built yet';
    show(location.hash.slice(1) || 'overview');
  }).catch((err) => { $('#stamp').textContent = `Could not load data: ${err.message}`; });
})();
