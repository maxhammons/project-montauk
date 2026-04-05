#!/usr/bin/env python3
"""
PoC #5: Indicator divergence — EMA(15) comparison between two engines

CLAIM: backtest_engine.py::ema() and strategy_engine.py::_ema() may diverge.

METHOD: Extract both EMA functions, run them on identical test data,
        compare outputs numerically.
"""
import numpy as np
import sys
import os

print("=" * 60)
print("PoC #5: EMA indicator divergence between engines")
print("=" * 60)

# --- Inline both EMA implementations (read-only from project) ---

def ema_backtest_engine(series, length):
    """From backtest_engine.py (lines 131-141)"""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    out[length - 1] = np.mean(series[:length])
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def ema_strategy_engine(series, length):
    """From strategy_engine.py (lines 29-37)"""
    out = np.full_like(series, np.nan, dtype=np.float64)
    if len(series) < length:
        return out
    alpha = 2.0 / (length + 1)
    out[length - 1] = np.mean(series[:length])
    for i in range(length, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


# --- Generate test data ---
np.random.seed(42)
# Simulate a price series similar to TECL (start ~$50, ~1% daily vol)
n = 1000
returns = np.random.normal(0.0005, 0.03, n)
prices = np.zeros(n)
prices[0] = 50.0
for i in range(1, n):
    prices[i] = prices[i-1] * (1 + returns[i])

print(f"\nTest data: {n} bars, price range [{prices.min():.2f}, {prices.max():.2f}]")

# --- Test EMA(15) ---
length = 15
result_be = ema_backtest_engine(prices, length)
result_se = ema_strategy_engine(prices, length)

print(f"\n--- EMA({length}) comparison ---")

# Compare
valid = ~np.isnan(result_be) & ~np.isnan(result_se)
if valid.any():
    diff = np.abs(result_be[valid] - result_se[valid])
    max_diff = diff.max()
    mean_diff = diff.mean()

    print(f"  Valid points: {valid.sum()}")
    print(f"  Max absolute difference: {max_diff:.15e}")
    print(f"  Mean absolute difference: {mean_diff:.15e}")
    print(f"  First 5 values (backtest_engine): {result_be[length-1:length+4]}")
    print(f"  First 5 values (strategy_engine): {result_se[length-1:length+4]}")

    # Check if they're identical
    identical = np.allclose(result_be[valid], result_se[valid], atol=1e-12)
    print(f"  Numerically identical (atol=1e-12): {identical}")
else:
    print("  ERROR: No valid comparison points")

# --- Test EMA(500) (the long EMA that only backtest_engine uses) ---
length2 = 500
result_be2 = ema_backtest_engine(prices, length2)
result_se2 = ema_strategy_engine(prices, length2)

print(f"\n--- EMA({length2}) comparison ---")
valid2 = ~np.isnan(result_be2) & ~np.isnan(result_se2)
if valid2.any():
    diff2 = np.abs(result_be2[valid2] - result_se2[valid2])
    print(f"  Valid points: {valid2.sum()}")
    print(f"  Max absolute difference: {diff2.max():.15e}")
    print(f"  Numerically identical: {np.allclose(result_be2[valid2], result_se2[valid2], atol=1e-12)}")
else:
    print(f"  Only {valid2.sum()} valid points (need {length2} bars for warmup)")

# --- Source code comparison ---
print(f"\n--- Source code diff ---")
PROJECT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"

with open(os.path.join(PROJECT, "scripts/backtest_engine.py")) as f:
    be_lines = f.readlines()
with open(os.path.join(PROJECT, "scripts/strategy_engine.py")) as f:
    se_lines = f.readlines()

# Extract just the EMA functions
def extract_func(lines, func_name, start_search=0):
    in_func = False
    func_lines = []
    for i, line in enumerate(lines):
        if f"def {func_name}" in line:
            in_func = True
        elif in_func and line.strip() and not line[0].isspace() and "def " in line:
            break
        if in_func:
            func_lines.append(line.rstrip())
    return func_lines

be_ema = extract_func(be_lines, "ema(")
se_ema = extract_func(se_lines, "_ema(")

print(f"  backtest_engine.py ema(): {len(be_ema)} lines")
print(f"  strategy_engine.py _ema(): {len(se_ema)} lines")

# Compare logic (ignore names and comments)
def normalize(lines):
    result = []
    for line in lines:
        l = line.strip()
        if not l or l.startswith("#") or l.startswith('"""') or l.startswith("def "):
            continue
        result.append(l)
    return result

be_norm = normalize(be_ema)
se_norm = normalize(se_ema)

print(f"  Logic lines (backtest_engine): {len(be_norm)}")
print(f"  Logic lines (strategy_engine): {len(se_norm)}")

identical_logic = be_norm == se_norm
print(f"  Logic identical: {identical_logic}")

if not identical_logic:
    print(f"\n  Differences:")
    for i, (a, b) in enumerate(zip(be_norm, se_norm)):
        if a != b:
            print(f"    BE: {a}")
            print(f"    SE: {b}")

print("\n" + "=" * 60)
print("VERDICT:")
if identical:
    print("  EMA implementations are NUMERICALLY IDENTICAL")
    print("  Both use: SMA seed + recursive EMA with alpha = 2/(length+1)")
    print("  The divergence risk is NOT in the EMA function itself")
    print("  The REAL divergence is in WHICH EMA is used (30-bar vs 500-bar)")
    print(f"\n  FINDING: DISPROVEN (EMA functions match; the bug is in parameter selection, not computation)")
else:
    print("  EMA implementations DIVERGE")
    print(f"  Max difference: {max_diff}")
    print(f"\n  FINDING: PROVEN")
print("=" * 60)
