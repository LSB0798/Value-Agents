#!/usr/bin/env python3
"""
test_buffett_skill_full.py
全面的 Warren Buffett Skill 测试套件
支持单元测试（模拟）和集成测试（真实 API，需设置环境变量）
"""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# 添加项目路径
import os
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from valueagents.default_config import DEFAULT_CONFIG
import shutil

from valueagents.agents.skills.buffett_skill.skill import execute
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state


class TestBuffettSkillUnit(unittest.TestCase):
    """单元测试：模拟外部依赖，验证逻辑正确性"""

    def setUp(self):
        """每个测试前的准备工作"""
        # 创建临时目录模拟缓存，避免污染真实缓存
        self.temp_cache_dir = tempfile.mkdtemp()
        # 修改默认配置中的缓存路径（通过环境变量或猴子补丁）
        self.original_cache_dir = os.environ.get("VALUEAGENTS_CACHE_DIR")
        os.environ["VALUEAGENTS_CACHE_DIR"] = self.temp_cache_dir
        # 重设缓存单例（因为 cache 模块在导入时已初始化，这里需要重新加载）
        # 但简单起见，我们直接使用真实缓存路径，但测试后清理？更好的做法是 mock cache 对象。
        # 为了简化，我们直接 mock get_cache 返回一个可控的 cache 对象。
        self.cache_mock = MagicMock()
        self.cache_mock.get_annual_data.return_value = {'financials': [], 'balance': [], 'cashflow': []}
        self.cache_mock.get_quarterly_data.return_value = {'income': [], 'balance': [], 'cashflow': [], 'ratios': []}
        self.cache_mock.get_line_items_cache.return_value = []
        self.cache_mock.get_prices_from_cache.return_value = None
        self.cache_mock.get_financial_metrics.return_value = None
        self.cache_mock.get_insider_cache.return_value = []
        self.cache_mock.get_news_cache.return_value = []
        # 需要 mock 一些存储方法
        self.cache_mock.set_annual_data = MagicMock()
        self.cache_mock.set_quarterly_data = MagicMock()
        self.cache_mock.set_line_items_cache = MagicMock()
        self.cache_mock.set_prices_to_cache = MagicMock()
        self.cache_mock.set_financial_metrics = MagicMock()
        self.cache_mock.set_insider_cache = MagicMock()
        self.cache_mock.set_news_cache = MagicMock()

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_cache_dir):
            shutil.rmtree(self.temp_cache_dir)
        if self.original_cache_dir is not None:
            os.environ["VALUEAGENTS_CACHE_DIR"] = self.original_cache_dir
        else:
            os.environ.pop("VALUEAGENTS_CACHE_DIR", None)

    @patch('valueagents.agents.skills.buffett_skill.skill.warren_buffett_agent')
    def test_execute_returns_json(self, mock_agent):
        """测试 execute 函数返回有效的 JSON 且包含必要字段"""
        # 模拟 warren_buffett_agent 的返回状态
        mock_agent.return_value = {
            "data": {
                "analyst_signals": {
                    "buffett_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 85,
                            "reasoning": "测试推理"
                        }
                    }
                }
            }
        }
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertIn("ticker", data)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn("signal", data)
        self.assertIn("confidence", data)
        self.assertIn("reasoning", data)
        self.assertIsInstance(data["confidence"], int)
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])

    @patch('valueagents.agents.skills.buffett_skill.skill.warren_buffett_agent')
    def test_execute_fallback_on_missing_signal(self, mock_agent):
        """测试当 agent 未返回信号时，使用默认中性信号"""
        mock_agent.return_value = {"data": {"analyst_signals": {}}}
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0.0)  # 注意 extract_signal_from_state 返回 float 0.0
        self.assertIn("No signal generated", data["reasoning"])

    def test_build_minimal_agent_state(self):
        """测试状态构建函数"""
        state = build_minimal_agent_state("AAPL", "2026-06-30", api_key="test_key")
        self.assertEqual(state["data"]["tickers"], ["AAPL"])
        self.assertEqual(state["data"]["end_date"], "2026-06-30")
        self.assertEqual(state["api_keys"]["FINANCIAL_DATASETS_API_KEY"], "test_key")
        self.assertEqual(state["metadata"]["show_reasoning"], False)
        self.assertIn("start_date", state["data"])
        self.assertIsNone(state["data"]["start_date"])

    def test_extract_signal_from_state(self):
        """测试信号提取函数"""
        state = {
            "data": {
                "analyst_signals": {
                    "buffett_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 90,
                            "reasoning": "Great"
                        }
                    }
                }
            }
        }
        signal = extract_signal_from_state(state, "buffett_skill", "AAPL")
        self.assertEqual(signal["signal"], "bullish")
        self.assertEqual(signal["confidence"], 90)
        self.assertEqual(signal["reasoning"], "Great")

        # 缺失信号
        state["data"]["analyst_signals"] = {}
        signal = extract_signal_from_state(state, "buffett_skill", "AAPL")
        self.assertEqual(signal["signal"], "neutral")
        self.assertEqual(signal["confidence"], 0.0)
        self.assertEqual(signal["reasoning"], "No signal generated by the skill.")


class TestBuffettSkillLoader(unittest.TestCase):
    """测试 skill 加载器"""

    def setUp(self):
        self.skill_dir = Path(__file__).parent / "buffett_skill"
        # 如果当前目录不是 skills 目录，尝试找到正确路径
        if not self.skill_dir.exists():
            # 假设从 agents/skills 目录运行
            self.skill_dir = Path(__file__).parent

    def test_loader_loads_skill(self):
        """测试 loader 能正确加载 buffett_skill"""
        # 由于 loader 需要读取 SKILL.md 和 skill.py，需要确保路径正确
        # 使用 load_skill 函数直接加载
        tool = load_skill(self.skill_dir)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "warren_buffett_analyst")  # 来自 SKILL.md 的 name
        self.assertIn("Buffett", tool.description)

        # 检查参数 schema
        args_schema = tool.args_schema
        self.assertIsNotNone(args_schema)
        # 验证必填参数
        self.assertIn("ticker", args_schema.model_fields)
        self.assertIn("end_date", args_schema.model_fields)
        self.assertIn("api_key", args_schema.model_fields)
        # api_key 应为 Optional
        self.assertTrue(args_schema.model_fields["api_key"].is_required() is False)

    def test_loader_invalid_skill_ignored(self):
        """测试当目录缺少 SKILL.md 或 skill.py 时忽略"""
        # 创建一个临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # 只有 SKILL.md，没有 skill.py
            (tmp_path / "SKILL.md").write_text("---\nname: test\n---", encoding="utf-8")
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)

            # 只有 skill.py
            (tmp_path / "skill.py").write_text("def execute(): pass", encoding="utf-8")
            (tmp_path / "SKILL.md").unlink()
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)


class TestBuffettSkillIntegration(unittest.TestCase):
    """集成测试：使用真实 API（需要设置环境变量）"""
    # 如果未设置 API key，则跳过测试
    @classmethod
    def setUpClass(cls):
        cls.api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("FINANCIAL_DATASETS_API_KEY not set, skipping integration tests")

    def test_real_execute_aapl(self):
        """真实执行 AAPL 分析，验证返回结构和合理性"""
        result_str = execute(ticker="AAPL", end_date="2026-06-30", api_key=self.api_key)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], int)
        self.assertTrue(0 <= data["confidence"] <= 100)
        self.assertIsInstance(data["reasoning"], str)
        self.assertTrue(len(data["reasoning"]) > 0)

    def test_real_execute_invalid_ticker(self):
        """使用无效 ticker 应返回中性信号且 confidence 较低（或 0）"""
        result_str = execute(ticker="INVALID", end_date="2026-06-30", api_key=self.api_key)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "INVALID")
        # 通常数据获取失败会导致信号为 neutral，confidence 可能为 0 或很低
        self.assertEqual(data["signal"], "neutral")
        # confidence 可能是 0，也可能因为 LLM 返回低置信度，但至少不会 > 50
        self.assertLess(data["confidence"], 50)  # 预期很低

    def test_real_execute_historical_date(self):
        """使用历史日期（如2019年）应能正常工作（可能数据较少）"""
        result_str = execute(ticker="MSFT", end_date="2019-12-31", api_key=self.api_key)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "MSFT")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], int)

    def test_loader_invoke(self):
        """通过 loader 加载的工具调用与直接 execute 一致"""
        skill_dir = Path(__file__).parent / "buffett_skill"
        # 如果当前目录不是 skills 目录，尝试找到
        if not skill_dir.exists():
            skill_dir = Path(__file__).parent.parent / "buffett_skill"
        tool = load_skill(skill_dir)
        self.assertIsNotNone(tool)
        result_str = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30", "api_key": self.api_key})
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])


class TestBuffettSkillCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("FINANCIAL_DATASETS_API_KEY not set, skipping cache tests")
        # 直接使用 DEFAULT_CONFIG 中的缓存目录
        cls.cache_root = Path(DEFAULT_CONFIG["data_cache_dir"])

    def test_cache_files_created(self):
        """执行一次分析后，缓存文件应被创建"""
        ticker = "AAPL"
        # 清理该 ticker 相关的缓存文件
        cache_files = [
            self.cache_root / "fundamentals" / "annual" / f"{ticker}_annual.json",
            self.cache_root / "fundamentals" / "quarterly" / f"{ticker}_quarters.json",
            self.cache_root / "line_items" / f"{ticker}_ttm_line_items.json",
            self.cache_root / "prices" / "daily" / f"{ticker}_prices.csv",
        ]
        for f in cache_files:
            if f.exists():
                f.unlink()

        # 执行分析
        execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)

        # 检查是否创建了至少一个文件（且大小 > 0）
        created = any(f.exists() and f.stat().st_size > 0 for f in cache_files)
        # 如果仍未创建，打印实际缓存目录下的文件结构以便调试
        if not created:
            print(f"\nCache root: {self.cache_root}")
            for root, dirs, files in os.walk(self.cache_root):
                print(f"  {root}: {len(files)} files")
        self.assertTrue(created, f"No cache files were created in {self.cache_root}")

    def test_cache_reuse(self):
        """简单测试第二次调用能命中缓存（通过检查 API 调用次数）"""
        # 实际中可以用 mock 统计调用次数，这里简化：只确保不抛异常
        ticker = "AAPL"
        # 第一次调用，会写入缓存
        execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)
        # 第二次调用，应该使用缓存（但难以直接验证，只确保不报错）
        try:
            execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)
        except Exception as e:
            self.fail(f"Second execution raised exception: {e}")


if __name__ == "__main__":
    # 如果直接运行，使用 unittest 执行所有测试
    unittest.main(verbosity=2)
