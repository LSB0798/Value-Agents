# valueagents/agents/skills/registry.py
"""
SkillRegistry：skill 的单一真相源。

职责：
  1. 一次性加载所有 skills（带容错，委托给 loader）
  2. 提供分层查询 API
     - list_for_selection(): L1 视图，用于工具选择
     - get_meta(name):        单个 skill 的完整元信息（含 workflow）
     - get_tool(name):        可调用的 StructuredTool
  3. 全局单例缓存，避免 Bull/Bear 重复加载
"""

from pathlib import Path
from typing import Optional, Any

from valueagents.agents.skills.loader import load_all_skills


class SkillRegistry:
    """Skill 的单一真相源，提供 L1 选择视图和工具访问接口。"""

    def __init__(self, skills_root: Optional[Path] = None):
        if skills_root is None:
            skills_root = Path(__file__).parent
        self._root = skills_root
        self._tools: dict[str, Any] = {}   # name -> StructuredTool
        self._load()

    # ---------- 加载 ----------
    def _load(self):
        tools = load_all_skills(self._root)
        for t in tools:
            if not t.name:
                # 极端情况：name 为空，跳过避免字典键冲突
                print(f"[SkillRegistry] Skipping tool with empty name: {t}")
                continue
            self._tools[t.name] = t
        print(f"[SkillRegistry] Loaded {len(self._tools)} skills from {self._root}")

    # ---------- L1：工具选择视图 ----------
    def list_for_selection(self, exclude: Optional[set[str]] = None) -> list[dict]:
        """
        返回用于工具选择的 L1 视图。

        每个元素：
          {
            "name":         str,
            "description":  str,        # 120 字截断
            "best_for":     list[str],
            "not_for":      list[str],
            "capabilities": list[str],
          }
        """
        exclude = exclude or set()
        out: list[dict] = []
        for name, tool in self._tools.items():
            if name in exclude:
                continue
            md = tool.metadata or {}
            out.append({
                "name": name,
                "description": tool.description or "",
                "best_for": list(md.get("best_for", []) or []),
                "not_for": list(md.get("not_for", []) or []),
                "capabilities": list(md.get("capabilities", []) or []),
            })
        return out

    # ---------- 元信息查询 ----------
    def get_meta(self, name: str) -> Optional[dict]:
        """返回单个 skill 的元信息。找不到返回 None。"""
        tool = self._tools.get(name)
        if tool is None:
            return None
        md = tool.metadata or {}
        return {
            "name": name,
            "description": tool.description or "",
            "full_description": md.get("full_description", ""),
            "best_for": list(md.get("best_for", []) or []),
            "not_for": list(md.get("not_for", []) or []),
            "capabilities": list(md.get("capabilities", []) or []),
            "workflow": md.get("workflow", ""),
        }

    # ---------- 工具对象 ----------
    def get_tool(self, name: str):
        """返回 StructuredTool 对象；找不到返回 None。"""
        return self._tools.get(name)

    # ---------- 辅助 ----------
    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self):
        return len(self._tools)

    def __contains__(self, name: str):
        return name in self._tools


# ============================================================
# 全局单例缓存：Bull 和 Bear 共享同一个 registry
# ============================================================
_REGISTRY_CACHE: dict[str, SkillRegistry] = {}


def get_registry(skills_root: Optional[Path] = None) -> SkillRegistry:
    """
    获取全局单例。同一 skills_root 只会加载一次。
    """
    if skills_root is None:
        skills_root = Path(__file__).parent
    key = str(skills_root.resolve())
    if key not in _REGISTRY_CACHE:
        _REGISTRY_CACHE[key] = SkillRegistry(skills_root)
    return _REGISTRY_CACHE[key]
