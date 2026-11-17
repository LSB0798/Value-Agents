# ./valueagents/learning/recorder.py
"""DecisionRecord 归档 — Phase 2.5

在 portfolio_manager 节点末尾、ConversationalOrchestrator.run 末尾调用。
存储：valueagents/learning/decisions/{ticker}_{date}_{id}.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .schema import DecisionRecord


_DEFAULT_DIR = Path(__file__).parent / "decisions"


def get_decisions_dir() -> Path:
    """获取归档目录（可被环境变量覆盖）。"""
    import os
    override = os.environ.get("VALUEAGENTS_DECISIONS_DIR", "").strip()
    d = Path(override) if override else _DEFAULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch_price_at_date(ticker: str, end_date: str, lookback_days: int = 7) -> Optional[float]:
    """拉取 end_date 或其之前最近交易日的收盘价，失败返回 None。

    非交易日（周末/节假日）自动向前回溯 lookback_days 找最近交易日。
    """
    try:
        from datetime import datetime, timedelta
        from valueagents.agents.src.tools.api import get_prices, prices_to_df

        try:
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            start_date = (dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        except Exception:
            start_date = end_date

        prices = get_prices(ticker, start_date=start_date, end_date=end_date)
        if not prices:
            return None
        df = prices_to_df(prices)
        if df.empty:
            return None

        price = float(df["close"].iloc[-1])
        actual_date = (
            df.index[-1].strftime("%Y-%m-%d")
            if hasattr(df.index[-1], "strftime")
            else str(df.index[-1])
        )
        if actual_date != end_date:
            print(f"   ℹ️ [record_decision] {end_date} 非交易日，使用 {actual_date} 收盘价")
        return price
    except Exception as e:
        print(f"   ⚠️ [record_decision] price fetch failed: {type(e).__name__}: {e}")
        return None


def record_decision(
    ticker: str,
    end_date: str,
    final_rating: str,
    evidence_graph: Optional[dict[str, Any]] = None,
    master_signals: Optional[dict[str, Any]] = None,
    risk_profile: Optional[dict[str, Any]] = None,
    reasoning_mode: str = "legacy",
    meta: Optional[dict[str, Any]] = None,
) -> Optional[DecisionRecord]:
    """归档一次决策。失败返回 None，不抛异常。

    Returns:
        DecisionRecord 实例（成功）或 None（失败）
    """
    try:
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        price = _fetch_price_at_date(ticker, end_date)

        record = DecisionRecord(
            decision_id=decision_id,
            ticker=ticker,
            end_date=end_date,
            timestamp=datetime.now(timezone.utc),
            evidence_graph=evidence_graph or {},
            master_signals=master_signals or {},
            risk_profile=risk_profile,
            final_rating=final_rating,
            reasoning_mode=reasoning_mode,  # type: ignore
            price_at_decision=price,
            meta=meta or {},
        )

        out_path = get_decisions_dir() / f"{ticker}_{end_date}_{decision_id}.json"
        out_path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"   📝 [decision_record] saved → {out_path.name}")
        return record
    except Exception as e:
        print(f"   ⚠️ [record_decision] failed: {type(e).__name__}: {e}")
        return None


def load_decisions(
    ticker: Optional[str] = None,
    since: Optional[str] = None,
    mode: Optional[str] = None,
) -> list[DecisionRecord]:
    """加载决策记录。

    Args:
        ticker: 只加载该 ticker 的记录（None = 全部）
        since: 只加载 end_date >= since 的记录（YYYY-MM-DD）
        mode: 只加载 reasoning_mode == mode 的记录

    Returns:
        DecisionRecord 列表（按 timestamp 降序）
    """
    out: list[DecisionRecord] = []
    for f in get_decisions_dir().glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            rec = DecisionRecord(**data)
        except Exception:
            continue
        if ticker and rec.ticker != ticker:
            continue
        if since and rec.end_date < since:
            continue
        if mode and rec.reasoning_mode != mode:
            continue
        out.append(rec)
    out.sort(key=lambda r: r.timestamp, reverse=True)
    return out


__all__ = ["record_decision", "load_decisions", "get_decisions_dir"]