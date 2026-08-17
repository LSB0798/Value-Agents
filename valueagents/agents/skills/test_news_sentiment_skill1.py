#!/usr/bin/env python
# test_news_sentiment_skill.py
"""
全面测试 News Sentiment Skill 的功能、性能和错误处理。
该 Skill 依赖 LLM 进行情感分类，但测试中会使用 mock 加速。
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import os
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"
# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from valueagents.agents.skills.news_sentiment_skill.skill import execute
from valueagents.agents.src.analysts.news_sentiment import (
    news_sentiment_agent,
    parse_news_text,
    _calculate_confidence_score,
    Sentiment,
)
from valueagents.agents.utils.agent_utils import get_news
from valueagents.agents.src.data.cache import get_cache


class TestNewsSentimentSkill(unittest.TestCase):
    """测试 News Sentiment Skill 的各项功能"""

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

    # -------------------- 1. 解析功能测试 --------------------
    def test_parse_news_text(self):
        """测试新闻文本解析函数"""
        sample = """
## Test News

### Headline 1
This is a summary.
Link: http://example.com

### Headline 2
Another summary with no link.
"""
        articles = parse_news_text(sample)
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Headline 1")
        self.assertEqual(articles[0]["summary"], "This is a summary.")
        self.assertEqual(articles[1]["title"], "Headline 2")
        self.assertEqual(articles[1]["summary"], "Another summary with no link.")
        print("✅ parse_news_text works correctly")

    def test_parse_news_text_empty(self):
        """测试空新闻文本"""
        articles = parse_news_text("")
        self.assertEqual(articles, [])
        articles = parse_news_text("No news found")
        self.assertEqual(articles, [])
        print("✅ parse_news_text handles empty input")

    # -------------------- 2. 置信度计算测试 --------------------
    def test_calculate_confidence_with_confidences(self):
        """测试带有 LLM 置信度的置信度计算"""
        sentiment_confidences = {0: 90, 1: 80, 2: 70}
        total = 3
        bullish = 2
        bearish = 1
        conf = _calculate_confidence_score(
            sentiment_confidences=sentiment_confidences,
            total_signals=total,
            overall_signal="bullish",
            bullish_signals=bullish,
            bearish_signals=bearish,
        )
        # 平均置信度 = (90+80+70)/3 = 80, 优势比例 = 2/3 = 0.6667
        # 预期 = 0.7*80 + 0.3*66.67 = 56 + 20 = 76
        expected = 0.7 * 80 + 0.3 * (2 / 3) * 100
        self.assertAlmostEqual(conf, round(expected, 2))
        print("✅ Confidence calculation with LLM confidences correct")

    def test_calculate_confidence_without_confidences(self):
        """测试没有 LLM 置信度时的置信度计算"""
        conf = _calculate_confidence_score(
            sentiment_confidences={},
            total_signals=5,
            overall_signal="neutral",
            bullish_signals=2,
            bearish_signals=2,
        )
        # 最大计数 = 2, 比例 = 2/5 = 0.4, 期望 = 40
        self.assertEqual(conf, 40.0)
        print("✅ Confidence calculation without LLM confidences correct")

    def test_calculate_confidence_no_signals(self):
        """测试无信号时的置信度"""
        conf = _calculate_confidence_score(
            sentiment_confidences={},
            total_signals=0,
            overall_signal="neutral",
            bullish_signals=0,
            bearish_signals=0,
        )
        self.assertEqual(conf, 0.0)
        print("✅ Confidence calculation with no signals correct")

    # -------------------- 3. 新闻获取与解析集成测试（mock） --------------------
    @patch("valueagents.agents.src.analysts.news_sentiment.get_news")
    @patch("valueagents.agents.src.analysts.news_sentiment.call_llm")
    def test_news_fetch_and_parse_mock(self, mock_call_llm, mock_get_news):
        """测试新闻获取和解析流程（mock 数据）"""
        # 模拟新闻返回
        mock_get_news.invoke.return_value = """
## AAPL News

### Apple Reports Record Revenue
Summary: Apple revenue exceeds expectations.
Link: http://example.com

### Apple Faces Regulatory Scrutiny
Summary: EU investigates Apple's App Store policies.
Link: http://example.com
"""
        # 根据新闻标题内容返回情感（避免 prompt 中的干扰词）
        def side_effect(prompt, model, *args, **kwargs):
            if "Record Revenue" in prompt:
                return Sentiment(sentiment="positive", confidence=85)
            elif "Regulatory Scrutiny" in prompt:
                return Sentiment(sentiment="negative", confidence=75)
            else:
                return Sentiment(sentiment="neutral", confidence=50)
        mock_call_llm.side_effect = side_effect

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
        result_state = news_sentiment_agent(state, agent_id="test_sentiment")
        signals = result_state["data"]["analyst_signals"]["test_sentiment"][self.ticker]
        # 一正一负 → 中性
        self.assertEqual(signals["signal"], "neutral")
        # 置信度: 平均 (85+75)/2=80, 优势比例=1/2=0.5, 期望=0.7*80+0.3*50=56+15=71
        expected = round(0.7 * 80 + 0.3 * (1/2) * 100, 2)
        self.assertAlmostEqual(signals["confidence"], expected)
        reasoning = signals["reasoning"]
        self.assertIn("news_sentiment", reasoning)
        metrics = reasoning["news_sentiment"]["metrics"]
        self.assertEqual(metrics["total_articles"], 2)
        self.assertEqual(metrics["bullish_articles"], 1)
        self.assertEqual(metrics["bearish_articles"], 1)
        self.assertEqual(metrics["neutral_articles"], 0)
        print("✅ News fetch and parse (mock) passed")

    # -------------------- 4. 完整 Skill 执行测试（真实 LLM） --------------------
    def test_skill_execute_real_llm(self):
        """测试 skill.execute() 真实执行（会调用 LLM 进行情感分类）"""
        # 由于会调用 LLM，但新闻数量有限，通常较快。
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

        reasoning = result["reasoning"]
        self.assertIn("news_sentiment", reasoning)
        metrics = reasoning["news_sentiment"]["metrics"]
        self.assertIn("total_articles", metrics)
        self.assertIn("bullish_articles", metrics)
        self.assertIn("bearish_articles", metrics)
        self.assertIn("neutral_articles", metrics)
        self.assertIn("articles_classified_by_llm", metrics)

        print(f"✅ skill.execute() with real LLM completed in {elapsed:.2f}s")
        print(f"   Signal: {result['signal']}, Confidence: {result['confidence']}")

    # -------------------- 5. 缓存性能测试 --------------------
    def test_cache_performance(self):
        """测试缓存是否加速（新闻获取缓存，LLM 仍会调用）"""
        # 第一次执行（可能从网络获取新闻）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        first_time = time.time() - start

        # 第二次执行（新闻可能从缓存读取，但 LLM 仍调用）
        start = time.time()
        execute(self.ticker, self.end_date, api_key=self.api_key)
        cached_time = time.time() - start

        print(f"⏱️  First execution: {first_time:.2f}s")
        print(f"⏱️  Cached execution: {cached_time:.2f}s")
        # 由于新闻获取通常较快，且 LLM 每次都会调用，加速可能有限，但至少不严重退化
        self.assertLess(cached_time, first_time * 1.1)  # 允许 10% 波动

    # -------------------- 6. 多 ticker 测试 --------------------
    def test_multiple_tickers(self):
        """测试多个 ticker 是否能正常执行（仅检查不报错）"""
        tickers = ["AAPL", "MSFT", "GOOGL"]
        for ticker in tickers[:2]:  # 只测前两个，避免耗时
            try:
                result_json = execute(ticker, self.end_date, api_key=self.api_key)
                result = json.loads(result_json)
                self.assertIn("signal", result)
                print(f"✅ {ticker}: signal={result['signal']}")
            except Exception as e:
                self.fail(f"Failed for {ticker}: {e}")

    # -------------------- 7. 错误处理测试 --------------------
    def test_invalid_ticker(self):
        """测试无效 ticker 应返回 neutral 且置信度 0"""
        try:
            result_json = execute("INVALID_TICKER", self.end_date, api_key=self.api_key)
            result = json.loads(result_json)
            self.assertEqual(result["signal"], "neutral")
            self.assertEqual(result["confidence"], 0.0)
            reasoning = result["reasoning"]["news_sentiment"]["metrics"]
            self.assertEqual(reasoning["total_articles"], 0)
            print("✅ Invalid ticker handled correctly")
        except Exception as e:
            self.fail(f"Invalid ticker raised exception: {e}")

    def test_no_news(self):
        """测试极早日期可能无新闻，应返回 neutral 且置信度 0"""
        try:
            result_json = execute(self.ticker, "2000-01-01", api_key=self.api_key)
            result = json.loads(result_json)
            self.assertEqual(result["signal"], "neutral")
            self.assertEqual(result["confidence"], 0.0)
            print("✅ No news scenario handled correctly")
        except Exception as e:
            self.fail(f"No news scenario raised exception: {e}")

    # -------------------- 8. Mock 分类测试（避免真实 LLM） --------------------
    @patch("valueagents.agents.src.analysts.news_sentiment.call_llm")
    def test_classification_with_mock_llm(self, mock_call_llm):
        """测试分类逻辑使用模拟 LLM 返回固定结果"""
        # 准备模拟新闻文本
        mock_news = """
### Positive Headline
Positive summary.

### Negative Headline
Negative summary.

### Neutral Headline
Neutral summary.
"""
        with patch("valueagents.agents.src.analysts.news_sentiment.get_news") as mock_get_news:
            mock_get_news.invoke.return_value = mock_news
            # 模拟 LLM 返回
            def side_effect(prompt, model, *args, **kwargs):
                if "Positive" in prompt:
                    return Sentiment(sentiment="positive", confidence=90)
                elif "Negative" in prompt:
                    return Sentiment(sentiment="negative", confidence=80)
                else:
                    return Sentiment(sentiment="neutral", confidence=70)
            mock_call_llm.side_effect = side_effect

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
            result_state = news_sentiment_agent(state, agent_id="test_mock")
            signals = result_state["data"]["analyst_signals"]["test_mock"][self.ticker]
            # 一正一负一中立 → 中性
            self.assertEqual(signals["signal"], "neutral")
            # 置信度: 平均 (90+80+70)/3=80, 优势比例=max(1,1)/3=1/3≈0.3333
            # 期望=0.7*80+0.3*33.33=56+10=66
            expected = round(0.7 * 80 + 0.3 * (1/3) * 100, 2)
            self.assertAlmostEqual(signals["confidence"], expected)
            metrics = signals["reasoning"]["news_sentiment"]["metrics"]
            self.assertEqual(metrics["total_articles"], 3)
            self.assertEqual(metrics["bullish_articles"], 1)
            self.assertEqual(metrics["bearish_articles"], 1)
            self.assertEqual(metrics["neutral_articles"], 1)
            print("✅ Classification with mock LLM passed")


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
    unittest.main(verbosity=2)
    # 可选：performance_benchmark()