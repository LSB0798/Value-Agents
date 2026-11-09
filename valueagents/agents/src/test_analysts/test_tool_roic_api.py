#!/usr/bin/env python
"""
测试 ROIC.ai API 获取 ROIC 数据
需要设置环境变量 ROIC_API_KEY 或直接填入下方
"""

import os
import sys
import json
import requests
from pprint import pprint

# ===== 配置 =====
# 优先从环境变量读取，若未设置则使用硬编码（请替换为您的 key）
API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
TICKER = "AAPL"
BASE_URL = "https://api.roic.ai"

def test_profitability_ratios(ticker):
    """获取盈利能力比率（包含 ROIC、ROE、ROA 等）"""
    # 正确的端点：v2/fundamental/ratios/profitability/{identifier}
    url = f"{BASE_URL}/v2/fundamental/ratios/profitability/{ticker}"
    params = {
        "apikey": API_KEY,
        "period": "annual",      # 年度数据
        "limit": 5,              # 返回最近 5 个周期
        "order": "DESC"          # 按时间降序（最新的在前）
    }
    
    print(f"\n🔍 请求 URL: {url}")
    print(f"📊 参数: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print("\n✅ 成功获取数据！")
        print("=" * 60)
        
        if isinstance(data, list) and len(data) > 0:
            print(f"📋 返回 {len(data)} 条记录")
            print("\n📊 盈利能力比率数据:")
            for i, item in enumerate(data):
                print(f"\n--- 记录 {i+1} (年份: {item.get('period_label', 'N/A')}) ---")
                print(f"  📈 ROIC (return_on_inv_capital): {item.get('return_on_inv_capital')}")
                print(f"  📈 ROE (return_com_eqy): {item.get('return_com_eqy')}")
                print(f"  📈 ROA (return_on_asset): {item.get('return_on_asset')}")
                print(f"  📈 ROC (return_on_cap): {item.get('return_on_cap')}")
                print(f"  📊 毛利率 (gross_margin): {item.get('gross_margin')}")
                print(f"  📊 营业利润率 (oper_margin): {item.get('oper_margin')}")
                print(f"  📊 净利润率 (profit_margin): {item.get('profit_margin')}")
                print(f"  💰 有效税率 (eff_tax_rate): {item.get('eff_tax_rate')}")
                print(f"  📅 报告日期: {item.get('date')}")
                print(f"  📅 财年: {item.get('fiscal_year')}")
            
            # 提取最新的 ROIC
            latest_roic = data[0].get('return_on_inv_capital')
            print(f"\n🎯 最新 ROIC: {latest_roic}")
            return data
        else:
            print("⚠️ 返回数据为空或格式异常")
            pprint(data, indent=2, width=100)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应内容: {e.response.text[:500]}")
        return None

def test_company_profile(ticker):
    """获取公司简介（验证 API 是否正常工作）"""
    url = f"{BASE_URL}/v2/company/profile/{ticker}"
    params = {"apikey": API_KEY}
    
    print(f"\n🔍 测试公司简介端点: {url}")
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # 处理可能的列表返回
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]  # 取第一个（通常唯一）
                    print("✅ 公司简介获取成功（从列表中提取）")
                else:
                    print("⚠️ 返回空列表")
                    return None
            else:
                print("✅ 公司简介获取成功")
            
            print(f"  公司名称: {data.get('name')}")
            print(f"  行业: {data.get('industry')}")
            print(f"  市值: {data.get('market_cap')}")
            return data
        else:
            print(f"⚠️ 返回状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 公司简介请求失败: {e}")
        return None

if __name__ == "__main__":
    if not API_KEY or API_KEY == "your_roic_api_key_here":
        print("⚠️ 请先设置 ROIC_API_KEY 环境变量，或修改脚本中的 API_KEY 变量。")
        print("示例: export ROIC_API_KEY='your_key_here'")
        sys.exit(1)
    
    print(f"🧪 测试 ROIC.ai API 获取 {TICKER} 的数据")
    print(f"🔑 使用 API Key: {API_KEY[:8]}...")
    
    # 1. 先测试公司简介（验证 API 是否正常工作）
    print("\n" + "=" * 60)
    test_company_profile(TICKER)
    
    # 2. 获取盈利能力比率（包含 ROIC）
    print("\n" + "=" * 60)
    data = test_profitability_ratios(TICKER)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")