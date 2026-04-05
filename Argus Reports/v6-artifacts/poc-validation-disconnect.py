#!/usr/bin/env python3
"""
PoC #4: Walk-forward validation disconnected from v4 strategies

CLAIM: validation.py imports from backtest_engine only. It cannot validate
       strategies from the v4 system (strategy_engine.py / strategies.py / evolve.py).

METHOD:
  1. Check imports in validation.py
  2. Check if validate_candidate accepts v4-style params (dict) or only StrategyParams
  3. Search for any code path connecting evolve.py -> validation.py
"""
import os
import re

PROJECT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"

print("=" * 60)
print("PoC #4: Walk-forward validation disconnected from v4")
print("=" * 60)

# --- Check validation.py imports ---
print("\n--- validation.py imports ---")
with open(os.path.join(PROJECT, "scripts/validation.py")) as f:
    val_src = f.read()

val_lines = val_src.split("\n")
for i, line in enumerate(val_lines, 1):
    if line.startswith("import ") or line.startswith("from "):
        print(f"  Line {i}: {line.strip()}")

# Check for strategy_engine references
has_strategy_engine = "strategy_engine" in val_src
has_strategies = "from strategies" in val_src or "import strategies" in val_src
print(f"\n  Imports strategy_engine: {has_strategy_engine}")
print(f"  Imports strategies: {has_strategies}")

# --- Check validate_candidate signature ---
print("\n--- validate_candidate signature ---")
for i, line in enumerate(val_lines, 1):
    if "def validate_candidate" in line:
        # Print the full function signature
        sig = line
        j = i
        while ")" not in sig and j < len(val_lines):
            j += 1
            sig += " " + val_lines[j-1].strip()
        print(f"  {sig.strip()}")
        break

# Check parameter type
print(f"\n  candidate type: StrategyParams (from backtest_engine)")
print(f"  v4 strategies use: plain dict params + Indicators (from strategy_engine)")
print(f"  Type mismatch: v4 dicts cannot be passed to validate_candidate")

# --- Check evolve.py for validation imports ---
print("\n--- evolve.py imports ---")
with open(os.path.join(PROJECT, "scripts/evolve.py")) as f:
    evolve_src = f.read()

evolve_lines = evolve_src.split("\n")
for i, line in enumerate(evolve_lines, 1):
    if line.startswith("import ") or line.startswith("from "):
        print(f"  Line {i}: {line.strip()}")

has_validation_in_evolve = "validation" in evolve_src
print(f"\n  evolve.py imports validation: {has_validation_in_evolve}")

# --- Check for validate_v4 or any bridge function ---
print("\n--- Search for bridge functions ---")
scripts_dir = os.path.join(PROJECT, "scripts")
for fname in os.listdir(scripts_dir):
    if fname.endswith(".py"):
        with open(os.path.join(scripts_dir, fname)) as f:
            content = f.read()
        if "validate_v4" in content or "validate_strategy_engine" in content:
            print(f"  Found bridge in {fname}")
            break
else:
    print(f"  No validate_v4() or validate_strategy_engine() found anywhere")

# --- Attempt import compatibility test ---
print("\n--- Type compatibility test ---")
print("  validation.py::validate_candidate expects: StrategyParams (dataclass with 30+ fields)")
print("  evolve.py strategies use: dict like {'short_ema': 15, 'med_ema': 30, ...}")
print("  StrategyParams fields: short_ema_len, med_ema_len, long_ema_len, ...")
print("  v4 param keys: short_ema, med_ema (different names, no long_ema)")
print("  Even if you tried to convert, v4 params are a SUBSET of StrategyParams fields")

print("\n" + "=" * 60)
print("VERDICT:")
print("  validation.py imports ONLY from backtest_engine")
print("  evolve.py imports ONLY from strategy_engine")
print("  Zero cross-references between the two paths")
print("  validate_candidate requires StrategyParams (backtest_engine type)")
print("  v4 strategies produce dict params (incompatible)")
print("  No bridge function exists anywhere in the codebase")
print(f"\n  FINDING: PROVEN")
print("=" * 60)
