#!/usr/bin/env python
"""
全面测试 technical_analyst_agent 的功能
验证 get_prices 数据获取、各技术指标计算及信号合成
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_prices, prices_to_df
from valueagents.agents.src.analysts.technicals import (
    calculate_trend_signals,
    calculate_mean_reversion_signals,
    calculate_momentum_signals,
    calculate_volatility_signals,
    calculate_stat_arb_signals,
    weighted_signal_combination,
)

def test_technical_for_ticker(ticker, start_date, end_date):
    """模拟 technical_analyst_agent 的核心逻辑，打印各指标和最终信号"""
    print(f"\n=== 测试 {ticker} ===")
    
    # 1. 获取价格数据
    print("--- 获取价格数据 ---")
    prices = get_prices(ticker, start_date, end_date)
    if not prices:
        print("  ❌ 无价格数据，跳过")
        return None
    prices_df = prices_to_df(prices)
    print(f"  ✅ 获取到 {len(prices_df)} 条价格记录")
    print(f"  最新价格: {prices_df['close'].iloc[-1]:.2f}")
    
    # 2. 计算各策略信号
    print("\n--- 趋势信号 ---")
    trend = calculate_trend_signals(prices_df)
    print(f"  信号: {trend['signal']}, 置信度: {trend['confidence']:.2f}")
    print(f"  指标: ADX={trend['metrics']['adx']:.2f}, 趋势强度={trend['metrics']['trend_strength']:.2f}")
    
    print("\n--- 均值回归信号 ---")
    mean_rev = calculate_mean_reversion_signals(prices_df)
    print(f"  信号: {mean_rev['signal']}, 置信度: {mean_rev['confidence']:.2f}")
    print(f"  指标: Z-score={mean_rev['metrics']['z_score']:.2f}, 价格vs布林={mean_rev['metrics']['price_vs_bb']:.2f}")
    print(f"  RSI(14)={mean_rev['metrics']['rsi_14']:.2f}, RSI(28)={mean_rev['metrics']['rsi_28']:.2f}")
    
    print("\n--- 动量信号 ---")
    momentum = calculate_momentum_signals(prices_df)
    print(f"  信号: {momentum['signal']}, 置信度: {momentum['confidence']:.2f}")
    print(f"  指标: 1月动量={momentum['metrics']['momentum_1m']:.4f}, 3月={momentum['metrics']['momentum_3m']:.4f}, 6月={momentum['metrics']['momentum_6m']:.4f}")
    print(f"  成交量动量={momentum['metrics']['volume_momentum']:.2f}")
    
    print("\n--- 波动率信号 ---")
    vol = calculate_volatility_signals(prices_df)
    print(f"  信号: {vol['signal']}, 置信度: {vol['confidence']:.2f}")
    print(f"  指标: 历史波动率={vol['metrics']['historical_volatility']:.4f}, 波动率制度={vol['metrics']['volatility_regime']:.2f}")
    print(f"  Z-score={vol['metrics']['volatility_z_score']:.2f}, ATR比率={vol['metrics']['atr_ratio']:.4f}")
    
    print("\n--- 统计套利信号 ---")
    stat_arb = calculate_stat_arb_signals(prices_df)
    print(f"  信号: {stat_arb['signal']}, 置信度: {stat_arb['confidence']:.2f}")
    print(f"  指标: Hurst指数={stat_arb['metrics']['hurst_exponent']:.2f}, 偏度={stat_arb['metrics']['skewness']:.2f}, 峰度={stat_arb['metrics']['kurtosis']:.2f}")
    
    # 3. 合成最终信号
    print("\n--- 合成信号 ---")
    strategy_weights = {
        "trend": 0.25,
        "mean_reversion": 0.20,
        "momentum": 0.25,
        "volatility": 0.15,
        "stat_arb": 0.15,
    }
    signals = {
        "trend": trend,
        "mean_reversion": mean_rev,
        "momentum": momentum,
        "volatility": vol,
        "stat_arb": stat_arb,
    }
    combined = weighted_signal_combination(signals, strategy_weights)
    print(f"  最终信号: {combined['signal']}, 置信度: {combined['confidence']:.2f}")
    
    # 4. 合理性检查
    print("\n--- 合理性检查 ---")
    # 检查各置信度是否在 0-1 之间
    all_confidences = [trend['confidence'], mean_rev['confidence'], momentum['confidence'], vol['confidence'], stat_arb['confidence']]
    if all(0 <= c <= 1 for c in all_confidences):
        print("  ✅ 所有单策略置信度在 0-1 范围内")
    else:
        print("  ⚠️  有置信度超出 0-1 范围")
    if 0 <= combined['confidence'] <= 1:
        print("  ✅ 最终置信度在 0-1 范围内")
    else:
        print("  ⚠️  最终置信度超出 0-1 范围")
    # 检查信号类型
    valid_signals = {'bullish', 'bearish', 'neutral'}
    if all(s['signal'] in valid_signals for s in signals.values()):
        print("  ✅ 所有信号类型有效")
    else:
        print("  ⚠️  有信号类型无效")
    return combined

def test_edge_cases():
    """测试边缘情况：数据不足或无效 ticker"""
    print("\n" + "="*80)
    print("测试边缘情况：数据不足（最近日期）")
    print("="*80)
    # 用很短的时间区间模拟数据不足
    start = "2026-07-20"
    end = "2026-07-24"
    ticker = "AAPL"
    prices = get_prices(ticker, start, end)
    if prices:
        prices_df = prices_to_df(prices)
        print(f"获取到 {len(prices_df)} 条数据（少于50条），测试指标计算...")
        try:
            # 尝试调用函数，它们可能会处理不足数据
            trend = calculate_trend_signals(prices_df)
            print("  ✅ 趋势信号函数未崩溃")
        except Exception as e:
            print(f"  ❌ 趋势信号函数出错: {e}")
        # 其他函数类似，不再逐一测试，因为实际中会跳过该ticker
    
    print("\n测试无效 ticker:")
    prices = get_prices("INVALID_TICKER_XYZ", "2026-07-01", "2026-07-24")
    if not prices:
        print("  ✅ 无效 ticker 返回空数据，符合预期")
    else:
        print("  ⚠️  无效 ticker 竟返回数据")

def main():
    print("测试 Technical Analyst 数据流和指标计算")
    print(f"USE_EDGAR = {os.environ.get('USE_EDGAR', '未设置')}")
    print(f"USE_YFINANCE = {os.environ.get('USE_YFINANCE', '未设置')}")
    
    start_date = "2025-07-25"
    end_date = "2026-07-24"
    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = {}
    for ticker in tickers:
        results[ticker] = test_technical_for_ticker(ticker, start_date, end_date)
    
    # 汇总
    print("\n" + "="*80)
    print("汇总结果")
    print("="*80)
    for ticker, res in results.items():
        if res:
            print(f"{ticker}: 信号={res['signal']}, 置信度={res['confidence']:.2f}")
        else:
            print(f"{ticker}: 数据缺失，跳过")
    
    # 边缘测试
    test_edge_cases()
    
    print("\n所有测试完成。")

if __name__ == "__main__":
    main()
