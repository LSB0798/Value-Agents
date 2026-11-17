#!/usr/bin/env python
# scripts/dump_evidence.py
"""
Phase 2 W1 gate 验收工具：把 4 个 analyst 的 evidence bundle 落盘并打印 claim 摘要。

用法：
    python scripts/dump_evidence.py B1              # 跑 B1，落盘 + 打印
    python scripts/dump_evidence.py B1 --no-run     # 不跑 pipeline，读上次 dump 再打印

输出：
    tmp/evidence_verify/{ticker}_market_evidence.json
    tmp/evidence_verify/{ticker}_sentiment_evidence.json
    tmp/evidence_verify/{ticker}_news_evidence.json
    tmp/evidence_verify/{ticker}_fundamentals_evidence.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

BASELINE_DIR = _REPO_ROOT / "tests" / "baseline"
DUMP_DIR = _REPO_ROOT / "tmp" / "evidence_verify"

ANALYST_SKILLS = [
    "market_analyst",
    "social_analyst",
    "news_analyst",
    "fundamentals_analyst",
]

REPORT_KEYS = {
    "market_analyst": "market_report",
    "social_analyst": "sentiment_report",
    "news_analyst": "news_report",
    "fundamentals_analyst": "fundamentals_report",
}


def load_baseline(case_id: str) -> dict:
    matches = list(BASELINE_DIR.glob(f"{case_id}_*.json"))
    if not matches:
        raise FileNotFoundError(f"Baseline not found for {case_id}")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def build_config(research_depth: int = 5) -> dict:
    from valueagents.default_config import DEFAULT_CONFIG as BASE_CFG
    config = BASE_CFG.copy()
    config["llm_provider"] = "openai"
    config["backend_url"] = "http://10.20.223.75:8001/v1"
    config["quick_think_llm"] = "qwen3.6-27B"
    config["deep_think_llm"] = "qwen3.6-27B"
    config["output_language"] = "English"
    depth_bounds = {1: (1, 2), 3: (2, 4), 5: (3, 5)}
    min_r, max_r = depth_bounds.get(research_depth, (3, 5))
    config["min_debate_rounds"] = min_r
    config["max_debate_rounds"] = max_r
    config["max_risk_discuss_rounds"] = research_depth
    config["decision_temperature"] = 0.0
    return config


def run_pipeline(case: dict) -> None:
    """跑 4 个 analyst，把 evidence 落盘。"""
    from valueagents.agents.skills.core import load_core_skill
    from valueagents.agents.skills.contract import SkillContext
    from valueagents.llm_clients import create_llm_client

    ticker = case["ticker"]
    end_date = case["end_date"]
    config = build_config(case.get("config", {}).get("research_depth", 5))

    client = create_llm_client(
        provider=config["llm_provider"],
        model=config["quick_think_llm"],
        base_url=config["backend_url"],
    )
    llm = client.get_llm()

    artifacts = {"company_of_interest": ticker, "trade_date": end_date}
    DUMP_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for skill_name in ANALYST_SKILLS:
        print(f"\n{'='*60}\n  Running {skill_name} ...\n{'='*60}")
        skill = load_core_skill(f"{skill_name}_skill")
        if skill is None:
            print(f"  ✗ failed to load {skill_name}_skill")
            continue
        ctx = SkillContext(
            ticker=ticker, end_date=end_date, artifacts=artifacts,
            llm=llm, api_key=None, config=config,
        )
        try:
            result = skill.execute(ctx)
        except Exception as e:
            print(f"  ✗ {skill_name} raised: {type(e).__name__}: {e}")
            continue
        if not result or not result.outputs:
            print(f"  ✗ {skill_name} returned empty")
            continue

        artifacts.update(result.outputs)

        # 找到 evidence key
        ev_key = next(
            (k for k in result.outputs if k.endswith("_evidence")),
            None,
        )
        if ev_key is None:
            print(f"  ⚠️ {skill_name}: no *_evidence in outputs {list(result.outputs.keys())}")
            continue

        ev_bundle = result.outputs[ev_key]
        report_key = REPORT_KEYS[skill_name]
        narrative = result.outputs.get(report_key, "")

        dump = {
            "skill": skill_name,
            "ticker": ticker,
            "end_date": end_date,
            "report_key": report_key,
            "report_preview": narrative[:500],
            "report_is_insufficient": narrative.strip().startswith("INSUFFICIENT_DATA"),
            "evidence_bundle": ev_bundle,
        }
        dump_path = DUMP_DIR / f"{ticker}_{ev_key}.json"
        dump_path.write_text(
            json.dumps(dump, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        n_claims = len(ev_bundle.get("claims", []))
        n_signals = len(ev_bundle.get("signals", []))
        n_evidence = len(ev_bundle.get("evidence", []))
        print(f"  ✓ {skill_name}: evidence={n_evidence} claims={n_claims} signals={n_signals}")
        print(f"  → dumped: {dump_path.relative_to(_REPO_ROOT)}")

    print(f"\n总耗时: {time.time()-t0:.1f}s")
    print(f"\n落盘目录: {DUMP_DIR}")


def print_for_review(ticker: str) -> None:
    """从落盘 JSON 读，打印每条 claim 供人工验收。"""
    ev_files = sorted(DUMP_DIR.glob(f"{ticker}_*_evidence.json"))
    if not ev_files:
        print(f"✗ 没有找到 {ticker} 的 dump 文件，请先不带 --no-run 跑一次")
        return

    print("\n" + "=" * 78)
    print(f"  Phase 2 W1 Gate — Claim 保真度验收（{ticker}）")
    print("=" * 78)
    print("\n说明：")
    print("  - 每个 analyst 抽 1-2 条 claim，共 5 条")
    print("  - 对每条 claim 判断：")
    print("    (1) statement 是否合理")
    print("    (2) evidence_ids 是否能支持该 statement")
    print("  - 通过率 ≥ 3/5 即可过关")

    total_claims = 0
    for f in ev_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        skill = data["skill"]
        bundle = data["evidence_bundle"]
        claims = bundle.get("claims", [])
        evidence_map = {ev["id"]: ev for ev in bundle.get("evidence", [])}

        print("\n" + "-" * 78)
        print(f"  [{skill}]  data_quality={'INSUFFICIENT' if data['report_is_insufficient'] else 'ok'}")
        print(f"  report_preview: {data['report_preview'][:120]}...")
        print(f"  claims={len(claims)} signals={len(bundle.get('signals', []))}")
        print("-" * 78)

        for i, cl in enumerate(claims, start=1):
            total_claims += 1
            print(f"\n  Claim {i}/{len(claims)}  id={cl['id']}")
            print(f"    framework: {cl.get('framework')}  confidence: {cl.get('confidence')}")
            print(f"    statement: {cl.get('statement')}")
            for eid in cl.get("evidence_ids", []):
                ev = evidence_map.get(eid)
                if ev:
                    content = ev.get("content", {})
                    text = content.get("text", "")[:300].replace("\n", " ")
                    print(f"    evidence {eid}: {text}...")
                else:
                    print(f"    evidence {eid}: (NOT FOUND)")
            print()

    print("=" * 78)
    print(f"  共 {total_claims} 条 claim。请按下面的表填 5 条判定：")
    print("=" * 78)
    print("""
  验收表（请你填）：

  | # | skill | statement 合理? | evidence 支持? | 总判定 |
  |---|-------|-----------------|----------------|--------|
  | 1 |       | Y / N           | Y / N          | 通过/不通过 |
  | 2 |       | Y / N           | Y / N          | 通过/不通过 |
  | 3 |       | Y / N           | Y / N          | 通过/不通过 |
  | 4 |       | Y / N           | Y / N          | 通过/不通过 |
  | 5 |       | Y / N           | Y / N          | 通过/不通过 |

  通过数 ≥ 3 → Phase 2 W1 gate PASS
  通过数 ≤ 2 → 提取器需重做
""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="B1 / B2 / B3")
    parser.add_argument("--no-run", action="store_true", help="只读上次 dump，不重跑")
    args = parser.parse_args()

    case = load_baseline(args.case_id)
    print(f"[dump_evidence] case={args.case_id}  ticker={case['ticker']}  date={case['end_date']}")

    if not args.no_run:
        run_pipeline(case)
    else:
        print("[dump_evidence] --no-run：跳过 pipeline，直接打印上次 dump")

    print_for_review(case["ticker"])


if __name__ == "__main__":
    main()
