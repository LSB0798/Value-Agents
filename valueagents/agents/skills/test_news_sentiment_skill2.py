#!/usr/bin/env python3
"""
test_news_sentiment_skill.py
全面的 News Sentiment Skill 测试套件
- 单元测试（模拟）
- 加载器测试
- 集成测试（需要 ALPHA_VANTAGE_API_KEY 或模拟）
- 缓存测试（无磁盘缓存，仅检查逻辑）
"""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import os
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from valueagents.agents.skills.news_sentiment_skill.skill import execute
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state


class TestNewsSentimentSkillUnit(unittest.TestCase):
    """单元测试：模拟外部依赖"""

    def setUp(self):
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

    @patch('valueagents.agents.skills.news_sentiment_skill.skill.news_sentiment_agent')
    def test_execute_returns_json(self, mock_agent):
        mock_agent.return_value = {
            "data": {
                "analyst_signals": {
                    "news_sentiment_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 55.0,
                            "reasoning": {"news_sentiment": {"signal": "bullish"}}
                        }
                    }
                }
            }
        }
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn("signal", data)
        self.assertIn("confidence", data)
        self.assertIn("reasoning", data)
        self.assertIsInstance(data["confidence"], float)
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])

    @patch('valueagents.agents.skills.news_sentiment_skill.skill.news_sentiment_agent')
    def test_execute_fallback_on_missing_signal(self, mock_agent):
        mock_agent.return_value = {"data": {"analyst_signals": {}}}
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0.0)

    @patch('valueagents.agents.skills.news_sentiment_skill.skill.news_sentiment_agent')
    def test_execute_exception_handling(self, mock_agent):
        mock_agent.side_effect = ValueError("API key missing")
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertIn("Analysis failed", data["reasoning"])

    def test_build_minimal_agent_state(self):
        state = build_minimal_agent_state("AAPL", "2026-06-30", api_key="test_key")
        self.assertEqual(state["data"]["tickers"], ["AAPL"])
        self.assertEqual(state["data"]["end_date"], "2026-06-30")

    def test_extract_signal_from_state(self):
        state = {
            "data": {
                "analyst_signals": {
                    "news_sentiment_skill": {
                        "AAPL": {
                            "signal": "bearish",
                            "confidence": 30.0,
                            "reasoning": {"news_sentiment": {"signal": "bearish"}}
                        }
                    }
                }
            }
        }
        signal = extract_signal_from_state(state, "news_sentiment_skill", "AAPL")
        self.assertEqual(signal["signal"], "bearish")
        self.assertEqual(signal["confidence"], 30.0)
        state["data"]["analyst_signals"] = {}
        signal = extract_signal_from_state(state, "news_sentiment_skill", "AAPL")
        self.assertEqual(signal["signal"], "neutral")


class TestNewsSentimentSkillLoader(unittest.TestCase):
    def setUp(self):
        self.skill_dir = Path(__file__).parent / "news_sentiment_skill"
        if not self.skill_dir.exists():
            self.skill_dir = Path(__file__).parent.parent / "news_sentiment_skill"

    def test_loader_loads_skill(self):
        tool = load_skill(self.skill_dir)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "news_sentiment_analyst")
        self.assertIn("sentiment", tool.description.lower())
        args_schema = tool.args_schema
        self.assertIn("ticker", args_schema.model_fields)
        self.assertIn("end_date", args_schema.model_fields)

    def test_loader_invalid_skill_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "SKILL.md").write_text("---\nname: test\n---", encoding="utf-8")
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)


class TestNewsSentimentSkillIntegration(unittest.TestCase):
    """集成测试：需要 Alpha Vantage API Key（设置 ALPHA_VANTAGE_API_KEY）"""
    @classmethod
    def setUpClass(cls):
        # 检查是否有 Alpha Vantage API Key
        cls.alpha_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
        if not cls.alpha_key:
            raise unittest.SkipTest("ALPHA_VANTAGE_API_KEY not set, skipping integration tests")

    def test_real_execute_aapl(self):
        result_str = execute(ticker="AAPL", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], float)
        self.assertTrue(0 <= data["confidence"] <= 100)
        self.assertIsInstance(data["reasoning"], dict)
        self.assertIn("news_sentiment", data["reasoning"])
        metrics = data["reasoning"]["news_sentiment"]["metrics"]
        self.assertIn("total_articles", metrics)
        self.assertIn("bullish_articles", metrics)
        self.assertIn("bearish_articles", metrics)

    def test_real_execute_invalid_ticker(self):
        # 无效 ticker 可能仍返回空结果，但应返回中性信号
        result_str = execute(ticker="INVALID", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        # reasoning 可能包含默认信息
        self.assertIsInstance(data["reasoning"], dict)

    def test_loader_invoke(self):
        skill_dir = Path(__file__).parent / "news_sentiment_skill"
        if not skill_dir.exists():
            skill_dir = Path(__file__).parent.parent / "news_sentiment_skill"
        tool = load_skill(skill_dir)
        self.assertIsNotNone(tool)
        result_str = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30", "api_key": None})
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])


class TestNewsSentimentSkillCache(unittest.TestCase):
    """News Sentiment 不依赖磁盘缓存，仅做逻辑验证"""
    def test_no_cache_required(self):
        # 该 Skill 不依赖磁盘缓存，所以无需检查文件
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
