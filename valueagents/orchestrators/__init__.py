# valueagents/orchestrators/__init__.py
"""
valueagents.orchestrators — 对话式编排器（阶段 5）。

对外提供：
  - ConversationalOrchestrator: LLM 驱动 skill 调度的主循环
  - ArtifactStore: 中间产物黑板
  - SkillCatalog: skill 元数据（kind / requires / produces）
  - SkillAdapter: 统一调用大师 skill 与 core skill

设计原则：
  - 本包不 import valueagents.graph（避免与 graph 模式循环依赖）
  - skill 本身不改，Adapter 在运行时适配两种接口
  - 依赖懒加载（`__getattr__`），避免 import 本包时触发重依赖（LLM client / registry）
"""

from typing import Any

__all__ = [
    "ArtifactStore",
    "SkillCatalog",
    "SkillAdapter",
    "ConversationalOrchestrator",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """懒加载：只有真正访问时才 import 对应模块。"""
    if name == "ArtifactStore":
        from .artifact_store import ArtifactStore
        return ArtifactStore
    if name == "SkillCatalog":
        from .skill_catalog import SkillCatalog
        return SkillCatalog
    if name == "SkillAdapter":
        from .skill_adapter import SkillAdapter
        return SkillAdapter
    if name == "ConversationalOrchestrator":
        from .conversational import ConversationalOrchestrator
        return ConversationalOrchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
