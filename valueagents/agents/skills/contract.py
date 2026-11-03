# ./valueagents/agents/skills/contract.py
from pydantic import BaseModel
from enum import Enum
from typing import Any, Optional

class SkillKind(str, Enum):
    LEAF = "leaf"
    META = "meta"
    CORE = "core"   # 🆕 第 1 期新增：7 个流程模块

class SkillContext(BaseModel):
    ticker: str
    end_date: str
    artifacts: dict[str, Any]        # LangGraph state 的只读视图
    llm: Any                         # 主 LLM（带 callbacks）
    api_key: Optional[str] = None
    config: dict = {}
    model_config = {"arbitrary_types_allowed": True}

class SkillResult(BaseModel):
    outputs: dict[str, Any]          # 写回 state 的字段
    logs: list[str] = []
    metadata: dict = {}

class SkillManifest(BaseModel):
    name: str
    kind: SkillKind
    description: str
    requires: list[str] = []
    produces: list[str] = []
    composes: list[str] = []
    best_for: list[str] = []
    not_for: list[str] = []
    capabilities: list[str] = []
