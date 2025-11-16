from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

# Downstream services
CREDIT_API_BASE = "http://127.0.0.1:8002"
FRAUD_API_BASE = "http://127.0.0.1:8001"

app = FastAPI(title="Risk Demo Gateway")

# Allow the static site from port 8010 to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8010",
        "http://localhost:8010",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _forward_json(target_url: str, payload: dict):
    """
    Forward JSON to downstream service and always return JSON (or JSON error).
    """
    try:
        resp = requests.post(target_url, json=payload, timeout=10)
    except requests.RequestException as e:
        # Gateway couldn't reach downstream
        raise HTTPException(status_code=502, detail=f"Downstream error: {e}")

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            return resp.json()
        except ValueError:
            # Downstream sent broken JSON
            raise HTTPException(
                status_code=502,
                detail=f"Invalid JSON from downstream: {resp.text[:200]}",
            )
    # Non-JSON body (HTML error, traceback, etc.)
    raise HTTPException(
        status_code=resp.status_code or 502,
        detail=resp.text[:500],
    )

@app.post("/credit/score")
@app.post("/api/credit/score")
async def credit_score(request: Request):
    payload = await request.json()
    return _forward_json(f"{CREDIT_API_BASE}/score", payload)

@app.post("/fraud/score")
@app.post("/api/fraud/score")
async def fraud_score(request: Request):
    payload = await request.json()

    # Ensure required field for backend schema
    if "account_age_days" not in payload:
        # Pick a sane default for demo purposes
        payload["account_age_days"] = 365

    return _forward_json(f"{FRAUD_API_BASE}/score", payload)


@app.get("/health")
def health():
    return {"ok": True}
