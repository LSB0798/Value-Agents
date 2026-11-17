#!/usr/bin/env python
# scripts/run_reflection.py
"""
Phase 4 W3 CLI：对 wrong 决策生成反思。

用法：
    python scripts/run_reflection.py                       # 扫描 + 生成（规则模式）
    python scripts/run_reflection.py --llm                 # 扫描 + 生成（LLM 模式）
    python scripts/run_reflection.py --list                # 列出已有反思
    python scripts/run_reflection.py --list --ticker NFLX
    python scripts/run_reflection.py --inject-to-memory    # 注入 memory（当前进程）
"""

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from valueagents.learning import Reflection, get_reflections_dir


def main():
    parser = argparse.ArgumentParser(description="Phase 4 W3 Reflection CLI")
    parser.add_argument("--llm", action="store_true", help="用 LLM 生成 lesson（默认规则）")
    parser.add_argument("--list", action="store_true", help="列出已有反思")
    parser.add_argument("--ticker", default=None, help="只处理指定 ticker")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--inject-to-memory", action="store_true",
                        help="把反思注入 FinancialSituationMemory（当前进程内）")
    args = parser.parse_args()

    llm = None
    if args.llm:
        try:
            from valueagents.llm_clients import create_llm_client
            from valueagents.settings import settings
            client = create_llm_client(
                provider="openai",
                model="qwen3.6-27B",
                base_url=settings.compress_api_url or "http://10.20.223.75:8001/v1",
            )
            llm = client.get_llm()
            print("[run_reflection] LLM loaded")
        except Exception as e:
            print(f"[run_reflection] ⚠️ LLM load failed: {e}; using rule")
            llm = None

    r = Reflection(llm=llm)
    print(f"[run_reflection] reflections dir: {get_reflections_dir()}")

    # --inject-to-memory 模式
    if args.inject_to_memory:
        try:
            from valueagents.agents.utils.memory import FinancialSituationMemory
            from valueagents.default_config import DEFAULT_CONFIG
            mem = FinancialSituationMemory("reflect_memory", DEFAULT_CONFIG)
            n = r.inject_to_memory(mem, ticker=args.ticker)
            print(f"[run_reflection] injected {n} notes")
        except Exception as e:
            print(f"[run_reflection] ⚠️ inject failed: {e}")
        return

    # --list 模式
    if args.list:
        notes = r.load_all()
        if args.ticker:
            notes = [n for n in notes if n.ticker == args.ticker]
        if not notes:
            print("[run_reflection] no reflections found")
            return
        print(f"\n{'='*78}")
        print(f"  {len(notes)} reflections")
        print(f"{'='*78}\n")
        for n in notes[:args.limit]:
            print(f"[{n.ticker} @ {n.end_date}]  rating={n.rating}  "
                  f"return={n.actual_return_pct:+.1f}%  by={n.generated_by}")
            print(f"  what: {n.what_went_wrong}")
            print(f"  lesson: {n.lesson}")
            print()
        return

    # 默认：扫描 + 生成
    print("[run_reflection] scanning wrong decisions ...")
    notes = r.review_all_wrong(limit=args.limit)
    if not notes:
        print("[run_reflection] no new reflections generated")
        return
    print(f"\n[run_reflection] generated {len(notes)} new reflections:")
    for n in notes:
        print(f"  [{n.ticker}] {n.what_went_wrong[:80]}...")
        print(f"    → {n.lesson[:100]}...")


if __name__ == "__main__":
    main()
