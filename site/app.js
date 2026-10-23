/* HCD Letter Tracker: reads data/*.json (scripts/build_site_data.py) and search/ (scripts/build_search_index.py) and draws six tabs. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const fmt = d3.format(',');
  const pct = d3.format('.0%');
  const parse = d3.utcParse('%Y-%m-%d');
  const fdate = (s) => (s ? d3.utcFormat('%b %-d, %Y')(parse(s)) : '—');
  // build time is UTC; show the California calendar date
  const caDate = (iso) => new Date(iso).toLocaleDateString('en-US', { timeZone: 'America/Los_Angeles', month: 'short', day: 'numeric', year: 'numeric' });
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
  const readCell = (r) => el('td', { class: 'read' }, r.text ? el('button', { type: 'button', class: 'link', 'data-read': r.text }, 'Read') : null, link(r.pdf || (r.req && gh(r.req)), 'PDF'),
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


  /** Horizontal bars: items [{label, value, title?}] */
  function hbars(node, items, { fmtv = fmt, color = css('--accent'), max, onClick } = {}) {
    node.replaceChildren();
    const W = Math.max(300, node.clientWidth), rowH = 22, m = { t: 4, r: 44, b: 4, l: Math.min(260, W * 0.48) };
    const H = m.t + m.b + items.length * rowH;
    const x = d3.scaleLinear([0, max ?? (d3.max(items, (d) => d.value) || 1)], [m.l, W - m.r]);
    const svg = d3.select(node).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img');
    const g = svg.selectAll('g').data(items).join('g').attr('transform', (_, i) => `translate(0,${m.t + i * rowH})`)
      .style('cursor', onClick ? 'pointer' : null).on('click', (_, d) => onClick?.(d));
    g.append('text').attr('x', m.l - 6).attr('y', rowH / 2).attr('dy', '0.35em').attr('text-anchor', 'end')
      .text((d) => (d.label.length > 44 ? `${d.label.slice(0, 42)}…` : d.label)).append('title').text((d) => d.title || d.label);
    g.append('rect').attr('x', m.l).attr('y', 4).attr('height', rowH - 8).attr('rx', 2).attr('width', (d) => Math.max(0, x(d.value) - m.l)).attr('fill', color);
    g.append('text').attr('x', (d) => x(d.value) + 4).attr('y', rowH / 2).attr('dy', '0.35em').text((d) => fmtv(d.value));
    return svg;
  }

  // ---------- page-address state (per tab), so views can be shared ----------
  const params = () => new URLSearchParams((location.hash.split('?')[1]) || '');
  function setParams(obj) {
    const [tab] = (location.hash.slice(1) || 'overview').split('?');
    const p = params();
    for (const [k, v] of Object.entries(obj)) { if (v == null || v === '') p.delete(k); else p.set(k, v); }
    const qs = p.toString();
    history.replaceState(null, '', `#${tab}${qs ? `?${qs}` : ''}`);
  }

  /**
   * Sortable, filterable table with CSV download and "show more".
   * columns: [{ key, label, value: r => sortable value, render?: r => Node|string, num?, cls?, filter?: 'select', csv?: r => string, hideSm? }]
   */
  function dataTable(host, { id, columns, rows, sort, pageSize = 100, onRow, csvName, empty = 'Nothing to show.' }) {
    const P = params();
    const st = { q: P.get(`${id}.q`) || '', sort: P.get(`${id}.s`) || sort || '', f: {}, shown: pageSize };
    for (const c of columns) if (c.filter) st.f[c.key] = P.get(`${id}.f.${c.key}`) || '';
    const val = (c, r) => (c.value ? c.value(r) : r[c.key]);
    const txt = (c, r) => (c.csv ? c.csv(r) : String(val(c, r) ?? ''));
    const bar = el('div', { class: 'dt-bar' });
    const q = el('input', { type: 'search', placeholder: 'Filter rows', 'aria-label': 'Filter rows', value: st.q });
    bar.append(el('label', { class: 'ctl' }, 'Filter', q));
    const sels = {};
    for (const c of columns.filter((c) => c.filter)) {
      const vals = [...new Set(rows.flatMap((r) => { const v = val(c, r); return Array.isArray(v) ? v : [v]; }).filter((v) => v !== '' && v != null).map(String))]
        .sort((a, b) => (c.num ? a - b : a.localeCompare(b)));
      const s = el('select', {}, el('option', { value: '' }, 'All'), ...vals.map((v) => el('option', { value: v }, v)));
      s.value = st.f[c.key];
      sels[c.key] = s;
      bar.append(el('label', { class: 'ctl' }, c.label, s));
    }
    const count = el('span', { class: 'dt-count grow' });
    const dl = el('button', { type: 'button', class: 'btn ghost sm' }, 'Download CSV');
    bar.append(count, dl);
    const thead = el('tr', {}, ...columns.map((c) => el('th', { class: `sortable${c.num ? ' num' : ''}${c.hideSm ? ' hide-sm' : ''}`, 'data-k': c.key, tabindex: '0' }, c.label)));
    const tbody = el('tbody');
    const more = el('button', { type: 'button', class: 'btn ghost sm', hidden: true });
    const table = el('table', { class: 't' }, el('thead', {}, thead), tbody);
    host.replaceChildren(el('div', { class: 'dt' }, bar, el('div', { class: 'tablebox tall' }, table), more));
    let view = [];
    const save = () => setParams({ [`${id}.q`]: st.q, [`${id}.s`]: st.sort, ...Object.fromEntries(Object.entries(st.f).map(([k, v]) => [`${id}.f.${k}`, v])) });
    function compute() {
      const needle = st.q.toLowerCase();
      view = rows.filter((r) => (!needle || columns.some((c) => txt(c, r).toLowerCase().includes(needle)))
        && Object.entries(st.f).every(([k, v]) => { if (!v) return true; const c = columns.find((x) => x.key === k); const x = val(c, r); return Array.isArray(x) ? x.map(String).includes(v) : String(x) === v; }));
      if (st.sort) {
        const desc = st.sort.endsWith('-'), k = st.sort.replace(/[-+]$/, ''), c = columns.find((x) => x.key === k);
        if (c) view.sort((a, b) => { const x = val(c, a), y = val(c, b); const r = typeof x === 'number' && typeof y === 'number' ? x - y : String(x ?? '').localeCompare(String(y ?? ''), undefined, { numeric: true }); return desc ? -r : r; });
      }
      for (const th of thead.children) {
        const k = th.dataset.k;
        th.setAttribute('aria-sort', st.sort.replace(/[-+]$/, '') === k ? (st.sort.endsWith('-') ? 'descending' : 'ascending') : 'none');
      }
      draw(true);
    }
    function draw(reset) {
      if (reset) { tbody.replaceChildren(); st.drawn = 0; }
      const end = Math.min(view.length, reset ? st.shown : st.drawn + pageSize);
      for (let i = st.drawn; i < end; i++) {
        const r = view[i];
        const tr = el('tr', { class: onRow ? 'click' : null, tabindex: onRow ? '0' : null },
          ...columns.map((c) => { const v = c.render ? c.render(r) : val(c, r); const td = el('td', { class: [c.num ? 'num' : '', c.cls || '', c.hideSm ? 'hide-sm' : ''].join(' ').trim() || null }); td.append(v instanceof Node ? v : document.createTextNode(c.num && typeof v === 'number' ? fmt(v) : String(v ?? ''))); return td; }));
        if (onRow) {
          tr.addEventListener('click', (e) => { if (!e.target.closest('a,button')) onRow(r, tr); });
          tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') onRow(r, tr); });
        }
        tbody.append(tr);
      }
      st.drawn = end;
      if (!view.length) tbody.append(el('tr', {}, el('td', { colspan: String(columns.length), class: 'empty' }, empty)));
      count.textContent = `${fmt(view.length)} of ${fmt(rows.length)} rows`;
      more.hidden = st.drawn >= view.length;
      more.textContent = `Show more (${fmt(view.length - st.drawn)} left)`;
    }
    q.addEventListener('input', () => { st.q = q.value.trim(); save(); compute(); });
    for (const [k, s] of Object.entries(sels)) s.addEventListener('change', () => { st.f[k] = s.value; save(); compute(); });
    thead.addEventListener('click', (e) => {
      const th = e.target.closest('th'); if (!th) return;
      const k = th.dataset.k, c = columns.find((x) => x.key === k);
      const cur = st.sort.replace(/[-+]$/, '');
      st.sort = cur === k ? (st.sort.endsWith('-') ? `${k}+` : `${k}-`) : `${k}${c.num ? '-' : '+'}`;
      save(); compute();
    });
    thead.addEventListener('keydown', (e) => { if (e.key === 'Enter') e.target.click(); });
    more.onclick = () => draw(false);
    dl.onclick = () => {
      const qv = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
      const lines = [columns.map((c) => qv(c.label)).join(',')].concat(view.map((r) => columns.map((c) => qv(txt(c, r))).join(',')));
      const a = el('a', { href: URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })), download: `${csvName || id}.csv` });
      document.body.append(a); a.click(); a.remove();
    };
    compute();
    return { refresh(newRows) { rows = newRows; compute(); } };
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
    const latest = H.concat(E).filter((r) => r.date).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 200);
    dataTable($('#latest'), { id: 'lt', rows: latest, sort: 'date-', pageSize: 25, csvName: 'hcd-latest-letters',
      columns: [{ key: 'date', label: 'Date', render: (r) => fdate(r.date), csv: (r) => r.date, cls: 'd' },
        { key: 'jur', label: 'Jurisdiction', render: (r) => el('button', { type: 'button', class: 'link', 'data-go': r.jur }, STATEWIDE.has(r.key) ? 'Statewide' : r.jur) },
        { key: 'what', label: 'Letter', value: (r) => (r.src === 'HAU' ? r.type : `${r.type}${r.finding ? ` · ${r.finding}` : ''}`) },
        { key: 'src', label: 'Source', filter: 'select', value: (r) => (r.src === 'HAU' ? 'HAU' : 'HE review'), render: (r) => el('span', { class: 'src' }, r.src === 'HAU' ? 'HAU' : 'HE review') },
        { key: 'read', label: 'Read', cls: 'read', value: () => '', render: (r) => tdContent(readCell(r)), csv: (r) => r.pdf || '' }] });
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
      const q = '';
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
      const smax = d3.max(rows, (r) => d3.max(r.byYear));
      $('#st-title').textContent = { statutes: 'Most-cited statutes, HCD tags', cites: 'Statutes cited in the letters', keywords: 'Most-used keywords' }[kind];
      dataTable($('#st-table'), { id: `st${kind}`, rows, sort: 'n-', pageSize: 100, csvName: `hcd-${kind}`,
        columns: [{ key: 'tag', label: kind === 'keywords' ? 'Keyword' : 'Statute', cls: kind === 'keywords' ? '' : 'code',
          render: (r) => (KW_VARIANTS[r.tag] ? el('span', { title: `Groups: ${KW_VARIANTS[r.tag].join('; ')}` }, r.tag) : r.tag) },
          { key: 'n', label: 'Letters', num: true }, { key: 'recent', label: 'Last 12 mo.', num: true },
          { key: 'spark', label: 'By year', value: (r) => r.n, render: (r) => sparkline(r.byYear, smax), csv: (r) => r.byYear.join(' '), hideSm: true },
          { key: 'first', label: 'First', value: (r) => r.first || '', render: (r) => r.first?.slice(0, 4) || '' },
          { key: 'last', label: 'Latest', value: (r) => r.last || '', render: (r) => fdate(r.last), cls: 'd' }],
        onRow: (r) => { picked = r.tag; detail(r); } });
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
      dataTable($('#st-d-table'), { id: 'std', rows: r.rs, sort: 'date-', csvName: 'hcd-letters',
        columns: [{ key: 'date', label: 'Date', render: (x) => fdate(x.date), csv: (x) => x.date, cls: 'd' },
          { key: 'jur', label: 'Jurisdiction', render: (x) => el('button', { type: 'button', class: 'link', 'data-go': x.jur }, STATEWIDE.has(x.key) ? 'Statewide' : x.jur) },
          { key: 'src', label: 'Source', filter: 'select', value: (x) => (x.src === 'HAU' ? 'HAU' : 'HE review') },
          { key: 'what', label: 'Letter', value: (x) => (x.src === 'HAU' ? x.type : `${x.type}${x.finding ? ` · ${x.finding}` : ''}`) },
          { key: 'year', label: 'Year', filter: 'select', hideSm: true },
          { key: 'read', label: 'Read', cls: 'read', value: () => '', render: (x) => tdContent(readCell(x)), csv: (x) => x.pdf || '' }] });
      $('#st-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };
    $$('#statutes .seg button').forEach((b) => { b.onclick = () => {
      kind = b.dataset.kind; picked = null; $('#st-detail').hidden = true;
      $$('#statutes .seg button').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      table();
    }; });
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

    const out = C.filter((c) => /out/i.test(c.status));
    dataTable($('#co-out'), { id: 'co', rows: out, sort: 'county+', csvName: 'hcd-out-of-compliance',
      columns: [{ key: 'jur', label: 'Jurisdiction', render: (c) => el('button', { type: 'button', class: 'link', 'data-go': c.jur }, c.jur) },
        { key: 'county', label: 'County', filter: 'select' }, { key: 'cycle', label: 'Cycle', filter: 'select' },
        { key: 'status', label: 'Status', filter: 'select', render: (c) => pill(c.status) },
        { key: 'latest', label: 'Latest submittal', value: (c) => `${c.recordType} (${c.reviewStatus})`, hideSm: true },
        { key: 'received', label: 'Received', render: (c) => fdate(c.received), csv: (c) => c.received, cls: 'd' },
        { key: 'reviewed', label: 'Reviewed', render: (c) => fdate(c.reviewed), csv: (c) => c.reviewed, cls: 'd' }] });
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
    const host = el('div');
    $('#pl-body').replaceChildren(head, facts, all.length ? host : el('p', { class: 'empty' }, 'No letters on file.'));
    if (all.length) {
      dataTable(host, { id: 'pl', rows: all, sort: 'date-', csvName: `hcd-letters-${name}`,
        columns: [{ key: 'date', label: 'Date', render: (r) => fdate(r.date), csv: (r) => r.date, cls: 'd' },
          { key: 'src', label: 'Source', filter: 'select', value: (r) => (r.src === 'HAU' ? 'HAU' : 'HE review'), render: (r) => el('span', { class: 'src' }, r.src === 'HAU' ? 'HAU' : 'HE review') },
          { key: 'type', label: 'Letter', filter: 'select' },
          { key: 'cycle', label: 'Cycle', filter: 'select', value: (r) => r.cycle || '' },
          { key: 'details', label: 'Details', hideSm: true, value: (r) => (r.src === 'HAU' ? [r.laws.join('; '), r.statutes.length ? ` · ${r.statutes.slice(0, 6).join(', ')}${r.statutes.length > 6 ? '…' : ''}` : ''].join('')
            : [r.finding ? r.finding : '', r.days != null ? ` · ${r.days} days` : ''].join('')) },
          { key: 'read', label: 'Read', cls: 'read', value: () => '', render: (r) => tdContent(readCell(r)), csv: (r) => r.pdf || '' }] });
    }
  }
  function goPlace(name) {
    location.hash = '#place';
    show('place');
    $('#pl-q').value = name;
    $('#pl-q').dispatchEvent(new Event('change'));
  }

  // ---------- shared: letter text, JSON on demand ----------
  const TEXTS = new Map();
  const fetchText = (path) => {
    if (!TEXTS.has(path)) {
      TEXTS.set(path, fetch(`https://raw.githubusercontent.com/${REPO}/main/${path.split('/').map(encodeURIComponent).join('/')}`)
        .then((r) => (r.ok ? r.text() : '')).catch(() => ''));
    }
    return TEXTS.get(path);
  };
  const JSONS = new Map();
  const getJSON = (n) => { if (!JSONS.has(n)) JSONS.set(n, fetch(`data/${n}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)); return JSONS.get(n); };
  let BY_TEXT = null;
  const rowByText = (path) => {
    if (!BY_TEXT) { BY_TEXT = new Map(); for (const r of DATA.A) if (r.text && !BY_TEXT.has(r.text)) BY_TEXT.set(r.text, r); }
    return BY_TEXT.get(path);
  };
  const ROUNDS = ['1st', '2nd', '3rd', '4th+'];
  const roundOf = (n) => ROUNDS[Math.min(n, 4) - 1];
  const letterCols = (extra = []) => [
    { key: 'date', label: 'Date', render: (r) => fdate(r.date), csv: (r) => r.date, cls: 'd' },
    { key: 'jur', label: 'Jurisdiction', render: (r) => el('button', { type: 'button', class: 'link', 'data-go': r.jur }, r.jur) },
    { key: 'county', label: 'County', filter: 'select', hideSm: true },
    ...extra,
    { key: 'read', label: 'Read', cls: 'read', value: () => '', render: (r) => tdContent(readCell(rowByText(r.text) || { text: r.text })), csv: (r) => (r.text ? gh(r.text) : '') },
  ];
  const tdContent = (td) => { const f = document.createDocumentFragment(); f.append(...td.childNodes); return f; };
  // Whole-word matching and sentence splitting WITHOUT regex lookbehind: Safari before iOS 16.4 can't parse lookbehind groups.
  const termRx = (pats, flags) => new RegExp(`(^|[^a-z0-9])(${pats.join('|')})(?![a-z0-9])`, flags);
  const hits = (rx, s) => { const out = []; rx.lastIndex = 0; let m; while ((m = rx.exec(s))) { out.push({ index: m.index + m[1].length, text: m[2] }); if (!m[0].length) rx.lastIndex++; } return out; };
  const splitSentences = (p) => p.replace(/([.;:])\s+(?=[A-Z(•])/g, '$1\u0000').split('\u0000');  // same as the Python split in build_site_data.py

  // ---------- Requirements ----------
  DRAW.requirements = async () => {
    const R = await getJSON('requirements');
    if (!R) { $('#rq-facts').textContent = 'The requirements data is built by the weekly review-letter job; it is not available yet.'; return; }
    const D = R.dict;
    const ALL = R.rows.map((r) => ({ jur: D.jur[r[0]], county: D.county[r[1]], date: r[2], type: D.type[r[3]], cycle: r[4], round: r[5],
      compliance: D.compliance[r[6]], kind: D.kind[r[7]], reqs: r[8].map((i) => D.req[i]), issues: r[9].map((i) => D.issue[i]).filter((x) => x !== '(no topic label)'),
      commits: r[10].map((i) => D.commit[i]), text: D.text[r[11]], words: r[12] }));
    const PROGS = R.programs.map((p) => ({ jur: D.jur[p[0]], date: p[1], cycle: p[2], program: D.program[p[3]], category: D.category[p[4]], text: D.text[p[5]] }));
    const label = { reqs: (k) => `${R.reqLabels[k] || k} (${k})`, issues: (k) => k, commits: (k) => k };
    const P = params();
    let view = P.get('view') || 'reqs';
    $('#rq-cycle').value = P.get('cycle') || '6,7';
    const cs = $('#rq-county');
    if (cs.options.length < 2) cs.append(...[...new Set(ALL.map((r) => r.county).filter(Boolean))].sort().map((c) => el('option', { value: c }, c)));
    cs.value = P.get('county') || '';
    const KIND = (r) => (r.compliance === 'In compliance'
      ? (r.kind.startsWith('Draft meets') ? 'Draft meets requirements' : r.kind.startsWith('Adopted') || r.kind.startsWith('Rezoning completed') ? 'In compliance, adopted' : 'Other, in compliance')
      : r.compliance === 'Out of compliance'
        ? (r.kind === 'Revisions needed' ? 'Revisions needed' : r.kind.startsWith('Meets requirements') || r.kind.startsWith('Rezoning ordinance') ? 'Meets law, rezoning not done' : 'Other, out of compliance')
        : 'No finding');
    const KKEYS = ['Revisions needed', 'Meets law, rezoning not done', 'Other, out of compliance', 'Draft meets requirements', 'In compliance, adopted', 'Other, in compliance', 'No finding'];
    const kcol = () => ({ 'Revisions needed': css('--out'), 'Meets law, rezoning not done': css('--amber'), 'Other, out of compliance': css('--s5'),
      'Draft meets requirements': css('--s4'), 'In compliance, adopted': css('--in'), 'Other, in compliance': css('--s1'), 'No finding': css('--rule') });

    function render() {
      const cyc = new Set($('#rq-cycle').value.split(',')), county = cs.value;
      setParams({ cycle: $('#rq-cycle').value === '6,7' ? '' : $('#rq-cycle').value, county, view: view === 'reqs' ? '' : view });
      const L = ALL.filter((r) => cyc.has(r.cycle) && (!county || r.county === county));
      const full = L.filter((r) => r.kind === 'Revisions needed');
      // first In per jurisdiction and cycle
      const byJ = d3.group(L, (r) => `${r.jur}|${r.cycle}`);
      const firstIn = new Map();
      for (const [k, rs] of byJ) { const ins = rs.filter((r) => r.compliance === 'In compliance').map((r) => r.round); firstIn.set(k, ins.length ? d3.min(ins) : null); }
      const reached = [...firstIn.values()].filter((v) => v);
      const cycTxt = [...cyc].map((c) => `${c}th`).join(' and ');
      $('#rq-facts').replaceChildren(
        el('span', {}, el('b', {}, fmt(L.length)), ` letters with text, ${cycTxt} cycle${cyc.size > 1 ? 's' : ''}${county ? `, ${county} County` : ''}`),
        el('span', {}, el('b', {}, fmt(byJ.size)), ' jurisdiction-cycles'),
        el('span', {}, el('b', {}, fmt(reached.length)), ' reached compliance'),
        reached.length ? el('span', {}, 'median ', el('b', {}, d3.median(reached)), ' reviews to get there') : null,
        el('span', {}, el('b', {}, fmt(full.length)), ' "revisions needed" letters'));

      const rc = d3.rollup(reached, (v) => v.length, (v) => (v >= 6 ? '6+' : String(v)));
      const cats = ['1', '2', '3', '4', '5', '6+'];
      stackedBars($('#rq-reach'), { cats, keys: ['Jurisdictions'], colors: { Jurisdictions: css('--accent') }, value: (c) => rc.get(c) || 0, label: 'Reviews to compliance', height: 220 });
      const kc = d3.rollup(L, (v) => v.length, (r) => roundOf(r.round), KIND);
      const kk = KKEYS.filter((k) => L.some((r) => KIND(r) === k));
      legend($('#rq-kinds-legend'), kk.map((k) => [k, kcol()[k]]));
      stackedBars($('#rq-kinds'), { cats: ROUNDS, keys: kk, colors: kcol(), value: (b, k) => kc.get(b)?.get(k) || 0, percent: true, totals: true, label: 'Kinds of letters by round', height: 240 });

      // table by view
      const nB = d3.rollup(full, (v) => v.length, (r) => roundOf(r.round));
      const cnt = new Map();
      for (const r of full) for (const k of r[view]) {
        if (!cnt.has(k)) cnt.set(k, { key: k, n: 0, b: Object.fromEntries(ROUNDS.map((x) => [x, 0])), letters: [] });
        const c = cnt.get(k); c.n++; c.b[roundOf(r.round)]++; c.letters.push(r);
      }
      const rows = [...cnt.values()].map((c) => {
        const sh = Object.fromEntries(ROUNDS.map((b) => [b, nB.get(b) ? c.b[b] / nB.get(b) : 0]));
        const lateN = (nB.get('3rd') || 0) + (nB.get('4th+') || 0);
        const late = lateN ? (c.b['3rd'] + c.b['4th+']) / lateN : 0;
        return { ...c, label: label[view](c.key), share: c.n / Math.max(1, full.length), sh, stay: sh['1st'] ? late / sh['1st'] : null };
      });
      const shade = d3.scaleSequential([0, 1], d3.interpolateRgb(css('--panel'), css('--accent')));
      const heat = (v) => { const td = el('span', {}, v ? pct(v) : ''); return td; };
      const TITLES = { reqs: 'Requirements HCD finds unmet, by round', issues: 'Issues HCD raises, by round', commits: 'Program commitments HCD asks for, by round' };
      $('#rq-t-title').textContent = TITLES[view];
      $('#rq-t-note').textContent = `Share of "revisions needed" letters in each round (${ROUNDS.map((b) => `${b}: ${fmt(nB.get(b) || 0)}`).join(', ')}) where HCD wrote about it. `
        + 'Staying power: share in 3rd-and-later letters ÷ share in 1st letters; near 1 or above means it keeps coming back. Click a row for the letters.';
      $$('#requirements .seg button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
      const heatCol = (b) => ({ key: b, label: b, num: true, value: (r) => r.sh[b], render: (r) => heat(r.sh[b]), csv: (r) => r.sh[b].toFixed(3) });
      dataTable($('#rq-table'), { id: 'rq', sort: 'n-', csvName: `hcd-${view}-by-round`, rows,
        columns: [{ key: 'label', label: view === 'reqs' ? 'Requirement' : view === 'issues' ? 'Issue' : 'Commitment' },
          { key: 'n', label: 'Letters', num: true }, ...ROUNDS.map(heatCol),
          { key: 'stay', label: 'Staying power', num: true, value: (r) => r.stay ?? -1, render: (r) => (r.stay == null ? '' : r.stay.toFixed(2)), csv: (r) => (r.stay == null ? '' : r.stay.toFixed(2)) }],
        onRow: (r) => detail(r.label, r.letters, `${fmt(r.n)} "revisions needed" letters in which HCD wrote about this.`) });
      // shade heat cells after render
      requestAnimationFrame(() => $$('#rq-table td.num').forEach((td) => { const m = /^(\d+)%$/.exec(td.textContent); if (m) { td.style.background = shade(+m[1] / 100); if (+m[1] > 55) td.style.color = css('--panel'); } }));

      // last hurdles
      const lasts = [];
      for (const [k, rs] of byJ) {
        const fi = firstIn.get(k);
        const prior = rs.filter((r) => r.kind === 'Revisions needed' && fi && r.round < fi);
        if (prior.length) lasts.push(prior.reduce((a, b) => (b.round > a.round ? b : a)));
      }
      const lc = d3.rollups(lasts.flatMap((r) => r[view]), (v) => v.length, (d) => d).sort((a, b) => b[1] - a[1]).slice(0, 14);
      hbars($('#rq-last'), lc.map(([k, n]) => ({ label: label[view](k), value: n / Math.max(1, lasts.length), key: k })), { fmtv: pct, max: 1,
        onClick: (d) => detail(d.label, lasts.filter((r) => r[view].includes(d.key)), 'Last "revisions needed" letter before compliance.') });

      const PR = PROGS.filter((p) => cyc.has(p.cycle) && (!county || (ALL.find((r) => r.text === p.text)?.county === county)));
      const pc = d3.rollups(PR, (v) => v.length, (p) => p.category).sort((a, b) => b[1] - a[1]);
      hbars($('#rq-prog'), pc.map(([k, n]) => ({ label: k, value: n })), { color: css('--in') });
      const names = d3.rollups(PR, (v) => ({ n: new Set(v.map((p) => p.text)).size, category: v[0].category, cycles: [...new Set(v.map((p) => p.cycle))].sort().join(', '), letters: v }),
        (p) => p.program.toLowerCase().replace(/\s+/g, ' ').trim()).map(([name, o]) => ({ name: o.letters[0].program, ...o }));
      dataTable($('#rq-prog-table'), { id: 'rqp', sort: 'n-', csvName: 'hcd-programs-in-compliance-letters', rows: names,
        columns: [{ key: 'name', label: 'Program' }, { key: 'category', label: 'Category', filter: 'select' }, { key: 'n', label: 'Letters', num: true }, { key: 'cycles', label: 'Cycles', hideSm: true }],
        onRow: (r) => detail(`Program: ${r.name}`, r.letters.map((p) => ALL.find((x) => x.text === p.text) || p), 'Letters finding compliance that name this program.') });
    }
    function detail(title, letters, note) {
      $('#rq-detail').hidden = false;
      $('#rq-d-title').textContent = title;
      $('#rq-d-note').textContent = note;
      dataTable($('#rq-d-table'), { id: 'rqd', sort: 'date-', csvName: 'hcd-letters', rows: letters,
        columns: letterCols([{ key: 'cycle', label: 'Cycle', filter: 'select' }, { key: 'round', label: 'Round', num: true, filter: 'select' },
          { key: 'kind', label: 'Letter', value: (r) => r.kind || '', filter: 'select' }]) });
      $('#rq-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    $('#rq-cycle').onchange = render;
    cs.onchange = render;
    $$('#requirements .seg button').forEach((b) => { b.onclick = () => { view = b.dataset.view; render(); }; });
    $('#rq-d-close').onclick = () => { $('#rq-detail').hidden = true; };
    render();
  };

  // ---------- Language ----------
  DRAW.language = async () => {
    const LG = await getJSON('language');
    let src = params().get('src') || 'HE';
    const pretty = (t) => t.replace(/<JUR>/g, '[jurisdiction]').replace(/<JTYPE>/g, '[City/County]').replace(/<DATE>/g, '[date]').replace(/<N>/g, '[#]');
    function render() {
      setParams({ src: src === 'HE' ? '' : src });
      $$('#language .seg button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.src === src)));
      $('#lg-detail').hidden = true;
      const pat = LG?.sources?.[src]?.patterns;
      if (!pat) {
        $('#lg-table').replaceChildren(el('p', { class: 'empty' }, 'Built by the weekly job for these letters; not available yet.'));
        $('#lg-heads').replaceChildren();
        return;
      }
      const years = [...new Set(pat.groups.flatMap((g) => Object.keys(g.byYear)))].sort();
      const smax = d3.max(pat.groups, (g) => d3.max(Object.values(g.byYear)));
      const rows = pat.groups.map((g) => {
        const ys = Object.keys(g.byYear).sort();
        return { ...g, text: pretty(g.example), first: ys[0] || '', last: ys[ys.length - 1] || '', nvar: g.variants.length, out: g.outShare };
      });
      dataTable($('#lg-table'), { id: 'lg', sort: 'letters-', csvName: `hcd-standard-paragraphs-${src}`, rows, pageSize: 50,
        columns: [{ key: 'text', label: 'Paragraph', render: (r) => (r.text.length > 240 ? `${r.text.slice(0, 238)}…` : r.text) },
          { key: 'letters', label: 'Letters', num: true },
          { key: 'share', label: 'Share', num: true, value: (r) => r.letters / pat.total, render: (r) => pct(r.letters / pat.total), csv: (r) => (r.letters / pat.total).toFixed(3) },
          { key: 'first', label: 'Years', value: (r) => r.first, render: (r) => `${r.first}–${r.last}`, csv: (r) => `${r.first}-${r.last}`, cls: 'd' },
          { key: 'spark', label: 'By year', value: (r) => r.letters, render: (r) => sparkline(years.map((y) => r.byYear[y] || 0), smax), csv: (r) => years.map((y) => r.byYear[y] || 0).join(' '), hideSm: true },
          { key: 'nvar', label: 'Variants', num: true, hideSm: true },
          ...(src === 'HE' ? [{ key: 'out', label: 'Out share', num: true, value: (r) => r.out ?? -1, render: (r) => (r.out == null ? '' : pct(r.out)), csv: (r) => r.out ?? '' }] : [])],
        onRow: (r) => detail(r, pat, years) });
      dataTable($('#lg-heads'), { id: 'lgh', sort: 'n-', csvName: `hcd-headings-${src}`, pageSize: 30,
        rows: pat.headings.map(([h, n]) => ({ h: pretty(h), n })), columns: [{ key: 'h', label: 'Heading' }, { key: 'n', label: 'Letters', num: true }] });
    }
    function detail(g, pat, years) {
      $('#lg-detail').hidden = false;
      $('#lg-d-title').textContent = `Standard paragraph: ${fmt(g.letters)} letters, ${g.first}–${g.last}`;
      $('#lg-d-note').textContent = g.out == null ? '' : `${pct(g.out)} of the letters using it find the element out of compliance.`;
      $('#lg-d-text').textContent = g.text;
      const vs = (g.variants.length ? g.variants : [{ letters: g.letters, byYear: g.byYear, example: g.example, diff: [] }]).slice(0, 5);
      const keys = vs.map((_, i) => `Wording ${i + 1}`);
      const colors = Object.fromEntries(keys.map((k, i) => [k, css(`--s${(i % 5) + 1}`)]));
      const other = Object.fromEntries(years.map((y) => [y, Math.max(0, (g.byYear[y] || 0) - d3.sum(vs, (v) => v.byYear[y] || 0))]));
      const allKeys = keys.concat(d3.sum(Object.values(other)) ? ['Other wordings'] : []);
      colors['Other wordings'] = css('--rule');
      legend($('#lg-d-legend'), allKeys.map((k) => [k, colors[k]]));
      stackedBars($('#lg-d-chart'), { cats: years, keys: allKeys, colors, value: (y, k) => (k === 'Other wordings' ? other[y] : vs[keys.indexOf(k)].byYear[y] || 0), label: 'Letters per year by wording', height: 220 });
      $('#lg-d-variants').replaceChildren(el('h3', { class: 'sub' }, 'Wordings'), ...vs.map((v, i) => {
        const ys = Object.keys(v.byYear).sort();
        const body = i === 0 || !v.diff.length ? el('div', {}, pretty(v.example))
          : el('div', {}, ...v.diff.map(([op, t]) => (op === '=' ? `${pretty(t.length > 220 ? `${t.slice(0, 100)} … ${t.slice(-100)}` : t)} ` : el(op === '-' ? 'del' : 'ins', { class: op === '-' ? 'dd' : 'di' }, `${pretty(t)} `))));
        return el('div', { class: 'variant' }, el('div', { class: 'vh' }, `Wording ${i + 1}: ${fmt(v.letters)} letters, ${ys[0]}–${ys[ys.length - 1]}${i ? ' — changes from wording 1 marked' : ''}`), body);
      }));
      const letters = g.members.map((m) => pat.letters[m]).map((t) => { const r = rowByText(t); return r ? { ...r, text: t } : { text: t, date: '', jur: '' }; });
      const host = el('div');
      $('#lg-d-letters').replaceChildren(el('h3', { class: 'sub' }, 'Letters that use it'), host);
      dataTable(host, { id: 'lgd', sort: 'date-', csvName: 'hcd-letters-using-paragraph', rows: letters, pageSize: 50,
        columns: letterCols([{ key: 'type', label: 'Letter', value: (r) => r.type || '', filter: 'select' },
          { key: 'finding', label: 'Finding', value: (r) => r.finding || '', filter: 'select' }]) });
      $('#lg-detail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    $$('#language .seg button').forEach((b) => { b.onclick = () => { src = b.dataset.src; render(); }; });
    $('#lg-d-close').onclick = () => { $('#lg-detail').hidden = true; };
    render();
  };

  // ---------- Reader ----------
  const sentenceKey = (s, names) => {   // must match sentence_key() in scripts/build_site_data.py
    let k = s.toLowerCase();
    for (const n0 of names) { const n = (n0 || '').toLowerCase().replace(' county', '').trim(); if (n.length > 2) k = k.split(n).join(' '); }
    k = k.replace(/\b(city|county|town)('s|’s)?\b/g, ' ').replace(/[\d,]+(\.\d+)?/g, '#').replace(/[^a-z#]+/g, ' ').trim();
    return k.length > 30 ? k : null;
  };
  const READER = { marks: [], cur: -1, path: '' };
  async function openReader(path, { find = '' } = {}) {
    const dlg = $('#reader');
    const r = rowByText(path) || { text: path };
    READER.path = path;
    $('#rd-title').textContent = r.jur ? `${STATEWIDE.has(r.key) ? 'Statewide' : r.jur}${r.county ? `, ${r.county} County` : ''}` : path.split('/').pop();
    $('#rd-sub').textContent = [r.date ? fdate(r.date) : '', r.src === 'HAU' ? `HAU · ${r.type}` : r.type ? `Review · ${r.type}${r.cycle ? ` · cycle ${r.cycle}` : ''}${r.finding ? ` · ${r.finding}` : ''}` : '', r.req ? 'Requested from HCD' : ''].filter(Boolean).join(' · ');
    $('#rd-links').replaceChildren(...[link(r.pdf || (r.req && gh(r.req)), 'PDF'), r.hePdf ? link(r.hePdf, 'Element reviewed') : null, link(gh(path), 'Text on GitHub')].filter(Boolean));
    $('#rd-body').replaceChildren(el('p', { class: 'busy' }, 'Loading…'));
    if (!dlg.open) { if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', ''); }
    setParams({ read: path });
    const [text, lg] = await Promise.all([fetchText(path), getJSON('language')]);
    if (READER.path !== path) return;
    const std = new Set(lg?.sources?.[path.startsWith('hau/') ? 'HAU' : 'HE']?.standard || []);
    const names = [r.jur, r.county].filter(Boolean);
    READER.paras = (text || '').split(/\n\s*\n/).map((p) => p.replace(/\s+/g, ' ').trim()).filter(Boolean)
      .filter((p) => !/^Page \d+$/.test(p))
      .map((p) => splitSentences(p).map((sx) => { const k = sentenceKey(sx, names); return { s: sx, std: !!(k && std.has(fnv1a(k).toString(16))) }; }));
    if (!text) { $('#rd-body').replaceChildren(el('p', { class: 'busy' }, 'The text could not be loaded.')); return; }
    $('#rd-find').value = find;
    drawReader();
  }
  function drawReader() {
    const q = $('#rd-find').value.trim();
    const terms = parseQuery(q);
    const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pats = [...terms.phrases.map((p) => p.map(esc).join("[^a-z0-9.']+")), ...terms.words.map(esc)];
    const rx = pats.length ? termRx(pats, 'gi') : null;
    const body = $('#rd-body');
    body.classList.toggle('dim', $('#rd-dim').checked);
    body.replaceChildren(...READER.paras.map((ss) => el('p', {}, ...ss.flatMap((x, i) => {
      const span = el('span', { class: x.std ? 'std' : null });
      const lab = i === 0 ? /^([A-Z][A-Za-z0-9’'&/(),\- ]{2,80}?):\s/.exec(x.s) : null;
      let s = x.s;
      if (lab) { span.append(el('span', { class: 'label' }, `${lab[1]}: `)); s = s.slice(lab[0].length); }
      if (rx) { let last = 0; for (const h of hits(rx, s)) { span.append(s.slice(last, h.index), el('mark', {}, h.text)); last = h.index + h.text.length; } span.append(s.slice(last)); } else span.append(s);
      return [span, ' '];
    }))));
    READER.marks = $$('mark', body);
    READER.cur = READER.marks.length ? 0 : -1;
    $('#rd-count').textContent = q ? `${fmt(READER.marks.length)} match${READER.marks.length === 1 ? '' : 'es'}` : '';
    gotoMark(0);
  }
  function gotoMark(d) {
    if (!READER.marks.length) return;
    READER.marks[READER.cur]?.classList.remove('cur');
    READER.cur = (READER.cur + d + READER.marks.length) % READER.marks.length;
    const m = READER.marks[READER.cur];
    m.classList.add('cur');
    m.scrollIntoView({ block: 'center' });
    $('#rd-count').textContent = `${READER.cur + 1} of ${fmt(READER.marks.length)}`;
  }
  $('#rd-find').addEventListener('input', () => { clearTimeout(READER.t); READER.t = setTimeout(drawReader, 200); });
  $('#rd-find').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); gotoMark(e.shiftKey ? -1 : 1); } });
  $('#rd-next').onclick = () => gotoMark(1);
  $('#rd-prev').onclick = () => gotoMark(-1);
  $('#rd-dim').onchange = () => $('#rd-body').classList.toggle('dim', $('#rd-dim').checked);
  $('#rd-close').onclick = () => { const d = $('#reader'); if (d.close) d.close(); else { d.removeAttribute('open'); READER.path = ''; setParams({ read: '' }); } };
  $('#reader').addEventListener('close', () => { READER.path = ''; setParams({ read: '' }); });

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
    const getText = fetchText;
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
      const rx = termRx(pats, 'gi');
      // center on the first exact phrase if there is one, else the first match of anything
      const lead = phrases.length ? hits(termRx([pats[0]], 'gi'), flat)[0] : null;
      const first = lead || hits(rx, flat)[0];
      const at = first ? first.index : 0;
      let a = Math.max(0, at - 120), b = Math.min(flat.length, at + 160);
      while (a > 0 && flat[a] !== ' ') a--;
      while (b < flat.length && flat[b] !== ' ') b++;
      const part = flat.slice(a, b);
      const nodes = [a > 0 ? '…' : ''];
      let last = 0;
      for (const h of hits(rx, part)) { nodes.push(part.slice(last, h.index), el('mark', {}, h.text)); last = h.index + h.text.length; }
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
    const rb = e.target.closest('[data-read]');
    if (rb) { e.preventDefault(); openReader(rb.dataset.read, { find: rb.closest('#search') ? ($('#sr-q').value || '') : '' }); return; }
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
    $('#stamp').textContent = d.meta ? `Updated ${caDate(d.meta.built)} · ${fmt(d.H.length)} HAU and ${fmt(d.E.length)} review letters` : 'Data not built yet';
    show(location.hash.slice(1) || 'overview');
    const rd = params().get('read');
    if (rd) openReader(rd);
  }).catch((err) => { $('#stamp').textContent = `Could not load data: ${err.message}`; });
})();
