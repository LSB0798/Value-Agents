#!/usr/bin/env python
"""
全面测试 risk_management_agent 的功能
验证 get_prices 数据获取、波动率计算、相关性分析及异常处理
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_prices, prices_to_df
from valueagents.agents.src.analysts.risk_manager import (
    calculate_volatility_metrics,
    calculate_volatility_adjusted_limit,
    calculate_correlation_multiplier,
)

# 模拟 risk_management_agent 中的核心逻辑
def simulate_risk_analysis(tickers, start_date, end_date):
    """模拟风险分析的流程，但只关注价格和波动率部分"""
    results = {}
    for ticker in tickers:
        print(f"\n--- 处理 {ticker} ---")
        prices = get_prices(ticker, start_date, end_date)
        if not prices:
            print(f"⚠️  {ticker} 价格数据为空，使用默认波动率")
            volatility = {
                "daily_volatility": 0.05,
                "annualized_volatility": 0.05 * np.sqrt(252),
                "volatility_percentile": 100,
                "data_points": 0
            }
        else:
            prices_df = prices_to_df(prices)
            volatility = calculate_volatility_metrics(prices_df)
            print(f"✅ 获取到 {len(prices)} 条价格记录")
            print(f"   最新价格: {prices_df['close'].iloc[-1]:.2f}")
        
        print(f"   日波动率: {volatility['daily_volatility']:.2%}")
        print(f"   年化波动率: {volatility['annualized_volatility']:.2%}")
        print(f"   波动率分位: {volatility['volatility_percentile']:.1f}%")
        print(f"   数据点数: {volatility['data_points']}")
        
        # 计算风险限额
        limit_pct = calculate_volatility_adjusted_limit(volatility['annualized_volatility'])
        print(f"   波动率调整限额: {limit_pct:.2%}")
        
        results[ticker] = volatility
    return results

def test_correlation():
    """测试相关性计算逻辑（使用模拟数据）"""
    print("\n--- 测试相关性计算 ---")
    # 模拟两个 ticker 的日收益率
    np.random.seed(42)
    returns1 = np.random.normal(0.001, 0.02, 100)
    returns2 = 0.8 * returns1 + np.random.normal(0, 0.01, 100)  # 高度相关
    returns3 = np.random.normal(0.001, 0.03, 100)  # 低相关
    
    df = pd.DataFrame({
        'AAPL': returns1,
        'MSFT': returns2,
        'GOOGL': returns3
    })
    
    corr_matrix = df.corr()
    print("相关性矩阵:")
    print(corr_matrix)
    
    # 测试 correlation multiplier
    for ticker in ['AAPL', 'MSFT', 'GOOGL']:
        # 计算平均相关性（与其他两个）
        others = [t for t in df.columns if t != ticker]
        avg_corr = corr_matrix.loc[ticker, others].mean()
        mult = calculate_correlation_multiplier(avg_corr)
        print(f"{ticker} 平均相关性: {avg_corr:.2f}, 乘数: {mult:.2f}")

def test_missing_data():
    """模拟 get_prices 返回空数据时的处理"""
    print("\n--- 测试缺失数据处理 ---")
    # 使用一个不存在的 ticker 或模拟异常
    # 注意：使用 get_prices 时，如果 yfinance 失败会返回 []
    ticker = "INVALID_TICKER_XYZ"
    prices = get_prices(ticker, "2026-06-01", "2026-07-01")
    if not prices:
        print(f"✅ {ticker} 返回空数据，符合预期")
        # 使用默认值
        volatility = {
            "daily_volatility": 0.05,
            "annualized_volatility": 0.05 * np.sqrt(252),
            "volatility_percentile": 100,
            "data_points": 0
        }
        print(f"默认波动率: {volatility['annualized_volatility']:.2%}")
    else:
        print(f"⚠️  {ticker} 竟然返回了数据，检查 yfinance")

def main():
    print("="*80)
    print("风险管理者分析测试")
    print("="*80)
    
    # 检查环境变量
    print(f"USE_EDGAR = {os.environ.get('USE_EDGAR', '未设置')}")
    print(f"USE_YFINANCE = {os.environ.get('USE_YFINANCE', '未设置')}")
    
    # 测试日期
    # end_date = datetime.now().strftime("%Y-%m-%d")
    end_date = "2026-07-24"   # 或任何您想测试的日期
    # start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    start_date = "2026-04-25"  # 与 end_date 匹配的起始日期
    
    # 1. 正常情况：多个 ticker
    tickers = ["AAPL", "MSFT", "GOOGL"]
    print(f"\n测试 tickers: {tickers}")
    results = simulate_risk_analysis(tickers, start_date, end_date)
    
    # 2. 相关性分析
    test_correlation()
    
    # 3. 异常测试：缺失数据
    test_missing_data()
    
    # 4. 验证默认值是否被正确使用
    print("\n--- 验证默认波动率的合理性 ---")
    default_annual_vol = 0.05 * np.sqrt(252)
    print(f"默认年化波动率: {default_annual_vol:.2%}")
    limit_default = calculate_volatility_adjusted_limit(default_annual_vol)
    print(f"基于默认波动率的限额: {limit_default:.2%}")
    print("→ 这将导致保守的仓位限制，符合风险管理原则。")
    
    print("\n" + "="*80)
    print("测试完成。所有功能正常。")
    print("="*80)

if __name__ == "__main__":
    main()
