# Fraud Rules — Changelog

> Policy: Any change to files under `fraud_detection_system/rules/*.yml` **must** add a new version section below with date, rationale, and sign-offs. This keeps CI governance green and your audit trail complete.

## v1.0.0 - 2025-10-24
Baseline production ruleset paired with the baseline model (Stage 3) and the FastAPI scoring service (Stage 4).

### Rules included
- **R001_HIGH_AMOUNT_NEW_ACCOUNT** — Flag very high amounts on young accounts.
- **R002_VELOCITY_SPIKE** — Flag short-window spikes vs recent user baseline.
- **R003_CROSS_BORDER_ODD_HOURS** — Flag cross-border activity at risky hours.

### Sign-offs
- Owner: ____________________  Date: __________
- Risk Lead: ________________  Date: __________
- Release Manager: __________  Date: __________

---

### Pre-v1 history (notes)
- 2025-10-18 — Added “High Amount + New Device” rule with a $7,500 threshold to reduce false positives on loyal users.
- 2025-10-12 — Adjusted “Velocity Spike” multiplier from **3.0×** to **3.5×** after weekend surge analysis.

