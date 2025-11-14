(async function () {
    try {
      const cfg = await loadConfig();
  
      // Load credit + fraud KPIs
      const creditRows = await loadCsv('credit/kpis_daily.csv');
      const fraudRows  = await loadCsv('fraud/kpis_daily.csv');
  
      const cLatest = latestByDate(creditRows);
      const fLatest = latestByDate(fraudRows);
  
      // Fill KPI cards
      document.getElementById('credit-kpi').innerHTML = `
        <div class="text-center">
          <div class="text-sm text-slate-600 mb-1">Avg PD</div>
          <div class="text-2xl font-semibold text-indigo-600">${fmtPct(cLatest.avg_pd)}</div>
          <div class="text-xs text-slate-500 mt-1">EL Today: ${fmtMoney(cLatest.el_today)}</div>
        </div>`;
  
      document.getElementById('fraud-kpi').innerHTML = `
        <div class="text-center">
          <div class="text-sm text-slate-600 mb-1">Flagged %</div>
          <div class="text-2xl font-semibold text-emerald-600">${fmtPct(fLatest.flagged_rate)}</div>
          <div class="text-xs text-slate-500 mt-1">Precision: ${fmtPct(fLatest.precision)}</div>
        </div>`;
  
      // Freshness banner + card
      const maxDate = [cLatest.date, fLatest.date].sort().slice(-1)[0];
      const lbl = document.getElementById('freshness-label'); if (lbl) lbl.textContent = `Freshness: ${maxDate}`;
      const freshnessCard = document.getElementById('freshness-kpi');
      if (freshnessCard) {
        freshnessCard.innerHTML = `
          <div class="text-center">
            <div class="text-sm text-slate-600 mb-1">Most Recent Data</div>
            <div class="text-2xl font-semibold text-slate-800">${maxDate}</div>
            <div class="text-xs text-slate-500 mt-1">${cfg.mode === 'local' ? 'Local pipelines' : 'Bundled demo data'}</div>
          </div>`;
      }
  
      // Sparklines (last 14)
      const slice14 = (rows, key) => rows.slice(-14).map(r => Number(r[key]));
      const creditLabels = creditRows.slice(-14).map(r => r.date);
      const fraudLabels  = fraudRows.slice(-14).map(r => r.date);
  
      const creditCtx = document.getElementById('credit-sparkline').getContext('2d');
      new Chart(creditCtx, {
        type: 'line',
        data: { labels: creditLabels, datasets: [{ label: 'Avg PD', data: slice14(creditRows, 'avg_pd'), borderWidth: 2, tension: .3 }] },
        options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { callback: (v) => (v * 100).toFixed(0) + '%' } } } }
      });
  
      const fraudCtx = document.getElementById('fraud-sparkline').getContext('2d');
      new Chart(fraudCtx, {
        type: 'line',
        data: { labels: fraudLabels, datasets: [{ label: 'Flagged %', data: slice14(fraudRows, 'flagged_rate'), borderWidth: 2, tension: .3 }] },
        options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { callback: (v) => (v * 100).toFixed(0) + '%' } } } }
      });
    } catch (e) {
      console.error(e);
      // Leave "Loading..." text if something fails
    }
  })();
  