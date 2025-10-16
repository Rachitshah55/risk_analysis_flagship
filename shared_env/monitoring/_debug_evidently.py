import sys, importlib, pkgutil, os

print("== Python ==")
print("executable:", sys.executable)
print()

print("== Import evidently top-level ==")
try:
    import evidently
    print("evidently.__file__:", getattr(evidently, "__file__", None))
    print("evidently.__version__:", getattr(evidently, "__version__", None))
except Exception as e:
    print("FAILED top-level import:", e)

print("\n== Try submodules ==")
for m in ["evidently.report", "evidently.metric_preset", "evidently.dashboard", "evidently.tabs"]:
    try:
        importlib.import_module(m)
        print("OK:", m)
    except Exception as e:
        print("NO:", m, "->", e)

print("\n== First 5 sys.path entries ==")
for p in sys.path[:5]:
    print(" -", p)
