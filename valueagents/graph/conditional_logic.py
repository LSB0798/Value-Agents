# valueagents/graph/conditional_logic.py

from valueagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1, min_debate_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.min_debate_rounds = min_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"
    
    def should_continue_gnews(self, state: AgentState):
        """Determine if GNews analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_gnews"
        return "Msg Clear Gnews"
    
    def should_continue_alpha_news(self, state: AgentState):
        """Determine if Alpha News analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_alpha_news"
        return "Msg Clear Alpha_news"
    
    def should_continue_finnhub_news(self, state: AgentState):
        """Determine if Finnhub News analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_finnhub_news"
        return "Msg Clear Finnhub_news"
    
    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""

        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # 3 rounds of back-and-forth between 2 agents
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "Portfolio Manager"
        if state["risk_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"

    def should_continue_bull(self, state: AgentState) -> str:
        debate = state["investment_debate_state"]
        round_num = debate.get("current_round", 1)

        # Bull 完成时本轮尚未结束（Bear 还没说），必须进入 Bear
        # 仅做安全保护：如果轮数已异常超过 max，才停止
        if round_num > self.max_debate_rounds:
            debate["stop_reason"] = "max_rounds_reached"
            return "Research Manager"

        return "Bear Researcher"
    
    def should_continue_bear(self, state: AgentState) -> str:
        debate = state["investment_debate_state"]
        round_num = debate.get("current_round", 1)   # Bear 完成时 = 已完成轮数 + 1
        completed = round_num - 1                     # 🆕 已完成轮数

        # 硬下限：还没到 min
        if completed < self.min_debate_rounds:
            return "Bull Researcher"

        # 硬上限：已完成轮数达到 max
        if completed >= self.max_debate_rounds:
            debate["stop_reason"] = "max_rounds_reached"
            return "Research Manager"

        # 软判据：连续 2 轮双方都无新论点
        if debate.get("no_new_points_streak", 0) >= 1:
            debate["stop_reason"] = "argument_space_exhausted"
            return "Research Manager"

        return "Bull Researcher"
