#!/usr/bin/env python3
"""
test_jhunjhunwala_skill.py
全面的 Rakesh Jhunjhunwala Skill 测试套件
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

from valueagents.agents.skills.jhunjhunwala_skill.skill import execute
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state


class TestJhunjhunwalaSkillUnit(unittest.TestCase):
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

    @patch('valueagents.agents.skills.jhunjhunwala_skill.skill.rakesh_jhunjhunwala_agent')
    def test_execute_returns_json(self, mock_agent):
        mock_agent.return_value = {
            "data": {
                "analyst_signals": {
                    "jhunjhunwala_skill": {
                        "AAPL": {
                            "signal": "neutral",
                            "confidence": 65.0,
                            "reasoning": "Jhunjhunwala style reasoning"
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

    @patch('valueagents.agents.skills.jhunjhunwala_skill.skill.rakesh_jhunjhunwala_agent')
    def test_execute_fallback_on_missing_signal(self, mock_agent):
        mock_agent.return_value = {"data": {"analyst_signals": {}}}
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0.0)

    @patch('valueagents.agents.skills.jhunjhunwala_skill.skill.rakesh_jhunjhunwala_agent')
    def test_execute_exception_handling(self, mock_agent):
        mock_agent.side_effect = ValueError("Test error")
        result = execute(ticker="INVALID", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertIn("Analysis failed", data["reasoning"])

    def test_build_minimal_agent_state(self):
        state = build_minimal_agent_state("AAPL", "2026-06-30", api_key="test_key")
        self.assertEqual(state["data"]["tickers"], ["AAPL"])

    def test_extract_signal_from_state(self):
        state = {
            "data": {
                "analyst_signals": {
                    "jhunjhunwala_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 80.0,
                            "reasoning": {"test": "ok"}
                        }
                    }
                }
            }
        }
        signal = extract_signal_from_state(state, "jhunjhunwala_skill", "AAPL")
        self.assertEqual(signal["signal"], "bullish")
        state["data"]["analyst_signals"] = {}
        signal = extract_signal_from_state(state, "jhunjhunwala_skill", "AAPL")
        self.assertEqual(signal["signal"], "neutral")


class TestJhunjhunwalaSkillLoader(unittest.TestCase):
    def setUp(self):
        self.skill_dir = Path(__file__).parent / "jhunjhunwala_skill"
        if not self.skill_dir.exists():
            self.skill_dir = Path(__file__).parent.parent / "jhunjhunwala_skill"

    def test_loader_loads_skill(self):
        tool = load_skill(self.skill_dir)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "rakesh_jhunjhunwala_analyst")
        self.assertIn("Jhunjhunwala", tool.description)
        args_schema = tool.args_schema
        self.assertIn("ticker", args_schema.model_fields)
        self.assertIn("end_date", args_schema.model_fields)

    def test_loader_invalid_skill_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "SKILL.md").write_text("---\nname: test\n---", encoding="utf-8")
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)


class TestJhunjhunwalaSkillIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        use_yfinance = os.environ.get("USE_YFINANCE", "false").lower() == "true"
        use_edgar = os.environ.get("USE_EDGAR", "false").lower() == "true"
        has_api_key = bool(os.environ.get("FINANCIAL_DATASETS_API_KEY"))
        if not (use_yfinance or use_edgar or has_api_key):
            raise unittest.SkipTest("No data source available")

    def test_real_execute_aapl(self):
        result_str = execute(ticker="AAPL", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], float)
        self.assertTrue(0 <= data["confidence"] <= 100)
        self.assertIsInstance(data["reasoning"], str)
        self.assertTrue(len(data["reasoning"]) > 0)

    def test_real_execute_invalid_ticker(self):
        result_str = execute(ticker="INVALID", end_date="2026-06-30", api_key=None)
        data = json.loads(result_str)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertTrue("failed" in data["reasoning"].lower() or "no signal" in data["reasoning"].lower())

    def test_loader_invoke(self):
        skill_dir = Path(__file__).parent / "jhunjhunwala_skill"
        if not skill_dir.exists():
            skill_dir = Path(__file__).parent.parent / "jhunjhunwala_skill"
        tool = load_skill(skill_dir)
        self.assertIsNotNone(tool)
        result_str = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30", "api_key": None})
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])


class TestJhunjhunwalaSkillCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        use_yfinance = os.environ.get("USE_YFINANCE", "false").lower() == "true"
        use_edgar = os.environ.get("USE_EDGAR", "false").lower() == "true"
        if not (use_yfinance or use_edgar):
            raise unittest.SkipTest("Need data source to test disk cache")
        from valueagents.default_config import DEFAULT_CONFIG
        cls.cache_root = Path(DEFAULT_CONFIG["data_cache_dir"])
        if not cls.cache_root.exists():
            raise unittest.SkipTest("Cache root missing")

    def test_cache_files_exist(self):
        ticker = "AAPL"
        # Jhunjhunwala uses TTM metrics + annual line items
        quarterly_file = self.cache_root / "fundamentals" / "quarterly" / f"{ticker}_quarters.json"
        line_item_file = self.cache_root / "line_items" / f"{ticker}_annual_line_items.json"
        self.assertTrue(quarterly_file.exists() and quarterly_file.stat().st_size > 0,
                        f"Quarterly cache missing: {quarterly_file}")
        self.assertTrue(line_item_file.exists() and line_item_file.stat().st_size > 0,
                        f"Annual line items missing: {line_item_file}")

    def test_cache_reuse(self):
        ticker = "AAPL"
        try:
            execute(ticker=ticker, end_date="2026-06-30", api_key=None)
        except Exception as e:
            self.fail(f"First execution failed: {e}")
        try:
            execute(ticker=ticker, end_date="2026-06-30", api_key=None)
        except Exception as e:
            self.fail(f"Second execution failed: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
