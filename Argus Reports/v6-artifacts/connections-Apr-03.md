# Connections Graph — Apr-03

## Root Cause Clusters

### Cluster A: "The Dual Engine Schism" (ALL 5 specialists)
**Root cause**: strategy_engine.py was created as a fresh implementation rather than extending backtest_engine.py. This single architectural decision cascades into:
- Architecture F1: Competing backtesting architectures
- Risk R-01: Dual engine divergence
- Data-Integrity F1: Divergent engines producing incompatible results
- Vision-Drift F7: Two coexisting engines
- Velocity F1: Duplicate backtesting engines
- Risk R-08: Validation framework can't validate v4 strategies
- Data-Integrity F4: Walk-forward validation disconnected
- Architecture F2: Triple-duplicated indicator code
- Data-Integrity F3: RSI calculation diverges from Pine Script

### Cluster B: "The RSI Regime Illusion" (ALL 5 specialists)
**Root cause**: A 36-second optimizer run declared RSI Regime the winner against a crippled 8.2.1 baseline with no validation. Cascades into:
- Architecture F6: montauk_821 NOT faithful to real 8.2.1 (30-bar vs 500-bar EMA)
- Risk R-02: Wrong EMA exit in strategies.py
- Data-Integrity F1: 4.7x comparison invalid (6 missing features)
- Risk R-03: RSI Regime dangerously overfitted (100% win/10 trades/75% DD)
- Data-Integrity F2: Classic overfitting signatures
- Architecture F8: Evolve run trivially short (36 seconds)
- Velocity F8: 2.7% of parameter space explored
- Risk R-10: Fitness function under-penalizes catastrophic drawdowns
- Cross-pollination: "4.7x gap is a triple illusion" (strawman baseline + wrong RSI + in-sample only)

### Cluster C: "The Charter Gap" (Architecture + Vision-Drift + Risk)
**Root cause**: The project evolved from Pine Script editing to Python strategy discovery platform without updating its governing document.
- Vision-Drift F1: Identity metamorphosis
- Vision-Drift F2: Charter S8 mean-reversion ban violated
- Vision-Drift F3: Metrics silently replaced (MAR → vs_bah)
- Vision-Drift F4: Charter frozen 31 days
- Architecture F4: Charter violation
- Vision-Drift F5: Feature acceptance checklist not applied
- Vision-Drift F10: Python coding rules missing

### Cluster D: "The Deployment Gap" (Architecture + Risk + Vision-Drift + Velocity)
**Root cause**: Pine Script generation only supports 8.2.1. The optimizer can discover but cannot deploy.
- Architecture F5: Pine generation bottleneck
- Risk R-15: generate_pine.py cannot produce non-Montauk strategies
- Vision-Drift F12: generate_pine.py cannot handle non-8.2.1
- Velocity F7: Deployment bottleneck
- Vision-Drift F8: No parity validation for non-8.2.1

### Cluster E: "Dead Weight" (Architecture + Vision-Drift + Velocity)
**Root cause**: Each spike rewrite left behind its predecessor without cleanup.
- Architecture F3: 1,028 lines dead code
- Velocity F2: 39% dead code (1,819 lines)
- Vision-Drift F11: Dead code from rapid pivots
- Velocity F3: Spike skill 4x rewrites

### Cluster F: "Zero Safety Net" (Risk + Velocity)
**Root cause**: Financial calculation code with no tests, no CI, no deployment gates.
- Risk R-05: Zero test coverage
- Velocity F4: Zero tests
- Risk R-07: No deployment guardrails
- Risk R-04: Silent exception swallowing

## Open Questions Resolved by Cross-Pollination

| Question | Asked By | Answered By | Answer |
|----------|----------|-------------|--------|
| ADX implementations differ materially? | Architecture | Data-Integrity, Risk | Yes — v4 uses nan_to_num(0.0) biasing warmup; v3 uses proper Wilder summation |
| process_orders_on_close match Python? | Risk | Architecture, Data-Integrity | Mostly yes, but v4 has same-bar exit+entry suppression when cooldown=0 |
| TECL leverage decay modeled? | Risk | All | No, but prices embed it. Regime scoring 30% bear threshold is too low for 3x ETF |
| RSI boundary <= vs < cause divergence? | Data-Integrity | Architecture | Yes — confirmed 1-character fix needed in strategies.py line 133 |
| bear_avoidance=1.0 default inflating? | Data-Integrity | Architecture | Yes — free 0.5 added to composite in bear-free windows |
| RSI paradigm shift deliberate or unconscious? | Vision-Drift | All | Deliberate tactically (spike.md opened search), unconscious constitutionally (Charter never consulted) |
| Charter update or code rein in? | Vision-Drift | Vision-Drift, Velocity | Update Charter, but ONLY after RSI Regime passes walk-forward validation against a correct baseline |
| Will 8-hour run change rankings? | Velocity | Velocity, Risk | RSI Regime stays #1 (gap too large), but fix baseline FIRST — running 8 hours on broken baseline wastes time |
| Is 4x rewrite pattern convergence or indecision? | Velocity | Velocity | Convergence — each version contracted scope. v5 only if fixing baseline narrows RSI advantage |

## Strongest Cross-Lens Findings

1. **The 4.7x fitness gap is a triple illusion** (Vision-Drift × Data-Integrity × Architecture): Strawman baseline (wrong EMA + 6 missing features) + wrong RSI signals (np.diff prepend) + in-sample-only evaluation. RSI Regime's actual superiority is unknown.

2. **Governance cascade failure** (Risk × Vision-Drift): All 7 layers from Charter to deployment have bypasses. RSI Regime proves the entire chain can be circumvented.

3. **Fix then run sequencing** (Velocity × all): Running 8 hours on the broken baseline wastes 16 hours total (8 to run, 8 to re-run after fixing). Fix montauk_821 and merge engines FIRST.

4. **spike.md is the de facto Charter** (Vision-Drift): It overrides scope, identity, language, backtesting, and metrics without formal governance.
