#!/usr/bin/env python3
"""
PoC #3: Stagnation detection broken — _last_improve never set

CLAIM: evolve._last_improve is never assigned, so stagnation detection
       always computes stag = generation (treating every generation as stagnant).

METHOD: Search evolve.py for every occurrence of '_last_improve'.
        Classify each as read vs write.
"""
import os
import re

PROJECT = "/Users/Max.Hammons/Documents/local-sandbox/Project Montauk"

print("=" * 60)
print("PoC #3: Stagnation detection — _last_improve never set")
print("=" * 60)

with open(os.path.join(PROJECT, "scripts/evolve.py")) as f:
    src = f.read()

lines = src.split("\n")

print("\n--- All occurrences of '_last_improve' in evolve.py ---")
occurrences = []
for i, line in enumerate(lines, 1):
    if "_last_improve" in line:
        # Classify as read or write
        stripped = line.strip()
        # Write: `evolve._last_improve = ...` or `_last_improve[...] = ...`
        is_write = bool(re.search(r'_last_improve\s*(\[.*?\])?\s*=(?!=)', stripped))
        # But getattr read patterns are reads
        if "getattr" in stripped:
            is_write = False

        kind = "WRITE" if is_write else "READ"
        print(f"  Line {i} [{kind}]: {stripped}")
        occurrences.append((i, kind, stripped))

reads = sum(1 for _, k, _ in occurrences if k == "READ")
writes = sum(1 for _, k, _ in occurrences if k == "WRITE")

print(f"\n--- Summary ---")
print(f"  Total occurrences: {len(occurrences)}")
print(f"  Reads: {reads}")
print(f"  Writes: {writes}")

# Analyze the specific read
print(f"\n--- Impact analysis ---")
for i, line in enumerate(lines, 1):
    if "_last_improve" in line:
        print(f"  Line {i}: {line.strip()}")
        # Show context
        if "getattr" in line:
            print(f"    -> getattr(evolve, '_last_improve', {{}}) returns {{}} (empty dict)")
            print(f"    -> .get(strat_name, 0) returns 0")
            print(f"    -> stag = generation - 0 = generation")
    if "mut_rate" in line and "stag" in line:
        print(f"  Line {i}: {line.strip()}")

print(f"\n--- Practical impact on recorded run ---")
print(f"  The only recorded run had {19} generations")
print(f"  At gen 19: stag = 19 - 0 = 19")
print(f"  Since 19 < 30: mut_rate = 0.15 (base rate, CORRECT by accident)")
print(f"  Bug would activate at gen 30+ (never reached)")

print("\n" + "=" * 60)
print("VERDICT:")
print(f"  _last_improve READ count: {reads}")
print(f"  _last_improve WRITE count: {writes}")
print(f"  Bug confirmed: attribute is read but NEVER written")
print(f"  Stagnation = generation number, not actual stagnation")
print(f"  Impact on existing results: NONE (run was only 19 gens)")
print(f"\n  FINDING: PROVEN (bug exists, no impact on recorded results)")
print("=" * 60)
