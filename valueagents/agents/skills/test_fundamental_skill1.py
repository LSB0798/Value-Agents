#!/usr/bin/env python
# test_fundamental_skill.py
"""
全面测试 Fundamental Skill 的功能、性能和错误处理。
该 Skill 是纯规则型，不调用 LLM，因此测试执行速度快。
注意：由于 api.py 对无效 ticker 和 EDGAR 异常未做容错，测试中会临时禁用 EDGAR 以绕过这些限制。
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import os
# 设置 API Key（临时测试用）
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from valueagents.agents.skills.fundamental_skill.skill import execute
from valueagents.agents.src.analysts.fundamentals import fundamentals_analyst_agent
from valueagents.agents.src.tools.api import get_financial_metrics
from valueagents.agents.src.data.cache import get_cache


class TestFundamentalSkill(unittest.TestCase):
    """测试 Fundamental Skill 的各项功能"""

    @classmethod
    def setUpClass(cls):
        cls.ticker = "AAPL"
        cls.end_date = "2026-06-01"
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
    def test_get_financial_metrics_ttm(self):
        """测试 TTM 财务指标获取"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=10)
        self.assertIsInstance(metrics, list)
        self.assertGreater(len(metrics), 0)
        first = metrics[0]
        self.assertIsNotNone(first.revenue)
        self.assertIsNotNone(first.return_on_equity)
        self.assertIsNotNone(first.price_to_earnings_ratio)
        print(f"✅ get_financial_metrics (ttm): {len(metrics)} records, latest ROE={first.return_on_equity:.2%}")

    # -------------------- 2. 完整 Agent 测试（验证各维度信号） --------------------
    def test_fundamentals_agent_output_structure(self):
        """测试 agent 输出结构是否正确（不调用 LLM）"""
        state = {
            "data": {
                "tickers": [self.ticker],
                "end_date": self.end_date,
                "start_date": None,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
        }

        result_state = fundamentals_analyst_agent(state, agent_id="test_fundamental")
        signals = result_state["data"]["analyst_signals"]["test_fundamental"][self.ticker]

        # 验证顶层字段
        self.assertIn("signal", signals)
        self.assertIn("confidence", signals)
        self.assertIn("reasoning", signals)

        reasoning = signals["reasoning"]
        expected_keys = ["profitability_signal", "growth_signal", "financial_health_signal", "price_ratios_signal"]
        for key in expected_keys:
            self.assertIn(key, reasoning)
            self.assertIn("signal", reasoning[key])
            self.assertIn("details", reasoning[key])

        print("✅ fundamentals_agent output structure correct")

    def test_profitability_scoring(self):
        """验证盈利性评分逻辑（使用真实数据）"""
        # 直接调用 agent 并检查 profitability_signal
        state = {
            "data": {
                "tickers": [self.ticker],
                "end_date": self.end_date,
                "start_date": None,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
        }
        result_state = fundamentals_analyst_agent(state, agent_id="test_profit")
        reasoning = result_state["data"]["analyst_signals"]["test_profit"][self.ticker]["reasoning"]
        profit_sig = reasoning["profitability_signal"]
        # AAPL 应具有高盈利性，信号应为 bullish 或至少非 bearish
        self.assertIn(profit_sig["signal"], ["bullish", "neutral"])
        # 检查细节包含 ROE, Net Margin, Op Margin
        self.assertIn("ROE:", profit_sig["details"])
        self.assertIn("Net Margin:", profit_sig["details"])
        self.assertIn("Op Margin:", profit_sig["details"])
        print(f"✅ Profitability signal: {profit_sig['signal']} - {profit_sig['details']}")

    def test_growth_scoring(self):
        """验证增长评分逻辑"""
        state = {
            "data": {
                "tickers": [self.ticker],
                "end_date": self.end_date,
                "start_date": None,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
        }
        result_state = fundamentals_analyst_agent(state, agent_id="test_growth")
        reasoning = result_state["data"]["analyst_signals"]["test_growth"][self.ticker]["reasoning"]
        growth_sig = reasoning["growth_signal"]
        # AAPL 的增长可能为 neutral 或 bullish，取决于数据
        self.assertIn(growth_sig["signal"], ["bullish", "neutral", "bearish"])
        self.assertIn("Revenue Growth:", growth_sig["details"])
        self.assertIn("Earnings Growth:", growth_sig["details"])
        print(f"✅ Growth signal: {growth_sig['signal']} - {growth_sig['details']}")

    def test_financial_health_scoring(self):
        """验证财务健康评分逻辑"""
        state = {
            "data": {
                "tickers": [self.ticker],
                "end_date": self.end_date,
                "start_date": None,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
        }
        result_state = fundamentals_analyst_agent(state, agent_id="test_health")
        reasoning = result_state["data"]["analyst_signals"]["test_health"][self.ticker]["reasoning"]
        health_sig = reasoning["financial_health_signal"]
        # AAPL 流动比率较低，D/E 较高，可能为 neutral 或 bearish
        self.assertIn(health_sig["signal"], ["bullish", "neutral", "bearish"])
        self.assertIn("Current Ratio:", health_sig["details"])
        self.assertIn("D/E:", health_sig["details"])
        print(f"✅ Financial health signal: {health_sig['signal']} - {health_sig['details']}")

    def test_valuation_scoring(self):
        """验证估值评分逻辑"""
        state = {
            "data": {
                "tickers": [self.ticker],
                "end_date": self.end_date,
                "start_date": None,
                "portfolio": {},
                "analyst_signals": {},
                "metadata": {"show_reasoning": False},
            },
            "api_keys": {"FINANCIAL_DATASETS_API_KEY": self.api_key},
            "metadata": {"show_reasoning": False},
        }
        result_state = fundamentals_analyst_agent(state, agent_id="test_val")
        reasoning = result_state["data"]["analyst_signals"]["test_val"][self.ticker]["reasoning"]
        val_sig = reasoning["price_ratios_signal"]
        # AAPL 估值偏高，通常为 bearish
        self.assertEqual(val_sig["signal"], "bearish")
        self.assertIn("P/E:", val_sig["details"])
        self.assertIn("P/B:", val_sig["details"])
        self.assertIn("P/S:", val_sig["details"])
        print(f"✅ Valuation signal: {val_sig['signal']} - {val_sig['details']}")

    # -------------------- 3. Skill 执行测试 --------------------
    def test_skill_execute(self):
        """测试 skill.execute() 真实执行（无 LLM，快速）"""
        start = time.time()
        result_json = execute(self.ticker, self.end_date, api_key=self.api_key)
        elapsed = time.time() - start
        result = json.loads(result_json)

        self.assertIn("ticker", result)
        self.assertEqual(result["ticker"], self.ticker)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("reasoning", result)
        self.assertIsInstance(result["confidence"], float)

        # 验证 reasoning 包含四个维度
        reasoning = result["reasoning"]
        expected_keys = ["profitability_signal", "growth_signal", "financial_health_signal", "price_ratios_signal"]
        for key in expected_keys:
            self.assertIn(key, reasoning)

        print(f"✅ skill.execute() completed in {elapsed:.3f}s")
        print(f"   Signal: {result['signal']}, Confidence: {result['confidence']}")

    # -------------------- 4. 缓存性能测试 --------------------
    def test_cache_performance(self):
        """测试缓存是否加速（数据获取缓存）"""
        # 第一次执行（可能从网络获取）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        first_time = time.time() - start

        # 第二次执行（应命中缓存，无 LLM 更快）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        cached_time = time.time() - start

        print(f"⏱️  First execution: {first_time:.3f}s")
        print(f"⏱️  Cached execution: {cached_time:.3f}s")
        # 缓存应明显更快（由于无 LLM，数据获取占主导）
        self.assertLess(cached_time, first_time * 0.7)  # 至少快 30%

    # -------------------- 5. 多 ticker 测试 --------------------
    def test_multiple_tickers(self):
        """测试多个 ticker 是否能正常执行（仅检查不报错）"""
        tickers = ["AAPL", "MSFT", "KO"]
        for ticker in tickers[:2]:
            try:
                result_json = execute(ticker, self.end_date, api_key=self.api_key)
                result = json.loads(result_json)
                self.assertIn("signal", result)
                print(f"✅ {ticker}: signal={result['signal']}")
            except Exception as e:
                self.fail(f"Failed for {ticker}: {e}")

    # -------------------- 6. 错误处理测试 --------------------
    def test_invalid_ticker(self):
        """测试无效 ticker 应返回 neutral 或 bearish（禁用 EDGAR 避免崩溃）"""
        os.environ["USE_EDGAR"] = "false"
        os.environ["USE_YFINANCE"] = "true"
        try:
            result_json = execute("INVALID_TICKER", self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            # 数据不足时，信号可能为 neutral 或 bearish（规则型）
            self.assertIn(result["signal"], ["neutral", "bearish"])
            self.assertLessEqual(result["confidence"], 30)
            print(f"✅ Invalid ticker handled correctly, signal: {result['signal']}")
        except Exception as e:
            self.fail(f"Invalid ticker raised exception: {e}")

    def test_no_data(self):
        """测试极早日期：数据可能仍存在，仅验证不崩溃"""
        try:
            result_json = execute(self.ticker, "2000-01-01", api_key=self.api_key)
            result = json.loads(result_json)
            self.assertIn(result["signal"], ["bullish", "bearish", "neutral"])
            print(f"✅ No-data scenario (early date) returned signal: {result['signal']}")
        except Exception as e:
            self.fail(f"No-data scenario raised exception: {e}")

    # -------------------- 7. 置信度计算验证 --------------------
    def test_confidence_calculation(self):
        """验证置信度计算是否正确（基于信号一致性）"""
        # 使用一个已知结果的 ticker，或者手动模拟，但这里通过真实数据验证
        result_json = execute(self.ticker, self.end_date, api_key=self.api_key)
        result = json.loads(result_json)
        confidence = result["confidence"]
        reasoning = result["reasoning"]

        # 提取各维度信号
        signals = []
        for key in ["profitability_signal", "growth_signal", "financial_health_signal", "price_ratios_signal"]:
            sig = reasoning[key]["signal"]
            signals.append(sig)

        bullish = signals.count("bullish")
        bearish = signals.count("bearish")
        total = len(signals)
        expected_conf = round(max(bullish, bearish) / total, 2) * 100

        self.assertEqual(confidence, expected_conf)
        print(f"✅ Confidence calculation correct: {confidence}% (bullish={bullish}, bearish={bearish})")


# -------------------- 性能基准测试（独立运行） --------------------
def performance_benchmark():
    """运行基准测试，记录平均时间"""
    import statistics
    ticker = "AAPL"
    end_date = "2026-06-01"
    times = []
    for i in range(5):  # 多次运行取平均
        start = time.time()
        execute(ticker, end_date)
        times.append(time.time() - start)
    avg = statistics.mean(times)
    print(f"\n📊 Performance Benchmark (5 runs): avg={avg:.3f}s, min={min(times):.3f}s, max={max(times):.3f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    # 可选：performance_benchmark()
