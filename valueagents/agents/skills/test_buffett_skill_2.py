# test_buffett_skill.py
import json
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from valueagents.agents.skills.buffett_skill.skill import execute
from valueagents.agents.src.analysts.warren_buffett import (
    warren_buffett_agent,
    analyze_fundamentals,
    analyze_moat,
    calculate_intrinsic_value,
)
from valueagents.agents.src.tools.api import get_financial_metrics, search_line_items, get_market_cap
from valueagents.agents.src.data.cache import get_cache


class TestBuffettSkill(unittest.TestCase):
    """测试 Buffett Skill 的各项功能"""

    @classmethod
    def setUpClass(cls):
        """所有测试共享的配置"""
        cls.ticker = "AAPL"
        cls.end_date = "2026-06-01"
        cls.api_key = "dummy"  # 实际会从环境变量读取
        cls.skill = execute  # 直接引用 execute 函数

    def setUp(self):
        """每个测试前重置缓存（可选）"""
        # 不清除缓存，以测试缓存复用
        pass

    # -------------------- 1. 数据获取测试 --------------------
    def test_get_financial_metrics(self):
        """测试财务指标获取（应命中缓存或从 yfinance 获取）"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=5)
        self.assertIsInstance(metrics, list)
        self.assertGreater(len(metrics), 0)
        # 检查关键字段
        first = metrics[0]
        self.assertIsNotNone(first.revenue)
        self.assertIsNotNone(first.net_income)
        self.assertIsNotNone(first.market_cap)
        print(f"✅ get_financial_metrics: {len(metrics)} records, latest revenue=${first.revenue:,.0f}")

    def test_search_line_items(self):
        """测试行项目获取"""
        line_items = ["revenue", "net_income", "free_cash_flow", "total_debt"]
        items = search_line_items(self.ticker, line_items, self.end_date, period="ttm", limit=5)
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
        item = items[0]
        for field in line_items:
            self.assertTrue(hasattr(item, field), f"Missing field {field}")
        print(f"✅ search_line_items: {len(items)} records, latest revenue=${item.revenue:,.0f}")

    # -------------------- 2. 分析函数单元测试 --------------------
    def test_analyze_fundamentals(self):
        """测试基本面分析函数（需要真实数据）"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=10)
        result = analyze_fundamentals(metrics)
        self.assertIn("score", result)
        self.assertIn("details", result)
        self.assertIsInstance(result["score"], int)
        print(f"✅ analyze_fundamentals: score={result['score']}, details={result['details']}")

    def test_analyze_moat(self):
        """测试护城河分析"""
        metrics = get_financial_metrics(self.ticker, self.end_date, period="ttm", limit=10)
        result = analyze_moat(metrics)
        self.assertIn("score", result)
        self.assertIn("max_score", result)
        self.assertIn("details", result)
        print(f"✅ analyze_moat: score={result['score']}/{result['max_score']}")

    def test_calculate_intrinsic_value(self):
        """测试内在价值计算（需要 line items）"""
        line_items = search_line_items(
            self.ticker,
            ["net_income", "depreciation_and_amortization", "capital_expenditure",
             "working_capital", "outstanding_shares", "shareholders_equity"],
            self.end_date,
            period="ttm",
            limit=10
        )
        result = calculate_intrinsic_value(line_items)
        self.assertIsNotNone(result.get("intrinsic_value"))
        self.assertGreater(result["intrinsic_value"], 0)
        print(f"✅ calculate_intrinsic_value: IV=${result['intrinsic_value']:,.0f}")

    # -------------------- 3. 完整 Agent 测试（可能调用 LLM） --------------------
    @patch("valueagents.agents.src.analysts.warren_buffett.call_llm")
    def test_warren_buffett_agent_mock_llm(self, mock_call_llm):
        """测试 agent 完整流程，但模拟 LLM 返回固定信号"""
        # 模拟 LLM 返回
        mock_call_llm.return_value = MagicMock(
            signal="bullish",
            confidence=85,
            reasoning="Mocked reasoning"
        )

        # 构造最小状态
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

        result_state = warren_buffett_agent(state, agent_id="test_agent")
        signals = result_state["data"]["analyst_signals"]["test_agent"][self.ticker]
        self.assertEqual(signals["signal"], "bullish")
        self.assertEqual(signals["confidence"], 85)
        print("✅ warren_buffett_agent (with mock LLM) passed")

    # -------------------- 4. Skill 执行测试（真实 LLM，可选） --------------------
    def test_skill_execute(self):
        """测试 skill.execute() 真实执行（会调用 LLM，耗时较长）"""
        # 如果不想每次都调用 LLM，可以跳过或使用 mock
        # 这里使用真实执行，但只运行一次
        start = time.time()
        result_json = execute(self.ticker, self.end_date, api_key=self.api_key)
        elapsed = time.time() - start
        result = json.loads(result_json)

        # 验证输出结构
        self.assertIn("ticker", result)
        self.assertEqual(result["ticker"], self.ticker)
        self.assertIn("signal", result)
        self.assertIn("confidence", result)
        self.assertIn("reasoning", result)
        self.assertIsInstance(result["confidence"], int)

        print(f"✅ skill.execute() completed in {elapsed:.2f}s")
        print(f"   Signal: {result['signal']}, Confidence: {result['confidence']}")
        print(f"   Reasoning: {result['reasoning'][:100]}...")

    # -------------------- 5. 缓存性能测试 --------------------
    def test_cache_performance(self):
        """测试缓存是否显著加速"""
        # 第一次调用（可能从网络获取）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        first_time = time.time() - start

        # 第二次调用（应命中缓存）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        cached_time = time.time() - start

        print(f"⏱️  First execution: {first_time:.2f}s")
        print(f"⏱️  Cached execution: {cached_time:.2f}s")
        # 缓存应明显更快（假设 > 2x 加速）
        self.assertLess(cached_time, first_time * 0.8)  # 至少快 20%

    # -------------------- 6. 多 ticker 测试 --------------------
    def test_multiple_tickers(self):
        """测试多个 ticker 是否能正常执行（仅检查不报错）"""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers[:2]:  # 只测前两个，避免太慢
            try:
                result_json = execute(ticker, self.end_date, api_key=self.api_key)
                result = json.loads(result_json)
                self.assertIn("signal", result)
                print(f"✅ {ticker}: signal={result['signal']}")
            except Exception as e:
                self.fail(f"Failed for {ticker}: {e}")

    # -------------------- 7. 错误处理测试 --------------------
    def test_invalid_ticker(self):
        """测试无效 ticker 应返回 neutral"""
        try:
            result_json = execute("INVALID_TICKER", self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            self.assertEqual(result["signal"], "neutral")
            # 置信度可能很低
            self.assertLessEqual(result["confidence"], 30)
            print("✅ Invalid ticker handled correctly")
        except Exception as e:
            self.fail(f"Invalid ticker raised exception: {e}")

    def test_no_data(self):
        """测试极端日期（可能无数据）"""
        try:
            # 很早的日期，可能无数据
            result_json = execute(self.ticker, "2000-01-01", api_key=self.api_key)
            result = json.loads(result_json)
            # 应该返回 neutral
            self.assertEqual(result["signal"], "neutral")
            print("✅ No-data scenario handled")
        except Exception as e:
            self.fail(f"No-data scenario raised exception: {e}")

    # -------------------- 8. 并发测试（可选） --------------------
    # 可添加多线程测试，但较复杂，略

# -------------------- 性能基准测试（独立运行） --------------------
def performance_benchmark():
    """运行基准测试，记录平均时间"""
    import statistics
    ticker = "AAPL"
    end_date = "2026-06-01"
    times = []
    for i in range(3):
        start = time.time()
        execute(ticker, end_date)
        times.append(time.time() - start)
    avg = statistics.mean(times)
    print(f"\n📊 Performance Benchmark (3 runs): avg={avg:.2f}s, min={min(times):.2f}s, max={max(times):.2f}s")


if __name__ == "__main__":
    # 运行单元测试
    unittest.main(verbosity=2)

    # 如果直接运行，可以额外执行性能基准
    # performance_benchmark()
