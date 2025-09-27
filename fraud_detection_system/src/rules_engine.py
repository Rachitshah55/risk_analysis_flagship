import pandas as pd, yaml

class RulesEngine:
    def __init__(self, rules_path):
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f) or []

    def evaluate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        def norm(expr: str) -> str:
            # keep as-is; placeholders for future normalization if needed
            return expr
        for i, r in enumerate(self.rules):
            name = r.get("name", f"rule_{i}")
            cond = norm(r["condition"])
            try:
                mask = out.eval(cond, engine="python", parser="pandas")
            except Exception:
                mask = pd.Series(False, index=out.index)
            out[f"rule__{name}"] = mask.astype(int)
        # aggregate to flags/review
        out["rule_flag"] = 0
        out["rule_review"] = 0
        for i, r in enumerate(self.rules):
            name = r.get("name", f"rule_{i}")
            col = f"rule__{name}"
            if r.get("action") == "flag":
                out["rule_flag"] = out["rule_flag"] | out[col]
            if r.get("action") == "review":
                out["rule_review"] = out["rule_review"] | out[col]
        return out
# ===== END: rules_engine.py =====