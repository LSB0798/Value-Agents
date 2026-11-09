#!/usr/bin/env python
"""
测试 secfin 返回的数据帧结构，了解所有可用的列名和示例数据
"""

import os
import sys
import pandas as pd
from secfin import SECClient, Company

# 设置身份标识
CLIENT = SECClient("ValueAgents research contact@example.com")

def print_dataframe_info(df, name):
    """打印 DataFrame 的详细信息"""
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"{'='*60}")
    print(f"Shape: {df.shape}")
    print(f"\n📋 列名列表:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\n📈 前 3 行数据:")
    print(df.head(3).to_string())
    
    print(f"\n📉 后 3 行数据:")
    print(df.tail(3).to_string())
    
    # 检查常见字段是否存在
    common_fields = [
        'revenue', 'net_income', 'ebit', 'interest_expense', 'income_tax_expense',
        'eps_basic', 'eps_diluted', 'shares_outstanding',
        'total_assets', 'current_assets', 'total_liabilities', 'current_liabilities',
        'stockholders_equity', 'book_value_per_share', 'total_debt',
        'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
        'free_cash_flow', 'capital_expenditures', 'dividends_paid'
    ]
    
    print(f"\n🔍 关键字段存在性检查:")
    for field in common_fields:
        exists = field in df.columns
        status = "✅" if exists else "❌"
        print(f"  {status} {field}")

def main():
    ticker = "AAPL"
    print(f"🔍 获取 {ticker} 的 secfin 数据...")
    
    company = Company(ticker, CLIENT)
    
    # 获取三大报表的 DataFrame
    income_df = company.get_income_statement().to_dataframe()
    balance_df = company.get_balance_sheet().to_dataframe()
    cashflow_df = company.get_cash_flow().to_dataframe()
    
    # 转换索引为 datetime
    income_df.index = pd.to_datetime(income_df.index)
    balance_df.index = pd.to_datetime(balance_df.index)
    cashflow_df.index = pd.to_datetime(cashflow_df.index)
    
    # 按年份分组取最后一条（年末数据）
    annual_income = income_df.groupby(income_df.index.year).last()
    annual_balance = balance_df.groupby(balance_df.index.year).last()
    annual_cashflow = cashflow_df.groupby(cashflow_df.index.year).last()
    
    print_dataframe_info(annual_income, "Annual Income Statement")
    print_dataframe_info(annual_balance, "Annual Balance Sheet")
    print_dataframe_info(annual_cashflow, "Annual Cash Flow")
    
    # 额外：检查一些特定字段的值
    print("\n" + "="*60)
    print("📋 特定字段样本值 (最近 3 年)")
    print("="*60)
    
    years = sorted(annual_income.index, reverse=True)[:3]
    for yr in years:
        print(f"\n--- 年份 {yr} ---")
        # 利润表
        print("  Income:")
        for col in ['revenue', 'net_income', 'ebit', 'interest_expense', 'eps_basic', 'eps_diluted', 'shares_outstanding']:
            if col in annual_income.columns:
                val = annual_income.loc[yr, col]
                print(f"    {col}: {val}")
        # 资产负债表
        print("  Balance:")
        for col in ['total_assets', 'current_assets', 'total_liabilities', 'current_liabilities', 'stockholders_equity']:
            if col in annual_balance.columns:
                val = annual_balance.loc[yr, col]
                print(f"    {col}: {val}")
        # 现金流量表
        print("  Cashflow:")
        for col in ['operating_cash_flow', 'free_cash_flow', 'capital_expenditures', 'dividends_paid']:
            if col in annual_cashflow.columns:
                val = annual_cashflow.loc[yr, col]
                print(f"    {col}: {val}")

if __name__ == "__main__":
    main()
