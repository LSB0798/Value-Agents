#!/usr/bin/env python3
"""
test_technical_skill.py
全面的 Technical Skill 测试套件
- 单元测试（模拟价格数据）
- 加载器测试
- 集成测试（使用真实价格数据）
- 缓存测试（检查价格缓存文件）
"""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from valueagents.agents.skills.technical_skill.skill import execute
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state


class TestTechnicalSkillUnit(unittest.TestCase):
    """单元测试：模拟价格数据，验证逻辑正确性"""

    def setUp(self):
        # 使用临时缓存避免污染真实缓存
        self.temp_cache_dir = tempfile.mkdtemp()
        self.original_cache_dir = os.environ.get("VALUEAGENTS_CACHE_DIR")
        os.environ["VALUEAGENTS_CACHE_DIR"] = self.temp_cache_dir

    def tearDown(self):
        if os.path.exists(self.temp_cache_dir):
            shutil.rmtree(self.temp_cache_dir)
        if self.original_cache_dir is not None:
            os.environ["VALUEAGENTS_CACHE_DIR"] = self.original_cache_dir
        else:
            os.environ.pop("VALUEAGENTS_CACHE_DIR", None)

    @patch('valueagents.agents.skills.technical_skill.skill.technical_analyst_agent')
    def test_execute_returns_json(self, mock_agent):
        mock_agent.return_value = {
            "data": {
                "analyst_signals": {
                    "technical_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 72,
                            "reasoning": {
                                "trend_following": {"signal": "bullish", "confidence": 70},
                                "mean_reversion": {"signal": "neutral", "confidence": 50},
                                "momentum": {"signal": "bullish", "confidence": 80},
                                "volatility": {"signal": "neutral", "confidence": 50},
                                "statistical_arbitrage": {"signal": "bullish", "confidence": 65}
                            }
                        }
                    }
                }
            }
        }
        result = execute(ticker="AAPL", start_date="2025-01-01", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn("signal", data)
        self.assertIn("confidence", data)
        self.assertIn("reasoning", data)
        self.assertIsInstance(data["confidence"], int)
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])

    @patch('valueagents.agents.skills.technical_skill.skill.technical_analyst_agent')
    def test_execute_fallback_on_missing_signal(self, mock_agent):
        mock_agent.return_value = {"data": {"analyst_signals": {}}}
        result = execute(ticker="AAPL", start_date="2025-01-01", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0.0)

    @patch('valueagents.agents.skills.technical_skill.skill.technical_analyst_agent')
    def test_execute_exception_handling(self, mock_agent):
        mock_agent.side_effect = ValueError("Network error")
        result = execute(ticker="AAPL", start_date="2025-01-01", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertIn("Analysis failed", data["reasoning"])

    def test_build_minimal_agent_state(self):
        state = build_minimal_agent_state("AAPL", end_date="2026-06-30", api_key="test_key", start_date="2025-01-01")
        self.assertEqual(state["data"]["tickers"], ["AAPL"])
        self.assertEqual(state["data"]["end_date"], "2026-06-30")
        self.assertEqual(state["data"]["start_date"], "2025-01-01")
        self.assertEqual(state["api_keys"]["FINANCIAL_DATASETS_API_KEY"], "test_key")

    def test_extract_signal_from_state(self):
        state = {
            "data": {
                "analyst_signals": {
                    "technical_skill": {
                        "AAPL": {
                            "signal": "bearish",
                            "confidence": 65,
                            "reasoning": {"trend": "bearish"}
                        }
                    }
                }
            }
        }
        signal = extract_signal_from_state(state, "technical_skill", "AAPL")
        self.assertEqual(signal["signal"], "bearish")
        self.assertEqual(signal["confidence"], 65)
        state["data"]["analyst_signals"] = {}
        signal = extract_signal_from_state(state, "technical_skill", "AAPL")
        self.assertEqual(signal["signal"], "neutral")
        self.assertEqual(signal["confidence"], 0.0)


class TestTechnicalSkillLoader(unittest.TestCase):
    def setUp(self):
        self.skill_dir = Path(__file__).parent / "technical_skill"
        if not self.skill_dir.exists():
            self.skill_dir = Path(__file__).parent.parent / "technical_skill"

    def test_loader_loads_skill(self):
        tool = load_skill(self.skill_dir)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "technical_analyst")
        self.assertIn("technical", tool.description.lower())
        args_schema = tool.args_schema
        self.assertIn("ticker", args_schema.model_fields)
        self.assertIn("start_date", args_schema.model_fields)
        self.assertIn("end_date", args_schema.model_fields)
        self.assertIn("api_key", args_schema.model_fields)
        self.assertTrue(args_schema.model_fields["api_key"].is_required() is False)

    def test_loader_invalid_skill_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "SKILL.md").write_text("---\nname: test\n---", encoding="utf-8")
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)


class TestTechnicalSkillIntegration(unittest.TestCase):
    """集成测试：使用真实价格数据（需要网络或缓存）"""
    @classmethod
    def setUpClass(cls):
        use_yfinance = os.environ.get("USE_YFINANCE", "true").lower() == "true"
        if not use_yfinance and not os.environ.get("FINANCIAL_DATASETS_API_KEY"):
            raise unittest.SkipTest("No data source available for price data")

    def test_real_execute_aapl(self):
        """真实执行 AAPL 技术分析（过去1年）"""
        result_str = execute(ticker="AAPL", start_date="2025-06-01", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], int)
        self.assertTrue(0 <= data["confidence"] <= 100)
        self.assertIsInstance(data["reasoning"], dict)
        expected_keys = ["trend_following", "mean_reversion", "momentum", "volatility", "statistical_arbitrage"]
        for key in expected_keys:
            self.assertIn(key, data["reasoning"])
            self.assertIn("signal", data["reasoning"][key])
            self.assertIn("confidence", data["reasoning"][key])

    def test_real_execute_insufficient_data(self):
        """数据不足时（少于30天），信号应为中性或置信度较低（<60）"""
        result_str = execute(ticker="AAPL", start_date="2026-06-25", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        if data["signal"] != "neutral":
            self.assertLess(data["confidence"], 60,
                            f"Non-neutral signal with insufficient data should have low confidence, got {data['confidence']}")

    def test_real_execute_invalid_ticker(self):
        """无效 ticker 应返回中性信号和 0 置信度，无论具体错误消息"""
        result_str = execute(ticker="INVALID", start_date="2025-06-01", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertTrue(
            "failed" in data["reasoning"].lower() or "no signal" in data["reasoning"].lower(),
            f"Unexpected reasoning: {data['reasoning']}"
        )

    def test_loader_invoke(self):
        """通过 loader 加载的工具调用与直接 execute 一致"""
        skill_dir = Path(__file__).parent / "technical_skill"
        if not skill_dir.exists():
            skill_dir = Path(__file__).parent.parent / "technical_skill"
        tool = load_skill(skill_dir)
        self.assertIsNotNone(tool)
        result_str = tool.invoke({
            "ticker": "AAPL",
            "start_date": "2025-06-01",
            "end_date": "2026-06-30",
            "api_key": None
        })
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])


class TestTechnicalSkillCache(unittest.TestCase):
    """缓存测试：检查价格缓存文件是否正常"""
    @classmethod
    def setUpClass(cls):
        use_yfinance = os.environ.get("USE_YFINANCE", "true").lower() == "true"
        if not use_yfinance:
            raise unittest.SkipTest("Price cache requires yfinance")
        from valueagents.default_config import DEFAULT_CONFIG
        cls.cache_root = Path(DEFAULT_CONFIG["data_cache_dir"])
        if not cls.cache_root.exists():
            raise unittest.SkipTest("Cache root missing")

    def test_cache_files_exist(self):
        """检查价格缓存文件是否存在（说明之前运行过）"""
        ticker = "AAPL"
        price_file = self.cache_root / "prices" / "daily" / f"{ticker}_prices.csv"
        if not price_file.exists():
            # 尝试查找 .bak
            price_file = self.cache_root / "prices" / "daily" / f"{ticker}_prices.csv.bak"
        self.assertTrue(price_file.exists() and price_file.stat().st_size > 0,
                        f"Price cache file missing: {price_file}")

    def test_cache_reuse(self):
        """第二次调用应正常执行（使用缓存）"""
        ticker = "AAPL"
        try:
            execute(ticker=ticker, start_date="2025-06-01", end_date="2026-06-30", api_key=None)
        except Exception as e:
            self.fail(f"First execution failed: {e}")
        try:
            execute(ticker=ticker, start_date="2025-06-01", end_date="2026-06-30", api_key=None)
        except Exception as e:
            self.fail(f"Second execution failed: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
