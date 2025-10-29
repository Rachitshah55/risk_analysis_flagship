# Pull Request — Risk Analysis Flagship

## Summary
<!-- What changed and why? Keep it crisp. -->

## Checklist — Governance & Audit
- [ ] **Fraud rules changed?** (`fraud_detection_system/rules/*.yml`)
  - [ ] `fraud_detection_system/rules/CHANGELOG.md` updated with `## vX.Y.Z - YYYY-MM-DD`
  - [ ] Rationale + scope included
  - [ ] Sign-offs block filled (Owner, Risk Lead, Release Mgr)
- [ ] **Models/artifacts changed?**
  - [ ] Credit: `docs/model_cards/credit_model.md` updated (Change Log, metrics, MLflow run ID)
  - [ ] Fraud: `docs/model_cards/fraud_model.md` updated (Change Log, metrics, MLflow run ID)
  - [ ] If `PROD_POINTER.txt` changed: added smoke evidence (`/health` OK, 1–2 `/score` vectors)
- [ ] **Release line?** (`release/*` branch or `v*` tag)
  - [ ] Audit pack built & committed: `docs_global/audits/YYYY-MM-DD/`
- [ ] **Governance Gate (local)**
  - [ ] Ran `.venv\Scripts\python.exe shared_env\ci\governance_gate.py` → **OK**
- [ ] **Secrets check**
  - [ ] No secrets committed (e.g., `shared_env/secrets/*.json`, `.env`). Use `.env.template` only.
- [ ] **Runbooks** updated if operational behavior changed

## Evidence
- MLflow run IDs:  
- Screenshots / paths:  
- Audit pack path: `docs_global/audits/YYYY-MM-DD/`

## Approvals
- [ ] Owner  
- [ ] Risk Lead  
- [ ] Release Manager
