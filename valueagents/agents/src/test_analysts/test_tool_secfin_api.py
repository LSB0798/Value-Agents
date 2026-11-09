#!/usr/bin/env python
"""
探索 secfin 库的 API 结构，确定如何正确获取财务数据。
"""

import sys
import pandas as pd
from secfin import SECClient, Company

# 身份标识（使用合法信息）
CLIENT = SECClient("ValueAgents research contact@example.com")

def inspect_object(obj, name):
    """打印对象类型、属性和方法（非私有）"""
    print(f"\n=== {name} ===")
    print(f"Type: {type(obj)}")
    attrs = [a for a in dir(obj) if not a.startswith('_')]
    print(f"Attributes/Methods: {attrs}")
    # 尝试常用属性
    for attr in ['data', 'annual', 'quarterly', 'to_dataframe']:
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if callable(val):
                print(f"  - {attr}() -> callable")
            else:
                print(f"  - {attr}: {type(val)}")
                if isinstance(val, pd.DataFrame):
                    print(f"      DataFrame shape: {val.shape}")
                    print(f"      Columns: {val.columns.tolist()}")
                    print(f"      Head:\n{val.head()}")
        else:
            print(f"  - {attr}: not present")
    # 如果是 DataFrame 类型，直接展示
    if isinstance(obj, pd.DataFrame):
        print("Is DataFrame directly.")
        print("Columns:", obj.columns.tolist())
        print("Index:", obj.index)
        print("Head:\n", obj.head())

def main():
    ticker = "AAPL"
    print(f"Testing secfin with {ticker}...")
    company = Company(ticker, CLIENT)
    
    # 1. 利润表
    income = company.get_income_statement()
    inspect_object(income, "Income Statement")
    
    # 2. 资产负债表
    balance = company.get_balance_sheet()
    inspect_object(balance, "Balance Sheet")
    
    # 3. 现金流量表
    cashflow = company.get_cash_flow()
    inspect_object(cashflow, "Cash Flow")
    
    # 额外尝试：直接获取数据
    print("\n=== Attempting to extract data via common methods ===")
    # 尝试 to_dataframe
    for obj, name in [(income, "Income"), (balance, "Balance"), (cashflow, "Cashflow")]:
        if hasattr(obj, 'to_dataframe'):
            try:
                df = obj.to_dataframe()
                print(f"{name}: to_dataframe() returned DataFrame shape {df.shape}")
                print(df.head())
            except Exception as e:
                print(f"{name}: to_dataframe() failed: {e}")
        if hasattr(obj, 'data'):
            try:
                data = obj.data
                if isinstance(data, pd.DataFrame):
                    print(f"{name}: data is DataFrame shape {data.shape}")
                    print(data.head())
                else:
                    print(f"{name}: data type: {type(data)}")
            except Exception as e:
                print(f"{name}: data access failed: {e}")
    
    # 尝试获取年报数据
    print("\n=== Attempting to get annual data via company methods ===")
    # 或许可以通过 company 直接获取？但文档未明确，先尝试。
    # 有些库使用 company.financials.annual 等，但 secfin 可能不同。
    # 尝试使用 company.get_financials() 或类似? 目前未发现。

if __name__ == "__main__":
    main()
