from pathlib import Path

import yaml

from harnessos.protocol.models import Role


def load_roles(path: Path) -> dict[Role, str]:
    data = yaml.safe_load(path.read_text()) or {}
    roles = data.get("roles", {})
    return {Role(name): cfg.get("runtime", "opencode") for name, cfg in roles.items()}


def load_skill(role: Role, skills_dir: Path) -> str:
    path = skills_dir / role.value / "SKILL.md"
    return path.read_text() if path.exists() else ""
