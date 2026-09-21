"""Distribution inventory for work-protocol; runtime behavior is tested by execution."""

from __future__ import annotations

from catalog_core import SKILLS_DIR, errors

SKILL = "work-protocol"
REQUIRED_PATHS = (
    "SKILL.md",
    "references/task-state-and-evidence.md",
    "references/workspace-isolation.md",
    "scripts/workctl.py",
    "scripts/work_protocol_runtime/common.py",
    "scripts/work_protocol_runtime/workctl.py",
)


def validate(*, readme_text: str | None = None) -> None:
    missing = [path for path in REQUIRED_PATHS if not (SKILLS_DIR / SKILL / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required runtime payload: {missing}")
