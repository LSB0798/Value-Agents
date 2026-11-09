# valueagents/agents/src/data/cache.py
import json
import os
import pandas as pd
from valueagents.default_config import DEFAULT_CONFIG
from datetime import datetime
from valueagents.agents.utils.news_schema import NewsItem

def _news_fingerprint(record: dict) -> str:
    """
    从缓存记录中提取 fingerprint。
    - 新记录：直接取 'fingerprint' 字段
    - 旧记录：即时通过 NewsItem.from_dict 计算（缺字段自动补全）
    - 兜底：title + date 拼接
    """
    fp = record.get("fingerprint")
    if fp:
        return fp
    try:
        return NewsItem.from_dict(record).fingerprint()
    except Exception:
        title = (record.get("title") or "").strip().lower()
        date = (record.get("date") or "").strip()
        return f"{title}|{date}"

class Cache:
    """In-memory cache for API responses with optional disk persistence for quarterly data."""

    def __init__(self):
        self._prices_cache: dict[str, list[dict[str, any]]] = {}
        self._financial_metrics_cache: dict[str, list[dict[str, any]]] = {}
        self._line_items_cache: dict[str, list[dict[str, any]]] = {}
        self._insider_trades_cache: dict[str, list[dict[str, any]]] = {}
        self._company_news_cache: dict[str, list[dict[str, any]]] = {}

        # 季度数据缓存目录（基于 DEFAULT_CONFIG）
        self._quarter_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "fundamentals",
            "quarterly"
        )
        os.makedirs(self._quarter_cache_dir, exist_ok=True)

        self._annual_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "fundamentals", "annual"
        )
        os.makedirs(self._annual_cache_dir, exist_ok=True)

        self._edgar_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "fundamentals", "edgar"
        )
        os.makedirs(self._edgar_cache_dir, exist_ok=True)

        self._prices_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "prices", "daily"
        )
        os.makedirs(self._prices_cache_dir, exist_ok=True)

        self._line_items_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"], 
            "line_items")
        os.makedirs(self._line_items_cache_dir, exist_ok=True)

        self._insider_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "insider"
        )
        os.makedirs(self._insider_cache_dir, exist_ok=True)

        self._news_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "news"
        )
        os.makedirs(self._news_cache_dir, exist_ok=True)

        # 🆕 market_cap 独立磁盘缓存目录
        self._market_cap_cache_dir = os.path.join(
            DEFAULT_CONFIG["data_cache_dir"],
            "market_cap"
        )
        os.makedirs(self._market_cap_cache_dir, exist_ok=True)

    def _merge_data(self, existing, new_data, key_field):
        """
        Merge existing and new data, avoiding duplicates.

        key_field 可以是：
        - str: 直接作为 dict key 使用（旧行为，向后兼容）
        - callable(record) -> str: 用函数计算 key（新行为，用于 fingerprint）
        """
        if not existing:
            return list(new_data)

        if callable(key_field):
            existing_keys = {key_field(item) for item in existing}
            merged = list(existing)
            for item in new_data:
                k = key_field(item)
                if k not in existing_keys:
                    existing_keys.add(k)
                    merged.append(item)
            return merged

        # ---- 旧行为：字符串 key ----
        existing_keys = {item[key_field] for item in existing}
        merged = existing.copy()
        merged.extend([item for item in new_data if item[key_field] not in existing_keys])
        return merged

    # ---------- 原有的内存缓存方法 ----------
    def get_prices(self, key: str) -> list[dict[str, any]] | None:
        return self._prices_cache.get(key)

    def set_prices(self, key: str, data: list[dict[str, any]]):
        self._prices_cache[key] = self._merge_data(self._prices_cache.get(key), data, key_field="time")

    def get_financial_metrics(self, key: str) -> list[dict[str, any]] | None:
        return self._financial_metrics_cache.get(key)

    def set_financial_metrics(self, key: str, data: list[dict[str, any]]):
        self._financial_metrics_cache[key] = self._merge_data(self._financial_metrics_cache.get(key), data, key_field="report_period")

    def get_line_items(self, key: str) -> list[dict[str, any]] | None:
        return self._line_items_cache.get(key)

    def set_line_items(self, key: str, data: list[dict[str, any]]):
        self._line_items_cache[key] = self._merge_data(self._line_items_cache.get(key), data, key_field="report_period")

    def get_insider_trades(self, key: str) -> list[dict[str, any]] | None:
        return self._insider_trades_cache.get(key)

    def set_insider_trades(self, key: str, data: list[dict[str, any]]):
        self._insider_trades_cache[key] = self._merge_data(self._insider_trades_cache.get(key), data, key_field="filing_date")

    def get_company_news(self, key: str) -> list[dict[str, any]] | None:
        return self._company_news_cache.get(key)

    def set_company_news(self, key: str, data: list[dict[str, any]]):
        self._company_news_cache[key] = self._merge_data(self._company_news_cache.get(key), data, key_field="date")

    # ---------- 年度数据持久化 ----------
    def get_annual_data(self, ticker: str) -> dict:
        """从磁盘读取该 ticker 的年度数据（含 financials, balance, cashflow）。"""
        file_path = os.path.join(self._annual_cache_dir, f"{ticker}_annual.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and all(k in data for k in ('financials','balance','cashflow')):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading annual data for {ticker}: {e}")
        return {'financials': [], 'balance': [], 'cashflow': []}

    def set_annual_data(self, ticker: str, data: dict) -> None:
        """将年度数据字典写入磁盘（覆盖）。"""
        if not isinstance(data, dict) or not all(k in data for k in ('financials','balance','cashflow')):
            raise ValueError("data must be a dict with keys 'financials', 'balance', 'cashflow'")
        file_path = os.path.join(self._annual_cache_dir, f"{ticker}_annual.json")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing annual data for {ticker}: {e}")

    # ---------- 新增：季度数据持久化 ----------
    def _get_quarter_file_path(self, ticker: str) -> str:
        """返回季度缓存文件的完整路径。"""
        # 清理 ticker，防止非法字符（但一般只有字母数字和点）
        safe_ticker = ticker.replace('/', '_')  # 如果有斜杠
        return os.path.join(self._quarter_cache_dir, f"{safe_ticker}_quarters.json")

    def get_quarters(self, ticker: str) -> list[dict]:
        """
        从磁盘读取该 ticker 的所有季度数据。
        如果文件不存在，返回空列表。
        """
        file_path = self._get_quarter_file_path(ticker)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        # 如果格式不对，返回空并记录日志（这里简单打印）
                        print(f"[Cache] Warning: {file_path} does not contain a list, returning empty.")
                        return []
            except Exception as e:
                print(f"[Cache] Error reading quarter file for {ticker}: {e}")
                return []
        return []

    def set_quarters(self, ticker: str, data: list[dict]):
        """
        将季度数据列表写入磁盘（覆盖写入）。
        调用者负责确保 data 是一个列表，且已去重合并。
        """
        if not isinstance(data, list):
            raise ValueError("data must be a list of dictionaries")
        file_path = self._get_quarter_file_path(ticker)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)  # default=str 处理日期等非序列化类型
        except Exception as e:
            print(f"[Cache] Error writing quarter file for {ticker}: {e}")

    def get_quarterly_data(self, ticker: str) -> dict:
        """从磁盘读取该 ticker 的季度数据字典（含 income, balance, cashflow, ratios）。"""
        file_path = self._get_quarter_file_path(ticker)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and all(k in data for k in ('income','balance','cashflow','ratios')):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading quarterly data for {ticker}: {e}")
        return {'income': [], 'balance': [], 'cashflow': [], 'ratios': []}

    def set_quarterly_data(self, ticker: str, data: dict) -> None:
        """将季度数据字典写入磁盘（覆盖）。"""
        if not isinstance(data, dict) or not all(k in data for k in ('income','balance','cashflow','ratios')):
            raise ValueError("data must be a dict with keys 'income', 'balance', 'cashflow', 'ratios'")
        file_path = self._get_quarter_file_path(ticker)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing quarterly data for {ticker}: {e}")

    def merge_quarters(self, ticker: str, new_quarters: list[dict], key_field: str = "date") -> list[dict]:
        """
        合并现有季度数据和新数据，去重（基于 key_field），并返回合并后的列表。
        同时自动保存到磁盘。
        """
        existing = self.get_quarters(ticker)
        merged = self._merge_data(existing, new_quarters, key_field)
        self.set_quarters(ticker, merged)
        return merged

    # ---------- EDGAR 数据持久化 ----------
    def get_edgar_data(self, ticker: str) -> dict | None:
        file_path = os.path.join(self._edgar_cache_dir, f"{ticker}_edgar.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Cache] Error reading EDGAR data for {ticker}: {e}")
                return None
        return None

    def set_edgar_data(self, ticker: str, data: dict) -> None:
        file_path = os.path.join(self._edgar_cache_dir, f"{ticker}_edgar.json")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing EDGAR data for {ticker}: {e}")

    @staticmethod
    def _df_to_storable(df: pd.DataFrame) -> dict:
        """将 DataFrame 转换为可存储的字典（包含 records 和 index_name）。"""
        if df.empty:
            return {'records': [], 'index_name': 'index'}
        idx_name = df.index.name or 'index'
        reset = df.reset_index()
        records = reset.to_dict('records')
        return {'records': records, 'index_name': idx_name}

    @staticmethod
    def _storable_to_df(stored: dict) -> pd.DataFrame:
        """从存储的字典重建 DataFrame。"""
        records = stored.get('records', [])
        idx_name = stored.get('index_name', 'index')
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if idx_name in df.columns:
            df.set_index(idx_name, inplace=True)
        return df

    # ---------- 价格数据持久化 ----------
    def get_prices_from_cache(self, ticker: str, start_date: str, end_date: str) -> list[dict] | None:
        file_path = os.path.join(self._prices_cache_dir, f"{ticker}_prices.csv")
        if not os.path.exists(file_path):
            return None
        try:
            df = pd.read_csv(file_path)
            # 确保 time 列存在
            if 'time' not in df.columns:
                # 如果列名为 Date，重命名为 time
                if 'Date' in df.columns:
                    df.rename(columns={'Date': 'time'}, inplace=True)
                else:
                    return None
            # 转换为 datetime 以便过滤
            df['time'] = pd.to_datetime(df['time'])
            df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
            # 转换回字符串格式
            df['time'] = df['time'].dt.strftime('%Y-%m-%d')
            if df.empty:
                return None
            return df.to_dict('records')
        except Exception as e:
            print(f"[Cache] Error reading prices for {ticker}: {e}")
            return None

    def set_prices_to_cache(self, ticker: str, prices: list[dict]) -> None:
        if not prices:
            return
        # 读取现有缓存
        existing = self.get_prices_from_cache(ticker, "1970-01-01", "2099-12-31")  # 或直接读取整个文件
        # 合并去重（以 time 为键）
        existing_dict = {p['time']: p for p in existing} if existing else {}
        for p in prices:
            time_key = p['time'] if 'time' in p else p['Date']   # 统一字段名
            existing_dict[time_key] = p
        merged = list(existing_dict.values())
        # 按时间排序
        merged.sort(key=lambda x: x.get('time') or x.get('Date'))
        # 写入 CSV
        file_path = os.path.join(self._prices_cache_dir, f"{ticker}_prices.csv")
        df = pd.DataFrame(merged)
        df.to_csv(file_path, index=False)

    def get_line_items_cache(self, ticker: str, period: str) -> list[dict]:
        file_path = os.path.join(self._line_items_cache_dir, f"{ticker}_{period}_line_items.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading line items for {ticker} ({period}): {e}")
        return []

    def set_line_items_cache(self, ticker: str, period: str, records: list[dict]):
        if not records:
            return
        existing = self.get_line_items_cache(ticker, period)
        merged = self._merge_data(existing, records, key_field="report_period")
        file_path = os.path.join(self._line_items_cache_dir, f"{ticker}_{period}_line_items.json")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(merged, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing line items for {ticker} ({period}): {e}")

    def get_insider_cache(self, ticker: str) -> list[dict]:
        file_path = os.path.join(self._insider_cache_dir, f"{ticker}_insider.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading insider for {ticker}: {e}")
        return []

    def set_insider_cache(self, ticker: str, records: list[dict]):
        if not records:
            return
        existing = self.get_insider_cache(ticker)
        merged = self._merge_data(existing, records, key_field="filing_date")
        file_path = os.path.join(self._insider_cache_dir, f"{ticker}_insider.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(merged, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing insider for {ticker}: {e}")

    def get_news_cache(self, ticker: str) -> list[dict]:
        """从磁盘读取该 ticker 的所有新闻记录。"""
        file_path = os.path.join(self._news_cache_dir, f"{ticker}_news.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading news for {ticker}: {e}")
        return []

    def set_news_cache(self, ticker: str, records: list[dict]) -> None:
        """
        将新闻记录列表写入磁盘（按 fingerprint 合并去重后覆盖）。
        向后兼容：旧记录缺 fingerprint 时会自动计算。
        """
        if not records:
            return
        existing = self.get_news_cache(ticker)
        merged = self._merge_data(existing, records, key_field=_news_fingerprint)
        merged.sort(key=lambda r: (r.get("date", ""), r.get("source_tier", 3)))
        file_path = os.path.join(self._news_cache_dir, f"{ticker}_news.json")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(merged, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing news for {ticker}: {e}")


    # ---------------------------------------------------------------------------
    # 新增：NewsItem 级别的读写接口（Step 5）
    # ---------------------------------------------------------------------------
    def get_news_as_items(self, ticker: str) -> list[NewsItem]:
        """
        读取 ticker 的新闻缓存，转换为 NewsItem 列表。
        旧记录通过 NewsItem.from_dict 自动补全 source_tier / provider 等字段。
        无效记录会被跳过（不抛异常）。
        """
        raw = self.get_news_cache(ticker)
        items: list[NewsItem] = []
        for r in raw:
            try:
                items.append(NewsItem.from_dict(r))
            except Exception as e:
                print(f"[Cache] Skip invalid news record for {ticker}: {e}")
        return items


    def set_news_items(self, ticker: str, items: list[NewsItem]) -> None:
        """
        将 NewsItem 列表写入磁盘（按 fingerprint 合并去重）。
        """
        if not items:
            return
        self.set_news_cache(ticker, [it.to_dict() for it in items])


    # ---------------------------------------------------------------------------
    # 新增：全球新闻缓存（Step 5）
    # 复用 _news_cache_dir，用固定 ticker 名 'GLOBAL' 区分
    # ---------------------------------------------------------------------------
    def _get_global_news_file_path(self) -> str:
        return os.path.join(self._news_cache_dir, "GLOBAL_news.json")


    def get_global_news_cache(self) -> list[dict]:
        """从磁盘读取全球新闻缓存。"""
        file_path = self._get_global_news_file_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[Cache] Error reading global news: {e}")
        return []


    def set_global_news_cache(self, records: list[dict]) -> None:
        """将全球新闻记录写入磁盘（按 fingerprint 合并去重后覆盖）。"""
        if not records:
            return
        existing = self.get_global_news_cache()
        merged = self._merge_data(existing, records, key_field=_news_fingerprint)
        file_path = self._get_global_news_file_path()
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(merged, f, indent=2, default=str)
        except Exception as e:
            print(f"[Cache] Error writing global news: {e}")


    def get_global_news_as_items(self) -> list[NewsItem]:
        """读取全球新闻缓存，转换为 NewsItem 列表。"""
        raw = self.get_global_news_cache()
        items: list[NewsItem] = []
        for r in raw:
            try:
                items.append(NewsItem.from_dict(r))
            except Exception as e:
                print(f"[Cache] Skip invalid global news record: {e}")
        return items


    # ---------- 🆕 market_cap 磁盘缓存 ----------
    def get_market_cap(self, ticker: str, end_date: str) -> float | None:
        """
        读取 (ticker, end_date) 对应的市值缓存。
        找不到返回 None。
        """
        safe_ticker = ticker.replace('/', '_')
        file_path = os.path.join(
            self._market_cap_cache_dir,
            f"{safe_ticker}_{end_date}.json"
        )
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    val = data.get("market_cap")
                    if val is not None:
                        return float(val)
            except Exception as e:
                print(f"[Cache] Error reading market_cap for {ticker} @ {end_date}: {e}")
        return None


    def set_market_cap(self, ticker: str, end_date: str, value: float) -> None:
        """
        写入 (ticker, end_date) 的市值缓存。value 为 None 时跳过。
        """
        if value is None:
            return
        safe_ticker = ticker.replace('/', '_')
        file_path = os.path.join(
            self._market_cap_cache_dir,
            f"{safe_ticker}_{end_date}.json"
        )
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(
                    {"ticker": ticker, "end_date": end_date, "market_cap": float(value)},
                    f, indent=2
                )
        except Exception as e:
            print(f"[Cache] Error writing market_cap for {ticker} @ {end_date}: {e}")


    def set_global_news_items(self, items: list[NewsItem]) -> None:
        """将 NewsItem 列表写入全球新闻缓存。"""
        if not items:
            return
        self.set_global_news_cache([it.to_dict() for it in items])

    def _get_news_file_path(self, ticker: str) -> str:
        """返回新闻缓存文件的完整路径"""
        safe_ticker = ticker.replace('/', '_')
        return os.path.join(self._news_cache_dir, f"{safe_ticker}_news.json")

    def load_news_articles(self, ticker: str) -> dict:
        """
        加载该 ticker 的完整新闻数据（含 articles 列表和元数据）。
        Returns:
            {"ticker": ticker, "last_updated": ..., "articles": [...]}
        """
        file_path = self._get_news_file_path(ticker)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "articles" in data:
                        return data
            except Exception as e:
                print(f"[Cache] Error reading news for {ticker}: {e}")
        return {"ticker": ticker, "last_updated": None, "articles": []}

    def save_news_articles(self, ticker: str, articles: list[dict]) -> None:
        """
        保存新闻文章列表到 JSON 文件（合并去重后覆盖）。
        去重键：url（优先）或 (date, title) 组合。
        """
        existing_data = self.load_news_articles(ticker)
        existing_articles = existing_data.get("articles", [])

        # 建立去重索引
        seen_keys = set()
        for art in existing_articles:
            key = art.get("url") or f"{art.get('date')}_{art.get('title')}"
            seen_keys.add(key)

        merged = list(existing_articles)
        for art in articles:
            key = art.get("url") or f"{art.get('date')}_{art.get('title')}"
            if key not in seen_keys:
                merged.append(art)
                seen_keys.add(key)

        # 按日期降序排序
        merged.sort(key=lambda x: x.get("date", ""), reverse=True)

        output = {
            "ticker": ticker,
            "last_updated": datetime.now().isoformat(),
            "article_count": len(merged),
            "articles": merged,
        }

        file_path = self._get_news_file_path(ticker)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False, default=str)
            print(f"   💾 [Cache] 已保存 {len(merged)} 条新闻到 {file_path}")
        except Exception as e:
            print(f"[Cache] Error writing news for {ticker}: {e}")

_cache = Cache()

def get_cache() -> Cache:
    return _cache