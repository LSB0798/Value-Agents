# valueagents/graph/adapter.py
import time

from valueagents.agents.skills.contract import SkillContext
from valueagents.agents.skills.runtime import set_current_llm, reset_current_llm   # 🆕


def _skill_name(skill) -> str:
    return getattr(skill, "name", None) or getattr(skill, "__name__", "?") or "?"


def skill_to_graph_node(skill, llm):
    name = _skill_name(skill)

    def node(state: dict) -> dict:
        _config = state.get("_config") or {}
        if name == "risk_team":
            print(f"[adapter] risk_team: _config from state = {_config}")

        ctx = SkillContext(
            ticker=state.get("company_of_interest", ""),
            end_date=state.get("trade_date", ""),
            artifacts=dict(state),
            llm=llm,
            api_key=(state.get("api_keys") or {}).get("FINANCIAL_DATASETS_API_KEY"),
            config=_config,
        )

        # 🆕 进入 skill 前设置 contextvars（覆盖 7 个 core skill 的内部调用）
        token = set_current_llm(llm)

        t0 = time.perf_counter()
        try:
            result = skill.func(ctx) if hasattr(skill, "func") else skill.execute(ctx)
        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f"   ⏱️  [skill] {name:24s}  {elapsed:7.2f}s  ❌ {type(e).__name__}: {e}")
            raise
        finally:
            # 🆕 无论成功失败都复位，避免污染后续节点
            reset_current_llm(token)

        elapsed = time.perf_counter() - t0
        outputs = dict(result.outputs)
        keys = list(outputs.keys())
        print(f"   ⏱️  [skill] {name:24s}  {elapsed:7.2f}s  outputs={keys}")

        return outputs

    return node