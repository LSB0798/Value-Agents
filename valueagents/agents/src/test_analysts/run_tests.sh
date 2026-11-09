#!/bin/bash

# 测试文件列表
tests=(
    "test_cache_quarters.py"
    "test_technical_analyst.py"
    "test_sentiment_format.py"
    "test_sentiment_analyst.py"
    "test_risk_manager.py"
    "test_phil_fisher_agent.py"
    "test_line_items_cache.py"
    "test_insider_cache.py"
    "test_news_cache.py"
    "test_yf_prices_cache.py"
    "test_edgar_cache.py"
    "test_yf_cache.py"
    "test_roic_cache.py"
    "test_charlie_munger_agent.py"
    "test_charlie_munger.py"
    "test_cathie_wood.py"
    "test_bill_ackman.py"
    "test_valuation.py"
    "test_warren_buffett.py"
    "test_bill_ackman_debug.py"
    "test_rakesh.py"
    "test_stanley_druckenmiller.py"
    "test_tmp.py"
    "test_roic_cashflow_fields.py"
    "test_damodaran_debug.py"
    "test_yfinance_cashflow.py"
    "test_prices_api.py"
    "test_prices.py"
)

tests2=(
    "diagnose_ttm_roe.py"
    "explore_alpha_vantage.py"
    "test_api_ttm.py"
    "test_ben_graham_debug.py"
    "test_ben_graham_dividend_flow.py"
    "test_ben_graham.py"
    "test_damodaran_analysis.py"
    "test_edgar_fields.py"
    "test_edgar_ttm_final.py"
    "test_edgar_ttm.py"
    "test_eps_yf.py"
    "test_fundamentals_analyst_agent.py"
    "test_fundamentals.py"
    "test_growth_agent.py"
    "test_growth_trend.py"
    "test_interest_expense.py"
    "test_michael_burry.py"
    "test_mohnish_pabrai.py"
    "test_nassim_taleb.py"
    "test_peter_lynch_agent.py"
    "test_peter_lynch.py"
    "test_phil_fisher.py"
    "test_roic_fields.py"
    "test_roic_ttm_fields.py"
    "test_search_line_items_ttm.py"
    "test_secfin_quarterly.py"
    "test_tool_data_sources_for_munger.py"
    "test_tool_dividend_detection.py"
    "test_tool_edgar_data_depth.py"
    "test_tool_edgar_data.py"
    "test_tool_financial_metrics_fields.py"
    "test_tool_finnhub_insider_news.py"
    "test_tool_finnhub_pe0.py"
    "test_tool_finnhub_pe.py"
    "test_tool_roic_api.py"
    "test_tool_secfinapi1.py"
    "test_tool_secfinapi2.py"
    "test_tool_secfin_api.py"
    "test_tool_secfinapi_ratios.py"
    "test_tool_secfin_dataframe.py"
    "test_tsla_roic_fields.py"
    "test_ttm_methods.py"
    "test_ttm_roe_after_fix.py"
    "test_ttm_synthesis.py"
    "test_yfinance.py"
    "test_yfinance_quarterly.py"
)

echo "========== 开始批量测试 =========="
failed=()

for file in "${tests[@]}"; do
    echo ""
    echo ">>> 正在运行: $file"
    python "$file"
    exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        echo "!!! [ERROR] $file 运行失败 (exit code: $exit_code)"
        failed+=("$file")
    else
        echo "✓ $file 通过"
    fi
done

echo ""
echo "========== 测试完成 =========="
if [ ${#failed[@]} -eq 0 ]; then
    echo "所有测试全部通过！"
else
    echo "以下 ${#failed[@]} 个文件运行失败："
    for f in "${failed[@]}"; do
        echo "  - $f"
    done
fi
