# Convergence Map — Apr-09

**Convergent findings:**
- The hash index cache (`hash-index.json`) is vulnerable to engine-version poisoning. Bug fixes to the backtester do not invalidate old cached scores, permanently corrupting the optimizer's memory.
- The fitness formula's multiplier logic (HHI, complexity, drawdown) obscures the primary "Beat Buy & Hold" target, making the score opaque and gameable.

**Contested claims:**
- **The Dual-Engine Necessity:** The Pragmatist argues the split between Python optimization and Pine Script execution is fundamentally fatal. The Craftsman and Accelerator argue it is a necessary friction that provides superior testing capabilities, which just needs better deployment tooling (an injection script).

**Blocker inventory:**
- Pragmatist: The architectural split between the optimization engine and execution environment.
- Futurist: Algebraic fitness penalties leading to equation-gaming.
- Craftsman: Opaque, multiplier-based ranking system.
- Accelerator: Air-gapped deployment (manual parameter transcription).
- Exploiter: Unversioned cache poisoning.

**Evolution summary:**
Positions coalesced around the Exploiter's finding as the most immediate existential threat. The debate shifted from abstract concerns about dual-engine translation to concrete issues of trust in the optimizer's output and deployment velocity.