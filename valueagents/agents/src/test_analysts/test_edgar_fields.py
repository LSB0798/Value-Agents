#!/usr/bin/env python
"""
测试 secfin (EDGAR) 能够提供哪些 FinancialMetrics 字段
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from secfin import SECClient, Company
import yfinance as yf

# 获取 SEC 客户端
def get_sec_client():
    return SECClient("ValueAgents research contact@example.com")

def test_edgar_fields(ticker="AAPL"):
    client = get_sec_client()
    company = Company(ticker, client)

    # 获取年度报表（默认是年度）
    income_df = company.get_income_statement().to_dataframe()
    balance_df = company.get_balance_sheet().to_dataframe()
    cashflow_df = company.get_cash_flow().to_dataframe()

    # 转换日期索引
    income_df.index = pd.to_datetime(income_df.index)
    balance_df.index = pd.to_datetime(balance_df.index)
    cashflow_df.index = pd.to_datetime(cashflow_df.index)

    # 按年分组取最后一条（年报）
    annual_income = income_df.groupby(income_df.index.year).last()
    annual_balance = balance_df.groupby(balance_df.index.year).last()
    annual_cashflow = cashflow_df.groupby(cashflow_df.index.year).last()

    # 取最近一年
    latest_year = annual_income.index[-1]
    print(f"最新财年: {latest_year}")
    print("\n--- 利润表字段 ---")
    print(annual_income.columns.tolist())
    print("\n--- 资产负债表字段 ---")
    print(annual_balance.columns.tolist())
    print("\n--- 现金流量表字段 ---")
    print(annual_cashflow.columns.tolist())

    # 提取关键数据
    rev = annual_income.loc[latest_year, 'revenue'] if 'revenue' in annual_income.columns else None
    net_income = annual_income.loc[latest_year, 'net_income'] if 'net_income' in annual_income.columns else None
    ebit = annual_income.loc[latest_year, 'operating_income'] if 'operating_income' in annual_income.columns else None
    if ebit is None and 'ebit' in annual_income.columns:
        ebit = annual_income.loc[latest_year, 'ebit']
    gross_profit = annual_income.loc[latest_year, 'gross_profit'] if 'gross_profit' in annual_income.columns else None
    interest_expense = annual_income.loc[latest_year, 'interest_expense'] if 'interest_expense' in annual_income.columns else None
    total_assets = annual_balance.loc[latest_year, 'total_assets'] if 'total_assets' in annual_balance.columns else None
    total_liabilities = annual_balance.loc[latest_year, 'total_liabilities'] if 'total_liabilities' in annual_balance.columns else None
    stockholders_equity = annual_balance.loc[latest_year, 'stockholders_equity'] if 'stockholders_equity' in annual_balance.columns else None
    current_assets = annual_balance.loc[latest_year, 'current_assets'] if 'current_assets' in annual_balance.columns else None
    current_liabilities = annual_balance.loc[latest_year, 'current_liabilities'] if 'current_liabilities' in annual_balance.columns else None
    cash = annual_balance.loc[latest_year, 'cash'] if 'cash' in annual_balance.columns else None
    total_debt = annual_balance.loc[latest_year, 'long_term_debt'] if 'long_term_debt' in annual_balance.columns else None
    if total_debt is None and 'total_debt' in annual_balance.columns:
        total_debt = annual_balance.loc[latest_year, 'total_debt']
    # 存货
    inventory = annual_balance.loc[latest_year, 'inventory'] if 'inventory' in annual_balance.columns else None
    # 应收账款
    receivables = annual_balance.loc[latest_year, 'accounts_receivable'] if 'accounts_receivable' in annual_balance.columns else None

    # 现金流量表
    fcf = None
    if 'free_cash_flow' in annual_cashflow.columns:
        fcf = annual_cashflow.loc[latest_year, 'free_cash_flow']
    else:
        ocf = annual_cashflow.loc[latest_year, 'operating_cash_flow'] if 'operating_cash_flow' in annual_cashflow.columns else None
        capex = annual_cashflow.loc[latest_year, 'capital_expenditures'] if 'capital_expenditures' in annual_cashflow.columns else None
        if ocf is not None and capex is not None:
            fcf = ocf - abs(capex)
    dividends_paid = annual_cashflow.loc[latest_year, 'dividends_paid'] if 'dividends_paid' in annual_cashflow.columns else None

    # 流通股（可能来自利润表）
    shares_outstanding = annual_income.loc[latest_year, 'shares_outstanding'] if 'shares_outstanding' in annual_income.columns else None
    if shares_outstanding is None:
        stock = yf.Ticker(ticker)
        shares_outstanding = stock.info.get('sharesOutstanding')

    # 获取市值（用 yfinance）
    market_cap = None
    try:
        stock = yf.Ticker(ticker)
        market_cap = stock.info.get('marketCap')
    except:
        pass

    # 计算指标
    gross_margin = gross_profit / rev if (gross_profit and rev) else None
    operating_margin = ebit / rev if (ebit and rev) else None
    net_margin = net_income / rev if (net_income and rev) else None
    roe = net_income / stockholders_equity if (net_income and stockholders_equity) else None
    roa = net_income / total_assets if (net_income and total_assets) else None
    roic = None  # 需要从 ROIC API 获取，secfin 没有直接提供
    debt_to_equity = total_debt / stockholders_equity if (total_debt and stockholders_equity) else None
    debt_to_assets = total_debt / total_assets if (total_debt and total_assets) else None
    current_ratio = current_assets / current_liabilities if (current_assets and current_liabilities) else None
    quick_ratio = (current_assets - inventory) / current_liabilities if (current_assets and inventory and current_liabilities) else None
    cash_ratio = cash / current_liabilities if (cash and current_liabilities) else None
    interest_coverage = ebit / interest_expense if (ebit and interest_expense and interest_expense != 0) else None
    payout_ratio = dividends_paid / net_income if (dividends_paid and net_income) else None

    # 周转率
    asset_turnover = rev / ((total_assets + (annual_balance.loc[annual_balance.index[0] if len(annual_balance)>1 else latest_year, 'total_assets'] if len(annual_balance)>1 else total_assets)) / 2) if rev and total_assets else None
    inventory_turnover = None
    if rev and inventory:
        inventory_turnover = rev / inventory  # 近似
    receivables_turnover = rev / receivables if (rev and receivables) else None
    days_sales_outstanding = 365 / receivables_turnover if receivables_turnover else None
    operating_cycle = None
    working_capital_turnover = rev / (current_assets - current_liabilities) if (rev and current_assets and current_liabilities) else None

    # 每股指标
    eps = net_income / shares_outstanding if (net_income and shares_outstanding) else None
    bvps = stockholders_equity / shares_outstanding if (stockholders_equity and shares_outstanding) else None
    fcf_ps = fcf / shares_outstanding if (fcf and shares_outstanding) else None

    # 估值倍数
    pe = market_cap / net_income if (market_cap and net_income) else None
    pb = market_cap / stockholders_equity if (market_cap and stockholders_equity) else None
    ps = market_cap / rev if (market_cap and rev) else None
    fcf_yield = fcf / market_cap if (fcf and market_cap) else None
    ev = market_cap + total_debt - cash if (market_cap and total_debt is not None and cash is not None) else None
    ev_ebitda = None  # 需要 EBITDA
    ev_revenue = ev / rev if (ev and rev) else None

    # 增长率（需要前一年的数据）
    prev_year = latest_year - 1
    if prev_year in annual_income.index:
        prev_rev = annual_income.loc[prev_year, 'revenue'] if 'revenue' in annual_income.columns else None
        prev_ni = annual_income.loc[prev_year, 'net_income'] if 'net_income' in annual_income.columns else None
        prev_equity = annual_balance.loc[prev_year, 'stockholders_equity'] if 'stockholders_equity' in annual_balance.columns else None
        prev_fcf = None
        if 'free_cash_flow' in annual_cashflow.columns:
            prev_fcf = annual_cashflow.loc[prev_year, 'free_cash_flow']
        else:
            prev_ocf = annual_cashflow.loc[prev_year, 'operating_cash_flow'] if 'operating_cash_flow' in annual_cashflow.columns else None
            prev_capex = annual_cashflow.loc[prev_year, 'capital_expenditures'] if 'capital_expenditures' in annual_cashflow.columns else None
            if prev_ocf is not None and prev_capex is not None:
                prev_fcf = prev_ocf - abs(prev_capex)
        prev_eps = prev_ni / shares_outstanding if (prev_ni and shares_outstanding) else None

        revenue_growth = (rev - prev_rev) / prev_rev if (prev_rev and prev_rev != 0) else None
        earnings_growth = (net_income - prev_ni) / prev_ni if (prev_ni and prev_ni != 0) else None
        book_value_growth = (stockholders_equity - prev_equity) / prev_equity if (prev_equity and prev_equity != 0) else None
        fcf_growth = (fcf - prev_fcf) / prev_fcf if (prev_fcf and prev_fcf != 0) else None
        eps_growth = (eps - prev_eps) / prev_eps if (prev_eps and prev_eps != 0) else None
        operating_income_growth = None  # need prev_ebit
        ebitda_growth = None  # need prev_ebitda
    else:
        revenue_growth = None
        earnings_growth = None
        book_value_growth = None
        fcf_growth = None
        eps_growth = None
        operating_income_growth = None
        ebitda_growth = None

    # PEG
    peg_ratio = pe / (eps_growth * 100) if (pe and eps_growth and eps_growth != 0) else None

    # 打印结果
    fields = {
        'revenue': rev,
        'net_income': net_income,
        'ebit': ebit,
        'free_cash_flow': fcf,
        'gross_margin': gross_margin,
        'operating_margin': operating_margin,
        'net_margin': net_margin,
        'return_on_equity': roe,
        'return_on_assets': roa,
        'return_on_invested_capital': roic,
        'debt_to_equity': debt_to_equity,
        'debt_to_assets': debt_to_assets,
        'current_ratio': current_ratio,
        'quick_ratio': quick_ratio,
        'cash_ratio': cash_ratio,
        'interest_coverage': interest_coverage,
        'payout_ratio': payout_ratio,
        'asset_turnover': asset_turnover,
        'inventory_turnover': inventory_turnover,
        'receivables_turnover': receivables_turnover,
        'days_sales_outstanding': days_sales_outstanding,
        'operating_cycle': operating_cycle,
        'working_capital_turnover': working_capital_turnover,
        'earnings_per_share': eps,
        'book_value_per_share': bvps,
        'free_cash_flow_per_share': fcf_ps,
        'price_to_earnings_ratio': pe,
        'price_to_book_ratio': pb,
        'price_to_sales_ratio': ps,
        'free_cash_flow_yield': fcf_yield,
        'enterprise_value': ev,
        'enterprise_value_to_revenue_ratio': ev_revenue,
        'enterprise_value_to_ebitda_ratio': ev_ebitda,
        'peg_ratio': peg_ratio,
        'revenue_growth': revenue_growth,
        'earnings_growth': earnings_growth,
        'book_value_growth': book_value_growth,
        'free_cash_flow_growth': fcf_growth,
        'earnings_per_share_growth': eps_growth,
        'operating_income_growth': operating_income_growth,
        'ebitda_growth': ebitda_growth,
    }

    print("\n--- 计算得到的字段值 (最新财年) ---")
    for k, v in fields.items():
        print(f"{k:30} : {v}")

    # 统计缺失
    missing = [k for k, v in fields.items() if v is None]
    print(f"\n缺失字段数量: {len(missing)}")
    print("缺失字段:", missing)

if __name__ == "__main__":
    test_edgar_fields("AAPL")
