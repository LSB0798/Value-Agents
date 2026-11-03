# valueagents/agents/skills/valuation_skill/skill.py
"""
Valuation Skill 的 Python 执行脚本。
负责调用原始 valuation_analyst_agent，并将结果封装为 JSON。
"""

import json
import re
from pathlib import Path
from typing import Optional

# 使用绝对导入
from valueagents.agents.skills.base import build_minimal_agent_state, extract_signal_from_state
from valueagents.agents.src.analysts.valuation import valuation_analyst_agent


def _load_workflow() -> str:
    """从本目录的 SKILL.md 中提取 ## Workflow 段落。找不到返回空串。"""
    md_path = Path(__file__).parent / "SKILL.md"
    if not md_path.exists():
        return ""
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception:
        return ""
    match = re.search(r"## Workflow\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return match.group(1).strip() if match else ""

def execute(
    ticker: str,
    end_date: str,
    api_key: Optional[str] = None,
) -> str:
    """
    执行综合估值分析，返回 JSON 字符串。
    
    Args:
        ticker: 股票代码，如 "AAPL"
        end_date: 分析截止日期，格式 "YYYY-MM-DD"
        api_key: Financial Datasets API Key（可选）
    
    Returns:
        JSON 字符串，包含 signal, confidence, reasoning
    """
    try:
        # 0. 读取 SKILL.md 的 Workflow
        workflow = _load_workflow()
        print(f"   [Skill: valuation] workflow length = {len(workflow)} chars")

        # 1. 构造最小化状态
        state = build_minimal_agent_state(ticker, end_date, api_key, skill_workflow=workflow)
        
        # 2. 调用原始分析师节点
        result_state = valuation_analyst_agent(state, agent_id="valuation_skill")
        
        # 3. 提取信号
        signal_data = extract_signal_from_state(result_state, "valuation_skill", ticker)
        
        # 4. 组装输出
        output = {
            "ticker": ticker,
            "signal": signal_data["signal"],
            "confidence": signal_data["confidence"],
            "reasoning": signal_data["reasoning"],
        }
    except Exception as e:
        output = {
            "ticker": ticker,
            "signal": "neutral",
            "confidence": 0,
            "reasoning": f"Analysis failed: {str(e)}"
        }
    
    return json.dumps(output, ensure_ascii=False, indent=2)