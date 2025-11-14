(async function () {
    const cfg = await loadConfig();
  
    // Load CSVs
    let kpis = [], metrics = [];
    try { kpis    = await loadCsv('fraud/kpis_daily.csv'); } catch (e) { console.error(e); }
    try { metrics = await loadCsv('fraud/metrics_daily.csv'); } catch (e) { console.error(e); }
  
    if (kpis.length) {
      const latest = latestByDate(kpis);
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      set('flagged-rate', fmtPct(latest.flagged_rate));
      set('precision',    fmtPct(latest.precision));
      set('recall',       fmtPct(latest.recall));
    }
  
    // Charts from metrics (30 days)
    if (metrics.length) {
      const last30 = metrics.slice(-30);
      const labels = last30.map(r => r.date);
      const prec   = last30.map(r => Number(r.precision));
      const rec    = last30.map(r => Number(r.recall));
  
      const pctx = document.getElementById('precision-trend-chart').getContext('2d');
      new Chart(pctx, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Precision', data: prec, borderWidth: 2, tension: .3 }] },
        options: { scales: { y: { ticks: { callback: (v) => (v * 100).toFixed(0) + '%' } } } }
      });
  
      const rctx = document.getElementById('recall-trend-chart').getContext('2d');
      new Chart(rctx, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Recall', data: rec, borderWidth: 2, tension: .3 }] },
        options: { scales: { y: { ticks: { callback: (v) => (v * 100).toFixed(0) + '%' } } } }
      });
    }
  
    // API demo
    const btn = document.getElementById('fraud-api-btn');
    const sample = document.getElementById('fraud-sample-btn');
    const payloadEl = document.getElementById('fraud-payload');
    const out = document.getElementById('fraud-api-response');
  
    if (cfg.useMock && btn) { btn.disabled = true; btn.title = 'Disabled in hosted/mock mode'; }
  
    sample?.addEventListener('click', () => { payloadEl.focus(); });
  
    btn?.addEventListener('click', async () => {
      try {
        const body = payloadEl.value || '{}';
        out.textContent = 'Scoring...';
        let data;
        if (cfg.useMock) {
          await new Promise(r => setTimeout(r, 200));
          data = { fraud_probability: 0.21, decision: "review", confidence: 0.88, model: "demo-fraud-v1" };
        } else {
          const r = await fetch(`${cfg.apiBase}/fraud/score`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
          data = await r.json();
        }
        out.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        out.textContent = `Error: ${e.message}`;
      }
    });
  
    // Show today's report link only in Local mode
    if (window.showTodayReportIfLocal) {
      await window.showTodayReportIfLocal('fraud', 'fraud-report-button');
    }
  })();
  