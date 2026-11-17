# ./valueagents/learning/weights.py
"""Phase 4 W1: MasterWeights

用历史准确率调整 master 的 confidence。
不改变 master 的原始输出，只在 EvidenceGraph / RiskProfile 层加乘数。

设计约束（plan.txt v1.1）：
- n < 30 时回退 raw_confidence（数据不足）
- multiplier 范围 [0.5, 1.5]（防止过度放大/缩小）
- 失败不影响 pipeline（try/except 包裹）
- 缓存：首次 compute 后缓存，refresh() 强制刷新
"""

from __future__ import annotations

import threading
from typing import Any, Optional


# 乘数边界与门槛
_MULT_MIN = 0.5
_MULT_MAX = 1.5
_MIN_SAMPLES = 30
_ACCURACY_BASELINE = 0.5


class MasterWeights:
    """历史准确率 → confidence 乘数。"""

    def __init__(self, lookback_days: int = 180, min_samples: int = _MIN_SAMPLES):
        self._lookback_days = lookback_days
        self._min_samples = min_samples
        self._accuracy_stats: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._lock = threading.Lock()

    # ============================================================
    # 数据加载
    # ============================================================
    def compute_weights(self) -> dict[str, dict[str, Any]]:
        """从 DecisionRecord 计算每个 master 的准确率。"""
        try:
            from .outcome import OutcomeTracker
            tracker = OutcomeTracker()
            stats = tracker.compute_master_accuracy(
                lookback_days=self._lookback_days,
                min_samples=self._min_samples,
            )
        except Exception as e:
            print(f"   ⚠️ [MasterWeights] compute failed: {type(e).__name__}: {e}")
            stats = {}

        with self._lock:
            self._accuracy_stats = stats
            self._loaded = True
        return stats

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.compute_weights()

    def refresh(self) -> dict[str, dict[str, Any]]:
        """强制重新计算（用于 daily_update 后刷新）。"""
        with self._lock:
            self._loaded = False
        return self.compute_weights()

    # ============================================================
    # 核心 API
    # ============================================================
    def get_effective_confidence(
        self,
        master_id: str,
        raw_confidence: float,
        scale: str = "0-1",
    ) -> float:
        """返回调整后的 confidence。

        Args:
            master_id: master 名（兼容 _analyst / _agent）
            raw_confidence: 原始 confidence
            scale: "0-1"（EvidenceGraph.Signal.strength）或
                   "0-100"（master_signals.confidence）

        Returns:
            调整后的 confidence，按 scale 对应的范围 clip：
            - "0-1"  → [0.0, 1.0]
            - "0-100" → [0.0, 100.0]
        """
        self._ensure_loaded()
        stats = self._accuracy_stats.get(master_id)
        if not stats or stats.get("n", 0) < self._min_samples:
            return raw_confidence

        accuracy = stats.get("accuracy")
        if accuracy is None:
            return raw_confidence

        multiplier = accuracy / _ACCURACY_BASELINE
        multiplier = max(_MULT_MIN, min(_MULT_MAX, multiplier))

        raw = raw_confidence * multiplier
        if scale == "0-100":
            return max(0.0, min(100.0, raw))
        # 默认 "0-1"
        return max(0.0, min(1.0, raw))

    def get_stats(self, master_id: str) -> Optional[dict[str, Any]]:
        self._ensure_loaded()
        return self._accuracy_stats.get(master_id)

    def all_stats(self) -> dict[str, dict[str, Any]]:
        self._ensure_loaded()
        return dict(self._accuracy_stats)


# ============================================================
# 应用权重到 master_signals
# ============================================================
def apply_weights_to_signals(
    master_signals: dict[str, Any],
    weights: Optional[MasterWeights] = None,
) -> dict[str, Any]:
    """对 master_signals 里的 confidence 应用权重乘数。

    ⚠️ 输入/输出 confidence 都是 0-100（与 master_signals 实际数据一致）。
    内部 `get_effective_confidence` 接受 0-1，所以这里做双向转换。
    """
    if not master_signals:
        return {}

    w = weights or _get_default_weights()
    out: dict[str, Any] = {}

    for name, sig_data in master_signals.items():
        if not isinstance(sig_data, dict):
            out[name] = sig_data
            continue

        # 单层
        if "signal" in sig_data and "confidence" in sig_data:
            raw_conf_100 = float(sig_data.get("confidence", 0) or 0)
            raw_conf_unit = raw_conf_100 / 100.0              # 🆕 0-100 → 0-1
            eff_conf_unit = w.get_effective_confidence(name, raw_conf_unit)
            new_entry = dict(sig_data)
            new_entry["confidence"] = eff_conf_unit * 100.0   # 🆕 0-1 → 0-100
            new_entry["_raw_confidence"] = raw_conf_100
            out[name] = new_entry
        else:
            # 双层：{ticker: {signal, confidence}}
            new_entry = {}
            for ticker, ticker_sig in sig_data.items():
                if not isinstance(ticker_sig, dict) or "signal" not in ticker_sig:
                    new_entry[ticker] = ticker_sig
                    continue
                raw_conf_100 = float(ticker_sig.get("confidence", 0) or 0)
                raw_conf_unit = raw_conf_100 / 100.0          # 🆕
                eff_conf_unit = w.get_effective_confidence(name, raw_conf_unit)
                new_ticker_sig = dict(ticker_sig)
                new_ticker_sig["confidence"] = eff_conf_unit * 100.0   # 🆕
                new_ticker_sig["_raw_confidence"] = raw_conf_100
                new_entry[ticker] = new_ticker_sig
            out[name] = new_entry

    return out


# ============================================================
# 全局单例
# ============================================================
_default_weights: Optional[MasterWeights] = None


def _get_default_weights() -> MasterWeights:
    global _default_weights
    if _default_weights is None:
        _default_weights = MasterWeights()
    return _default_weights


def reset_default_weights() -> None:
    """重置全局单例（测试用）。"""
    global _default_weights
    _default_weights = None


__all__ = [
    "MasterWeights",
    "apply_weights_to_signals",
    "reset_default_weights",
]
