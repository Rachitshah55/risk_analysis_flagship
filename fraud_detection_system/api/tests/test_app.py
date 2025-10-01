# ===== BEGIN: test_app.py =====
from fastapi.testclient import TestClient
from fraud_detection_system.api.app import app

client = TestClient(app)

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    for k in ["status", "model_timestamp", "rules_count", "features_count"]:
        assert k in data
    assert data["status"] == "ok"

def test_score_shape():
    payload = {
        "amount": 99.0,
        "account_age_days": 7,
        "country": "US",
        "device_id": "T1",
        "hour_of_day": 22
    }
    r = client.post("/score", json=payload)
    assert r.status_code == 200
    data = r.json()
    for k in ["decision", "proba", "rules_hit", "model_timestamp", "latency_ms"]:
        assert k in data
    assert isinstance(data["proba"], float)
    assert isinstance(data["rules_hit"], list)
# ===== END: test_app.py =====