# ValueAgents/valueagents/agents/src/tools/api.py
# git at 20260801
import datetime
import logging
import os
import pandas as pd
import numpy as np
import requests
import time
import inspect
from typing import Any
import json

logger = logging.getLogger(__name__)

from valueagents.agents.src.data.cache import get_cache
from valueagents.agents.src.data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
    CompanyFactsResponse,
)
from valueagents.default_config import DEFAULT_CONFIG

_cache = get_cache()

import yfinance as yf
from secfin import SECClient, Company
import finnhub
import requests

_ALL_LINE_ITEM_FIELDS = [f for f in LineItem.model_fields.keys() if f not in ('ticker', 'report_period', 'period', 'currency')]
# 行项目中的所有数值字段（用于类型转换）

# ------------------------------
# 配置管理（从环境变量读取，默认值）
# ------------------------------
def use_edgar() -> bool:
    return os.environ.get("USE_EDGAR", "false").lower() == "true"

def use_yfinance() -> bool:
    return os.environ.get("USE_YFINANCE", "false").lower() == "true"

_sec_client = None

def get_sec_client():
    global _sec_client
    if _sec_client is None:
        _sec_client = SECClient("ValueAgents research contact@example.com")
    return _sec_client

# ------------------------------
# 辅助函数
# ------------------------------
def _make_api_request(url: str, headers: dict, method: str = "GET", json_data: dict = None, max_retries: int = 3) -> requests.Response:
    for attempt in range(max_retries + 1):
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        else:
            response = requests.get(url, headers=headers)
        if response.status_code == 429 and attempt < max_retries:
            delay = 60 + (30 * attempt)
            time.sleep(delay)
            continue
        return response


def _fetch_yf_prices(ticker: str, start_date: str, end_date: str) -> list[Price] | None:
    cache = get_cache()
    cached_records = cache.get_prices_from_cache(ticker, start_date, end_date)
    if cached_records:
        return [Price(
            ticker=ticker,
            time=rec['time'],        # 改为 'time'
            open=rec['open'],
            high=rec['high'],
            low=rec['low'],
            close=rec['close'],
            volume=rec['volume'],
        ) for rec in cached_records]

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        if hist.empty:
            return None
        prices = []
        for dt, row in hist.iterrows():
            prices.append(Price(
                ticker=ticker,
                time=dt.strftime("%Y-%m-%d"),
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume'],
            ))
        cache.set_prices_to_cache(ticker, [p.model_dump() for p in prices])
        return prices
    except Exception as e:
        print(f"[API] yfinance failed: {e}")
        return None

# ------------------------------
# 价格数据（yfinance，永不付费）
# ------------------------------
def get_prices(ticker: str, start_date: str, end_date: str, api_key: str = None) -> list[Price]:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"
    print(f"[API] get_prices called by {caller} for {ticker} from {start_date} to {end_date}")

    cache_key = f"prices_{ticker}_{start_date}_{end_date}"
    if cached := _cache.get_prices(cache_key):
        return [Price(**p) for p in cached]

    # 始终使用 yfinance（免费）
    # 使用提取的 yfinance 数据获取函数
    prices = _fetch_yf_prices(ticker, start_date, end_date)
    if prices:
        _cache.set_prices(cache_key, [p.model_dump() for p in prices])
        return prices

    # 如果 yfinance 失败且没有启用 EDGAR/yfinance 模式（即 legacy 模式），则尝试付费 API
    if not use_edgar() and not use_yfinance():
        # 回退付费 API（仅当用户明确允许）
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key
        url = f"https://api.financialdatasets.ai/prices/?ticker={ticker}&interval=day&interval_multiplier=1&start_date={start_date}&end_date={end_date}"
        response = _make_api_request(url, headers)
        if response.status_code == 200:
            try:
                price_response = PriceResponse(**response.json())
                prices = price_response.prices
                _cache.set_prices(cache_key, [p.model_dump() for p in prices])
                return prices
            except Exception:
                pass
    return []

# ------------------------------
# 财务指标（EDGAR 优先，TTM 回退 yfinance）
# ------------------------------
def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[FinancialMetrics]:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"
    print(f"[API] get_financial_metrics called by {caller} for {ticker}, end_date={end_date}, period={period}, limit={limit}")

    cache_key = f"financial_metrics_{ticker}_{period}_{end_date}_{limit}"
    if cached := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**m) for m in cached]

    metrics = None
    if use_edgar():
        if period == "annual":
            metrics = _get_financial_metrics_edgar(ticker, end_date, limit)
        elif period == "ttm":
            metrics = _get_financial_metrics_roic_ttm(ticker, end_date, limit)
        if not metrics:
            print("[API] ROIC TTM insufficient or empty, falling back to yfinance")
            metrics = _get_financial_metrics_yf(ticker, end_date, period, limit)

    if use_yfinance() and not metrics:
        metrics = _get_financial_metrics_yf(ticker, end_date, period, limit)

    # 仅在 legacy 模式下（未启用任何免费模式）才尝试付费 API
    if not use_edgar() and not use_yfinance() and not metrics:
        print("[API] No free data available, falling back to paid API")
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key
        url = f"https://api.financialdatasets.ai/financial-metrics/?ticker={ticker}&report_period_lte={end_date}&limit={limit}&period={period}"
        response = _make_api_request(url, headers)
        if response.status_code == 200:
            try:
                metrics_response = FinancialMetricsResponse(**response.json())
                metrics = metrics_response.financial_metrics
            except Exception:
                pass

    if metrics:
        _cache.set_financial_metrics(cache_key, [m.model_dump() for m in metrics])

    # ......................................................................... #
    # 在 get_financial_metrics 中，return metrics 之前添加
    for i, m in enumerate(metrics[:3]):  # 只打印前3个，避免过长
        print(f"  [{i}] report_period={m.report_period}, revenue={m.revenue}, fcf={m.free_cash_flow}, "
            f"market_cap={m.market_cap}, roic={m.return_on_invested_capital}, roe={m.return_on_equity}")
    # ......................................................................... #
    return metrics or []


def _save_yf_annual_to_disk(ticker: str, data: dict) -> None:
    """
    将 yfinance 年度数据合并到磁盘缓存（先读现有，合并去重，再覆盖写入）。
    按 'report_period' 去重。
    """
    cache = get_cache()
    existing = cache.get_annual_data(ticker)
    
    def merge_lists(existing_list, new_list, key='report_period'):
        if not new_list:
            return existing_list
        if not existing_list:
            return new_list
        existing_dict = {item[key]: item for item in existing_list}
        for item in new_list:
            existing_dict[item[key]] = item
        return list(existing_dict.values())
    
    merged = {
        'financials': merge_lists(existing.get('financials', []), data.get('financials', [])),
        'balance': merge_lists(existing.get('balance', []), data.get('balance', [])),
        'cashflow': merge_lists(existing.get('cashflow', []), data.get('cashflow', [])),
    }
    
    cache.set_annual_data(ticker, merged)
    print(f"[Cache] Merged annual data for {ticker}: financials={len(merged['financials'])}, "
          f"balance={len(merged['balance'])}, cashflow={len(merged['cashflow'])}")


def _fetch_yf_financials(ticker: str, limit: int = 10) -> dict[str, any]:
    """从 yfinance 获取年度财务数据，合并缓存后返回规范化数据（DataFrame）。"""
    stock = yf.Ticker(ticker)
    info = stock.info

    # 从 yfinance 获取原始数据
    fin = stock.financials.T.sort_index(ascending=False).head(limit).reset_index()
    fin.rename(columns={'index': 'report_period'}, inplace=True)
    bal = stock.balance_sheet.T.sort_index(ascending=False).head(limit).reset_index()
    bal.rename(columns={'index': 'report_period'}, inplace=True)
    cf = stock.cashflow.T.sort_index(ascending=False).head(limit).reset_index()
    cf.rename(columns={'index': 'report_period'}, inplace=True)

    # 转换为字典列表（用于存储到缓存）
    new_data = {
        'financials': fin.to_dict('records') if not fin.empty else [],
        'balance': bal.to_dict('records') if not bal.empty else [],
        'cashflow': cf.to_dict('records') if not cf.empty else [],
        'info': info,
    }

    # 合并到磁盘缓存（缓存存储为字典列表）
    _save_yf_annual_to_disk(ticker, new_data)

    # 从缓存读取合并后的完整数据（字典列表）
    cache = get_cache()
    merged = cache.get_annual_data(ticker)   # 返回 {'financials': [...], 'balance': [...], 'cashflow': [...]}
    merged['info'] = info

    # ---------- 将字典列表转换为 DataFrame，并设置索引 ----------
    def _to_df(data_list: list[dict]) -> pd.DataFrame:
        if not data_list:
            return pd.DataFrame()
        df = pd.DataFrame(data_list)
        if 'report_period' in df.columns:
            # 去重：保留最后一个记录（通常最新）
            df = df.drop_duplicates(subset='report_period', keep='last')
            df.set_index('report_period', inplace=True)
            df.index = pd.to_datetime(df.index).strftime('%Y-%m-%d')
            df.sort_index(ascending=False, inplace=True)
        return df

    merged['financials'] = _to_df(merged['financials'])
    merged['balance'] = _to_df(merged['balance'])
    merged['cashflow'] = _to_df(merged['cashflow'])

    return merged


def _fetch_yf_financials_v0(ticker: str, limit: int = 10) -> dict[str, any]:
    """从 yfinance 获取年度财务数据，合并缓存后返回完整数据。"""
    stock = yf.Ticker(ticker)
    info = stock.info
    # 重置索引，将日期变为列 'report_period'
    fin = stock.financials.T.sort_index(ascending=False).head(limit).reset_index()
    fin.rename(columns={'index': 'report_period'}, inplace=True)
    bal = stock.balance_sheet.T.sort_index(ascending=False).head(limit).reset_index()
    bal.rename(columns={'index': 'report_period'}, inplace=True)
    cf = stock.cashflow.T.sort_index(ascending=False).head(limit).reset_index()
    cf.rename(columns={'index': 'report_period'}, inplace=True)

    new_data = {
        'financials': fin.to_dict('records') if not fin.empty else [],
        'balance': bal.to_dict('records') if not bal.empty else [],
        'cashflow': cf.to_dict('records') if not cf.empty else [],
        'info': info,
    }

    _save_yf_annual_to_disk(ticker, new_data)

    cache = get_cache()
    merged = cache.get_annual_data(ticker)
    merged['info'] = info

    return merged

# ------------------------------
# yfinance 实现（保留）
# ------------------------------
def _get_financial_metrics_yf(ticker, end_date, period, limit):
    print(f"[YF] _get_financial_metrics_yf called for {ticker}")
    yf_data = _fetch_yf_financials(ticker, limit)
    info = yf_data['info']

    fin = yf_data['financials']
    bal = yf_data['balance']
    cf = yf_data['cashflow']

    metrics_list = []
    yearly_records = []   # 用于计算增长率

    common_index = fin.index.intersection(bal.index).intersection(cf.index)
    for idx in common_index:
        # report_period = idx.strftime("%Y-%m-%d")
        report_period = idx
        revenue = fin.loc[idx, 'Total Revenue'] if 'Total Revenue' in fin.columns else None
        net_income = fin.loc[idx, 'Net Income'] if 'Net Income' in fin.columns else None
        ebit = fin.loc[idx, 'EBIT'] if 'EBIT' in fin.columns else None
        interest_expense = fin.loc[idx, 'Interest Expense'] if 'Interest Expense' in fin.columns else None
        total_debt = bal.loc[idx, 'Total Debt'] if 'Total Debt' in bal.columns else None
        shareholders_equity = bal.loc[idx, 'Total Equity Gross Minority Interest'] if 'Total Equity Gross Minority Interest' in bal.columns else None
        free_cash_flow = cf.loc[idx, 'Free Cash Flow'] if 'Free Cash Flow' in cf.columns else None

        # 计算比率
        roe = net_income / shareholders_equity if (net_income and shareholders_equity) else None
        debt_to_equity = total_debt / shareholders_equity if (total_debt and shareholders_equity) else None

        # 从 info 获取指标
        beta = info.get('beta')
        pe = info.get('trailingPE')
        market_cap = info.get('marketCap')
        # 获取 price_to_book（尝试多个键名）
        price_to_book = info.get('priceToBook') or info.get('priceToBookTrailing12Months') or info.get('price_to_book')
        # 获取 price_to_sales（尝试多个键名）
        price_to_sales = info.get('priceToSalesTrailing12Months') or info.get('priceToSales') or info.get('price_to_sales')
        # 如果仍为 None，用市值和营收计算（近似）
        if price_to_sales is None and market_cap and revenue:
            price_to_sales = market_cap / revenue

        # 获取 current_assets 和 current_liabilities（列名可能不同）
        current_assets = None
        current_liabilities = None
        if 'Current Assets' in bal.columns:
            current_assets = bal.loc[idx, 'Current Assets']
        elif 'current_assets' in bal.columns:
            current_assets = bal.loc[idx, 'current_assets']
        if 'Current Liabilities' in bal.columns:
            current_liabilities = bal.loc[idx, 'Current Liabilities']
        elif 'current_liabilities' in bal.columns:
            current_liabilities = bal.loc[idx, 'current_liabilities']

        # 计算净利率、营业利润率、流动比率
        net_margin = net_income / revenue if (net_income and revenue) else None
        operating_margin = ebit / revenue if (ebit and revenue) else None
        current_ratio = current_assets / current_liabilities if (current_assets and current_liabilities) else None

        # 获取 gross_profit（如果存在）
        gross_profit = None
        if 'Gross Profit' in fin.columns:
            gross_profit = fin.loc[idx, 'Gross Profit']
        elif 'gross_profit' in fin.columns:
            gross_profit = fin.loc[idx, 'gross_profit']
        gross_margin = gross_profit / revenue if (gross_profit and revenue) else None

        # 获取 shares_outstanding（从 info 或行内）
        # shares_outstanding = stock.info.get('sharesOutstanding')
        shares_outstanding = info.get('sharesOutstanding')

        # 构建字段
        fields = {field: None for field in FinancialMetrics.model_fields.keys()}
        fields.update({
            'ticker': ticker,
            'report_period': report_period,
            'period': period if period else "ttm",
            'currency': "USD",
            'revenue': revenue,
            'net_income': net_income,
            'free_cash_flow': free_cash_flow,
            'ebit': ebit,
            'interest_expense': interest_expense,
            'total_debt': total_debt,
            'shareholders_equity': shareholders_equity,
            'return_on_equity': roe,
            'debt_to_equity': debt_to_equity,
            'beta': beta,
            'price_to_earnings_ratio': pe,
            'market_cap': market_cap,
            'ev_to_ebit': None,
            'price_to_book_ratio': price_to_book,
            'price_to_sales_ratio': price_to_sales,
            'gross_margin': gross_margin,
            'net_margin': net_margin,
            'operating_margin': operating_margin,
            'current_ratio': current_ratio,
            'free_cash_flow_per_share': free_cash_flow / shares_outstanding if (free_cash_flow and shares_outstanding) else None,
            'earnings_per_share': net_income / shares_outstanding if (net_income and shares_outstanding) else None,
            'book_value_per_share': shareholders_equity / shares_outstanding if (shareholders_equity and shares_outstanding) else None,
        })

        # 记录 yearly_records 用于计算增长率
        yearly_records.append({
            'yr': pd.to_datetime(report_period).year,
            'revenue': revenue,
            'net_income': net_income,
            'equity': shareholders_equity,
            'fcf': free_cash_flow,
            'eps': fields['earnings_per_share'],
        })

        metrics_list.append(FinancialMetrics(**fields))

    # 计算增长率
    if yearly_records:
        _compute_growth_rates(metrics_list, yearly_records)

    return metrics_list


def _fetch_edgar_annual_data(ticker: str) -> dict[str, pd.DataFrame]:
    """
    从 SEC EDGAR 获取年度财报数据（利润表、资产负债表、现金流量表）。
    优先使用持久化缓存，若不存在则从 SEC 获取并缓存。
    """
    cache = get_cache()
    cached = cache.get_edgar_data(ticker)
    if cached and all(k in cached for k in ('income','balance','cashflow')):
        return {
            'income': cache._storable_to_df(cached['income']),
            'balance': cache._storable_to_df(cached['balance']),
            'cashflow': cache._storable_to_df(cached['cashflow']),
        }
    
    # 调用 SEC
    client = get_sec_client()
    company = Company(ticker, client)
    income_df = company.get_income_statement().to_dataframe()
    balance_df = company.get_balance_sheet().to_dataframe()
    cashflow_df = company.get_cash_flow().to_dataframe()
    
    # 存储缓存
    cache.set_edgar_data(ticker, {
        'income': cache._df_to_storable(income_df),
        'balance': cache._df_to_storable(balance_df),
        'cashflow': cache._df_to_storable(cashflow_df),
    })
    
    return {
        'income': income_df,
        'balance': balance_df,
        'cashflow': cashflow_df,
    }

# ------------------------------
# EDGAR 年度实现（仅 annual）
# ------------------------------
def _get_financial_metrics_edgar(ticker: str, end_date: str, limit: int) -> list[FinancialMetrics]:
    edgar_data = _fetch_edgar_annual_data(ticker)
    income_df = edgar_data['income']
    balance_df = edgar_data['balance']
    cashflow_df = edgar_data['cashflow']

    if income_df.empty:
        return []

    income_df.index = pd.to_datetime(income_df.index)
    balance_df.index = pd.to_datetime(balance_df.index)
    cashflow_df.index = pd.to_datetime(cashflow_df.index)

    annual_income = income_df.groupby(income_df.index.year).last()
    annual_balance = balance_df.groupby(balance_df.index.year).last()
    annual_cashflow = cashflow_df.groupby(cashflow_df.index.year).last()

    years = sorted(annual_income.index, reverse=True)[:limit]

    # stock = yf.Ticker(ticker)
    # info = stock.info
    # ---------- 新增重试逻辑 ----------
    max_retries = 2  # 首次尝试 + 1次重试
    info = None
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            break  # 成功则跳出
        except Exception as e:
            print(f"[EDGAR] Failed to fetch yfinance info for {ticker} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"[EDGAR] Waiting 60 seconds before retry...")
                time.sleep(60)
            else:
                # 最后一次尝试失败，抛出异常
                raise RuntimeError(f"Failed to fetch yfinance info for {ticker} after {max_retries} attempts") from e
    # ---------- 重试逻辑结束 ----------

    beta = info.get('beta')
    current_market_cap = info.get('marketCap')

    roic_by_year = _get_roic_from_api(ticker, limit=limit)
    pe_by_year = _get_finnhub_pe_series(ticker, limit=limit)

    metrics_list = []
    yearly_records = []
    
    for yr in years:
        report_period = f"{yr}-12-31"
        revenue = annual_income.loc[yr, 'revenue'] if 'revenue' in annual_income.columns else None
        net_income = annual_income.loc[yr, 'net_income'] if 'net_income' in annual_income.columns else None
        ebit = annual_income.loc[yr, 'operating_income'] if 'operating_income' in annual_income.columns else annual_income.loc[yr, 'ebit'] if 'ebit' in annual_income.columns else None
        interest_expense = annual_income.loc[yr, 'interest_expense'] if 'interest_expense' in annual_income.columns else None
        total_debt = annual_balance.loc[yr, 'total_debt'] if 'total_debt' in annual_balance.columns else annual_balance.loc[yr, 'long_term_debt'] if 'long_term_debt' in annual_balance.columns else None
        shareholders_equity = annual_balance.loc[yr, 'stockholders_equity'] if 'stockholders_equity' in annual_balance.columns else None

        # FCFF
        if 'free_cash_flow' in annual_cashflow.columns:
            free_cash_flow = annual_cashflow.loc[yr, 'free_cash_flow']
        else:
            ocf = annual_cashflow.loc[yr, 'operating_cash_flow'] if 'operating_cash_flow' in annual_cashflow.columns else None
            capex = annual_cashflow.loc[yr, 'capital_expenditures'] if 'capital_expenditures' in annual_cashflow.columns else None
            free_cash_flow = ocf - abs(capex) if (ocf is not None and capex is not None) else None

        roe = net_income / shareholders_equity if (net_income and shareholders_equity) else None
        debt_to_equity = total_debt / shareholders_equity if (total_debt and shareholders_equity) else None

        # ROIC
        roic = None
        if roic_by_year and yr in roic_by_year:
            roic = roic_by_year[yr] / 100.0

        # 历史市值
        historical_market_cap = None
        shares_outstanding = None
        if 'shares_outstanding' in annual_income.columns:
            shares_outstanding = annual_income.loc[yr, 'shares_outstanding']
        else:
            shares_outstanding = stock.info.get('sharesOutstanding')
        if shares_outstanding:
            try:
                start = pd.to_datetime(report_period)
                end = start + pd.Timedelta(days=5)
                if start > pd.Timestamp.today():
                    historical_market_cap = current_market_cap
                    return
                hist = stock.history(start=start.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'))
                if not hist.empty:
                    close_price = hist['Close'].iloc[-1]
                    historical_market_cap = close_price * shares_outstanding
            except:
                pass
        if historical_market_cap is None:
            historical_market_cap = current_market_cap

        # PE
        pe = pe_by_year.get(yr) if pe_by_year else info.get('trailingPE')

        # 现金
        cash = annual_balance.loc[yr, 'cash'] if 'cash' in annual_balance.columns else 0
        if pd.isna(cash):
            cash = 0

        fields = {field: None for field in FinancialMetrics.model_fields.keys()}
        ev = historical_market_cap + total_debt - cash if historical_market_cap is not None and total_debt is not None else None
        ev_to_ebit = (ev / ebit) if (ev is not None and ebit and ebit != 0) else None
        fields.update({
            'ticker': ticker,
            'report_period': report_period,
            'period': 'annual',
            'currency': 'USD',
            'revenue': revenue,
            'net_income': net_income,
            'free_cash_flow': free_cash_flow,
            'ebit': ebit,
            'interest_expense': interest_expense,
            'total_debt': total_debt,
            'shareholders_equity': shareholders_equity,
            'return_on_equity': roe,
            'debt_to_equity': debt_to_equity,
            'return_on_invested_capital': roic,
            'beta': beta,
            'price_to_earnings_ratio': pe,
            'market_cap': historical_market_cap,
            'enterprise_value': ev,
            'ev_to_ebit': ev_to_ebit,
        })

        # 补充字段（毛利率、净利率等）
        if revenue:
            fields['net_margin'] = net_income / revenue if net_income else None
            fields['operating_margin'] = ebit / revenue if ebit else None
            if 'gross_profit' in annual_income.columns:
                gross_profit = annual_income.loc[yr, 'gross_profit']
                fields['gross_margin'] = gross_profit / revenue if gross_profit else None

        if 'current_assets' in annual_balance.columns and 'current_liabilities' in annual_balance.columns:
            current_assets = annual_balance.loc[yr, 'current_assets']
            current_liabilities = annual_balance.loc[yr, 'current_liabilities']
            fields['current_ratio'] = current_assets / current_liabilities if current_liabilities else None

        if shares_outstanding:
            fields['free_cash_flow_per_share'] = free_cash_flow / shares_outstanding if free_cash_flow else None
            fields['earnings_per_share'] = net_income / shares_outstanding if net_income else None
            fields['book_value_per_share'] = shareholders_equity / shares_outstanding if shareholders_equity else None

        if historical_market_cap:
            if shareholders_equity:
                fields['price_to_book_ratio'] = historical_market_cap / shareholders_equity
            if revenue:
                fields['price_to_sales_ratio'] = historical_market_cap / revenue

        # 股息支付率
        if 'dividends_paid' in annual_cashflow.columns:
            dividends_paid = annual_cashflow.loc[yr, 'dividends_paid']
            if dividends_paid and net_income:
                fields['payout_ratio'] = dividends_paid / net_income

        # 利息覆盖
        if ebit and interest_expense and interest_expense != 0:
            fields['interest_coverage'] = ebit / interest_expense

        # FCF yield
        if free_cash_flow and historical_market_cap:
            fields['free_cash_flow_yield'] = free_cash_flow / historical_market_cap

        # EV/EBITDA 近似
        if ebit and fields.get('enterprise_value'):
            fields['enterprise_value_to_ebitda_ratio'] = fields['enterprise_value'] / ebit

        metrics_list.append(FinancialMetrics(**fields))

        yearly_records.append({
            'yr': yr,
            'revenue': revenue,
            'net_income': net_income,
            'equity': shareholders_equity,
            'fcf': free_cash_flow,
            'eps': fields['earnings_per_share'],
        })

    # 计算增长率
    _compute_growth_rates(metrics_list, yearly_records)

    return metrics_list

def _compute_growth_rates(metrics_list: list[FinancialMetrics], yearly_records: list):
    if len(yearly_records) < 2:
        return
    yearly_records.sort(key=lambda r: r['yr'])
    metrics_by_year = {m.report_period[:4]: m for m in metrics_list}
    for i in range(1, len(yearly_records)):
        prev = yearly_records[i-1]
        curr = yearly_records[i]

        yr_str = str(curr['yr'])
        m = metrics_by_year.get(yr_str)
        if not m:
            continue
        if prev['revenue'] and prev['revenue'] != 0:
            m.revenue_growth = (curr['revenue'] - prev['revenue']) / prev['revenue']
        if prev['net_income'] and prev['net_income'] != 0:
            m.earnings_growth = (curr['net_income'] - prev['net_income']) / prev['net_income']
        if prev['equity'] and prev['equity'] != 0:
            m.book_value_growth = (curr['equity'] - prev['equity']) / prev['equity']
        if prev['fcf'] and prev['fcf'] != 0 and curr['fcf'] is not None:
            m.free_cash_flow_growth = (curr['fcf'] - prev['fcf']) / prev['fcf']
        if prev['eps'] and prev['eps'] != 0 and curr['eps'] is not None:
            m.earnings_per_share_growth = (curr['eps'] - prev['eps']) / prev['eps']
        if m.earnings_per_share_growth and m.earnings_per_share_growth != 0 and m.price_to_earnings_ratio:
            m.peg_ratio = m.price_to_earnings_ratio / (m.earnings_per_share_growth * 100)


# ------------------------------
# ROIC API 请求（用于 TTM）
# ------------------------------
def _roic_request(endpoint: str, params: dict, retries=3, delay=12) -> dict | None:
    time.sleep(30)
    api_key = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
    if not api_key:
        return None
    url = f"https://api.roic.ai/v2/fundamental/{endpoint}"
    params["apikey"] = api_key
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                time.sleep(delay * (attempt + 1))
                continue
            else:
                return None
        except Exception:
            time.sleep(delay)
            continue
    return None

def _save_roic_quarters_to_disk(ticker: str, data: dict) -> None:
    """
    将季度数据合并到磁盘缓存（先读现有，合并去重，再覆盖写入）。
    """
    cache = get_cache()
    existing = cache.get_quarterly_data(ticker)
    
    # 定义合并函数（按 date 去重，新数据覆盖旧数据）
    def merge_lists(existing_list, new_list, key='date'):
        if not new_list:
            return existing_list
        if not existing_list:
            return new_list
        existing_dict = {item[key]: item for item in existing_list}
        for item in new_list:
            existing_dict[item[key]] = item
        return list(existing_dict.values())
    
    merged = {
        'income': merge_lists(existing.get('income', []), data.get('income', [])),
        'balance': merge_lists(existing.get('balance', []), data.get('balance', [])),
        'cashflow': merge_lists(existing.get('cashflow', []), data.get('cashflow', [])),
        'ratios': merge_lists(existing.get('ratios', []), data.get('ratios', [])),
    }

    # 写入缓存（覆盖）
    cache.set_quarterly_data(ticker, merged)
    
    # 打印合并后的数量，便于观察累积情况
    print(f"[Cache] Merged quarterly data for {ticker}: income={len(merged['income'])}, "
          f"balance={len(merged['balance'])}, cashflow={len(merged['cashflow'])}, "
          f"ratios={len(merged['ratios'])}")
    

def _fetch_roic_quarters(ticker: str, limit: int) -> dict[str, list[dict]]:
    """
    获取季度数据（利润表、资产负债表、现金流量表、比率）。
    1. 从 API 获取最新数据。
    2. 合并存储到缓存（增量更新）。
    3. 返回合并后的完整数据。
    """
    # 1. 从 API 获取原始数据
    income = _roic_request(f"income-statement/{ticker}", {"period": "quarterly", "limit": limit, "order": "DESC"})
    balance = _roic_request(f"balance-sheet/{ticker}", {"period": "quarterly", "limit": limit, "order": "DESC"})
    cashflow = _roic_request(f"cash-flow/{ticker}", {"period": "quarterly", "limit": limit, "order": "DESC"})
    ratios = _roic_request(f"ratios/profitability/{ticker}", {"period": "quarterly", "limit": limit, "order": "DESC"})
    
    new_data = {
        'income': income if income else [],
        'balance': balance if balance else [],
        'cashflow': cashflow if cashflow else [],
        'ratios': ratios if ratios else [],
    }
    
    # 2. 合并存储（增量更新）
    _save_roic_quarters_to_disk(ticker, new_data)
    
    # 3. 从缓存读取合并后的完整数据并返回
    cache = get_cache()
    merged = cache.get_quarterly_data(ticker)
    return merged

def _get_financial_metrics_roic_ttm(ticker: str, end_date: str, limit: int) -> list[FinancialMetrics]:
    """
    从 ROIC API 获取季度数据并合成 TTM（最近 4 个季度累加）。
    返回最多 limit 个 TTM 数据点（每个季度末对应一个 TTM）。
    同时计算 EPS、FCF per share、市销率、FCF 收益率、账面价值 per share、市净率、企业价值等。

    TODO: [Data Cache] 当前 ROIC 仅提供最近 7 个季度数据，导致合成的 TTM 点不足 5 个，
        无法计算同比增长率（如 revenue_growth, earnings_growth 等字段）。
        影响：依赖这些字段的分析师（如 fundamentals_analyst_agent）将无法获得增长信号，
        导致评分降低或信号偏保守。
        解决方案：建立本地数据缓存，随时间推移积累更多历史季度数据，
        当可用季度数 >= 9 时（可合成至少 5 个 TTM 点），增长率将自动计算填充。
        当前在数据不足时，以下字段将保持 None。
    """
    # 需要获取足够多的季度数据（limit + 3 因为需要前推 3 个季度）
    q_limit = limit + 3
    # 调用封装好的 API 访问函数
    roic_data = _fetch_roic_quarters(ticker, q_limit)
    income    = roic_data['income']
    balance   = roic_data['balance']
    cashflow  = roic_data['cashflow']
    ratios    = roic_data['ratios']

    if not income or not balance or not cashflow:
        return []

    # 按日期对齐
    dates = sorted(set(inc['date'] for inc in income) & set(bal['date'] for bal in balance) & set(cf['date'] for cf in cashflow))
    if len(dates) < 4:
        return []

    inc_by_date = {i['date']: i for i in income}
    bal_by_date = {b['date']: b for b in balance}
    cf_by_date = {c['date']: c for c in cashflow}
    rat_by_date = {r['date']: r for r in ratios} if ratios else {}

    # 获取 yfinance Ticker 对象，用于获取历史价格和市值
    stock = yf.Ticker(ticker)
    info = stock.info

    metrics = []
    dates_asc = sorted(dates)
    for i in range(3, len(dates_asc)):
        dt = dates_asc[i]
        window_dates = dates_asc[i-3:i+1]
        inc_window = [inc_by_date[d] for d in window_dates]
        cf_window = [cf_by_date[d] for d in window_dates]
        bal_latest = bal_by_date[dt]
        rat_latest = rat_by_date.get(dt, {})

        # ----- TTM 流量值（利润表、现金流量表） -----
        ttm_revenue = sum(w.get('is_sales_revenue_turnover', 0) for w in inc_window)
        ttm_net_income = sum(w.get('is_net_income', 0) for w in inc_window)
        ttm_ebit = sum(w.get('is_oper_income', 0) for w in inc_window)
        ttm_fcf = sum(w.get('cf_free_cash_flow', 0) for w in cf_window)
        ttm_ebitda = sum(w.get('ebitda', 0) for w in inc_window)  # ROIC 利润表有 ebitda

        # ----- 时点值（资产负债表） -----
        shares = bal_latest.get('bs_sh_out')
        equity = bal_latest.get('bs_total_equity')
        total_assets = bal_latest.get('bs_tot_asset')
        total_liabilities = bal_latest.get('bs_tot_liab')
        cash = bal_latest.get('bs_cash_near_cash_item')
        current_assets = bal_latest.get('bs_cur_asset_report')
        current_liab = bal_latest.get('bs_cur_liab')
        # 总债务 = 长期借款 + 短期借款
        lt_debt = bal_latest.get('bs_lt_borrow', 0)
        st_debt = bal_latest.get('bs_st_borrow', 0)
        total_debt = lt_debt + st_debt if (lt_debt is not None and st_debt is not None) else None

        # ----- 比率（从 ROIC 的比率端点获取，这些值通常已是 TTM 比率） -----
        roe = rat_latest.get('return_com_eqy', 0) / 100 if rat_latest else None
        roic = rat_latest.get('return_on_inv_capital', 0) / 100 if rat_latest else None
        operating_margin = rat_latest.get('oper_margin', 0) / 100 if rat_latest else None
        net_margin = rat_latest.get('profit_margin', 0) / 100 if rat_latest else None
        gross_margin = rat_latest.get('gross_margin', 0) / 100 if rat_latest else None

        # ----- 计算派生字段（TTM 每股指标和估值比率） -----
        # 获取报告期当日的收盘价（用于历史市值）
        try:
            # 获取报告期后一两个交易日的价格（报告期可能非交易日）
            start = dt
            end = (pd.to_datetime(dt) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            hist = stock.history(start=start, end=end)
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                price = info.get('currentPrice', info.get('regularMarketPrice'))
        except:
            price = info.get('currentPrice', info.get('regularMarketPrice'))

        if price is not None and shares is not None:
            historical_market_cap = price * shares
        else:
            historical_market_cap = info.get('marketCap')

        # 计算 EPS, FCF per share
        eps = ttm_net_income / shares if (ttm_net_income and shares) else None
        fcf_ps = ttm_fcf / shares if (ttm_fcf and shares) else None
        bvps = equity / shares if (equity and shares) else None

        # 估值比率
        ps_ratio = historical_market_cap / ttm_revenue if (historical_market_cap and ttm_revenue) else None
        fcf_yield = ttm_fcf / historical_market_cap if (ttm_fcf and historical_market_cap) else None
        pb_ratio = historical_market_cap / equity if (historical_market_cap and equity) else None
        ev = historical_market_cap + total_debt - cash if (historical_market_cap is not None and total_debt is not None and cash is not None) else None

        # 其他比率
        current_ratio = current_assets / current_liab if (current_assets and current_liab) else None
        debt_to_equity = total_debt / equity if (total_debt and equity) else None
        # 计算 PEG（需要市盈率和盈利增长率，但增长率需要至少两个 TTM 点，我们在外部计算）
        # 此处先留空，增长率将在列表构建后统一计算，更准确。

        # 从 yfinance 获取 beta 和 PE（当前值，历史 PE 较难获取，但可接受）
        beta = info.get('beta')
        pe = info.get('trailingPE')

        # 构建字段字典
        fields = {field: None for field in FinancialMetrics.model_fields.keys()}
        ev_to_ebit = (ev / ttm_ebit) if (ev is not None and ttm_ebit and ttm_ebit != 0) else None
        fields.update({
            'ticker': ticker,
            'report_period': dt,
            'period': 'ttm',
            'currency': 'USD',
            'revenue': ttm_revenue,
            'net_income': ttm_net_income,
            'free_cash_flow': ttm_fcf,
            'ebit': ttm_ebit,
            'ebitda': ttm_ebitda,
            'total_debt': total_debt,
            'shareholders_equity': equity,
            'return_on_equity': roe,
            'return_on_invested_capital': roic,
            'operating_margin': operating_margin,
            'net_margin': net_margin,
            'gross_margin': gross_margin,
            'debt_to_equity': debt_to_equity,
            'current_ratio': current_ratio,
            'market_cap': historical_market_cap,
            'enterprise_value': ev,
            'ev_to_ebit': ev_to_ebit,
            'price_to_earnings_ratio': pe,
            'price_to_book_ratio': pb_ratio,
            'price_to_sales_ratio': ps_ratio,
            'free_cash_flow_yield': fcf_yield,
            'earnings_per_share': eps,
            'book_value_per_share': bvps,
            'free_cash_flow_per_share': fcf_ps,
            'beta': beta,
        })
        metrics.append(FinancialMetrics(**fields))

        if len(metrics) >= limit:
            break

    # 计算增长率（需要至少 2 个 TTM 数据点）
    if len(metrics) >= 2:
        metrics_sorted = sorted(metrics, key=lambda m: m.report_period)
        for i in range(4, len(metrics_sorted)):
            curr = metrics_sorted[i]
            prev = metrics_sorted[i-4]
            curr_year = int(curr.report_period[:4])
            prev_year = int(prev.report_period[:4])
            if curr_year - prev_year == 1:
                # revenue_growth
                if (prev.revenue is not None and curr.revenue is not None and prev.revenue != 0):
                    curr.revenue_growth = (curr.revenue - prev.revenue) / prev.revenue
                # earnings_growth
                if (prev.net_income is not None and curr.net_income is not None and prev.net_income != 0):
                    curr.earnings_growth = (curr.net_income - prev.net_income) / prev.net_income
                # free_cash_flow_growth
                if (prev.free_cash_flow is not None and curr.free_cash_flow is not None and prev.free_cash_flow != 0):
                    curr.free_cash_flow_growth = (curr.free_cash_flow - prev.free_cash_flow) / prev.free_cash_flow
                # operating_income_growth
                if (prev.ebit is not None and curr.ebit is not None and prev.ebit != 0):
                    curr.operating_income_growth = (curr.ebit - prev.ebit) / prev.ebit
                # ebitda_growth
                if (prev.ebitda is not None and curr.ebitda is not None and prev.ebitda != 0):
                    curr.ebitda_growth = (curr.ebitda - prev.ebitda) / prev.ebitda
                # book_value_growth
                if (prev.book_value_per_share is not None and curr.book_value_per_share is not None and prev.book_value_per_share != 0):
                    curr.book_value_growth = (curr.book_value_per_share - prev.book_value_per_share) / prev.book_value_per_share
                # earnings_per_share_growth
                if (prev.earnings_per_share is not None and curr.earnings_per_share is not None and prev.earnings_per_share != 0):
                    curr.earnings_per_share_growth = (curr.earnings_per_share - prev.earnings_per_share) / prev.earnings_per_share
                # peg_ratio
                if (curr.price_to_earnings_ratio is not None and curr.earnings_per_share_growth is not None and curr.earnings_per_share_growth != 0):
                    curr.peg_ratio = curr.price_to_earnings_ratio / (curr.earnings_per_share_growth * 100)

        # 将修改后的 metrics 列表恢复为原始顺序（降序，即最新在前）
        metrics = sorted(metrics, key=lambda m: m.report_period, reverse=True)

    return metrics[:limit]


# ------------------------------
# ROIC API 和 PE 序列（保持不变）
# ------------------------------
def _get_roic_from_api(ticker: str, limit: int = 5) -> dict[int, float] | None:
    time.sleep(10)
    api_key = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
    if not api_key:
        return None
    url = f"https://api.roic.ai/v2/fundamental/ratios/profitability/{ticker}"
    params = {"apikey": api_key, "period": "annual", "limit": limit, "order": "DESC"}
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                roic_by_year = {}
                for item in data:
                    fiscal_year = item.get('fiscal_year')
                    roic = item.get('return_on_inv_capital')
                    if fiscal_year and roic is not None:
                        roic_by_year[fiscal_year] = roic
                return roic_by_year
            else:
                # 响应格式异常，视为无数据
                return {}
        else:
            # 非 200 状态码，视为请求失败
            return None
    except Exception as e:
        print(f"[DEBUG] ROIC API error: {e}")
    return None

def _get_finnhub_pe_series(ticker: str, limit: int = 5) -> dict[int, float] | None:
    api_key = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={api_key}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        series = data.get('series', {})
        annual = series.get('annual', {})
        if not annual:
            return None
        pe_entries = annual.get('pe', [])
        if not pe_entries:
            return None
        pe_by_year = {}
        count = 0
        for entry in pe_entries:
            if count >= limit:
                break
            period_str = entry.get('period')
            if not period_str:
                continue
            year = int(period_str[:4])
            pe = entry.get('v')
            if pe is not None:
                pe_by_year[year] = pe
                count += 1
        return pe_by_year if pe_by_year else None
    except Exception as e:
        print(f"[DEBUG] Finnhub PE API error: {e}")
        return None

def _get_goodwill_from_yfinance(ticker: str, year: int) -> float | None:
    """从 yfinance 资产负债表获取指定年份的商誉+无形资产总额"""
    try:
        stock = yf.Ticker(ticker)
        bal = stock.balance_sheet
        if bal is None or bal.empty:
            return None
        for col in bal.columns:
            col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
            if col_year == year:
                # 优先使用合并项
                if 'Goodwill And Other Intangible Assets' in bal.index:
                    val = bal.loc['Goodwill And Other Intangible Assets', col]
                    if val is not None and not pd.isna(val):
                        return abs(val)
                # 否则分别获取 Goodwill 和 Other Intangible Assets
                goodwill = None
                other_intangible = None
                if 'Goodwill' in bal.index:
                    val = bal.loc['Goodwill', col]
                    if val is not None and not pd.isna(val):
                        goodwill = abs(val)
                if 'Other Intangible Assets' in bal.index:
                    val = bal.loc['Other Intangible Assets', col]
                    if val is not None and not pd.isna(val):
                        other_intangible = abs(val)
                if goodwill is not None or other_intangible is not None:
                    return (goodwill or 0) + (other_intangible or 0)
        return None
    except Exception:
        return None

def _fetch_line_items_from_sources(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str,
    limit: int,
    api_key: str | None = None,
) -> list[LineItem]:
    """
    获取行项目数据，优先从磁盘缓存读取完整记录，若不足则从数据源获取并更新缓存，
    最后根据 line_items 过滤字段并返回 LineItem 对象列表。
    """
    # 1. 尝试从磁盘缓存读取该 ticker 和 period 的完整记录
    cached_records = _cache.get_line_items_cache(ticker, period)
    if cached_records and len(cached_records) >= limit:
        # 直接使用缓存，但需要进行字段过滤
        sorted_records = sorted(cached_records, key=lambda x: x.get('report_period', ''), reverse=True)[:limit]
        # 构建结果字典
        result_dicts = []
        for rec in sorted_records:
            item = {k: rec.get(k) for k in line_items + ['ticker', 'report_period', 'period', 'currency'] if k in rec}
            result_dicts.append(item)

        # ========== 新增调试打印 ==========
        for item in result_dicts:
            for key in list(item.keys()):
                if key not in ['ticker', 'report_period', 'period', 'currency']:
                    try:
                        item[key] = float(item[key])
                    except (ValueError, TypeError):
                        pass  # 非数值则保持原样
        # 构造 LineItem 后打印实际类型
        result = [LineItem(**item) for item in result_dicts]
        return result
        # return [LineItem(**item) for item in result_dicts]

    # 2. 缓存不足，从数据源获取全量数据
    result = None
    # 使用所有字段进行获取
    all_fields = _ALL_LINE_ITEM_FIELDS

    if use_edgar():
        try:
            if period.lower() == "ttm":
                result = _synthesize_ttm_line_items_from_roic(ticker, end_date, limit)
            else:
                result = _search_line_items_edgar(ticker, all_fields, end_date, period, limit)
        except Exception as e:
            result = None
        if result:
            # 将结果转换为字典列表
            new_records = [item.model_dump() for item in result]
            # 合并到磁盘缓存
            existing = _cache.get_line_items_cache(ticker, period) or []
            merged = _cache._merge_data(existing, new_records, key_field="report_period")
            _cache.set_line_items_cache(ticker, period, merged)
            # 根据 line_items 过滤并返回
            return _filter_line_items(merged, line_items, limit)

    if use_yfinance():
        result = _search_line_items_yf(ticker, all_fields, end_date, period, limit)
        if result:
            new_records = [item.model_dump() for item in result]
            existing = _cache.get_line_items_cache(ticker, period) or []
            merged = _cache._merge_data(existing, new_records, key_field="report_period")
            _cache.set_line_items_cache(ticker, period, merged)
            return _filter_line_items(merged, line_items, limit)

    # 付费 API（legacy 模式）
    if not use_edgar() and not use_yfinance():
        headers = {}
        financial_api_key = api_key or os.environ.get("FINANCIAL_DATASETS_API_KEY")
        if financial_api_key:
            headers["X-API-KEY"] = financial_api_key
        url = "https://api.financialdatasets.ai/financials/search/line-items"
        body = {"tickers": [ticker], "line_items": all_fields, "end_date": end_date, "period": period, "limit": limit}
        response = _make_api_request(url, headers, method="POST", json_data=body)
        if response.status_code == 200:
            try:
                data = response.json()
                response_model = LineItemResponse(**data)
                result = response_model.search_results
                if result:
                    new_records = [r.model_dump() for r in result]
                    existing = _cache.get_line_items_cache(ticker, period) or []
                    merged = _cache._merge_data(existing, new_records, key_field="report_period")
                    _cache.set_line_items_cache(ticker, period, merged)
                    return _filter_line_items(merged, line_items, limit)
            except Exception:
                pass

    # 如果所有数据源都失败，返回缓存中已有的（即使不足）
    fallback = _cache.get_line_items_cache(ticker, period) or []
    return _filter_line_items(fallback, line_items, limit) if fallback else []

def _filter_line_items(records: list[dict], line_items: list[str], limit: int) -> list[LineItem]:
    """辅助函数：从记录中筛选字段、排序、截取，并构造 LineItem 对象。"""
    if not records:
        return []
    sorted_records = sorted(records, key=lambda x: x.get('report_period', ''), reverse=True)
    limited = sorted_records[:limit]
    result_dicts = []
    for rec in limited:
        item = {k: rec.get(k) for k in line_items + ['ticker', 'report_period', 'period', 'currency'] if k in rec}
        
        result_dicts.append(item)
    return [LineItem(**item) for item in result_dicts]

# ------------------------------
# 行项目（EDGAR 优先）
# ------------------------------
def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[LineItem]:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"

    # 调用新的数据获取函数
    result = _fetch_line_items_from_sources(ticker, line_items, end_date, period, limit, api_key)
    
    if result:
        for i, item in enumerate(result[:3]):
            parts = [f"report_period={item.report_period}"]
            for f in line_items:
                val = getattr(item, f, None)
                parts.append(f"{f}={val}")
    return result

def _search_line_items_yf(ticker, line_items, end_date, period, limit):
    yf_data = _fetch_yf_financials(ticker, limit)
    info = yf_data['info']          # 虽然当前函数未使用 info，但可能后续需要
    fin = yf_data['financials']
    bal = yf_data['balance']
    cf = yf_data['cashflow']

    # 预定义列名可能变体，并返回当前行的值
    def get_col(df, idx, possible_names):
        for name in possible_names:
            if name in df.columns:
                val = df.loc[idx, name]
                if pd.isna(val):
                    return None
                return val
        return None

    result_items = []
    for idx in fin.index:
        # report_period = idx.strftime("%Y-%m-%d")
        report_period = idx
        item_dict = {"ticker": ticker, "report_period": report_period}

        # 利润表字段
        revenue = get_col(fin, idx, ['Total Revenue', 'Revenue'])
        gross_profit = get_col(fin, idx, ['Gross Profit'])
        operating_income = get_col(fin, idx, ['Operating Income', 'EBIT'])
        net_income = get_col(fin, idx, ['Net Income'])
        depreciation = get_col(fin, idx, ['Depreciation And Amortization', 'Depreciation & Amortization'])
        research_and_development = get_col(fin, idx, ['Research And Development', 'R&D', 'ResearchAndDevelopment'])

        # 资产负债表字段
        cash = get_col(bal, idx, ['Cash', 'Cash And Cash Equivalents'])
        total_debt = get_col(bal, idx, ['Total Debt'])
        current_assets = get_col(bal, idx, ['Current Assets'])
        current_liabilities = get_col(bal, idx, ['Current Liabilities'])
        shareholders_equity = get_col(bal, idx, ['Total Equity Gross Minority Interest', 'Stockholders Equity'])

        # 现金流量表字段
        free_cash_flow = get_col(cf, idx, ['Free Cash Flow'])
        capital_expenditure = get_col(cf, idx, ['Capital Expenditure'])
        ebitda = get_col(cf, idx, ['EBITDA', 'Ebitda'])
        if ebitda is None and operating_income is not None and depreciation is not None:
            ebitda = operating_income + depreciation

        dividends_paid = get_col(cf, idx, [
            'Cash Dividends Paid',
            'Common Stock Dividend Paid',
            'Dividends Paid',
            'Common Stock Dividends',
            'Dividends',
            'Cash Dividends',
            'Dividends Paid - Common',
            'Dividends Paid Common Stock',
            'Dividends And Other Cash Distributions'
        ])
        if dividends_paid is not None and dividends_paid > 0:
            dividends_paid = -dividends_paid

        # 计算衍生指标
        gross_margin = gross_profit / revenue if (revenue and gross_profit) else None
        operating_margin = operating_income / revenue if (revenue and operating_income) else None
        debt_to_equity = total_debt / shareholders_equity if (total_debt and shareholders_equity) else None

        # 流通股
        shares_outstanding = info.get('sharesOutstanding')
        earnings_per_share = net_income / shares_outstanding if (net_income and shares_outstanding) else None

        # 填充 item_dict（省略部分字段，保留所有）
        item_dict['revenue'] = revenue
        item_dict['gross_profit'] = gross_profit
        item_dict['gross_margin'] = gross_margin
        item_dict['operating_income'] = operating_income
        item_dict['operating_margin'] = operating_margin
        item_dict['net_income'] = net_income
        item_dict['free_cash_flow'] = free_cash_flow
        item_dict['total_debt'] = total_debt
        item_dict['cash_and_equivalents'] = cash
        item_dict['current_assets'] = current_assets
        item_dict['current_liabilities'] = current_liabilities
        item_dict['shareholders_equity'] = shareholders_equity
        item_dict['capital_expenditure'] = capital_expenditure
        item_dict['depreciation_and_amortization'] = depreciation
        item_dict['research_and_development'] = research_and_development
        item_dict['ebitda'] = ebitda
        item_dict['dividends_and_other_cash_distributions'] = dividends_paid
        item_dict['outstanding_shares'] = shares_outstanding
        item_dict['debt_to_equity'] = debt_to_equity
        item_dict['earnings_per_share'] = earnings_per_share

        item_dict['period'] = period if period else "ttm"
        item_dict['currency'] = "USD"

        result_items.append(LineItem(**item_dict))

    return result_items

def _synthesize_ttm_line_items_from_roic(ticker: str, end_date: str, limit: int) -> list[LineItem]:
    q_limit = limit + 3
    roic_data = _fetch_roic_quarters(ticker, q_limit)
    income = roic_data['income']
    balance = roic_data['balance']
    cashflow = roic_data['cashflow']

    if not income or not balance or not cashflow:
        return []

    inc_by_date = {i['date']: i for i in income}
    bal_by_date = {b['date']: b for b in balance}
    cf_by_date = {c['date']: c for c in cashflow}

    # 利润表和现金流量表共有的日期
    inc_dates = set(inc_by_date.keys())
    cf_dates = set(cf_by_date.keys())
    common_dates = sorted(inc_dates & cf_dates)

    if len(common_dates) < 4:
        return []

    bal_dates = sorted(bal_by_date.keys())

    def get_nearest_balance_date(target_date):
        for d in reversed(bal_dates):
            if d <= target_date:
                return d
        return None

    ttm_items = []
    for i in range(3, len(common_dates)):
        dt = common_dates[i]
        window_dates = common_dates[i-3:i+1]
        inc_window = [inc_by_date[d] for d in window_dates]
        cf_window = [cf_by_date[d] for d in window_dates]

        rev_sum = sum(w.get('is_sales_revenue_turnover', 0) for w in inc_window)
        ni_sum = sum(w.get('is_net_income', 0) for w in inc_window)
        ebit_sum = sum(w.get('is_oper_income', 0) for w in inc_window)
        gp_sum = sum(w.get('is_gross_profit', 0) for w in inc_window)
        depr_sum = sum(w.get('is_depr_exp', 0) for w in inc_window)

        fcf_sum = sum(w.get('cf_free_cash_flow', 0) for w in cf_window)
        capex_sum = sum(w.get('cf_cap_expenditures', 0) for w in cf_window)
        div_sum = sum(w.get('cf_dvd_paid', 0) for w in cf_window)

        # ===== 新增：累加股份发行/回购（季度值） =====
        incr_cap_sum = 0
        decr_cap_sum = 0
        has_data = False
        for w in cf_window:
            if 'cf_incr_cap_stock' in w and w['cf_incr_cap_stock'] is not None:
                incr_cap_sum += w['cf_incr_cap_stock']
                has_data = True
            if 'cf_decr_cap_stock' in w and w['cf_decr_cap_stock'] is not None:
                decr_cap_sum += w['cf_decr_cap_stock']
                has_data = True
        net_issuance = incr_cap_sum + decr_cap_sum if has_data else None
        # =============================================

        bal_date = get_nearest_balance_date(dt)
        if bal_date is None:
            continue
        bal_latest = bal_by_date[bal_date]

        shares = bal_latest.get('bs_sh_out')
        equity = bal_latest.get('bs_total_equity')
        lt_debt = bal_latest.get('bs_lt_borrow', 0)
        st_debt = bal_latest.get('bs_st_borrow', 0)
        total_debt = lt_debt + st_debt if (lt_debt is not None and st_debt is not None) else None
        cash = bal_latest.get('bs_cash_near_cash_item')
        current_assets = bal_latest.get('bs_cur_asset_report')
        current_liab = bal_latest.get('bs_cur_liab')
        total_assets = bal_latest.get('bs_tot_asset')
        total_liabilities = bal_latest.get('bs_tot_liab')
        working_capital = current_assets - current_liab if (current_assets is not None and current_liab is not None) else None

        item = LineItem(
            ticker=ticker,
            report_period=dt,
            period="ttm",
            currency="USD",
            revenue=rev_sum,
            net_income=ni_sum,
            ebit=ebit_sum,
            ebitda=(ebit_sum + depr_sum) if depr_sum else None,
            gross_margin=(gp_sum / rev_sum) if (gp_sum and rev_sum and rev_sum != 0) else None,
            operating_margin=(ebit_sum / rev_sum) if (ebit_sum and rev_sum and rev_sum != 0) else None,
            net_margin=(ni_sum / rev_sum) if (ni_sum and rev_sum and rev_sum != 0) else None,
            free_cash_flow=fcf_sum,
            capital_expenditure=capex_sum,
            depreciation_and_amortization=depr_sum,
            cash_and_equivalents=cash,
            total_debt=total_debt,
            shareholders_equity=equity,
            outstanding_shares=shares,
            earnings_per_share=(ni_sum / shares) if (ni_sum and shares) else None,
            book_value_per_share=(equity / shares) if (equity and shares) else None,
            working_capital=working_capital,
            interest_expense=None,
            dividends_and_other_cash_distributions=-div_sum if div_sum else None,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            current_assets=current_assets,
            current_liabilities=current_liab,
            issuance_or_purchase_of_equity_shares=net_issuance,
        )
        ttm_items.append(item)
        if len(ttm_items) >= limit:
            break

    ttm_items.sort(key=lambda x: x.report_period, reverse=True)
    return ttm_items

def _search_line_items_edgar(ticker, line_items, end_date, period, limit):
    edgar_data = _fetch_edgar_annual_data(ticker)
    income_df = edgar_data['income']
    balance_df = edgar_data['balance']
    cashflow_df = edgar_data['cashflow']

    if income_df.empty:
        return []

    income_df.index = pd.to_datetime(income_df.index)
    balance_df.index = pd.to_datetime(balance_df.index)
    cashflow_df.index = pd.to_datetime(cashflow_df.index)

    annual_income = income_df.groupby(income_df.index.year).last()
    annual_balance = balance_df.groupby(balance_df.index.year).last()
    annual_cashflow = cashflow_df.groupby(cashflow_df.index.year).last()

    years = sorted(annual_income.index, reverse=True)[:limit]
    result_items = []

    stock = yf.Ticker(ticker)
    current_shares = stock.info.get('sharesOutstanding')

    # 获取 ROIC 映射（用于所有年份）
    roic_by_year = _get_roic_from_api(ticker, limit=limit)

    for yr in years:
        report_period = f"{yr}-12-31"
        fields = {field: None for field in LineItem.model_fields.keys()}

        # 在 _search_line_items_edgar 的循环内部，在 fields.update 之前
        # 确保所有可能被访问的字段都存在，置为 None
        for field_name in [
            'revenue', 'gross_profit', 'gross_margin', 'operating_income', 'operating_margin',
            'net_income', 'free_cash_flow', 'total_debt', 'cash_and_equivalents',
            'current_assets', 'current_liabilities', 'shareholders_equity',
            'capital_expenditure', 'depreciation_and_amortization', 'research_and_development',
            'ebitda', 'ebit', 'interest_expense', 'outstanding_shares', 'earnings_per_share',
            'book_value_per_share', 'issuance_or_purchase_of_equity_shares',
            'dividends_and_other_cash_distributions', 'working_capital'
        ]:
            if field_name not in fields:
                fields[field_name] = None
                
        fields.update({
            'ticker': ticker,
            'report_period': report_period,
            'period': 'annual',
            'currency': 'USD',
        })

        fields['dividends_and_other_cash_distributions'] = None

        # 利润表
        if 'revenue' in annual_income.columns:
            fields['revenue'] = annual_income.loc[yr, 'revenue']
        if 'issuance_or_purchase_of_equity_shares' in annual_cashflow.columns:
            fields['issuance_or_purchase_of_equity_shares'] = annual_cashflow.loc[yr, 'issuance_or_purchase_of_equity_shares']
        # if 'gross_profit' in annual_income.columns:
        #     fields['gross_profit'] = annual_income.loc[yr, 'gross_profit']

        # ---- 计算 gross_profit，若直接存在则取，否则用 revenue - cost_of_revenue ----
        gross_profit = None
        if 'gross_profit' in annual_income.columns:
            gross_profit = annual_income.loc[yr, 'gross_profit']
        elif 'cost_of_revenue' in annual_income.columns:
            revenue = fields.get('revenue')
            cost_of_revenue = annual_income.loc[yr, 'cost_of_revenue']
            if revenue is not None and cost_of_revenue is not None:
                gross_profit = revenue - cost_of_revenue
        # 如果两种途径都未得到，gross_profit 保持 None
        fields['gross_profit'] = gross_profit

        # 计算 gross_margin
        if fields.get('gross_profit') is not None and fields.get('revenue') is not None and fields['revenue'] != 0:
            fields['gross_margin'] = fields['gross_profit'] / fields['revenue']
        # --------------------------------------------------------------------------------
        
        if fields.get('gross_profit') is not None and fields.get('revenue') is not None and fields['revenue'] != 0:
            fields['gross_margin'] = fields['gross_profit'] / fields['revenue']
        if 'operating_income' in annual_income.columns:
            fields['ebit'] = annual_income.loc[yr, 'operating_income']
        elif 'ebit' in annual_income.columns:
            fields['ebit'] = annual_income.loc[yr, 'ebit']
        if 'operating_income' in annual_income.columns:
            fields['operating_income'] = annual_income.loc[yr, 'operating_income']
        if 'interest_expense' in annual_income.columns:
            fields['interest_expense'] = annual_income.loc[yr, 'interest_expense']
        if 'net_income' in annual_income.columns:
            fields['net_income'] = annual_income.loc[yr, 'net_income']
        if 'research_and_development' in annual_income.columns:
            fields['research_and_development'] = annual_income.loc[yr, 'research_and_development']
        if 'operating_expenses' in annual_income.columns:
            fields['operating_expense'] = annual_income.loc[yr, 'operating_expenses']

        # 资产负债表
        if 'long_term_debt' in annual_balance.columns:
            fields['total_debt'] = annual_balance.loc[yr, 'long_term_debt']
        if 'cash' in annual_balance.columns:
            fields['cash_and_equivalents'] = annual_balance.loc[yr, 'cash']
        
        # 商誉/无形资产：优先 EDGAR，缺失时从 yfinance 回退
        goodwill_val = None
        if 'goodwill' in annual_balance.columns:
            goodwill_val = annual_balance.loc[yr, 'goodwill']
        elif 'intangible_assets' in annual_balance.columns:
            goodwill_val = annual_balance.loc[yr, 'intangible_assets']
        if goodwill_val is None or pd.isna(goodwill_val):
            goodwill_val = _get_goodwill_from_yfinance(ticker, yr)
        fields['goodwill_and_intangible_assets'] = goodwill_val

        if 'dividends_paid' in annual_cashflow.columns:
            fields['dividends_and_other_cash_distributions'] = -annual_cashflow.loc[yr, 'dividends_paid']

        # working_capital
        current_assets = annual_balance.loc[yr, 'current_assets'] if 'current_assets' in annual_balance.columns else None
        current_liabilities = annual_balance.loc[yr, 'current_liabilities'] if 'current_liabilities' in annual_balance.columns else None
        if current_assets is not None and current_liabilities is not None:
            fields['working_capital'] = current_assets - current_liabilities

        # 现金流量表
        if 'free_cash_flow' in annual_cashflow.columns:
            fcf = annual_cashflow.loc[yr, 'free_cash_flow']
        else:
            ocf = annual_cashflow.loc[yr, 'operating_cash_flow'] if 'operating_cash_flow' in annual_cashflow.columns else None
            capex = annual_cashflow.loc[yr, 'capital_expenditures'] if 'capital_expenditures' in annual_cashflow.columns else None
            fcf = ocf - abs(capex) if (ocf is not None and capex is not None) else None
        fields['free_cash_flow'] = fcf

        if 'capital_expenditures' in annual_cashflow.columns:
            fields['capital_expenditure'] = annual_cashflow.loc[yr, 'capital_expenditures']

        # 从 yfinance 获取 D&A
        if fields.get('depreciation_and_amortization') is None:
            try:
                cashflow_yf = stock.cashflow
                if cashflow_yf is not None and not cashflow_yf.empty:
                    if 'Depreciation' in cashflow_yf.index:
                        for col in cashflow_yf.columns:
                            col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                            if col_year == yr:
                                da_value = cashflow_yf.loc['Depreciation', col]
                                if da_value is not None and not pd.isna(da_value):
                                    fields['depreciation_and_amortization'] = abs(da_value)
                                    break
                    else:
                        for possible_name in ['Depreciation And Amortization', 'Depreciation & Amortization']:
                            if possible_name in cashflow_yf.index:
                                for col in cashflow_yf.columns:
                                    col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                                    if col_year == yr:
                                        da_value = cashflow_yf.loc[possible_name, col]
                                        if da_value is not None and not pd.isna(da_value):
                                            fields['depreciation_and_amortization'] = abs(da_value)
                                            break
                                if fields.get('depreciation_and_amortization') is not None:
                                    break
            except Exception as e:
                print(f"[EDGAR] Failed to get D&A from yfinance for {yr}: {e}")

        # 从 yfinance 获取 share issuance/buyback
        if fields.get('issuance_or_purchase_of_equity_shares') is None:
            try:
                cashflow_yf = stock.cashflow
                if cashflow_yf is not None and not cashflow_yf.empty:
                    possible_names = [
                        'Issuance Of Capital Stock',
                        'Common Stock Issuance',
                        'Common Stock Repurchase',
                        'Stock Repurchase',
                        'Common Stock Payments',
                        'Common Stock Issuance And Payments',
                        'Common Stock, Value, Issued'
                    ]
                    for name in possible_names:
                        if name in cashflow_yf.index:
                            for col in cashflow_yf.columns:
                                col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                                if col_year == yr:
                                    value = cashflow_yf.loc[name, col]
                                    if value is not None and not pd.isna(value):
                                        fields['issuance_or_purchase_of_equity_shares'] = value
                                        break
                            if fields.get('issuance_or_purchase_of_equity_shares') is not None:
                                break
            except Exception as e:
                print(f"[EDGAR] Failed to get issuance/purchase from yfinance for {yr}: {e}")

        # 从 yfinance 获取 EBITDA
        if fields.get('ebitda') is None:
            try:
                cashflow_yf = stock.cashflow
                if cashflow_yf is not None and not cashflow_yf.empty:
                    if 'EBITDA' in cashflow_yf.index:
                        for col in cashflow_yf.columns:
                            col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                            if col_year == yr:
                                ebitda_value = cashflow_yf.loc['EBITDA', col]
                                if ebitda_value is not None and not pd.isna(ebitda_value):
                                    fields['ebitda'] = abs(ebitda_value)
                                    break
                    else:
                        possible_names = ['Ebitda', 'EBITDA', 'Ebitda', 'Earnings Before Interest Taxes Depreciation Amortization']
                        for name in possible_names:
                            if name in cashflow_yf.index:
                                for col in cashflow_yf.columns:
                                    col_year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                                    if col_year == yr:
                                        ebitda_value = cashflow_yf.loc[name, col]
                                        if ebitda_value is not None and not pd.isna(ebitda_value):
                                            fields['ebitda'] = abs(ebitda_value)
                                            break
                                if fields.get('ebitda') is not None:
                                    break
            except Exception as e:
                print(f"[EDGAR] Failed to get EBITDA from yfinance for {yr}: {e}")

        # 流通股
        if 'shares_outstanding' in annual_income.columns:
            fields['outstanding_shares'] = annual_income.loc[yr, 'shares_outstanding']
        else:
            fields['outstanding_shares'] = current_shares

        # 补充字段
        if 'total_assets' in annual_balance.columns:
            fields['total_assets'] = annual_balance.loc[yr, 'total_assets']
        if 'total_liabilities' in annual_balance.columns:
            fields['total_liabilities'] = annual_balance.loc[yr, 'total_liabilities']
        if 'current_assets' in annual_balance.columns:
            fields['current_assets'] = annual_balance.loc[yr, 'current_assets']
        if 'current_liabilities' in annual_balance.columns:
            fields['current_liabilities'] = annual_balance.loc[yr, 'current_liabilities']
        if 'stockholders_equity' in annual_balance.columns:
            fields['shareholders_equity'] = annual_balance.loc[yr, 'stockholders_equity']

        if 'eps_basic' in annual_income.columns:
            fields['earnings_per_share'] = annual_income.loc[yr, 'eps_basic']
        elif 'eps_diluted' in annual_income.columns:
            fields['earnings_per_share'] = annual_income.loc[yr, 'eps_diluted']

        if 'book_value_per_share' in annual_balance.columns:
            fields['book_value_per_share'] = annual_balance.loc[yr, 'book_value_per_share']
        else:
            equity = fields.get('shareholders_equity')
            shares = fields.get('outstanding_shares')
            if equity is not None and shares is not None and shares != 0:
                fields['book_value_per_share'] = equity / shares

        if 'dividends_paid' in annual_cashflow.columns:
            fields['dividends_and_other_cash_distributions'] = -annual_cashflow.loc[yr, 'dividends_paid']

        # ========== 新增：填充 ROIC（放在这里） ==========
        roic = None
        if roic_by_year is None:
            # API 请求失败（例如 429 限流、网络异常等），抛出异常以便上层重试或处理
            error_msg = f"ROIC API request failed for {ticker}"
            raise Exception(error_msg)
        elif roic_by_year:
            # API 成功返回数据，尝试获取当前年份的 ROIC
            if yr in roic_by_year:
                roic = roic_by_year[yr] / 100.0
            elif str(yr) in roic_by_year:
                roic = roic_by_year[str(yr)] / 100.0
        if roic is not None:
            fields['return_on_invested_capital'] = roic
        # ==============================================

        # ========== 新增：计算 operating_margin 和 debt_to_equity ==========
        if fields.get('revenue') and fields.get('revenue') != 0:
            if fields.get('operating_income'):
                fields['operating_margin'] = fields['operating_income'] / fields['revenue']
        if fields.get('shareholders_equity') and fields.get('shareholders_equity') != 0:
            if fields.get('total_debt'):
                fields['debt_to_equity'] = fields['total_debt'] / fields['shareholders_equity']
        # ================================================================

        result_items.append(LineItem(**fields))
    return result_items

def _fetch_insider_trades_from_sources(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str | None = None,
) -> list[InsiderTrade]:
    """
    总是从 Finnhub 获取内幕交易数据，合并到磁盘缓存，返回缓存中的完整记录（按日期过滤）。
    如果 Finnhub 调用失败，则回退到缓存中已有数据（即使不足）。
    """
    # 总是调用 Finnhub 获取最新数据
    trades = _get_insider_trades_finnhub(ticker, end_date, start_date, limit)
    if trades:
        print(f"[Insider] Got {len(trades)} trades from Finnhub for {ticker}")
        new_records = [t.model_dump() for t in trades]
        existing = _cache.get_insider_cache(ticker) or []
        merged = _cache._merge_data(existing, new_records, key_field="filing_date")
        _cache.set_insider_cache(ticker, merged)
        print(f"[Insider] Cache now has {len(merged)} records for {ticker}")
        # 从合并后的缓存中过滤日期并返回
        filtered = _filter_insider_by_date(merged, start_date, end_date, limit)
        return [InsiderTrade(**item) for item in filtered] if filtered else trades[:limit]

    # 如果 Finnhub 失败，回退到缓存中已有的（即使不足）
    fallback = _cache.get_insider_cache(ticker) or []
    print(f"[Insider] Finnhub failed, returning {len(fallback)} cached records (may be insufficient) for {ticker}")
    filtered = _filter_insider_by_date(fallback, start_date, end_date, limit)
    return [InsiderTrade(**item) for item in filtered] if filtered else []

def _filter_insider_by_date(records: list[dict], start_date: str | None, end_date: str, limit: int) -> list[dict]:
    """按日期范围过滤内幕交易记录，并按 filing_date 降序排序，取前 limit 条。"""
    if not records:
        return []
    filtered = []
    for rec in records:
        filing_date = rec.get('filing_date', '')
        if filing_date:
            # 只取日期部分（如果包含时间）
            filing_date_clean = filing_date.split('T')[0] if 'T' in filing_date else filing_date
            if filing_date_clean <= end_date:
                if start_date is None or filing_date_clean >= start_date:
                    filtered.append(rec)
    # 按 filing_date 降序排列
    filtered.sort(key=lambda x: x.get('filing_date', ''), reverse=True)
    return filtered[:limit]

# ------------------------------
# 内幕交易（Finnhub）
# ------------------------------
def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[InsiderTrade]:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"

    return _fetch_insider_trades_from_sources(ticker, end_date, start_date, limit, api_key)

def _get_insider_trades_finnhub(ticker, end_date, start_date, limit):
    api_key = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
    if not api_key:
        return []
    if start_date is None:
        start_date = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    url = "https://finnhub.io/api/v1/stock/insider-transactions"
    params = {"symbol": ticker, "from": start_date, "token": api_key}
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get('data', [])[:limit]
        trades = []
        for item in raw:
            trades.append(InsiderTrade(
                ticker=ticker,
                filing_date=item.get('filingDate') or item.get('transactionDate'),
                transaction_date=item.get('transactionDate'),
                transaction_shares=item.get('change'),
                transaction_price=item.get('transactionPrice'),
                transaction_code=item.get('transactionCode'),
                name=item.get('name'),
                issuer=ticker,
                title="",
                is_board_director=False,
                transaction_price_per_share=item.get('transactionPrice'),
                transaction_value=item.get('change', 0) * item.get('transactionPrice', 0) if item.get('change') is not None and item.get('transactionPrice') is not None else None,
                shares_owned_before_transaction=0,
                shares_owned_after_transaction=0,
                security_title="Common Stock",
            ))
        return trades
    except Exception as e:
        return []


def _fetch_news_from_sources(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str | None = None,
) -> list[CompanyNews]:
    """
    总是从 Alpha Vantage（或 Finnhub）获取公司新闻，合并到磁盘缓存，返回缓存中的完整记录（按日期过滤）。
    如果所有数据源均失败，则回退到缓存中已有数据（即使不足）。
    """
    news_items = []
    # 优先 Alpha Vantage（包含情感数据）
    alpha_news = _get_company_news_alpha_vantage(ticker, end_date, start_date, limit)
    if alpha_news:
        print(f"[News] Got {len(alpha_news)} records from Alpha Vantage for {ticker}")
        news_items.extend(alpha_news)
    else:
        # 若 Alpha Vantage 失败，尝试 Finnhub
        finnhub_news = _get_company_news_finnhub(ticker, end_date, start_date, limit)
        if finnhub_news:
            print(f"[News] Got {len(finnhub_news)} records from Finnhub for {ticker}")
            news_items.extend(finnhub_news)

    if news_items:
        # 转换为字典并合并到磁盘缓存
        new_records = [n.model_dump() for n in news_items]
        # set_news_cache 内部会合并去重（按 date 字段）
        _cache.set_news_cache(ticker, new_records)
        print(f"[News] Cache updated for {ticker}, total records: {len(_cache.get_news_cache(ticker))}")
        # 从合并后的缓存中过滤日期并返回
        all_records = _cache.get_news_cache(ticker)
        filtered = _filter_news_by_date(all_records, start_date, end_date, limit)
        print(f"[News] Returning {len(filtered)} records after date filtering for {ticker}")
        return [CompanyNews(**item) for item in filtered] if filtered else []

    # 如果所有数据源都失败，回退到缓存中已有的（即使不足）
    fallback = _cache.get_news_cache(ticker) or []
    print(f"[News] All sources failed, returning {len(fallback)} cached records (may be insufficient) for {ticker}")
    filtered = _filter_news_by_date(fallback, start_date, end_date, limit)
    return [CompanyNews(**item) for item in filtered] if filtered else []

def _filter_news_by_date(records: list[dict], start_date: str | None, end_date: str, limit: int) -> list[dict]:
    """按日期范围过滤新闻，并按 date 降序排序，取前 limit 条。"""
    if not records:
        return []
    filtered = []
    for rec in records:
        date_str = rec.get('date', '')
        if not date_str:
            continue
        # 标准化日期
        if 'T' in date_str:
            ymd_part = date_str.split('T')[0]
            if len(ymd_part) == 8:
                date_clean = f"{ymd_part[:4]}-{ymd_part[4:6]}-{ymd_part[6:8]}"
            else:
                date_clean = ymd_part
        else:
            date_clean = date_str[:10]
        # 比较
        if date_clean <= end_date:
            if start_date is None or date_clean >= start_date:
                filtered.append(rec)
    filtered.sort(key=lambda x: x.get('date', ''), reverse=True)
    return filtered[:limit]

# ------------------------------
# 公司新闻（Alpha Vantage 优先，Finnhub 备选）
# ------------------------------
def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[CompanyNews]:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"

    return _fetch_news_from_sources(ticker, end_date, start_date, limit, api_key)

def _get_company_news_alpha_vantage(ticker, end_date, start_date, limit):
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "LEPNUFM9ZGGRXWDR")
    if not api_key:
        return []
    url = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "limit": min(limit, 50), "apikey": api_key, "sort": "LATEST"}
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        feed = data.get('feed', [])[:limit]
        news = []
        for item in feed:
            news.append(CompanyNews(
                ticker=ticker,
                date=item.get('time_published', '')[:10] if 'time_published' in item else None,
                title=item.get('title'),
                summary=item.get('summary'),
                source=item.get('source'),
                url=item.get('url'),
                sentiment=item.get('overall_sentiment_label'),
            ))
        return news
    except Exception as e:
        return []

def _get_company_news_finnhub(ticker, end_date, start_date, limit):
    api_key = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
    if not api_key:
        return []
    client = finnhub.Client(api_key=api_key)
    if start_date is None:
        start_date = (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        raw = client.company_news(ticker, _from=start_date, to=end_date)[:limit]
        news = []
        for item in raw:
            news.append(CompanyNews(
                ticker=ticker,
                date=datetime.datetime.fromtimestamp(item['datetime']).strftime("%Y-%m-%d") if 'datetime' in item else None,
                title=item.get('headline'),
                summary=item.get('summary'),
                source=item.get('source'),
                url=item.get('url'),
            ))
        return news
    except Exception as e:
        return []

# ------------------------------
# 市值（EDGAR 历史市值，否则 yfinance）
# ------------------------------
def get_market_cap(ticker: str, end_date: str, api_key: str = None) -> float | None:
    caller = inspect.stack()[1].function if len(inspect.stack()) > 1 else "unknown"

    # ── ① 独立磁盘缓存：命中直接返回，0 网络 ──
    cached = _cache.get_market_cap(ticker, end_date)
    if cached is not None:
        print(f"[MarketCap] Cache HIT for {ticker} @ {end_date}: {cached:.0f}")
        return cached

    result = None

    # ── ② yfinance 优先（当前市值，语义正确 + 速度快）──
    if use_yfinance() or use_edgar():
        try:
            stock = yf.Ticker(ticker)
            mc = stock.info.get('marketCap')
            if mc:
                result = mc
                print(f"[MarketCap] yfinance for {ticker}: {mc:.0f}")
        except Exception as e:
            print(f"[MarketCap] yfinance failed for {ticker}: {e}")

    # ── ③ EDGAR fallback（仅当 yfinance 失败）──
    if result is None and use_edgar():
        metrics = get_financial_metrics(ticker, end_date,
                                        period="annual", limit=1,
                                        api_key=api_key)
        if metrics and metrics[0].market_cap:
            result = metrics[0].market_cap
            print(f"[MarketCap] EDGAR fallback for {ticker}: {result:.0f}")

    # ── ④ 写缓存 ──
    if result is not None:
        _cache.set_market_cap(ticker, end_date, result)

    return result

# ------------------------------
# 工具函数
# ------------------------------
def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df

def get_price_data(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame:
    prices = get_prices(ticker, start_date, end_date, api_key=api_key)
    return prices_to_df(prices)
