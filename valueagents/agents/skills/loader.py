# valueagents/agents/skills/loader.py
import importlib.util
import re
from pathlib import Path
from typing import List, Optional, Callable, Any, Dict
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model, Field
import yaml


def _parse_skill_metadata(md_content: str) -> Dict[str, Any]:
    parts = md_content.split("---")
    if len(parts) < 3:
        raise ValueError("SKILL.md must contain YAML frontmatter (--- ... ---)")
    
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        raise ValueError("Invalid YAML frontmatter in SKILL.md")
    
    body = parts[2].strip()
    
    # 解析 Inputs
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
                        param_name = parts_line[0].strip("- `").strip("`").strip()
                        description = parts_line[1].strip()
                        is_optional = "Optional" in description or "optional" in description.lower()
                        inputs[param_name] = {
                            "description": description,
                            "optional": is_optional
                        }
    
    return {
        "name": metadata.get("name", ""),
        "description": metadata.get("description", ""),
        "inputs": inputs,
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
    
    tool = StructuredTool.from_function(
        func=execute_func,
        name=metadata.get("name", skill_dir.name),
        description=metadata.get("description", ""),
        args_schema=args_schema,
    )
    
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


def get_all_skills() -> List[StructuredTool]:
    return load_all_skills()