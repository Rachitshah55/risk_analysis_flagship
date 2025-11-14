(async function () {
    const cfg = await loadConfig();
  
    // Load CSV
    let rows = [];
    try { rows = await loadCsv('credit/kpis_daily.csv'); } catch (e) { console.error(e); }
  
    if (rows.length) {
      const latest = latestByDate(rows);
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      set('avg-pd',        fmtPct(latest.avg_pd));
      set('expected-loss', fmtMoney(latest.el_today));
      set('approvals',     fmtInt(latest.approvals));
      set('rejections',    fmtInt(latest.rejections));
  
      // Charts (30 days)
      const last30 = rows.slice(-30);
      const labels = last30.map(r => r.date);
      const pdVals = last30.map(r => Number(r.avg_pd));
      const elVals = last30.map(r => Number(r.el_today));
  
      const pdCtx = document.getElementById('pd-trend-chart').getContext('2d');
      new Chart(pdCtx, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Avg PD', data: pdVals, borderWidth: 2, tension: .3 }] },
        options: { scales: { y: { ticks: { callback: (v) => (v * 100).toFixed(0) + '%' } } } }
      });
  
      const elCtx = document.getElementById('el-trend-chart').getContext('2d');
      new Chart(elCtx, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Expected Loss', data: elVals, borderWidth: 2, tension: .3 }] },
        options: { scales: { y: { ticks: { callback: (v) => '$' + Number(v).toFixed(0) } } } }
      });
    }
  
    // API demo
    const btn = document.getElementById('score-api-btn');
    const useSample = document.getElementById('use-sample-btn');
    const payloadEl = document.getElementById('credit-payload');
    const out = document.getElementById('api-response');
  
    if (cfg.useMock && btn) { btn.disabled = true; btn.title = 'Disabled in hosted/mock mode'; }
  
    useSample?.addEventListener('click', () => {
      // already filled; keep button for consistency
      payloadEl.focus();
    });
  
    btn?.addEventListener('click', async () => {
      try {
        const body = payloadEl.value || '{}';
        out.textContent = 'Scoring...';
        let data;
        if (cfg.useMock) {
          await new Promise(r => setTimeout(r, 200));
          data = { pd: 0.083, confidence: 0.92, model: "demo-nonflat-v1" };
        } else {
          const r = await fetch(`${cfg.apiBase}/credit/score`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
          data = await r.json();
        }
        out.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        out.textContent = `Error: ${e.message}`;
      }
    });
  
    // Show today's report link only in Local mode (in case page JS runs before inline bootstrap)
    if (window.showTodayReportIfLocal) {
      await window.showTodayReportIfLocal('credit', 'report-button');
    }
  })();
  