#!/usr/bin/env python
# scripts/evaluate_learning.py
"""
Phase 4 W4 CLI：评估 Learning 效果。

用法：
    python scripts/evaluate_learning.py --mode legacy              # 只看 legacy 的 accuracy
    python scripts/evaluate_learning.py --mode framework           # 只看 framework
    python scripts/evaluate_learning.py --compare-all              # 全部模式对比
    python scripts/evaluate_learning.py --breakdown                # 按 dim/framework 拆解
    python scripts/evaluate_learning.py --since 2026-11-01         # 只看某日期后的决策

前提：
    需要 ≥ 50 个 settled（outcome ∈ {right, wrong}）决策才有统计意义。
    前 3-6 个月数据不足 → 输出 "insufficient data"，非错误。
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from valueagents.learning import load_decisions


def _format_pct(v) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def _summarize(records, name):
    settled = [r for r in records if r.outcome in ("right", "wrong")]
    n_total = len(records)
    n_settled = len(settled)
    right = sum(1 for r in settled if r.outcome == "right")
    accuracy = (right / n_settled) if n_settled > 0 else None
    return {
        "name": name,
        "total": n_total,
        "settled": n_settled,
        "right": right,
        "wrong": n_settled - right,
        "accuracy": accuracy,
    }


def _print_summary_row(s):
    print(
        f"  {s['name']:<20} total={s['total']:<4} settled={s['settled']:<4} "
        f"right={s['right']:<3} wrong={s['wrong']:<3} "
        f"accuracy={_format_pct(s['accuracy'])}"
    )


def cmd_mode(args):
    decisions = load_decisions(since=args.since)
    filtered = [d for d in decisions if d.reasoning_mode == args.mode]
    s = _summarize(filtered, args.mode)
    print(f"\n=== Mode: {args.mode} ===")
    _print_summary_row(s)
    if s["settled"] < 50:
        print(f"  ⚠️  settled={s['settled']} < 50 — 数据不足，仅参考")


def cmd_compare_all(args):
    decisions = load_decisions(since=args.since)
    print(f"\n{'='*80}")
    print(f"  Evaluate Learning — {len(decisions)} total decisions")
    print(f"{'='*80}")
    print()
    for mode in ("legacy", "framework", "ab"):
        filtered = [d for d in decisions if d.reasoning_mode == mode]
        if not filtered:
            print(f"  {mode:<20} (no decisions)")
            continue
        s = _summarize(filtered, mode)
        _print_summary_row(s)
    print()

    # 汇总
    total_settled = sum(1 for d in decisions if d.outcome in ("right", "wrong"))
    print(f"  Total settled: {total_settled}")
    if total_settled < 50:
        print(f"  ⚠️  total_settled={total_settled} < 50 — 数据不足，无法得出可靠结论")


def cmd_breakdown(args):
    decisions = load_decisions(since=args.since)
    settled = [d for d in decisions if d.outcome in ("right", "wrong")]
    if not settled:
        print("\n=== Breakdown ===")
        print("  (no settled decisions — insufficient data)")
        return

    print(f"\n{'='*80}")
    print(f"  Breakdown by rating (n={len(settled)} settled)")
    print(f"{'='*80}")
    by_rating = defaultdict(lambda: {"right": 0, "wrong": 0})
    for d in settled:
        by_rating[d.final_rating][d.outcome] += 1

    print(f"\n  {'Rating':<15} {'right':<8} {'wrong':<8} {'accuracy':<10}")
    print(f"  {'-'*40}")
    for rating in sorted(by_rating.keys()):
        r = by_rating[rating]["right"]
        w = by_rating[rating]["wrong"]
        acc = r / (r + w) if (r + w) > 0 else None
        print(f"  {rating:<15} {r:<8} {w:<8} {_format_pct(acc):<10}")

    # 按 ticker 分组
    by_ticker = defaultdict(lambda: {"right": 0, "wrong": 0})
    for d in settled:
        by_ticker[d.ticker][d.outcome] += 1
    print(f"\n  {'Ticker':<12} {'right':<8} {'wrong':<8} {'accuracy':<10}")
    print(f"  {'-'*40}")
    for ticker in sorted(by_ticker.keys()):
        r = by_ticker[ticker]["right"]
        w = by_ticker[ticker]["wrong"]
        acc = r / (r + w) if (r + w) > 0 else None
        print(f"  {ticker:<12} {r:<8} {w:<8} {_format_pct(acc):<10}")

    # 按 master 分组
    print(f"\n  Master signal accuracy (approximate, based on majority vote):")
    by_master = defaultdict(lambda: {"right": 0, "wrong": 0})
    for d in settled:
        for name, sig in (d.master_signals or {}).items():
            # 兼容单层/双层
            if isinstance(sig, dict) and "signal" in sig:
                direction = str(sig.get("signal", "neutral")).lower()
            else:
                direction = next(
                    (str(v.get("signal", "neutral")).lower()
                     for v in (sig or {}).values() if isinstance(v, dict) and "signal" in v),
                    "neutral",
                )
            if direction == "bullish" and d.final_rating in ("Buy", "Overweight") and d.outcome == "right":
                by_master[name]["right"] += 1
            elif direction == "bearish" and d.final_rating in ("Sell", "Underweight") and d.outcome == "right":
                by_master[name]["right"] += 1
            else:
                by_master[name]["wrong"] += 1

    print(f"  {'Master':<40} {'right':<8} {'wrong':<8} {'accuracy':<10}")
    print(f"  {'-'*70}")
    for name in sorted(by_master.keys()):
        r = by_master[name]["right"]
        w = by_master[name]["wrong"]
        acc = r / (r + w) if (r + w) > 0 else None
        print(f"  {name:<40} {r:<8} {w:<8} {_format_pct(acc):<10}")


def main():
    parser = argparse.ArgumentParser(description="Phase 4 W4: Evaluate Learning")
    parser.add_argument("--mode", choices=["legacy", "framework", "ab"], default=None,
                        help="只看某个 mode")
    parser.add_argument("--compare-all", action="store_true", help="对比所有 mode")
    parser.add_argument("--breakdown", action="store_true", help="按 rating/ticker/master 拆解")
    parser.add_argument("--since", default=None, help="只看 end_date >= YYYY-MM-DD 的决策")
    args = parser.parse_args()

    if args.breakdown:
        return cmd_breakdown(args)
    if args.compare_all:
        return cmd_compare_all(args)
    if args.mode:
        return cmd_mode(args)

    # 默认：对比所有
    return cmd_compare_all(args)


if __name__ == "__main__":
    main()
