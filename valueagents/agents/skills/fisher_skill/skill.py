# valueagents/agents/skills/fisher_skill/skill.py
"""
Fisher Skill 的 Python 执行脚本。
负责调用原始 phil_fisher_agent，并将结果封装为 JSON。
"""

import json
from typing import Optional

# 使用绝对导入
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state
from valueagents.agents.src.analysts.phil_fisher import phil_fisher_agent


def execute(
    ticker: str,
    end_date: str,
    api_key: Optional[str] = None,
) -> str:
    """
    执行 Phil Fisher 分析，返回 JSON 字符串。
    
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
        result_state = phil_fisher_agent(state, agent_id="fisher_skill")
        
        # 3. 提取信号
        signal_data = extract_signal_from_state(result_state, "fisher_skill", ticker)
        
        # 4. 组装输出
        output = {
            "ticker": ticker,
            "signal": signal_data["signal"],
            "confidence": signal_data["confidence"],
            "reasoning": signal_data["reasoning"],
        }
    except Exception as e:
        # 任何异常返回中性信号
        output = {
            "ticker": ticker,
            "signal": "neutral",
            "confidence": 0,
            "reasoning": f"Analysis failed: {str(e)}"
        }
    
    return json.dumps(output, ensure_ascii=False, indent=2)