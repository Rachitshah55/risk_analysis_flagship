# LOCAL_DEMO_GUIDE — Live API + docs_site Interview Demo

This guide is the **“do this before and during an interview”** script.

Goal:

- Show the **Cloudflare-hosted** showroom for context
- Then flip to **local mode** where docs_site uses **real APIs**
- Keep everything reproducible and easy to reset

---

## 1. Pre-demo checklist

Before you start:

- Repo cloned at `C:\DevProjects\risk_analysis_flagship`
- Python 3.13 installed
- `.venv` created
- `pip install -r requirements.txt` completed
- `.env` wired for alert bridge if you want to show alerts

---

## 2. Prep the venv and repo

From PowerShell:

```bash
cd C:\DevProjects\risk_analysis_flagship
.\.venv\Scripts\Activate.ps1
```

Keep this terminal open; it will be your **control center**.

---

## 3. Start core backend services

You need three backend processes:

1. **Credit API** (port 8002)
2. **Fraud API** (port 8001)
3. **Gateway** (port 8000)

### 3.1. Start Credit API (8002)

In Void IDE:

- `Run Task…` → **Credit API (dev)**

Verify in browser:

- `http://127.0.0.1:8002/health`  
  You should see JSON including the active credit model path (e.g. `credit_20251109_205733`).

### 3.2. Start Fraud API (8001)

In a second terminal (or a second task):

```bash
cd C:\DevProjects\risk_analysis_flagship
.\.venv\Scripts\Activate.ps1

python fraud_detection_system\api\run_api.py
```

Verify:

- `http://127.0.0.1:8001/health`
- `GET /docs` shows the FastAPI docs

### 3.3. Start Gateway (8000)

Back in your main terminal (with venv active):

```bash
python -m uvicorn shared_env.api_gateway:app --port 8000
```

Gateway routes:

- Proxies credit requests to `http://127.0.0.1:8002/score`
- Proxies fraud requests to `http://127.0.0.1:8001/score`
- Adds missing `account_age_days` for fraud payloads
- CORS: allows `http://127.0.0.1:8010`

---

## 4. Serve docs_site locally (8010)

In a **third** terminal:

```bash
cd C:\DevProjects\risk_analysis_flagship
python -m http.server 8010
```

Open:

- `http://127.0.0.1:8010/docs_site/`

You should see the same pages as the Cloudflare-hosted site.

---

## 5. Flip docs_site to local mode

Config file:

- `C:\DevProjects\risk_analysis_flagship\docs_site\config.json`

### 5.1. Hosted mode (committed version)

The committed config is:

```json
{
  "mode": "hosted",
  "apiBase": "http://127.0.0.1:8000",
  "useMock": true
}
```

In this mode:

- Charts read from `docs_site\demo_data\...` only
- API buttons are **visually present** but call mock handlers in JS

### 5.2. Local live-API mode (demo-only)

Before the interview, **temporarily** change config.json to:

```json
{
  "mode": "local",
  "apiBase": "http://127..0.1:8000",
  "useMock": false
}
```

Do **not** commit this change.

This tells docs_site to:

- Call the FastAPI gateway on port 8000
- Expect live responses for **“Score via API (local only)”** buttons
- Show real JSON in the response panel on the Credit and Fraud pages

---

## 6. Demo flow (what to click and say)

### 6.1. Start with hosted Cloudflare link

1. Show `https://risk-analysis-flagship.pages.dev/`
2. Explain:
   - Data is Kaggle-based and pre-aggregated
   - No live APIs in hosted mode (safe, static)
   - Charts come from `docs_site\demo_data\...` CSVs

### 6.2. Switch to local tab

1. Switch to `http://127.0.0.1:8010/docs_site/`
2. Confirm mode label (Home page) now reflects **local mode**:
   - e.g. `Mode: Local demo • Snapshot end: ...`
3. Briefly highlight:
   - Credit page KPIs and charts
   - Fraud page metrics and latency
   - Ops page server/flows cards

### 6.3. Run a live credit scoring call

On **Credit** page (local site):

1. Locate **“Score via API (local only)”** panel.
2. Click the button once.
3. Show in DevTools → Network:
   - Request: `POST http://127.0.0.1:8000/...credit.../score`
   - Response: HTTP 200, JSON body (score, PD, EL, etc.)
4. In the UI:
   - Highlight that the JSON response is rendered in the panel.

Explain:

- Credit API uses the same model referenced in MLflow
- Gateway routes and standardizes payloads, hiding service details from the frontend

### 6.4. Run a live fraud scoring call

On **Fraud** page (local site):

1. Find **“Score via API (local only)”** panel.
2. Click once.
3. Show in DevTools:
   - `POST http://127.0.0.1:8000/...fraud.../score`
   - Response: JSON with fraud flag, probability, and top drivers
4. Explain:
   - Fraud API logs async to `fraud_detection_system\api\logs\YYYYMMDD.jsonl`
   - Those logs feed Stage 5–7 monitoring + A/B evaluation

---

## 7. (Optional) Show alerts

If `.env` is configured for Slack/Gmail:

From another terminal:

```bash
cd C:\DevProjects\risk_analysis_flagship
.\.venv\Scripts\Activate.ps1

python shared_env\monitoring\alert_bridge.py --test --severity warn
```

Explain:

- Same bridge is used at the end of daily flows
- Severity controls whether messages fire (e.g. drift threshold, latency threshold)

Details in `docs/OPS_AND_GOVERNANCE.md`.

---

## 8. Post-demo cleanup

1. Stop services in reverse order:
   - Ctrl+C in:
     - gateway terminal (8000)
     - static server (8010)
     - fraud API
     - credit API
2. Deactivate venv (optional): `deactivate`

### 8.1. Reset docs_site config

In Void IDE (or Git UI):

- Open Source Control
- If `docs_site\config.json` is listed as modified:
  - Use **Discard Changes** to revert to the committed version

Committed config should be back to:

```json
{
  "mode": "hosted",
  "apiBase": "http://127.0.0.1:8000",
  "useMock": true
}
```

This keeps the repo safe and ready for the next run.

---

## 9. If anything breaks during demo

- If APIs are up but UI is failing:
  - Hit `http://127.0.0.1:8001/docs` and `http://127.0.0.1:8002/docs`
  - Show the OpenAPI spec directly
- If docs_site is up but gateway is down:
  - Switch config back to hosted mode and explain the design
- Worst case:
  - Keep Cloudflare hosted demo as fallback
  - Talk through local wiring using `docs/ARCHITECTURE.md` diagrams
