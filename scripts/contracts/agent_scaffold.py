"""Distribution checks for agent-scaffold; execution tests own its behavior."""
from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'agent-scaffold'
REQUIRED_PATHS = ('SKILL.md', 'NOTICE.md', 'references/testing-conventions.md', 'references/project-conventions.md', 'agent-scaffold.sh', 'scripts/harness-core.py', 'scripts/managed-assets.json', 'assets/scaffold/AGENTS.harness.md', 'assets/runtime/hooks/hook-paths.py')


def validate_agent_scaffold_contract(skill_dir: Path | None = None) -> None:
    root = skill_dir or SKILLS_DIR / SKILL
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required payload: {missing}")


def validate(*, readme_text: str | None = None) -> None:
    validate_agent_scaffold_contract()
