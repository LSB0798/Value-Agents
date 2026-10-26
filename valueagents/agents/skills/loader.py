# valueagents/agents/skills/loader.py
import importlib.util
import re
from pathlib import Path
from typing import List, Optional, Callable, Any, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field
import yaml


def _extract_workflow(body: str) -> str:
    """从 SKILL.md body 中提取 ## Workflow 段落内容。"""
    match = re.search(r"## Workflow\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    return match.group(1).strip() if match else ""

def _safe_list(
    metadata: Dict[str, Any],
    field_name: str,
    max_item_len: int = 80,
) -> list[str]:
    """
    安全解析 YAML frontmatter 中的 list 类型字段。

    行为：
      - 字段缺失 / None → 返回 []
      - 字段是单个字符串 → 包装为单元素列表
      - 字段不是 list → 打印警告并返回 []
      - 列表中的非字符串项被丢弃
      - 每项做 strip()，空项被丢弃
      - 超过 max_item_len 的项截断并加 "..."
    """
    raw = metadata.get(field_name, [])
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        print(
            f"[Skills] Warning: '{field_name}' must be a list, "
            f"got {type(raw).__name__}"
        )
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s:
            continue
        if len(s) > max_item_len:
            s = s[: max_item_len - 3] + "..."
        out.append(s)
    return out

def _parse_skill_metadata(md_content: str) -> Dict[str, Any]:
    # 用正则匹配开头的 YAML frontmatter（避免 split("---") 被正文中的表格分隔线干扰）
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", md_content, re.DOTALL)
    if not fm_match:
        raise ValueError("SKILL.md must contain YAML frontmatter (--- ... ---)")

    yaml_text = fm_match.group(1)
    body = fm_match.group(2).strip()

    metadata = yaml.safe_load(yaml_text)
    if not isinstance(metadata, dict):
        raise ValueError("Invalid YAML frontmatter in SKILL.md")

    # ─────────────────────────────────────────────────────────────
    # 🆕 解析 L1 决策元信息（best_for / not_for / capabilities）
    # ─────────────────────────────────────────────────────────────
    best_for = _safe_list(metadata, "best_for")
    not_for = _safe_list(metadata, "not_for")
    capabilities = _safe_list(metadata, "capabilities")

    # 缺失只警告，不报错（保持向后兼容）
    skill_name_for_log = metadata.get("name") or "<unnamed>"
    for fname, val in (
        ("best_for", best_for),
        ("not_for", not_for),
        ("capabilities", capabilities),
    ):
        if not val:
            print(
                f"[Skills] Warning: '{fname}' missing or empty in "
                f"{skill_name_for_log}"
            )

    # ─────────────────────────────────────────────────────────────
    # 解析 Inputs（逻辑不变）
    # ─────────────────────────────────────────────────────────────
    inputs = {}
    if "## Inputs" in body:
        pattern = r"## Inputs\s*\n(.*?)(?=\n## |\Z)"
        match = re.search(pattern, body, re.DOTALL)
        if match:
            input_text = match.group(1).strip()
            for line in input_text.split("\n"):
                line = line.strip()
                if line.startswith("- `"):
                    parts_line = line.split(":", 1)
                    if len(parts_line) == 2:
                        param_name = (
                            parts_line[0].strip("- `").strip("`").strip()
                        )
                        description = parts_line[1].strip()
                        is_optional = (
                            "Optional" in description
                            or "optional" in description.lower()
                        )
                        inputs[param_name] = {
                            "description": description,
                            "optional": is_optional,
                        }

    # ─────────────────────────────────────────────────────────────
    # 组装返回值
    # ─────────────────────────────────────────────────────────────
    return {
        # 🐛 修复：原为 metadata.get("name", "")，
        #    若 YAML 里有 name: 但值为 null，会得到 None 而非 ""
        #    统一用 or "" 保证返回字符串
        "name": metadata.get("name") or "",
        "description": metadata.get("description") or "",

        # 🆕 L1 决策元信息
        "best_for": best_for,
        "not_for": not_for,
        "capabilities": capabilities,

        # 原有字段
        "inputs": inputs,
        "workflow": _extract_workflow(body),
    }


def _create_args_schema(inputs: Dict[str, Any]) -> type[BaseModel]:
    from typing import Optional
    fields = {}
    
    for name, info in inputs.items():
        desc = info.get("description", "")
        is_optional = info.get("optional", False)
        if is_optional:
            fields[name] = (Optional[str], Field(default=None, description=desc))
        else:
            fields[name] = (str, Field(description=desc))
    
    # 确保必须的参数存在
    if "ticker" not in fields:
        fields["ticker"] = (str, Field(description="股票代码，如 AAPL"))
    if "end_date" not in fields:
        fields["end_date"] = (str, Field(description="分析截止日期，格式 YYYY-MM-DD"))
    if "api_key" not in fields:
        fields["api_key"] = (Optional[str], Field(default=None, description="Financial datasets API key（可选）"))
    
    return create_model("SkillArgs", **fields)


def load_skill(skill_dir: Path) -> Optional[StructuredTool]:
    md_file = skill_dir / "SKILL.md"
    py_file = skill_dir / "skill.py"
    
    if not md_file.exists() or not py_file.exists():
        print(f"[Skills] Skipping {skill_dir.name}: missing SKILL.md or skill.py")
        return None
    
    md_content = md_file.read_text(encoding="utf-8")
    metadata = _parse_skill_metadata(md_content)
    
    spec = importlib.util.spec_from_file_location(
        f"{skill_dir.name}_skill", py_file
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, "execute"):
        print(f"[Skills] {skill_dir.name}/skill.py must define 'execute' function")
        return None
    
    execute_func: Callable = getattr(module, "execute")
    inputs = metadata.get("inputs", {})
    args_schema = _create_args_schema(inputs)
    
    # 🆕 渐进式披露：描述截断到 120 字符（用于 bind_tools 时的工具清单）
    full_desc = metadata.get("description", "")
    short_desc = full_desc[:120] + ("..." if len(full_desc) > 120 else "")

    tool = StructuredTool.from_function(
        func=execute_func,
        name=metadata.get("name") or skill_dir.name,
        description=short_desc,
        args_schema=args_schema,
    )

    # 🆕 把 workflow 和完整描述挂到 tool 上，供 skill.py 和 researcher 读取
    tool.metadata = {
        **(getattr(tool, "metadata", None) or {}),
        "skill_dir": str(skill_dir),
        "full_description": full_desc,
        "workflow": metadata.get("workflow", ""),
        # 🆕 L1 决策元信息
        "best_for": metadata.get("best_for", []),
        "not_for": metadata.get("not_for", []),
        "capabilities": metadata.get("capabilities", []),
    }

    print(f"[Skills] Loaded: {tool.name}")
    return tool
    

def load_all_skills(skills_root: Optional[Path] = None) -> List[StructuredTool]:
    if skills_root is None:
        skills_root = Path(__file__).parent
    
    tools = []
    for subdir in skills_root.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("__") and not subdir.name.startswith("."):
            tool = load_skill(subdir)
            if tool:
                tools.append(tool)
    
    return tools


def get_skill_workflow(skill_name: str) -> str:
    """按名字返回某 skill 的 Workflow 文本。找不到返回空串。"""
    skills_root = Path(__file__).parent
    for subdir in skills_root.iterdir():
        if not subdir.is_dir() or subdir.name.startswith("__") or subdir.name.startswith("."):
            continue
        md_file = subdir / "SKILL.md"
        if not md_file.exists():
            continue
        try:
            metadata = _parse_skill_metadata(md_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if metadata.get("name") == skill_name:
            return metadata.get("workflow", "")
    return ""


def get_all_skills() -> List[StructuredTool]:
    return load_all_skills()