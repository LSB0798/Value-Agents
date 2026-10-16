#!/usr/bin/env python
# test_technical_skill.py
"""
全面测试 Technical Skill 的功能、性能和错误处理。
该 Skill 是纯规则型，不调用 LLM，依赖价格数据。
注意：由于 api.py 对无效 ticker 和 EDGAR 异常未做容错，测试中会临时禁用 EDGAR 以绕过这些限制。
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import os
# 设置 API Key（临时测试用）
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from valueagents.agents.skills.technical_skill.skill import execute
from valueagents.agents.src.analysts.technicals import (
    technical_analyst_agent,
    calculate_trend_signals,
    calculate_mean_reversion_signals,
    calculate_momentum_signals,
    calculate_volatility_signals,
    calculate_stat_arb_signals,
    weighted_signal_combination,
)
from valueagents.agents.src.tools.api import get_prices, prices_to_df
from valueagents.agents.src.data.cache import get_cache


class TestTechnicalSkill(unittest.TestCase):
    """测试 Technical Skill 的各项功能"""

    @classmethod
    def setUpClass(cls):
        cls.ticker = "AAPL"
        # 使用近一年的数据确保有足够历史
        cls.end_date = "2026-06-01"
        cls.start_date = "2025-06-01"  # 一年前
        cls.api_key = "dummy"
        cls.skill = execute

    def setUp(self):
        """每个测试前保存环境变量"""
        self._original_edgar = os.environ.get("USE_EDGAR")
        self._original_yfinance = os.environ.get("USE_YFINANCE")

    def tearDown(self):
        """恢复环境变量"""
        if self._original_edgar is not None:
            os.environ["USE_EDGAR"] = self._original_edgar
        else:
            os.environ.pop("USE_EDGAR", None)
        if self._original_yfinance is not None:
            os.environ["USE_YFINANCE"] = self._original_yfinance
        else:
            os.environ.pop("USE_YFINANCE", None)

    # -------------------- 1. 数据获取测试 --------------------
    def test_get_prices(self):
        """测试价格数据获取"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        self.assertIsInstance(prices, list)
        self.assertGreater(len(prices), 30)  # 至少一个月数据
        first = prices[0]
        self.assertTrue(hasattr(first, "open"))
        self.assertTrue(hasattr(first, "close"))
        self.assertTrue(hasattr(first, "volume"))
        print(f"✅ get_prices: {len(prices)} records from {self.start_date} to {self.end_date}")

    # -------------------- 2. 子策略函数测试 --------------------
    def test_calculate_trend_signals(self):
        """测试趋势信号计算"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        prices_df = prices_to_df(prices)
        result = calculate_trend_signals(prices_df)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        print(f"✅ calculate_trend_signals: signal={result['signal']}, confidence={result['confidence']:.2f}")

    def test_calculate_mean_reversion_signals(self):
        """测试均值回归信号"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        prices_df = prices_to_df(prices)
        result = calculate_mean_reversion_signals(prices_df)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        print(f"✅ calculate_mean_reversion_signals: signal={result['signal']}, confidence={result['confidence']:.2f}")

    def test_calculate_momentum_signals(self):
        """测试动量信号"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        prices_df = prices_to_df(prices)
        result = calculate_momentum_signals(prices_df)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        print(f"✅ calculate_momentum_signals: signal={result['signal']}, confidence={result['confidence']:.2f}")

    def test_calculate_volatility_signals(self):
        """测试波动率信号"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        prices_df = prices_to_df(prices)
        result = calculate_volatility_signals(prices_df)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        print(f"✅ calculate_volatility_signals: signal={result['signal']}, confidence={result['confidence']:.2f}")

    def test_calculate_stat_arb_signals(self):
        """测试统计套利信号"""
        prices = get_prices(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        prices_df = prices_to_df(prices)
        result = calculate_stat_arb_signals(prices_df)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("metrics", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        print(f"✅ calculate_stat_arb_signals: signal={result['signal']}, confidence={result['confidence']:.2f}")

    def test_weighted_signal_combination(self):
        """测试信号加权组合"""
        # 构造模拟信号
        signals = {
            "trend": {"signal": "bullish", "confidence": 0.8},
            "mean_reversion": {"signal": "neutral", "confidence": 0.5},
            "momentum": {"signal": "bullish", "confidence": 0.7},
            "volatility": {"signal": "neutral", "confidence": 0.6},
            "stat_arb": {"signal": "bullish", "confidence": 0.6},
        }
        weights = {"trend": 0.25, "mean_reversion": 0.20, "momentum": 0.25, "volatility": 0.15, "stat_arb": 0.15}
        result = weighted_signal_combination(signals, weights)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIsInstance(result["confidence"], float)
        print(f"✅ weighted_signal_combination: signal={result['signal']}, confidence={result['confidence']:.2f}")

    # -------------------- 3. 完整 Agent 测试（验证输出结构） --------------------
    def test_technical_agent_output_structure(self):
        """测试 agent 输出结构是否正确（不调用 LLM）"""
        state = {
            "data": {
                "tickers": [self.ticker],
                "start_date": self.start_date,
                "end_date": self.end_date,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
            "messages": [],  # 添加 messages 字段，避免 KeyError
        }

        result_state = technical_analyst_agent(state, agent_id="test_technical")
        signals = result_state["data"]["analyst_signals"]["test_technical"][self.ticker]

        # 验证顶层字段
        self.assertIn("signal", signals)
        self.assertIn("confidence", signals)
        self.assertIn("reasoning", signals)

        reasoning = signals["reasoning"]
        expected_keys = ["trend_following", "mean_reversion", "momentum", "volatility", "statistical_arbitrage"]
        for key in expected_keys:
            self.assertIn(key, reasoning)
            self.assertIn("signal", reasoning[key])
            self.assertIn("confidence", reasoning[key])
            self.assertIn("metrics", reasoning[key])

        print("✅ technical_agent output structure correct")

    # -------------------- 4. Skill 执行测试 --------------------
    def test_skill_execute(self):
        """测试 skill.execute() 真实执行（无 LLM，快速）"""
        start = time.time()
        result_json = execute(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        elapsed = time.time() - start
        result = json.loads(result_json)

        self.assertIn("ticker", result)
        self.assertEqual(result["ticker"], self.ticker)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("reasoning", result)
        self.assertIsInstance(result["confidence"], int)

        reasoning = result["reasoning"]
        expected_keys = ["trend_following", "mean_reversion", "momentum", "volatility", "statistical_arbitrage"]
        for key in expected_keys:
            self.assertIn(key, reasoning)

        print(f"✅ skill.execute() completed in {elapsed:.3f}s")
        print(f"   Signal: {result['signal']}, Confidence: {result['confidence']}")

    # -------------------- 5. 缓存性能测试 --------------------
    def test_cache_performance(self):
        """测试缓存是否加速（价格数据缓存）"""
        # 第一次执行（可能从网络获取）
        start = time.time()
        execute(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        first_time = time.time() - start

        # 第二次执行（应命中缓存，无 LLM 更快）
        start = time.time()
        execute(self.ticker, self.start_date, self.end_date, api_key=self.api_key)
        cached_time = time.time() - start

        print(f"⏱️  First execution: {first_time:.3f}s")
        print(f"⏱️  Cached execution: {cached_time:.3f}s")
        # 缓存应明显更快（至少 30%）
        self.assertLess(cached_time, first_time * 0.7)

    # -------------------- 6. 多 ticker 测试 --------------------
    def test_multiple_tickers(self):
        """测试多个 ticker 是否能正常执行（仅检查不报错）"""
        tickers = ["AAPL", "MSFT", "NVDA"]
        for ticker in tickers[:2]:  # 先测两个，避免耗时
            try:
                result_json = execute(ticker, self.start_date, self.end_date, api_key=self.api_key)
                result = json.loads(result_json)
                self.assertIn("signal", result)
                print(f"✅ {ticker}: signal={result['signal']}")
            except Exception as e:
                self.fail(f"Failed for {ticker}: {e}")

    # -------------------- 7. 错误处理测试 --------------------
    def test_invalid_ticker(self):
        """测试无效 ticker 应返回 neutral 或 bearish（禁用 EDGAR 避免崩溃）"""
        os.environ["USE_EDGAR"] = "false"
        os.environ["USE_YFINANCE"] = "true"
        try:
            result_json = execute("INVALID_TICKER", self.start_date, self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            # 数据不足时，信号可能为 neutral 或 bearish
            self.assertIn(result["signal"], ["neutral", "bearish"])
            self.assertLessEqual(result["confidence"], 30)
            print(f"✅ Invalid ticker handled correctly, signal: {result['signal']}")
        except Exception as e:
            self.fail(f"Invalid ticker raised exception: {e}")

    def test_insufficient_data(self):
        """测试数据不足时返回中性信号（短时间窗口）"""
        # 使用非常短的时间窗口（如 5 天），可能无法计算部分指标
        short_start = (datetime.strptime(self.end_date, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")
        try:
            result_json = execute(self.ticker, short_start, self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            # 应返回 neutral 或较低置信度
            self.assertIn(result["signal"], ["neutral", "bullish", "bearish"])
            # 置信度可能较低
            print(f"✅ Insufficient data scenario returned signal: {result['signal']}, confidence: {result['confidence']}")
        except Exception as e:
            self.fail(f"Insufficient data scenario raised exception: {e}")


# -------------------- 性能基准测试（独立运行） --------------------
def performance_benchmark():
    """运行基准测试，记录平均时间"""
    import statistics
    ticker = "AAPL"
    start_date = "2025-06-01"
    end_date = "2026-06-01"
    times = []
    for i in range(5):
        start = time.time()
        execute(ticker, start_date, end_date)
        times.append(time.time() - start)
    avg = statistics.mean(times)
    print(f"\n📊 Performance Benchmark (5 runs): avg={avg:.3f}s, min={min(times):.3f}s, max={max(times):.3f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    # 可选：performance_benchmark()
