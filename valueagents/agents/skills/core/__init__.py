# valueagents/agents/skills/core/__init__.py
"""
Core skills: 7 个流程模块的 skill 化实现。

目录约定：
    core/
    ├── __init__.py
    ├── market_analyst_skill/
    │   ├── SKILL.md       # frontmatter: name / kind / description / produces / ...
    │   └── skill.py       # 必须定义 execute(ctx: SkillContext) -> SkillResult
    ├── social_analyst_skill/
    └── ...

加载策略：
    - 延迟加载 + 缓存，避免循环 import
    - skill.py 用 importlib 加载，注入 sys.modules（防止 dataclass / pydantic 解析自身失败）
    - 本文件只 import contract（纯 schema），不 import valueagents.agents 下任何会触发循环的模块

用法（setup.py 里）：
    from valueagents.agents.skills.core import load_core_skill
    skill = load_core_skill("market_analyst_skill")
    node = skill_to_graph_node(skill, self.quick_thinking_llm)
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Optional


_CORE_ROOT = Path(__file__).parent
_CORE_SKILL_CACHE: dict[str, "CoreSkill"] = {}

# 允许的 skill 目录名后缀
_SKILL_DIR_SUFFIX = "_skill"


# ============================================================
# CoreSkill 包装
# ============================================================

class CoreSkill:
    """
    core skill 的薄包装。

    为什么不用 StructuredTool：
        - 输入是 SkillContext（不是 ticker/end_date 三个参数）
        - 不需要 bind_tools（内部自己走 tool loop）
        - setup.py 只需要 .name + .execute
    """

    __slots__ = ("name", "execute", "manifest", "module", "path")

    def __init__(
        self,
        name: str,
        execute,
        manifest: dict,
        module,
        path: Path,
    ):
        self.name = name
        self.execute = execute
        self.manifest = manifest
        self.module = module
        self.path = path

    def __repr__(self) -> str:
        return f"<CoreSkill {self.name} at {self.path.name}>"


# ============================================================
# SKILL.md frontmatter 解析
# ============================================================

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_manifest(md_text: str) -> dict:
    """从 SKILL.md 顶部 YAML frontmatter 提取元信息。失败返回 {}。"""
    m = _FRONTMATTER_RE.match(md_text)
    if not m:
        return {}
    try:
        import yaml  # 局部 import，避免启动时依赖
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[CoreSkill] Warning: failed to parse frontmatter: {e}")
        return {}


def _validate_manifest(manifest: dict, fallback_name: str) -> dict:
    """补全缺失字段；name 缺失时用目录名兜底。"""
    out = dict(manifest)
    out.setdefault("name", fallback_name)
    out.setdefault("kind", "core")
    out.setdefault("description", "")
    out.setdefault("requires", [])
    out.setdefault("produces", [])
    return out


# ============================================================
# 单目录加载
# ============================================================

def _load_from_dir(skill_dir: Path) -> Optional[CoreSkill]:
    py_file = skill_dir / "skill.py"
    md_file = skill_dir / "SKILL.md"

    if not py_file.exists():
        print(f"[CoreSkill] Skip {skill_dir.name}: missing skill.py")
        return None

    # 1) manifest
    manifest: dict = {}
    if md_file.exists():
        try:
            manifest = _parse_manifest(md_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[CoreSkill] Warning: cannot read {md_file}: {e}")
    else:
        print(f"[CoreSkill] Warning: {skill_dir.name} has no SKILL.md, using defaults")

    manifest = _validate_manifest(manifest, skill_dir.name)

    # 2) 动态加载 skill.py
    #    用扁平 module_name，避免 "valueagents.agents.skills.core.xxx" 父模块缺失问题
    module_name = f"_core_skill__{skill_dir.name}"
    if module_name in sys.modules:
        # 已加载过（理论上不应发生，因为我们在 _CORE_SKILL_CACHE 里已缓存）
        module = sys.modules[module_name]
    else:
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            print(f"[CoreSkill] Skip {skill_dir.name}: cannot create spec")
            return None

        module = importlib.util.module_from_spec(spec)
        # 必须注入 sys.modules：pydantic / dataclass 在类定义时会反查 __module__
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"[CoreSkill] Failed to load {skill_dir.name}: {type(e).__name__}: {e}")
            sys.modules.pop(module_name, None)
            return None

    # 3) 校验 execute
    execute_fn = getattr(module, "execute", None)
    if execute_fn is None or not callable(execute_fn):
        print(f"[CoreSkill] Skip {skill_dir.name}: skill.py must define execute(ctx)")
        sys.modules.pop(module_name, None)
        return None

    return CoreSkill(
        name=manifest["name"],
        execute=execute_fn,
        manifest=manifest,
        module=module,
        path=skill_dir,
    )


# ============================================================
# 对外 API
# ============================================================

def _normalize_dir_name(name: str) -> str:
    """'market_analyst' -> 'market_analyst_skill'；已带后缀则不动。"""
    if name.endswith(_SKILL_DIR_SUFFIX):
        return name
    return f"{name}{_SKILL_DIR_SUFFIX}"


def load_core_skill(skill_name: str) -> Optional[CoreSkill]:
    """
    按名字加载单个 core skill（带缓存）。

    Args:
        skill_name: 目录名或 skill 名，例如 "market_analyst_skill" 或 "market_analyst"

    Returns:
        CoreSkill 或 None
    """
    dir_name = _normalize_dir_name(skill_name)

    if dir_name in _CORE_SKILL_CACHE:
        return _CORE_SKILL_CACHE[dir_name]

    skill_dir = _CORE_ROOT / dir_name
    if not skill_dir.is_dir():
        print(f"[CoreSkill] Not found: {skill_dir}")
        return None

    skill = _load_from_dir(skill_dir)
    if skill is not None:
        _CORE_SKILL_CACHE[dir_name] = skill
    return skill


def load_all_core_skills() -> dict[str, CoreSkill]:
    """
    加载 core/ 下所有合法 skill。返回 {skill.name: CoreSkill}。

    用于诊断 / registry 注册（第 2 期）。
    """
    result: dict[str, CoreSkill] = {}
    if not _CORE_ROOT.is_dir():
        return result

    for sub in sorted(_CORE_ROOT.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name.startswith("_") or sub.name.startswith("."):
            continue
        if not (sub / "skill.py").exists():
            continue
        skill = load_core_skill(sub.name)
        if skill is not None:
            result[skill.name] = skill
    return result


def list_core_skill_names() -> list[str]:
    """列出 core/ 下所有合法 skill 目录名（不触发 importlib 加载）。"""
    names: list[str] = []
    if not _CORE_ROOT.is_dir():
        return names
    for sub in sorted(_CORE_ROOT.iterdir()):
        if (
            sub.is_dir()
            and not sub.name.startswith("_")
            and not sub.name.startswith(".")
            and (sub / "skill.py").exists()
        ):
            names.append(sub.name)
    return names


def clear_cache() -> None:
    """
    清空加载缓存（开发调试用）。

    注意：不清 sys.modules，因为下游可能已经持有 module 引用；
    若确实要热重载，需同时 pop sys.modules 并重建 graph。
    """
    _CORE_SKILL_CACHE.clear()


__all__ = [
    "CoreSkill",
    "load_core_skill",
    "load_all_core_skills",
    "list_core_skill_names",
    "clear_cache",
]
