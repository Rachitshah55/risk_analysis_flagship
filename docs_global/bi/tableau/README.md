# Tableau Seed — Risk Analytics (Credit + Fraud)

This folder holds a minimal packaged workbook (`Risk_Analytics_seed.twbx`) and the raw CSVs it references.

## Data sources (from this repo)
- Credit KPIs (daily): `docs_global/bi/credit/kpis_daily.csv`
- Fraud metrics (daily): `docs_global/bi/fraud/metrics_daily.csv`

## Open & refresh (Tableau Public/Desktop)
1. Double-click `Risk_Analytics_seed.twbx`.
2. If prompted to locate files:
   - Browse to this repo root, then pick the CSV path(s) above.
3. Click **Data** → **Refresh All Extracts** (or **Refresh** if live).
4. Dashboard: shows “Credit KPI Trend” + “Fraud Metrics” with basic trendlines.

## Replace/repair data sources (moved repo path)
1. **Data** (menu) → **Replace Data Source…**
2. Pick the “Current” source → choose “Replacement” source:
   - `docs_global/bi/credit/kpis_daily.csv`
   - `docs_global/bi/fraud/metrics_daily.csv`
3. Confirm fields map, then click **OK**.

## Publish (optional)
- Tableau Public: **File** → **Save to Tableau Public** → sign in and publish.
- Tableau Server/Cloud: **Server** → **Publish Workbook** (ensure the two CSVs are accessible on the server or use extracts).

## Tips & conventions
- Parse `date` as Date; KPI fields as Numbers.
- Keep the seed minimal; build richer dashboards in a new `.twbx` to avoid bloating the repo.
- If columns change, update sheet encodings, or regenerate the seed workbook.

## Troubleshooting
- **Dates show as Abc (string)** → Change Data Type to **Date**.
- **Null metrics** → CSV schema changed; re-map fields on the worksheet.
- **“File not found”** → Use **Replace Data Source…** and point to the CSVs in this repo.
