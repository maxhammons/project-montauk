#!/bin/bash
# Verify domain duplication and obsolete naming
grep -n 'class Trade' scripts/strategy_engine.py scripts/backtest_engine.py
grep -n 'class BacktestResult' scripts/strategy_engine.py scripts/backtest_engine.py
wc -l scripts/pine_generator.py
grep -n 'vs_bah' scripts/*.py | head -n 5