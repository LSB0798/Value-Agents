# valueagents/agents/hf_analysts_wrapper.py

import json
from typing import Dict, Any
from valueagents.agents.utils.agent_states import AgentState
from valueagents.agents.src.analysts import (
    ben_graham_agent,
    warren_buffett_agent,
    peter_lynch_agent,
    phil_fisher_agent,
    charlie_munger_agent,
    michael_burry_agent,
    aswath_damodaran_agent,
    cathie_wood_agent,
    bill_ackman_agent,
    rakesh_jhunjhunwala_agent,
    mohnish_pabrai_agent,
    nassim_taleb_agent,
    stanley_druckenmiller_agent,
    technical_analyst_agent,
    fundamentals_analyst_agent,
    growth_analyst_agent,
    news_sentiment_agent,
    sentiment_analyst_agent,
    valuation_analyst_agent,
)
from valueagents.agents.src.utils.llm import call_llm as hf_call_llm
from valueagents.agents.src.llm.models import get_model
from valueagents.agents.src.utils.api_key import get_api_key_from_state
import sys
import os

# 将 src 的路径加入 sys.path 以便内部导入（如 src.tools.api）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 我们需要一个适配函数：将 ValueAgents 的 state 转换为 hf_agent 期望的 state
def adapt_state_to_hf(ta_state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    将 ValueAgents 的状态转换为 ai-hedge-fund 分析师所期望的 AgentState 结构。
    """
    # ValueAgents 的状态中关键字段
    ticker = ta_state.get("company_of_interest", "")
    trade_date = ta_state.get("trade_date", "")

    # 🆕 计算 start_date = trade_date - 365 天（技术分析师需要历史数据）
    start_date = trade_date
    if trade_date:
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(trade_date, "%Y-%m-%d")
            start_date = (dt - timedelta(days=365)).strftime("%Y-%m-%d")
        except Exception:
            start_date = trade_date
    
    # 构建 hf 风格的 data 字段
    hf_data = {
        "tickers": [ticker],
        "start_date": start_date,   # 🆕 -365 天
        "end_date": trade_date,
        "portfolio": {},
        "analyst_signals": {},
        "current_prices": {},
    }
    
    # 构建 metadata
    hf_metadata = {
        "show_reasoning": False,
        "model_name": llm.model_name if hasattr(llm, "model_name") else "qwen3.6-27B",
        "model_provider": "openai",
        "llm": llm,
    }
    
    # 创建 hf 的 messages（空或占位）
    from langchain_core.messages import HumanMessage
    hf_messages = [HumanMessage(content=f"Analyze {ticker}")] if ticker else []

    return {
        "messages": hf_messages,
        "data": hf_data,
        "metadata": hf_metadata,
    }

def adapt_hf_result_to_state(ta_state: Dict[str, Any], hf_result: Dict[str, Any], agent_name: str) -> Dict[str, Any]:
    """
    将 hf 分析师返回的结果合并到 ValueAgents 的状态中。
    """
    # hf_result 通常包含 {"messages": [HumanMessage], "data": state["data"]}
    # 其中 state["data"]["analyst_signals"][agent_name] 包含了信号
    if "data" in hf_result and "analyst_signals" in hf_result["data"]:
        signals = hf_result["data"]["analyst_signals"]
        if agent_name in signals:
            ta_state.setdefault("master_analyst_signals", {})[agent_name] = signals[agent_name]
    return ta_state

def create_master_analyst_node(analyst_func, agent_id: str, llm):
    """通用的包装工厂"""
    def node(state: Dict[str, Any]):
        hf_state = adapt_state_to_hf(state, llm)
        result = analyst_func(hf_state, agent_id=agent_id)

        signals = {}
        if "data" in result and "analyst_signals" in result["data"]:
            if agent_id in result["data"]["analyst_signals"]:
                signals = {agent_id: result["data"]["analyst_signals"][agent_id]}
                # 🆕 精简打印（去掉 !!! / ~~~ 和 reasoning 内容）
                for ticker, sig in signals[agent_id].items():
                    print(f"   ✅ {agent_id} -> {ticker}: "
                          f"{sig.get('signal', 'N/A')} (conf: {sig.get('confidence', 0)})")
        else:
            print(f"   ⚠️ {agent_id} returned no signals")

        # 🆕 关键：只返回需要更新的字段（增量更新）
        return {"master_analyst_signals": signals}

    return node

# 为每个分析师生成节点
def create_ben_graham_node(llm):
    return create_master_analyst_node(ben_graham_agent, "ben_graham_agent", llm)

def create_warren_buffett_node(llm):
    return create_master_analyst_node(warren_buffett_agent, "warren_buffett_agent", llm)

# ... 其他类似，可以写一个字典映射
MASTER_ANALYST_MAP = {
    "ben_graham": ben_graham_agent,
    "warren_buffett": warren_buffett_agent,
    "peter_lynch": peter_lynch_agent,
    "phil_fisher": phil_fisher_agent,
    "charlie_munger": charlie_munger_agent,
    "michael_burry": michael_burry_agent,
    "aswath_damodaran": aswath_damodaran_agent,
    "cathie_wood": cathie_wood_agent,
    "bill_ackman": bill_ackman_agent,
    "rakesh_jhunjhunwala": rakesh_jhunjhunwala_agent,
    "mohnish_pabrai": mohnish_pabrai_agent,
    "nassim_taleb": nassim_taleb_agent,
    "stanley_druckenmiller": stanley_druckenmiller_agent,
    "technical_analyst": technical_analyst_agent,
    "fundamentals_analyst": fundamentals_analyst_agent,
    "growth_analyst": growth_analyst_agent,
    "news_sentiment_analyst": news_sentiment_agent,
    "sentiment_analyst": sentiment_analyst_agent,
    "valuation_analyst": valuation_analyst_agent,
}

def _normalize_master_name(name: str) -> str:
    """接受 'warren_buffett' 或 'warren_buffett_analyst' 两种输入，统一成 'warren_buffett'。
    
    这是为了同时兼容：
      - SkillCatalog 里的 name（'warren_buffett_analyst'）
      - MASTER_ANALYST_MAP 里的 key（'warren_buffett'）
    """
    if name and name.endswith("_analyst"):
        return name[:-len("_analyst")]
    return name

def get_master_analyst_node(name: str, llm):
    """根据 master 名创建 graph 节点。
    
    接受 'warren_buffett' 或 'warren_buffett_analyst' 两种输入。
    """
    normalized = _normalize_master_name(name)
    if normalized not in MASTER_ANALYST_MAP:
        raise ValueError(
            f"Unknown master analyst: {name!r} (normalized: {normalized!r}). "
            f"Available: {sorted(MASTER_ANALYST_MAP.keys())}"
        )
    # 🆕 agent_id 用 normalized + '_agent'，如 'warren_buffett_agent'
    return create_master_analyst_node(
        MASTER_ANALYST_MAP[normalized],
        f"{normalized}_agent",
        llm,
    )