# TECL Health Audit

Generated: 2026-04-27 21:46 UTC
Data through: 2026-04-21
Model: `tecl-health-v3-calibrated-diagnostic`

> Diagnostic-only report. TECL Health is not a buy/sell signal, not a strategy, and not part of leaderboard certification.

## Current Readout
| Date | Composite | Status | Confidence | Conflict | Fast Avg | Slow Avg |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-04-21 | 66.2 | constructive | 58.5 | 24.4 | 41.9 | 39.3 |

| Structure | Momentum | Stress | Participation |
| --- | --- | --- | --- |
| 33.0 | 87.0 | 35.1 | 77.9 |

## Calibration
| Setting | Value |
| --- | --- |
| Layer weights | structure 0.25, momentum 0.35, stress 0.20, participation 0.20 |
| Core blend | 0.65 geometric / 0.35 arithmetic |
| Recovery credit | 0.20 * max(0, min(momentum, participation) - stress) |
| Stress cap | final score capped at 55 + 0.85 * stress score + 0.5 * recovery credit |
| Basis | marker-cycle directional fit, named-regime separation, and crash compression |

## Coverage
| Input | Coverage |
| --- | --- |
| TECL rows | 8298 |
| VIX matched rows | 8298/8298 |
| Named regimes | 15 |
| Marker cycles | 28 |
| Marker-cycle directional fit | 23/28 |

## Observations
- Named-regime separation: bull/recovery average health is 56.3 vs bear/crash 19.5, a 36.8-point spread.
- Strongest named regime: Dot-com melt-up at 60.0 average health.
- Weakest named regime: Dot-com bust / Y2K fallout at 12.6 average health.
- Marker-cycle fit: 23/28 evaluated cycles are aligned or borderline.
- Main marker mismatches: 2001-04-05 to 2001-05-22 (risk_on, avg 6.7); 2021-08-26 to 2021-10-05 (risk_off, avg 60.2); 2024-03-04 to 2024-04-23 (risk_off, avg 57.9).
- Highest layer conflict by named regime: Dot-com melt-up at 18.7.
- Latest readout: 2026-04-21 is constructive with composite 66.2, confidence 58.5, and conflict 24.4.

## Named Regimes
| Regime | Kind | Dates | TECL Return | Avg | Min/Max | End | Struct/Mom/Stress/Part | Conf/Conflict | Fit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Early tech bull | bull | 1993-05-04 to 1998-10-07 | +1683.2% | 55.0 | 5.1/95.3 | 5.1 | 51/54/41/70 | 72/17 | aligned |
| Dot-com melt-up | bull | 1998-10-08 to 2000-03-24 | +1999.4% | 60.0 | 4.6/94.4 | 78.2 | 63/62/40/71 | 68/19 | aligned |
| Dot-com bust / Y2K fallout | bear | 2000-03-27 to 2002-10-09 | -99.9% | 12.6 | 1.9/77.5 | 3.5 | 7/15/15/18 | 87/8 | aligned |
| Housing / credit bull | bull | 2002-10-10 to 2007-10-31 | +592.5% | 50.3 | 3.9/90.4 | 77.3 | 41/50/60/58 | 77/14 | borderline |
| GFC crash | crash | 2007-11-01 to 2009-03-09 | -94.2% | 15.9 | 1.9/75.1 | 4.6 | 10/20/8/24 | 85/9 | aligned |
| QE recovery | recovery | 2009-03-10 to 2011-04-29 | +433.3% | 53.3 | 4.8/87.6 | 57.5 | 44/56/49/65 | 75/15 | borderline |
| Euro crisis / downgrade chop | chop | 2011-05-02 to 2012-11-15 | -16.7% | 45.3 | 5.4/90.4 | 14.7 | 36/45/52/58 | 79/13 | neutral |
| Secular tech bull | bull | 2012-11-16 to 2018-09-20 | +1456.6% | 58.3 | 6.0/89.7 | 73.0 | 54/59/57/66 | 81/11 | aligned |
| Tightening / trade-war drawdown | bear | 2018-09-21 to 2018-12-24 | -57.7% | 23.3 | 3.0/78.1 | 3.0 | 21/21/16/40 | 82/10 | aligned |
| Pre-COVID melt-up | bull | 2018-12-26 to 2020-02-19 | +311.1% | 57.7 | 3.4/92.8 | 89.2 | 51/61/40/69 | 75/15 | aligned |
| COVID crash | crash | 2020-02-20 to 2020-03-23 | -74.3% | 22.8 | 3.3/87.1 | 3.3 | 33/18/5/48 | 71/17 | aligned |
| Stimulus / reopening bull | bull | 2020-03-24 to 2021-11-19 | +689.5% | 59.6 | 4.5/89.1 | 84.6 | 55/60/43/74 | 72/16 | aligned |
| Inflation / hiking bear | bear | 2021-11-22 to 2022-10-12 | -75.6% | 22.8 | 3.0/87.3 | 4.5 | 18/24/19/32 | 84/9 | aligned |
| AI / disinflation bull | bull | 2022-10-13 to 2024-07-10 | +415.2% | 56.3 | 4.5/91.8 | 88.5 | 51/55/56/68 | 79/13 | aligned |
| Late-cycle policy volatility | policy | 2024-07-11 to 2026-04-21 | +29.5% | 45.2 | 2.8/88.7 | 66.2 | 39/42/43/64 | 77/14 | neutral |

## Marker Cycles
| Cycle | Markers | TECL Return | Avg | Start/End | Healthy Days | Fragile Days | Fit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1999-10-27 to 2000-03-23 | buy -> sell | +257.0% | 66.3 | 29.3/78.2 | 71% | 12% | aligned |
| 2000-03-23 to 2001-04-05 | sell -> buy | -97.4% | 16.7 | 78.2/2.9 | 3% | 91% | aligned |
| 2001-04-05 to 2001-05-22 | buy -> sell | +80.5% | 6.7 | 2.9/14.2 | 0% | 100% | mismatch |
| 2001-05-22 to 2002-10-07 | sell -> buy | -97.2% | 10.5 | 14.2/3.5 | 0% | 100% | aligned |
| 2002-10-07 to 2004-01-21 | buy -> sell | +373.8% | 50.1 | 3.5/89.1 | 46% | 46% | borderline |
| 2004-01-21 to 2004-08-12 | sell -> buy | -48.6% | 40.9 | 89.1/10.2 | 13% | 70% | aligned |
| 2004-08-12 to 2006-04-05 | buy -> sell | +79.1% | 49.4 | 10.2/74.3 | 31% | 52% | mismatch |
| 2006-04-05 to 2006-07-26 | sell -> buy | -36.6% | 28.1 | 74.3/14.3 | 9% | 83% | aligned |
| 2006-07-26 to 2007-10-29 | buy -> sell | +170.9% | 60.8 | 14.3/75.5 | 59% | 27% | aligned |
| 2007-10-29 to 2009-03-02 | sell -> buy | -93.3% | 16.6 | 75.5/4.7 | 2% | 96% | aligned |
| 2009-03-02 to 2011-02-09 | buy -> sell | +513.0% | 53.0 | 4.7/85.6 | 47% | 41% | borderline |
| 2011-02-09 to 2011-12-20 | sell -> buy | -34.8% | 37.8 | 85.6/29.6 | 5% | 77% | aligned |
| 2011-12-20 to 2018-10-03 | buy -> sell | +1759.8% | 57.8 | 29.6/78.1 | 51% | 36% | aligned |
| 2018-10-03 to 2018-12-28 | sell -> buy | -51.7% | 15.6 | 78.1/4.5 | 3% | 97% | aligned |
| 2018-12-28 to 2020-02-21 | buy -> sell | +265.1% | 58.3 | 4.5/82.1 | 52% | 39% | aligned |
| 2020-02-21 to 2020-03-25 | sell -> buy | -64.8% | 18.6 | 82.1/4.7 | 4% | 96% | aligned |
| 2020-03-25 to 2021-08-26 | buy -> sell | +515.4% | 59.2 | 4.7/84.7 | 51% | 35% | aligned |
| 2021-08-26 to 2021-10-05 | sell -> buy | -12.4% | 60.2 | 84.7/32.3 | 54% | 43% | mismatch |
| 2021-10-05 to 2021-12-30 | buy -> sell | +52.7% | 67.2 | 32.3/86.1 | 54% | 15% | aligned |
| 2021-12-30 to 2023-01-12 | sell -> buy | -71.4% | 16.4 | 86.1/31.5 | 2% | 98% | aligned |
| 2023-01-12 to 2024-03-04 | buy -> sell | +235.8% | 63.7 | 31.5/86.6 | 58% | 31% | aligned |
| 2024-03-04 to 2024-04-23 | sell -> buy | -20.7% | 57.9 | 86.6/33.1 | 42% | 39% | mismatch |
| 2024-04-23 to 2024-07-15 | buy -> sell | +60.4% | 64.3 | 33.1/86.4 | 58% | 28% | aligned |
| 2024-07-15 to 2024-08-05 | sell -> buy | -41.7% | 43.1 | 86.4/12.8 | 12% | 62% | aligned |
| 2024-08-05 to 2025-02-19 | buy -> sell | +58.1% | 46.2 | 12.8/46.5 | 25% | 62% | mismatch |
| 2025-02-19 to 2025-04-24 | sell -> buy | -47.5% | 12.5 | 46.5/5.3 | 2% | 98% | aligned |
| 2025-04-24 to 2025-10-30 | buy -> sell | +184.7% | 65.0 | 5.3/88.0 | 67% | 21% | aligned |
| 2025-10-30 to 2026-04-21 | sell -> open | -8.7% | 34.0 | 88.0/66.2 | 7% | 81% | aligned |

## Detected Cycle Snapshot
Last 12 algorithmic bull/bear cycles from `scripts/strategies/regime_map.py`.
| Type | Dates | Move | Duration | Avg Health | End Health | Fit |
| --- | --- | --- | --- | --- | --- | --- |
| bear | 2018-10-03 to 2018-12-24 | -59.7% | 2.7 mo | 16.2 | 3.0 | aligned |
| bull | 2018-12-24 to 2020-02-19 | +383.8% | 13.9 mo | 57.5 | 89.2 | aligned |
| bear | 2020-02-19 to 2020-03-23 | -75.1% | 1.1 mo | 25.5 | 3.3 | aligned |
| bull | 2020-03-23 to 2020-09-02 | +390.5% | 5.4 mo | 51.7 | 88.4 | borderline |
| bear | 2020-09-02 to 2020-10-30 | -37.1% | 1.9 mo | 51.6 | 24.1 | borderline |
| bull | 2020-10-30 to 2021-12-27 | +252.8% | 13.9 mo | 64.4 | 85.0 | aligned |
| bear | 2021-12-27 to 2022-10-12 | -78.0% | 9.5 mo | 17.7 | 4.5 | aligned |
| bull | 2022-10-12 to 2024-07-10 | +462.0% | 21.0 mo | 56.2 | 88.5 | aligned |
| bear | 2024-07-10 to 2025-04-08 | -66.7% | 8.9 mo | 41.0 | 2.8 | aligned |
| bull | 2025-04-08 to 2025-10-29 | +309.1% | 6.7 mo | 60.1 | 88.2 | aligned |
| bear | 2025-10-29 to 2026-03-30 | -49.8% | 5.0 mo | 34.4 | 6.5 | aligned |
| bull | 2026-03-30 to 2026-04-21 | +75.3% | 0.7 mo | 33.2 | 66.2 | mismatch |

## Calibration Targets
- Preserve diagnostic-only behavior: no buy/sell calls, no leaderboard rank effect, no certification effect.
- Use marker-cycle separation as the first tuning target: risk-on windows should average materially above risk-off windows.
- Use named crash/bear regimes as the stress test: crashes should compress the health score quickly without permanently suppressing recovery regimes.
- Treat fast and slow averages as readout aids, not the primary truth source, until lag is measured against marker transitions.
- Review mismatched cycles before changing weights; a mismatch may be a useful warning rather than a model error.

