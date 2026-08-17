# valueagents/agents/skills/technical_skill/skill.py
"""
Technical Skill 的 Python 执行脚本。
负责调用原始 technical_analyst_agent，并将结果封装为 JSON。
"""

import json
from typing import Optional

# 使用绝对导入
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state
from valueagents.agents.src.analysts.technicals import technical_analyst_agent


def execute(
    ticker: str,
    start_date: str,
    end_date: str,
    api_key: Optional[str] = None,
) -> str:
    """
    执行技术分析，返回 JSON 字符串。
    
    Args:
        ticker: 股票代码，如 "AAPL"
        start_date: 历史数据开始日期，格式 "YYYY-MM-DD"
        end_date: 分析截止日期，格式 "YYYY-MM-DD"
        api_key: Financial Datasets API Key（可选）
    
    Returns:
        JSON 字符串，包含 signal, confidence, reasoning
    """
    try:
        # 1. 构造最小化状态（传入 start_date 和 end_date）
        state = build_minimal_agent_state(
            ticker=ticker,
            end_date=end_date,
            api_key=api_key,
            start_date=start_date,
        )
        
        # 2. 调用原始分析师节点
        result_state = technical_analyst_agent(state, agent_id="technical_skill")
        
        # 3. 提取信号
        signal_data = extract_signal_from_state(result_state, "technical_skill", ticker)
        
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