# valueagents/agents/skills/policies/debate.py
"""
辩论停止判据（纯函数）。
从 graph/conditional_logic.should_continue_risk_analysis 抽离，供 meta skill 复用。
"""

from typing import Tuple


class DebatePolicy:

    @staticmethod
    def should_stop_risk(risk_state: dict, max_rounds: int) -> Tuple[bool, str]:
        """
        风险辩论停止判据（3 人 × N 轮）。

        Returns:
            (should_stop, reason)
        """
        count = risk_state.get("count", 0)
        if count >= 3 * max_rounds:
            return True, "max_rounds_reached"
        return False, ""
