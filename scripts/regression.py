#!/usr/bin/env python
# scripts/regression.py
"""
Regression Runner — Phase 0

用法：
    python scripts/regression.py --case B1
    python scripts/regression.py --all
    python scripts/regression.py --all --quick          # 只跑 4 analyst（~5-10 min/case）
    python scripts/regression.py --case B1 --repeat 3   # 跑 3 次看方差
    python scripts/regression.py --case B1 --capture    # 采集/覆盖 baseline
    python scripts/regression.py --all --mode legacy    # Phase 0 只支持 legacy

约束：
    - GPU 不能空闲 → 自动切 keepalive 到 quiet 模式
    - 支持中断恢复（Ctrl+C 后 baseline 不覆盖）
    - 输出 PASS/FAIL/WARN 三层判定
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 允许从 repo 根目录 import
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

BASELINE_DIR = _REPO_ROOT / "tests" / "baseline"
KEEPALIVE_MODE_FILE = _REPO_ROOT / "tmp" / "keepalive_mode.txt"

# 默认 3 个 master（若 user 未指定）
DEFAULT_MASTERS = [
    "warren_buffett_analyst",
    "charlie_munger_analyst",
    "ben_graham_analyst",
]

DEFAULT_CONFIG = {
    "llm_provider": "openai",
    "backend_url": "http://10.20.223.75:8001/v1",
    "quick_think_llm": "qwen3.6-27B",
    "deep_think_llm": "qwen3.6-27B",
    "output_language": "English",
    "research_depth": 5,
}

RATINGS = ["Buy", "Overweight", "Hold", "Underweight", "Sell"]


# ============================================================
# I/O
# ============================================================
def load_baseline(case_id: str) -> dict:
    """加载 baseline JSON。"""
    matches = list(BASELINE_DIR.glob(f"{case_id}_*.json"))
    if not matches:
        raise FileNotFoundError(f"Baseline not found for {case_id} in {BASELINE_DIR}")
    with open(matches[0], "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(baseline: dict) -> None:
    """覆盖写回 baseline JSON。"""
    path = BASELINE_DIR / f"{baseline['case_id']}_{baseline['ticker']}_{baseline['end_date']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    print(f"  [baseline] saved → {path.relative_to(_REPO_ROOT)}")


def list_baselines() -> list[str]:
    """列出所有 baseline case_id。"""
    ids = []
    for p in sorted(BASELINE_DIR.glob("B*.json")):
        case_id = p.stem.split("_")[0]
        if case_id not in ids:
            ids.append(case_id)
    return ids


# ============================================================
# 配置构造
# ============================================================
def build_config(research_depth: int = 5) -> dict:
    """构造 config（与 cli/main.py::run_analysis 对齐）。"""
    from valueagents.default_config import DEFAULT_CONFIG as BASE_CFG

    config = BASE_CFG.copy()
    config["llm_provider"] = DEFAULT_CONFIG["llm_provider"]
    config["backend_url"] = DEFAULT_CONFIG["backend_url"]
    config["quick_think_llm"] = DEFAULT_CONFIG["quick_think_llm"]
    config["deep_think_llm"] = DEFAULT_CONFIG["deep_think_llm"]
    config["output_language"] = DEFAULT_CONFIG["output_language"]

    depth_bounds = {1: (1, 2), 3: (2, 4), 5: (3, 5)}
    min_r, max_r = depth_bounds.get(research_depth, (3, 5))
    config["min_debate_rounds"] = min_r
    config["max_debate_rounds"] = max_r
    config["max_risk_discuss_rounds"] = research_depth

    return config


# ============================================================
# 执行：--quick 模式
# ============================================================
def run_quick(case: dict, config: dict, verbose: bool = True) -> dict:
    """只跑 4 analyst skill，验证 pipeline 通。"""
    from valueagents.agents.skills.core import load_core_skill
    from valueagents.agents.skills.contract import SkillContext
    from valueagents.llm_clients import create_llm_client

    ticker = case["ticker"]
    end_date = case["end_date"]
    t_total = time.time()

    client = create_llm_client(
        provider=config["llm_provider"],
        model=config["quick_think_llm"],
        base_url=config["backend_url"],
    )
    llm = client.get_llm()

    artifacts = {"company_of_interest": ticker, "trade_date": end_date}
    results: dict[str, dict] = {}

    for skill_name in ["market_analyst", "social_analyst", "news_analyst", "fundamentals_analyst"]:
        t0 = time.time()
        skill = load_core_skill(f"{skill_name}_skill") or load_core_skill(skill_name)
        if skill is None:
            raise RuntimeError(f"Failed to load {skill_name}_skill")

        ctx = SkillContext(
            ticker=ticker,
            end_date=end_date,
            artifacts=artifacts,
            llm=llm,
            api_key=None,
            config=config,
        )
        result = skill.execute(ctx)
        if result and result.outputs:
            artifacts.update(result.outputs)

        elapsed = time.time() - t0
        results[skill_name] = {
            "elapsed_seconds": round(elapsed, 1),
            "output_keys": list(result.outputs.keys()) if result else [],
        }
        if verbose:
            out = list(result.outputs.keys()) if result else []
            print(f"    ✓ {skill_name}: {elapsed:.1f}s, outputs={out}")

    return {
        "mode": "quick",
        "elapsed_seconds": round(time.time() - t_total, 1),
        "skills": results,
        "report_lengths": {
            k: len(artifacts.get(k, ""))
            for k in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]
        },
    }


# ============================================================
# 执行：full 模式
# ============================================================
def run_full(case: dict, config: dict, master_analysts: list[str], verbose: bool = True) -> dict:
    """跑完整 graph pipeline。"""
    from valueagents.graph.trading_graph import TradingAgentsGraph
    from cli.stats_handler import StatsCallbackHandler

    ticker = case["ticker"]
    end_date = case["end_date"]
    t0 = time.time()

    stats_handler = StatsCallbackHandler()

    graph = TradingAgentsGraph(
        selected_analysts=["market", "social", "news", "fundamentals"],
        use_master_analysts=bool(master_analysts),
        master_analysts_list=master_analysts or None,
        config=config,
        debug=False,
        callbacks=[stats_handler],
    )

    init_state = graph.propagator.create_initial_state(ticker, end_date)
    init_state["_config"] = {
        "min_debate_rounds": config.get("min_debate_rounds", 1),
        "max_debate_rounds": config.get("max_debate_rounds", 5),
        "max_risk_discuss_rounds": config.get("max_risk_discuss_rounds", 1),
    }
    init_state["_bull_memory"] = graph.bull_memory
    init_state["_bear_memory"] = graph.bear_memory
    init_state["_trader_memory"] = graph.trader_memory
    init_state["_invest_judge_memory"] = graph.invest_judge_memory
    init_state["_portfolio_manager_memory"] = graph.portfolio_manager_memory

    args = graph.propagator.get_graph_args(callbacks=[stats_handler])

    trace = []
    last_log = 0.0
    for chunk in graph.graph.stream(init_state, **args):
        trace.append(chunk)
        elapsed = time.time() - t0
        if verbose and elapsed - last_log > 120:  # 每 2 分钟打一次
            print(f"    [{elapsed/60:.0f} min] {len(trace)} chunks")
            last_log = elapsed

    elapsed_min = (time.time() - t0) / 60
    final_state = trace[-1] if trace else {}
    stats = stats_handler.get_stats()

    decision_text = final_state.get("final_trade_decision", "")
    actual = {
        "mode": "full",
        "final_trade_decision": decision_text[:500],
        "final_rating": extract_rating(decision_text),
        "report_lengths": {
            k: len(final_state.get(k, ""))
            for k in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]
        },
        "tokens_in": stats.get("tokens_in", 0),
        "tokens_out": stats.get("tokens_out", 0),
        "llm_calls": stats.get("llm_calls", 0),
        "tool_calls": stats.get("tool_calls", 0),
        "elapsed_minutes": round(elapsed_min, 1),
        "master_signals_summary": summarize_master_signals(
            final_state.get("master_analyst_signals", {})
        ),
    }
    return actual


# ============================================================
# 提取 & 比对
# ============================================================
def extract_rating(decision_text: str) -> str:
    """从 final_trade_decision 提取 rating。"""
    if not decision_text:
        return "UNKNOWN"
    m = re.search(
        r"Rating[\s\*:：]+\*{0,2}\s*(Buy|Overweight|Hold|Underweight|Sell)",
        decision_text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).capitalize()
    # 兜底：先看前缀
    head = decision_text[:200].lower()
    for r in RATINGS:
        if r.lower() in head:
            return r
    return "UNKNOWN"


def summarize_master_signals(signals: dict) -> dict:
    """统计 master signals 分布。"""
    counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    if not isinstance(signals, dict):
        return counts
    for _name, payload in signals.items():
        if not isinstance(payload, dict):
            continue
        if "signal" in payload:  # 单层
            sig = str(payload.get("signal", "neutral")).lower()
            if sig in counts:
                counts[sig] += 1
        else:  # 双层 {ticker: {...}}
            for ticker_sig in payload.values():
                if isinstance(ticker_sig, dict):
                    sig = str(ticker_sig.get("signal", "neutral")).lower()
                    if sig in counts:
                        counts[sig] += 1
    return counts


def compare(expected: dict, actual: dict, lenient: bool = False) -> tuple[bool, list[str], list[str]]:
    """返回 (passed, hard_failures, warnings)。"""
    failures: list[str] = []
    warnings: list[str] = []

    # 硬约束：final_rating 必须能解析出有效值（PM 输出格式没坏）
    # 软约束：与 baseline 不同 → WARN（决策漂移是已知的 LLM 方差）
    exp_rating = (expected.get("final_rating") or "").upper()
    act_rating = (actual.get("final_rating") or "UNKNOWN").upper()
    if act_rating == "UNKNOWN":
        failures.append("final_rating: UNKNOWN (PM output format broken)")
    elif exp_rating and exp_rating not in ("", "UNKNOWN") and act_rating != exp_rating:
        warnings.append(f"final_rating: {act_rating} (baseline {exp_rating}, drift accepted)")

    # 软约束：report_lengths
    for key, rng in (expected.get("report_lengths") or {}).items():
        lo, hi = rng
        act = actual.get("report_lengths", {}).get(key, 0)
        if not (lo <= act <= hi):
            warnings.append(f"{key}: {act} (range {lo}-{hi})")

    # 软约束：tokens_in
    ti_lo, ti_hi = expected.get("tokens_in_range", [0, 10**9])
    if not (ti_lo <= actual.get("tokens_in", 0) <= ti_hi):
        warnings.append(f"tokens_in: {actual.get('tokens_in')} (range {ti_lo}-{ti_hi})")

    # 软约束：tokens_out
    to_lo, to_hi = expected.get("tokens_out_range", [0, 10**9])
    if not (to_lo <= actual.get("tokens_out", 0) <= to_hi):
        warnings.append(f"tokens_out: {actual.get('tokens_out')} (range {to_lo}-{to_hi})")

    # 软约束：llm_calls
    lc_lo, lc_hi = expected.get("llm_calls_range", [0, 10**9])
    if not (lc_lo <= actual.get("llm_calls", 0) <= lc_hi):
        warnings.append(f"llm_calls: {actual.get('llm_calls')} (range {lc_lo}-{lc_hi})")

    # 软约束：elapsed
    el_lo, el_hi = expected.get("elapsed_minutes_range", [0, 10**6])
    if not (el_lo <= actual.get("elapsed_minutes", 0) <= el_hi):
        warnings.append(f"elapsed: {actual.get('elapsed_minutes')} (range {el_lo}-{el_hi})")

    # 软约束：master_signals
    exp_ms = expected.get("master_signals_summary") or {}
    act_ms = actual.get("master_signals_summary") or {}
    if exp_ms and act_ms:
        diff = sum(abs(act_ms.get(k, 0) - exp_ms.get(k, 0))
                   for k in ("bullish", "bearish", "neutral"))
        if diff > 3:
            warnings.append(f"master_signals: {act_ms} vs {exp_ms} (diff={diff} > 3)")

    return (len(failures) == 0, failures, warnings)


# ============================================================
# 输出
# ============================================================
def print_report(case_id: str, passed: bool, failures: list[str], warnings: list[str],
                 actual: dict, quick: bool):
    sep = "=" * 64
    status = "PASS" if passed else "FAIL"
    print(f"\n{sep}")
    print(f"  Regression {case_id}  →  {status}  ({'quick' if quick else 'full'})")
    print(f"{sep}")

    if quick:
        print(f"  skills: {list(actual.get('skills', {}).keys())}")
        print(f"  report_lengths: {actual.get('report_lengths', {})}")
        print(f"  elapsed: {actual.get('elapsed_seconds', 0):.1f}s")
    else:
        print(f"  final_rating: {actual.get('final_rating', '?')}")
        print("  report_lengths:")
        for k, v in (actual.get("report_lengths") or {}).items():
            print(f"    {k}: {v}")
        print(f"  tokens: in={actual.get('tokens_in', 0):,}  out={actual.get('tokens_out', 0):,}")
        print(f"  llm_calls: {actual.get('llm_calls', 0)}  tool_calls: {actual.get('tool_calls', 0)}")
        print(f"  master_signals: {actual.get('master_signals_summary', {})}")
        print(f"  elapsed: {actual.get('elapsed_minutes', 0):.1f} min")

    if failures:
        print(f"\n  ✗ Hard failures ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
    if warnings:
        print(f"\n  ⚠ Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    print(f"{sep}\n")


# ============================================================
# Keepalive 模式切换
# ============================================================
def enter_regression_mode() -> str:
    """切换 keepalive 到 quiet，返回原模式。"""
    KEEPALIVE_MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    original = "dev"
    if KEEPALIVE_MODE_FILE.exists():
        original = KEEPALIVE_MODE_FILE.read_text().strip() or "dev"
    KEEPALIVE_MODE_FILE.write_text("quiet")
    print(f"  [keepalive] mode: {original} → quiet")
    return original


def exit_regression_mode(original: str) -> None:
    KEEPALIVE_MODE_FILE.write_text(original)
    print(f"  [keepalive] mode: quiet → {original}")


# ============================================================
# 采集模式：合并多次结果
# ============================================================
def merge_capture(baseline: dict, actuals: list[dict]) -> dict:
    """把 N 次 actual 合并成 expected 范围。"""
    if not actuals:
        return baseline

    def _range(vals):
        vals = [v for v in vals if v is not None]
        if not vals:
            return [0, 0]
        lo, hi = min(vals), max(vals)
        # 留 10% 余量，避免边界抖动
        margin = max(1, int((hi - lo) * 0.1))
        return [max(0, lo - margin), hi + margin]

    exp = baseline.setdefault("expected", {})

    # final_rating：取众数
    ratings = [a.get("final_rating") for a in actuals if a.get("final_rating") not in (None, "UNKNOWN")]
    if ratings:
        exp["final_rating"] = max(set(ratings), key=ratings.count)

    # report_lengths
    for key in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]:
        vals = [a.get("report_lengths", {}).get(key) for a in actuals]
        exp.setdefault("report_lengths", {})[key] = _range(vals)

    # 标量指标
    for key, field in [
        ("tokens_in_range", "tokens_in"),
        ("tokens_out_range", "tokens_out"),
        ("llm_calls_range", "llm_calls"),
        ("elapsed_minutes_range", "elapsed_minutes"),
    ]:
        vals = [a.get(field) for a in actuals]
        exp[key] = _range(vals)

    # master_signals：取每个 bucket 的范围中值
    ms_keys = ("bullish", "bearish", "neutral")
    ms_vals = {k: [a.get("master_signals_summary", {}).get(k, 0) for a in actuals] for k in ms_keys}
    exp["master_signals_summary"] = {
        k: int(sum(v) / max(1, len(v))) for k, v in ms_vals.items()
    }

    baseline["source"] = "phase0_capture"
    baseline["captured_at"] = datetime.utcnow().isoformat() + "Z"
    return baseline


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Phase 0 Regression Runner")
    parser.add_argument("--case", type=str, default=None, help="单个 case_id（如 B1）")
    parser.add_argument("--all", action="store_true", help="跑所有 case")
    parser.add_argument("--quick", action="store_true", help="只跑 4 analyst（~5-10 min/case）")
    parser.add_argument("--repeat", type=int, default=1, help="每个 case 跑 N 次")
    parser.add_argument("--capture", action="store_true", help="采集模式：结果写回 baseline")
    parser.add_argument("--mode", choices=["legacy", "framework"], default="legacy",
                        help="Phase 0 只支持 legacy（framework 留 Phase 3）")
    parser.add_argument("--master-analysts", type=str, default="",
                        help="逗号分隔的 master 列表（默认 3 个）")
    parser.add_argument("--lenient", action="store_true",
                        help="宽容模式：final_rating 不同只 WARN")
    parser.add_argument("--no-keepalive-switch", action="store_true",
                        help="不自动切 keepalive 模式")
    args = parser.parse_args()

    if args.mode == "framework":
        print("✗ framework mode not implemented yet (Phase 3)")
        sys.exit(2)

    if not args.case and not args.all:
        parser.error("必须指定 --case 或 --all")

    case_ids = [args.case] if args.case else list_baselines()
    if not case_ids:
        print(f"✗ No baselines found in {BASELINE_DIR}")
        sys.exit(2)

    masters = [m.strip() for m in args.master_analysts.split(",") if m.strip()] or DEFAULT_MASTERS

    print(f"\n{'=' * 64}")
    print(f"  Phase 0 Regression")
    print(f"  cases: {case_ids}")
    print(f"  mode: {'quick' if args.quick else 'full'}")
    print(f"  repeat: {args.repeat}")
    print(f"  capture: {args.capture}")
    print(f"{'=' * 64}\n")

    original_mode = None
    if not args.no_keepalive_switch:
        original_mode = enter_regression_mode()

    all_passed = True
    summary = []

    try:
        for case_id in case_ids:
            baseline = load_baseline(case_id)
            config = build_config(baseline.get("config", {}).get("research_depth", 5))
            actuals: list[dict] = []

            print(f"\n[{case_id}] {baseline['ticker']} {baseline['end_date']}")
            for i in range(args.repeat):
                print(f"  run {i + 1}/{args.repeat} ...")
                try:
                    if args.quick:
                        actual = run_quick(baseline, config)
                    else:
                        actual = run_full(baseline, config, masters)
                    actuals.append(actual)
                except Exception as e:
                    print(f"  ✗ Exception: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    all_passed = False
                    summary.append((case_id, False, [f"exception: {e}"]))
                    break

            if not actuals:
                continue

            # 用第一次的 actual 对比（或 --capture 时全部合并）
            if args.quick:
                # quick 只验证 pipeline 通（outputs 非空）
                ok = all(actual["skills"] and all(v["output_keys"] for v in actual["skills"].values())
                         for actual in actuals)
                passed = ok
                print_report(case_id, passed, [] if ok else ["quick mode: some skill produced no output"],
                             [], actuals[-1], quick=True)
                if not passed:
                    all_passed = False
                summary.append((case_id, passed, [] if ok else ["quick pipeline empty"]))
            else:
                passed, failures, warnings = compare(
                    baseline.get("expected", {}), actuals[-1], lenient=args.lenient
                )
                print_report(case_id, passed, failures, warnings, actuals[-1], quick=False)

                if args.capture:
                    merged = merge_capture(baseline, actuals)
                    save_baseline(merged)
                    # 🆕 打印 merged 摘要，避免用户误以为存的是最后一次 actual
                    exp = merged.get("expected", {})
                    print(f"\n  [baseline merged] final_rating={exp.get('final_rating')}  "
                          f"report_lengths={exp.get('report_lengths')}")
                    print(f"  [baseline merged] tokens_in={exp.get('tokens_in_range')}  "
                          f"elapsed={exp.get('elapsed_minutes_range')}")

                if not passed:
                    all_passed = False
                summary.append((case_id, passed, failures + warnings))

    finally:
        if original_mode is not None:
            exit_regression_mode(original_mode)

    # 总览
    print(f"\n{'=' * 64}")
    print(f"  Summary")
    print(f"{'=' * 64}")
    for case_id, ok, notes in summary:
        status = "PASS" if ok else "FAIL"
        print(f"  {case_id}: {status}  ({len(notes)} notes)")
    print(f"{'=' * 64}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
