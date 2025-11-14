// ---- CONFIG ----
window.loadConfig = async function loadConfig() {
    try { const r = await fetch('config.json', { cache: 'no-store' }); return await r.json(); }
    catch { return { mode: 'hosted', apiBase: 'http://127.0.0.1:8000', useMock: true }; }
  };
  
  // Use ../docs_global in local mode; demo_data/* in hosted mode
  window.resolveCsvUrl = function resolveCsvUrl(cfg, rel) {
    if (cfg.mode === 'local') return `../docs_global/bi/${rel}`;
    return `demo_data/${rel}`;
  };
  
  // ---- CSV PARSER (simple) ----
  window.parseCsv = function parseCsv(text) {
    const lines = text.replace(/\r/g, '').trim().split('\n').filter(Boolean);
    if (lines.length === 0) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
      const cols = line.split(',').map(c => c.trim());
      const obj = {};
      headers.forEach((h, i) => obj[h] = (cols[i] === undefined ? '' : cols[i]));
      return obj;
    });
  };
  
  window.latestByDate = function latestByDate(rows, dateKey = 'date') {
    return rows.slice().sort((a, b) => a[dateKey] < b[dateKey] ? -1 : 1).slice(-1)[0];
  };
  
  // ---- FORMATTERS ----
  window.fmtPct = (x) => (x == null || x === '') ? '--%' : `${(Number(x) * 100).toFixed(1)}%`;
  window.fmtInt = (x) => (x == null || x === '') ? '--' : Number(x).toLocaleString();
  window.fmtMoney = (x) => (x == null || x === '') ? '$--' : Number(x).toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  
  // ---- REPORT LINKS ----
  window.buildTodayReportHref = function buildTodayReportHref(kind) { // 'credit' | 'fraud'
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const base = `../docs_global/reports/${kind}/${yyyy}-${mm}-${dd}`;
    return kind === 'credit'
      ? `${base}/credit_daily_report.html`
      : `${base}/fraud_daily_report.html`;
  };
  
  window.showTodayReportIfLocal = async function showTodayReportIfLocal(kind, containerId) {
    const cfg = await window.loadConfig();
    if (cfg.mode !== 'local') return;
    const wrap = document.getElementById(containerId);
    if (!wrap) return;
    const a = wrap.querySelector('a');
    if (!a) return;
    a.href = window.buildTodayReportHref(kind);
    wrap.classList.remove('hidden');
  };
  
  // ---- FETCH CSV ----
  window.loadCsv = async function loadCsv(relPath) {
    const cfg = await window.loadConfig();
    const url = window.resolveCsvUrl(cfg, relPath);
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(`Failed to load CSV: ${url}`);
    const text = await r.text();
    return window.parseCsv(text);
  };
  