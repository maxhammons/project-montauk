# Craftsman Position

**Position:** The system is not honestly optimizing for "Beat Buy & Hold".
**Evidence:** While `CLAUDE.md` and the metrics state `vs B&H` is the primary target, the multiplier chain means a strategy that beats B&H by 20% but has slightly too much cycle concentration (HHI > 0.35) gets zeroed out. A strategy with 4 trades instead of 5 gets zeroed out. We are optimizing for a highly specific, human-defined aesthetic of "robustness," not purely market performance. We need to untangle the hard gates from the continuous fitness score.