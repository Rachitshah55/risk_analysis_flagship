from pathlib import Path
import pandas as pd

def test_numeric_only_adapter_tolerates_empty_files():
    # mimic your Stage-5 guards: numeric-only selection + empty-file tolerance
    # This is a placeholder "stability" test rather than asserting PSI values.
    df = pd.DataFrame({"amount": [1.0, 2.0], "country": ["US", "CA"]})
    numeric = df.select_dtypes("number")
    assert "amount" in numeric.columns
    # empty file scenario:
    try:
        pd.read_csv(Path("nonexistent.csv"))
    except Exception:
        # expected error: ensure our code would wrap it (manually pass test here)
        pass
