"""Contract guards for the `agent-scaffold` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`agent-scaffold` skill contract changes.
"""

from __future__ import annotations

import re

from catalog_core import SKILLS_DIR, errors

SKILL = "agent-scaffold"


def validate_agent_scaffold_contract() -> None:
    """Keep Python 3.8+ a hard prerequisite throughout the selected router."""
    skill = SKILLS_DIR / "agent-scaffold" / "SKILL.md"
    if not skill.exists():
        return
    skill_text = skill.read_text(encoding="utf-8")
    stale_optional_python = {
        "retrofit fallback": r"without\s+python\s+the installer flags them instead",
        "workflow skip": r"subagents when python is unavailable",
        "conditional generator install": r"when\s+python\s+is\s+available\s+—\s+installs",
    }
    required_python_contract = {
        "hard prerequisite": (
            r"The harness requires\s+\*\*git, Python 3\.8\+, and Bash 3\.2\+\*\*\."
        ),
        "unconditional generator install": (
            r"installs\s+and\s+runs\s+the\s+subagent\s+generator"
        ),
    }
    found = [
        label
        for label, pattern in stale_optional_python.items()
        if re.search(pattern, skill_text, flags=re.IGNORECASE)
    ]
    missing = [
        label
        for label, pattern in required_python_contract.items()
        if not re.search(pattern, skill_text)
    ]
    if found or missing:
        errors.append(
            "agent-scaffold/SKILL.md: Python 3.8+ is a hard prerequisite; "
            f"missing={missing}, stale_optional={found}"
        )


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `agent-scaffold` contract."""
    validate_agent_scaffold_contract()
