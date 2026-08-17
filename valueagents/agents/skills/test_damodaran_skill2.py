#!/usr/bin/env python3
"""
test_damodaran_skill.py
全面的 Aswath Damodaran Skill 测试套件
支持单元测试（模拟）和集成测试（真实 API，需设置环境变量）
"""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from valueagents.agents.skills.damodaran_skill.skill import execute
from valueagents.agents.skills.loader import load_skill
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state

import os
# 设置 API Key（临时测试用）
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"

class TestDamodaranSkillUnit(unittest.TestCase):
    """单元测试：模拟外部依赖，验证逻辑正确性"""

    def setUp(self):
        """每个测试前的准备工作"""
        # 创建临时目录模拟缓存，避免污染真实缓存
        self.temp_cache_dir = tempfile.mkdtemp()
        # 修改默认配置中的缓存路径（通过环境变量）
        self.original_cache_dir = os.environ.get("VALUEAGENTS_CACHE_DIR")
        os.environ["VALUEAGENTS_CACHE_DIR"] = self.temp_cache_dir

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_cache_dir):
            shutil.rmtree(self.temp_cache_dir)
        if self.original_cache_dir is not None:
            os.environ["VALUEAGENTS_CACHE_DIR"] = self.original_cache_dir
        else:
            os.environ.pop("VALUEAGENTS_CACHE_DIR", None)

    @patch('valueagents.agents.skills.damodaran_skill.skill.aswath_damodaran_agent')
    def test_execute_returns_json(self, mock_agent):
        """测试 execute 函数返回有效的 JSON 且包含必要字段"""
        # 模拟 agent 返回状态
        mock_agent.return_value = {
            "data": {
                "analyst_signals": {
                    "damodaran_skill": {
                        "AAPL": {
                            "signal": "bullish",
                            "confidence": 72.5,
                            "reasoning": "Damodaran style reasoning"
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
        self.assertIsInstance(data["confidence"], (int, float))
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])

    @patch('valueagents.agents.skills.damodaran_skill.skill.aswath_damodaran_agent')
    def test_execute_fallback_on_missing_signal(self, mock_agent):
        """测试当 agent 未返回信号时，使用默认中性信号"""
        mock_agent.return_value = {"data": {"analyst_signals": {}}}
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0.0)
        self.assertIn("No signal generated", data["reasoning"])

    @patch('valueagents.agents.skills.damodaran_skill.skill.aswath_damodaran_agent')
    def test_execute_exception_handling(self, mock_agent):
        """测试异常捕获：当 agent 抛出异常时，返回中性信号"""
        mock_agent.side_effect = ValueError("Something went wrong")
        result = execute(ticker="AAPL", end_date="2026-06-30", api_key="fake_key")
        data = json.loads(result)
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertIn("Analysis failed", data["reasoning"])

    def test_build_minimal_agent_state(self):
        """测试状态构建函数"""
        state = build_minimal_agent_state("AAPL", "2026-06-30", api_key="test_key")
        self.assertEqual(state["data"]["tickers"], ["AAPL"])
        self.assertEqual(state["data"]["end_date"], "2026-06-30")
        self.assertEqual(state["api_keys"]["FINANCIAL_DATASETS_API_KEY"], "test_key")
        self.assertEqual(state["metadata"]["show_reasoning"], False)

    def test_extract_signal_from_state(self):
        """测试信号提取函数"""
        state = {
            "data": {
                "analyst_signals": {
                    "damodaran_skill": {
                        "AAPL": {
                            "signal": "bearish",
                            "confidence": 45.0,
                            "reasoning": "Overvalued"
                        }
                    }
                }
            }
        }
        signal = extract_signal_from_state(state, "damodaran_skill", "AAPL")
        self.assertEqual(signal["signal"], "bearish")
        self.assertEqual(signal["confidence"], 45.0)
        self.assertEqual(signal["reasoning"], "Overvalued")

        # 缺失信号
        state["data"]["analyst_signals"] = {}
        signal = extract_signal_from_state(state, "damodaran_skill", "AAPL")
        self.assertEqual(signal["signal"], "neutral")
        self.assertEqual(signal["confidence"], 0.0)
        self.assertEqual(signal["reasoning"], "No signal generated by the skill.")


class TestDamodaranSkillLoader(unittest.TestCase):
    """测试 skill 加载器"""

    def setUp(self):
        self.skill_dir = Path(__file__).parent / "damodaran_skill"
        if not self.skill_dir.exists():
            self.skill_dir = Path(__file__).parent.parent / "damodaran_skill"

    def test_loader_loads_skill(self):
        """测试 loader 能正确加载 damodaran_skill"""
        tool = load_skill(self.skill_dir)
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "aswath_damodaran_analyst")  # 来自 SKILL.md 的 name
        self.assertIn("Damodaran", tool.description)

        # 检查参数 schema
        args_schema = tool.args_schema
        self.assertIsNotNone(args_schema)
        self.assertIn("ticker", args_schema.model_fields)
        self.assertIn("end_date", args_schema.model_fields)
        self.assertIn("api_key", args_schema.model_fields)
        # api_key 应为 Optional
        self.assertTrue(args_schema.model_fields["api_key"].is_required() is False)

    def test_loader_invalid_skill_ignored(self):
        """测试当目录缺少 SKILL.md 或 skill.py 时忽略"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # 只有 SKILL.md，没有 skill.py
            (tmp_path / "SKILL.md").write_text("---\nname: test\n---", encoding="utf-8")
            tool = load_skill(tmp_path)
            self.assertIsNone(tool)


class TestDamodaranSkillIntegration(unittest.TestCase):
    """集成测试：使用真实 API（需要设置环境变量）"""
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
        self.assertIsInstance(data["confidence"], (int, float))
        self.assertTrue(0 <= data["confidence"] <= 100)
        self.assertIsInstance(data["reasoning"], str)
        self.assertTrue(len(data["reasoning"]) > 0)

        # Damodaran 分析应当有较长的推理文字（体现叙事风格）
        self.assertGreater(len(data["reasoning"]), 50)

    def test_real_execute_invalid_ticker(self):
        """使用无效 ticker 应返回中性信号且 confidence 为 0（异常捕获）"""
        result_str = execute(ticker="INVALID", end_date="2026-06-30", api_key=self.api_key)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "INVALID")
        self.assertEqual(data["signal"], "neutral")
        self.assertEqual(data["confidence"], 0)
        self.assertIn("Analysis failed", data["reasoning"])

    def test_real_execute_historical_date(self):
        """使用历史日期（如2019年）应能正常工作（可能数据较少）"""
        result_str = execute(ticker="MSFT", end_date="2019-12-31", api_key=self.api_key)
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "MSFT")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])
        self.assertIsInstance(data["confidence"], (int, float))

    def test_loader_invoke(self):
        """通过 loader 加载的工具调用与直接 execute 一致"""
        skill_dir = Path(__file__).parent / "damodaran_skill"
        if not skill_dir.exists():
            skill_dir = Path(__file__).parent.parent / "damodaran_skill"
        tool = load_skill(skill_dir)
        self.assertIsNotNone(tool)
        result_str = tool.invoke({"ticker": "AAPL", "end_date": "2026-06-30", "api_key": self.api_key})
        data = json.loads(result_str)
        self.assertEqual(data["ticker"], "AAPL")
        self.assertIn(data["signal"], ["bullish", "bearish", "neutral"])


class TestDamodaranSkillCache(unittest.TestCase):
    """测试缓存机制是否按预期工作（使用真实 API 但检查缓存文件）"""
    @classmethod
    def setUpClass(cls):
        cls.api_key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("FINANCIAL_DATASETS_API_KEY not set, skipping cache tests")
        from valueagents.default_config import DEFAULT_CONFIG
        cls.cache_root = Path(DEFAULT_CONFIG["data_cache_dir"])

    def test_cache_files_created(self):
        """执行一次分析后，缓存文件应被创建"""
        ticker = "AAPL"
        # 定义可能的缓存文件路径
        cache_files = [
            self.cache_root / "fundamentals" / "quarterly" / f"{ticker}_quarters.json",
            self.cache_root / "line_items" / f"{ticker}_ttm_line_items.json",
            self.cache_root / "prices" / "daily" / f"{ticker}_prices.csv",
        ]
        # 清理可能存在的旧缓存（可选，为了确保本次创建）
        for f in cache_files:
            if f.exists():
                f.unlink()

        # 执行分析
        execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)

        # 检查是否创建了至少一个文件
        created = any(f.exists() and f.stat().st_size > 0 for f in cache_files)
        self.assertTrue(created, f"No cache files were created in {self.cache_root}")

    def test_cache_reuse(self):
        """简单测试第二次调用能正常执行（不报错），体现缓存复用"""
        ticker = "AAPL"
        # 第一次调用，可能写入缓存
        try:
            execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)
        except Exception as e:
            self.fail(f"First execution failed: {e}")

        # 第二次调用，应该使用缓存，不报异常
        try:
            execute(ticker=ticker, end_date="2026-06-30", api_key=self.api_key)
        except Exception as e:
            self.fail(f"Second execution failed: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
