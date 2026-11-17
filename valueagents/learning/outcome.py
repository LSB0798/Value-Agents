# ./valueagents/learning/outcome.py
"""OutcomeTracker — Phase 2.5

职责：
  - daily_update: 每日拉取过去决策的当前价格，标记 outcome
  - compute_master_accuracy: 计算每个 master 历史准确率
  - backtest_mode: 用历史 case 模拟某个模式的准确率（Phase 3 用）

设计约束：
  - 数据不足时返回空，不抛异常
  - Phase 2.5 阶段 daily_update 可运行但结果稀疏（3 个月后才有效）
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .recorder import load_decisions, get_decisions_dir
from .schema import DecisionRecord, OutcomeDetails


# ── Outcome 判定阈值（可配置） ──
_THRESHOLD_PCT = {
    "Buy": 0.03,           # 涨 ≥ 3% 算 right
    "Overweight": 0.02,    # 涨 ≥ 2% 算 right
    "Underweight": -0.02,  # 跌 ≥ 2% 算 right
    "Sell": -0.03,         # 跌 ≥ 3% 算 right
}
_HOLD_TOLERANCE = 0.05     # Hold：|ret| ≤ 5% 算 right


class OutcomeTracker:
    """Outcome 追踪器。"""

    def __init__(self, decisions_dir: Optional[Path] = None):
        self._dir = decisions_dir or get_decisions_dir()

    # ============================================================
    # 1. 每日更新
    # ============================================================
    def daily_update(self, today: Optional[str] = None) -> dict[str, int]:
        """拉取过去决策的当前价格，标记 1m / 3m / 6m outcome。

        Args:
            today: 检查日期（YYYY-MM-DD，默认今天）

        Returns:
            {"updated_1m": N, "updated_3m": N, "updated_6m": N, "skipped": M}
        """
        today = today or datetime.utcnow().strftime("%Y-%m-%d")
        stats = {"updated_1m": 0, "updated_3m": 0, "updated_6m": 0, "skipped": 0}

        decisions = load_decisions()
        for rec in decisions:
            try:
                rec_path = self._dir / f"{rec.ticker}_{rec.end_date}_{rec.decision_id}.json"
                if not rec_path.exists():
                    stats["skipped"] += 1
                    continue

                changed = False

                # 1 个月
                if rec.price_at_1m is None and self._is_past(rec.end_date, today, 30):
                    p = self._fetch_price(rec.ticker, self._add_days(rec.end_date, 30))
                    if p is not None:
                        rec.price_at_1m = p
                        changed = True
                        stats["updated_1m"] += 1

                # 3 个月
                if rec.price_at_3m is None and self._is_past(rec.end_date, today, 90):
                    p = self._fetch_price(rec.ticker, self._add_days(rec.end_date, 90))
                    if p is not None:
                        rec.price_at_3m = p
                        changed = True
                        stats["updated_3m"] += 1

                # 6 个月
                if rec.price_at_6m is None and self._is_past(rec.end_date, today, 180):
                    p = self._fetch_price(rec.ticker, self._add_days(rec.end_date, 180))
                    if p is not None:
                        rec.price_at_6m = p
                        changed = True
                        stats["updated_6m"] += 1

                # 3 个月数据到齐后，判定 outcome
                if rec.outcome == "pending" and rec.price_at_3m is not None and rec.price_at_decision is not None:
                    rec.outcome = self._judge_outcome(
                        rec.final_rating, rec.price_at_decision, rec.price_at_3m
                    )
                    rec.outcome_details = OutcomeDetails(
                        horizon="3m",
                        price_at_decision=rec.price_at_decision,
                        price_at_check=rec.price_at_3m,
                        return_pct=(rec.price_at_3m - rec.price_at_decision) / rec.price_at_decision,
                        rating=rec.final_rating,
                        threshold_used=_THRESHOLD_PCT.get(rec.final_rating, 0.03),
                    )
                    changed = True

                if changed:
                    rec_path.write_text(
                        json.dumps(rec.model_dump(mode="json"), indent=2, default=str, ensure_ascii=False),
                        encoding="utf-8",
                    )
                else:
                    stats["skipped"] += 1
            except Exception as e:
                print(f"   ⚠️ [OutcomeTracker] {rec.decision_id} failed: {e}")
                stats["skipped"] += 1

        return stats

    # ============================================================
    # 2. 计算 master 历史准确率
    # ============================================================
    def compute_master_accuracy(
        self, lookback_days: int = 180, min_samples: int = 30
    ) -> dict[str, dict[str, Any]]:
        """计算每个 master 的历史准确率。

        Returns:
            {master_name: {"n": int, "accuracy": float, "by_direction": {...}}}
            数据不足（n < min_samples）的 master 不返回（或返回 n=0）
        """
        cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        decisions = load_decisions(since=cutoff)
        settled = [r for r in decisions if r.outcome in ("right", "wrong")]

        # master_name → direction → {"right": N, "wrong": N}
        stats: dict[str, dict[str, dict[str, int]]] = {}
        for rec in settled:
            for master_name, signals in rec.master_signals.items():
                if not isinstance(signals, dict):
                    continue
                # 兼容单层和双层
                sig_data = signals if "signal" in signals else next(
                    (v for v in signals.values() if isinstance(v, dict)), {}
                )
                direction = str(sig_data.get("signal", "")).lower()
                if direction not in ("bullish", "bearish", "neutral"):
                    continue
                stats.setdefault(master_name, {}).setdefault(direction, {"right": 0, "wrong": 0})
                # master 的 direction 对错：跟决策的 outcome 是否一致
                # 简化：master bullish 且决策 Buy/Overweight 且 outcome=right → right
                if self._direction_matches_outcome(direction, rec.final_rating, rec.outcome):
                    stats[master_name][direction]["right"] += 1
                else:
                    stats[master_name][direction]["wrong"] += 1

        out: dict[str, dict[str, Any]] = {}
        for name, by_dir in stats.items():
            total_right = sum(d["right"] for d in by_dir.values())
            total_wrong = sum(d["wrong"] for d in by_dir.values())
            n = total_right + total_wrong
            if n < min_samples:
                out[name] = {"n": n, "accuracy": None, "by_direction": by_dir, "note": f"insufficient (need {min_samples})"}
            else:
                out[name] = {
                    "n": n,
                    "accuracy": total_right / n,
                    "by_direction": by_dir,
                }
        return out

    # ============================================================
    # 3. Backtest
    # ============================================================
    def backtest_mode(
        self, mode: str, case_ids: list[str]
    ) -> dict[str, Any]:
        """回测：从已有 DecisionRecord 里筛选 mode 模式的记录，统计准确率。

        Phase 2.5 时只有 legacy 记录（框架保留）。
        Phase 3 后会有 framework 记录可对比。

        Args:
            mode: "legacy" / "framework" / "ab"
            case_ids: ["B1", "B2", "B3"]

        Returns:
            {"mode": str, "cases": {...}, "total": int, "settled": int, "accuracy": float|None}
        """
        all_decisions = load_decisions(mode=mode)
        case_decisions: dict[str, list[DecisionRecord]] = {c: [] for c in case_ids}
        for rec in all_decisions:
            # 匹配 case：ticker + end_date 对得上
            # 简化：从 meta 里拿 case_id（归档时传）
            cid = rec.meta.get("case_id") if rec.meta else None
            if cid in case_ids:
                case_decisions[cid].append(rec)

        settled = [r for r in all_decisions if r.outcome in ("right", "wrong")]
        right = sum(1 for r in settled if r.outcome == "right")

        return {
            "mode": mode,
            "cases": {c: len(recs) for c, recs in case_decisions.items()},
            "total": len(all_decisions),
            "settled": len(settled),
            "accuracy": (right / len(settled)) if settled else None,
        }

    # ============================================================
    # 内部辅助
    # ============================================================
    def _fetch_price(self, ticker: str, date: str, lookback_days: int = 7) -> Optional[float]:
        """拉取 date 或最近交易日的收盘价。"""
        try:
            from datetime import datetime, timedelta
            from valueagents.agents.src.tools.api import get_prices, prices_to_df

            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                start_date = (dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            except Exception:
                start_date = date

            prices = get_prices(ticker, start_date=start_date, end_date=date)
            if not prices:
                return None
            df = prices_to_df(prices)
            if df.empty:
                return None
            return float(df["close"].iloc[-1])
        except Exception:
            return None

    @staticmethod
    def _add_days(date: str, days: int) -> str:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            return (dt + timedelta(days=days)).strftime("%Y-%m-%d")
        except Exception:
            return date

    @staticmethod
    def _is_past(date: str, today: str, days: int) -> bool:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            return (datetime.strptime(today, "%Y-%m-%d") - dt).days >= days
        except Exception:
            return False

    @staticmethod
    def _judge_outcome(rating: str, p0: float, p1: float) -> str:
        if p0 <= 0:
            return "neutral"
        ret = (p1 - p0) / p0

        # ── Hold 单独处理：|ret| ≤ 容忍带 → right，超出 → wrong ──
        if rating == "Hold":
            return "right" if abs(ret) <= _HOLD_TOLERANCE else "wrong"

        # ── Buy / Overweight / Sell / Underweight ──
        th = _THRESHOLD_PCT.get(rating)
        if th is None:
            # 未知 rating（如 UNKNOWN）→ neutral
            return "neutral"

        if th > 0:
            # Buy / Overweight：涨够 th → right；跌够 th → wrong；中间 → neutral
            if ret >= th:
                return "right"
            if ret <= -th:
                return "wrong"
            return "neutral"

        # Sell / Underweight：跌够 |th| → right；涨够 |th| → wrong；中间 → neutral
        if ret <= th:
            return "right"
        if ret >= -th:
            return "wrong"
        return "neutral"

    @staticmethod
    def _direction_matches_outcome(
        direction: str, rating: str, outcome: str
    ) -> bool:
        if outcome == "right":
            if direction == "bullish" and rating in ("Buy", "Overweight"):
                return True
            if direction == "bearish" and rating in ("Sell", "Underweight"):
                return True
            if direction == "neutral" and rating == "Hold":
                return True
        return False


__all__ = ["OutcomeTracker"]
