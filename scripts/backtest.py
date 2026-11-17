#!/usr/bin/env python
# scripts/backtest.py
"""
Phase 2.5 Backtest CLI

用法：
    python scripts/backtest.py --mode legacy --cases B1,B2,B3
    python scripts/backtest.py --mode framework --cases B1,B2,B3   # Phase 3 后才有意义
    python scripts/backtest.py --compare-all
    python scripts/backtest.py --master-accuracy --lookback 180
"""

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from valueagents.learning.outcome import OutcomeTracker


def main():
    parser = argparse.ArgumentParser(description="Phase 2.5 Backtest CLI")
    parser.add_argument("--mode", choices=["legacy", "framework", "ab"], default="legacy")
    parser.add_argument("--cases", default="B1,B2,B3")
    parser.add_argument("--compare-all", action="store_true")
    parser.add_argument("--master-accuracy", action="store_true")
    parser.add_argument("--lookback", type=int, default=180)
    parser.add_argument("--daily-update", action="store_true")
    args = parser.parse_args()

    tracker = OutcomeTracker()

    if args.daily_update:
        print("[backtest] running daily_update ...")
        stats = tracker.daily_update()
        print(f"[backtest] done: {stats}")
        return

    if args.master_accuracy:
        print(f"[backtest] computing master accuracy (lookback={args.lookback}d) ...")
        acc = tracker.compute_master_accuracy(lookback_days=args.lookback)
        if not acc:
            print("[backtest] no settled decisions yet — return empty")
            return
        print(f"\n{'Master':<40} {'n':>6} {'accuracy':>10}")
        print("-" * 60)
        for name, data in sorted(acc.items(), key=lambda x: -(x[1]["n"] or 0)):
            n = data["n"]
            a = data["accuracy"]
            a_str = f"{a:.3f}" if a is not None else "(insufficient)"
            print(f"{name:<40} {n:>6} {a_str:>10}")
        return

    if args.compare_all:
        cases = [c.strip() for c in args.cases.split(",") if c.strip()]
        print(f"[backtest] compare-all over cases: {cases}\n")
        for mode in ["legacy", "framework", "ab"]:
            result = tracker.backtest_mode(mode=mode, case_ids=cases)
            print(f"=== Mode: {mode} ===")
            print(f"  total decisions: {result['total']}")
            print(f"  settled:         {result['settled']}")
            print(f"  accuracy:        {result['accuracy'] if result['accuracy'] is not None else 'N/A (no settled)'}")
            print(f"  cases:           {result['cases']}")
            print()
        return

    cases = [c.strip() for c in args.cases.split(",") if c.strip()]
    result = tracker.backtest_mode(mode=args.mode, case_ids=cases)
    print(f"=== Backtest Result (mode={args.mode}) ===")
    print(f"  total decisions: {result['total']}")
    print(f"  settled:         {result['settled']}")
    print(f"  accuracy:        {result['accuracy'] if result['accuracy'] is not None else 'N/A (no settled)'}")
    print(f"  cases:           {result['cases']}")


if __name__ == "__main__":
    main()
