
# valueagents/agents/skills/buffett_skill/skill.py
"""
Buffett Skill 的 Python 执行脚本。
负责调用原始 warren_buffett_agent，并将结果封装为 JSON。
"""

import json
from typing import Optional

# 从上级目录导入基础工具
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state
from valueagents.agents.src.analysts.warren_buffett import warren_buffett_agent


def execute(
    ticker: str,
    end_date: str,
    api_key: Optional[str] = None,
) -> str:
    """
    执行 Warren Buffett 分析，返回 JSON 字符串。
    
    Args:
        ticker: 股票代码，如 "AAPL"
        end_date: 分析截止日期，格式 "YYYY-MM-DD"
        api_key: Financial Datasets API Key（可选）
    
    Returns:
        JSON 字符串，包含 signal, confidence, reasoning
    """
    try:
        # 1. 构造最小化状态
        state = build_minimal_agent_state(ticker, end_date, api_key)
        
        # 2. 调用原始分析师节点
        # 注意：原始函数签名是 (state, agent_id) -> dict
        result_state = warren_buffett_agent(state, agent_id="buffett_skill")
        
        # 3. 提取信号
        signal_data = extract_signal_from_state(result_state, "buffett_skill", ticker)
        
        # 4. 组装输出
        output = {
            "ticker": ticker,
            "signal": signal_data["signal"],
            "confidence": signal_data["confidence"],
            "reasoning": signal_data["reasoning"],
        }
    except Exception as e:
        # 任何异常返回中性信号，并记录错误
        output = {
            "ticker": ticker,
            "signal": "neutral",
            "confidence": 0,
            "reasoning": f"Analysis failed: {str(e)}"
        }
    
    return json.dumps(output, ensure_ascii=False, indent=2)
