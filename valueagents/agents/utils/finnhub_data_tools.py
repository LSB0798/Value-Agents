# valueagents/agents/utils/finnhub_data_tools.py
import os
import finnhub
from datetime import datetime, timedelta
from langchain_core.tools import tool
from typing import Annotated
from .compress_utils import compress_text, estimate_word_count

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")  # 替换为您的 key
_client = None

def get_finnhub_client():
    global _client
    if _client is None:
        _client = finnhub.Client(api_key=FINNHUB_API_KEY)
    return _client

def _format_finnhub_articles(articles: list, ticker: str, start_date: str, end_date: str) -> str:
    """将 Finnhub 返回的新闻列表格式化为 Markdown 字符串"""
    if not articles:
        return f"No news found for {ticker} between {start_date} and {end_date}"
    lines = [f"## Finnhub News for {ticker}, from {start_date} to {end_date}:\n"]
    for art in articles[:10]:  # 限制条数
        headline = art.get('headline', 'No headline')
        source = art.get('source', 'Unknown')
        summary = art.get('summary', '')
        url = art.get('url', '')
        datetime_ts = art.get('datetime')
        if datetime_ts:
            dt = datetime.fromtimestamp(datetime_ts).strftime('%Y-%m-%d %H:%M')
        else:
            dt = 'Unknown'
        lines.append(f"### {headline} (source: {source}, time: {dt})")
        if summary:
            lines.append(f"Summary: {summary[:300]}...")
        if url:
            lines.append(f"Link: {url}")
        lines.append("")
    return "\n".join(lines)

def _format_finnhub_global_articles(articles: list, start_date: str, end_date: str) -> str:
    """将 Finnhub 返回的全球新闻格式化为原始文本"""
    if not articles:
        return f"No global news found for {end_date}"
    lines = [f"## Finnhub Global Market News (via SPY), from {start_date} to {end_date}:\n"]
    for art in articles[:10]:
        headline = art.get('headline', 'No headline')
        source = art.get('source', 'Unknown')
        summary = art.get('summary', '')
        url = art.get('url', '')
        dt = datetime.fromtimestamp(art.get('datetime', 0)).strftime('%Y-%m-%d %H:%M') if art.get('datetime') else 'Unknown'
        lines.append(f"### {headline} (source: {source}, time: {dt})")
        if summary:
            lines.append(f"Summary: {summary[:300]}...")
        if url:
            lines.append(f"Link: {url}")
        lines.append("")
    return "\n".join(lines)

@tool
def get_finnhub_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve company news for a specific stock using Finnhub API.
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        Formatted string containing news articles.
    """
    client = get_finnhub_client()
    try:
        # 确保日期格式正确
        articles = client.company_news(ticker, _from=start_date, to=end_date)
        raw_text = _format_finnhub_articles(articles, ticker, start_date, end_date)
        # print('[Finnhub News] raw_text : {}'.format(raw_text))
        # 压缩（max_words=200）
        word_count_raw_text = estimate_word_count(raw_text)
        compressed = compress_text(raw_text, 
                                   max_words=max(60, int(word_count_raw_text * 0.5)),
                                   role=f"Finnhub news for {ticker}")
        # print('def get_finnhub_news raw_text length : {}'.format(len(raw_text)))
        # print('def get_finnhub_news raw_text : {}'.format(raw_text))
        # print('def get_finnhub_news compressed length : {}'.format(len(compressed)))
        # print('def get_finnhub_news compressed : {}'.format(compressed))

        # print('[Finnhub News] compressed : {}'.format(compressed))
        # print(f"   🔄 [Finnhub News] Compressed: {len(raw_text)} chars → {len(compressed)} chars")
        return compressed
    except Exception as e:
        print(f"❌ [Finnhub] Error fetching news for {ticker}: {e}")
        return f"Error fetching Finnhub news for {ticker}: {str(e)}"

@tool
def get_finnhub_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 10,
) -> str:
    """
    Retrieve global/macro news using Finnhub by querying market ETFs like SPY.
    """
    start_date = (datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=look_back_days)).strftime("%Y-%m-%d")
    # 用 SPY 作为市场代表，获取市场新闻
    ticker = "SPY"
    client = get_finnhub_client()
    try:
        articles = client.company_news(ticker, _from=start_date, to=curr_date)
        # 限制条数
        articles = articles[:limit]

        raw_text = _format_finnhub_global_articles(articles, start_date, curr_date)
        # print('[Finnhub Global News] raw_text : {}'.format(raw_text))
        # 压缩（max_words=150）
        word_count_raw_text = estimate_word_count(raw_text)
        compressed = compress_text(raw_text, 
                                   max_words=max(60, int(word_count_raw_text * 0.5)),
                                   role="macroeconomic news (Finnhub)")
        # print('def get_finnhub_global_news raw_text length : {}'.format(len(raw_text)))
        # print('def get_finnhub_global_news raw_text : {}'.format(raw_text))
        # print('def get_finnhub_global_news compressed length : {}'.format(len(compressed)))
        # print('def get_finnhub_global_news compressed : {}'.format(compressed))

        # print('[Finnhub Global News] compressed : {}'.format(compressed))
        # print(f"   🔄 [Finnhub Global News] Compressed: {len(raw_text)} chars → {len(compressed)} chars")
        return compressed
    except Exception as e:
        print(f"❌ [Finnhub] Error fetching global news: {e}")
        return f"Error fetching global news from Finnhub: {str(e)}"