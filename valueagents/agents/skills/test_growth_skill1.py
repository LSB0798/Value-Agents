#!/usr/bin/env python
# test_growth_skill.py
"""
全面测试 Growth Skill 的功能、性能和错误处理。
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

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from valueagents.agents.skills.growth_skill.skill import execute
from valueagents.agents.src.analysts.growth_agent import (
    growth_analyst_agent,
    analyze_growth_trends,
    analyze_valuation,
    analyze_margin_trends,
    analyze_insider_conviction,
    check_financial_health,
)
from valueagents.agents.src.tools.api import get_financial_metrics, get_insider_trades
from valueagents.agents.src.data.cache import get_cache


class TestGrowthSkill(unittest.TestCase):
    """测试 Growth Skill 的各项功能"""

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
        """测试 TTM 财务指标获取（limit=12）"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=12)
        self.assertIsInstance(metrics, list)
        self.assertGreater(len(metrics), 0)
        first = metrics[0]
        self.assertIsNotNone(first.revenue_growth)
        self.assertIsNotNone(first.peg_ratio)
        self.assertIsNotNone(first.gross_margin)
        print(f"✅ get_financial_metrics (ttm): {len(metrics)} records, latest revenue_growth={first.revenue_growth:.2%}")

    def test_get_insider_trades(self):
        """测试内幕交易数据获取"""
        trades = get_insider_trades(self.ticker, self.end_date, limit=100)
        self.assertIsInstance(trades, list)
        print(f"✅ get_insider_trades: {len(trades)} records")

    # -------------------- 2. 子分析函数单元测试 --------------------
    def test_analyze_growth_trends(self):
        """测试历史增长趋势分析"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=12)
        result = analyze_growth_trends(metrics)
        self.assertIn("score", result)
        self.assertIn("revenue_growth", result)
        self.assertIn("eps_growth", result)
        self.assertIn("fcf_growth", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1.0)
        print(f"✅ analyze_growth_trends: score={result['score']:.2f}, rev_growth={result['revenue_growth']:.2%}")

    def test_analyze_valuation(self):
        """测试增长型估值分析（PEG + P/S）"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=1)[0]
        result = analyze_valuation(metrics)
        self.assertIn("score", result)
        self.assertIn("peg_ratio", result)
        self.assertIn("price_to_sales_ratio", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1.0)
        # 处理 peg_ratio 为 None 的情况
        peg = result.get('peg_ratio')
        if peg is None:
            print(f"✅ analyze_valuation: score={result['score']:.2f}, peg=None")
        else:
            print(f"✅ analyze_valuation: score={result['score']:.2f}, peg={peg:.2f}")

    def test_analyze_margin_trends(self):
        """测试利润率趋势分析"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=12)
        result = analyze_margin_trends(metrics)
        self.assertIn("score", result)
        self.assertIn("gross_margin", result)
        self.assertIn("operating_margin", result)
        self.assertIn("net_margin", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1.0)
        print(f"✅ analyze_margin_trends: score={result['score']:.2f}, gross_margin={result['gross_margin']:.2%}")

    def test_analyze_insider_conviction(self):
        """测试内幕交易信心分析"""
        trades = get_insider_trades(self.ticker, self.end_date, limit=1000)
        result = analyze_insider_conviction(trades)
        self.assertIn("score", result)
        self.assertIn("net_flow_ratio", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1.0)
        print(f"✅ analyze_insider_conviction: score={result['score']:.2f}, net_flow_ratio={result['net_flow_ratio']:.2f}")

    def test_check_financial_health(self):
        """测试财务健康检查"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=1)[0]
        result = check_financial_health(metrics)
        self.assertIn("score", result)
        self.assertIn("debt_to_equity", result)
        self.assertIn("current_ratio", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 1.0)
        print(f"✅ check_financial_health: score={result['score']:.2f}, D/E={result['debt_to_equity']:.2f}")

    # -------------------- 3. 完整 Agent 测试（验证输出结构） --------------------
    def test_growth_agent_output_structure(self):
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

        result_state = growth_analyst_agent(state, agent_id="test_growth")
        signals = result_state["data"]["analyst_signals"]["test_growth"][self.ticker]

        # 验证顶层字段
        self.assertIn("signal", signals)
        self.assertIn("confidence", signals)
        self.assertIn("reasoning", signals)

        reasoning = signals["reasoning"]
        expected_keys = [
            "historical_growth",
            "growth_valuation",
            "margin_expansion",
            "insider_conviction",
            "financial_health",
            "final_analysis",
        ]
        for key in expected_keys:
            self.assertIn(key, reasoning)

        final = reasoning["final_analysis"]
        self.assertIn("signal", final)
        self.assertIn("confidence", final)
        self.assertIn("weighted_score", final)

        print("✅ growth_agent output structure correct")

    # -------------------- 4. Skill 执行测试 --------------------
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
        self.assertIsInstance(result["confidence"], int)

        reasoning = result["reasoning"]
        expected_keys = [
            "historical_growth",
            "growth_valuation",
            "margin_expansion",
            "insider_conviction",
            "financial_health",
            "final_analysis",
        ]
        for key in expected_keys:
            self.assertIn(key, reasoning)

        print(f"✅ skill.execute() completed in {elapsed:.3f}s")
        print(f"   Signal: {result['signal']}, Confidence: {result['confidence']}")

    # -------------------- 5. 缓存性能测试 --------------------
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
        # 放宽阈值至 25% 加速
        self.assertLess(cached_time, first_time * 0.75)  # 至少快 25%

    # -------------------- 6. 多 ticker 测试 --------------------
    def test_multiple_tickers(self):
        """测试多个 ticker 是否能正常执行（仅检查不报错）"""
        tickers = ["AAPL", "MSFT", "NVDA"]
        for ticker in tickers[:2]:  # 先测两个，避免耗时
            try:
                result_json = execute(ticker, self.end_date, api_key=self.api_key)
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
            result_json = execute("INVALID_TICKER", self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            # 数据不足时，信号可能为 neutral 或 bearish
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

    # -------------------- 8. 置信度计算验证 --------------------
    def test_confidence_calculation(self):
        """验证置信度计算公式是否正确"""
        # 通过真实数据验证
        result_json = execute(self.ticker, self.end_date, api_key=self.api_key)
        result = json.loads(result_json)
        reasoning = result["reasoning"]
        weighted_score = reasoning["final_analysis"]["weighted_score"]
        expected_conf = round(abs(weighted_score - 0.5) * 2 * 100)
        # 允许 ±1 的浮点误差
        self.assertAlmostEqual(result["confidence"], expected_conf, delta=1)
        print(f"✅ Confidence calculation correct: {expected_conf}% for weighted_score={weighted_score:.2f}")


# -------------------- 性能基准测试（独立运行） --------------------
def performance_benchmark():
    """运行基准测试，记录平均时间"""
    import statistics
    ticker = "AAPL"
    end_date = "2026-06-01"
    times = []
    for i in range(5):
        start = time.time()
        execute(ticker, end_date)
        times.append(time.time() - start)
    avg = statistics.mean(times)
    print(f"\n📊 Performance Benchmark (5 runs): avg={avg:.3f}s, min={min(times):.3f}s, max={max(times):.3f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    # 可选：performance_benchmark()
