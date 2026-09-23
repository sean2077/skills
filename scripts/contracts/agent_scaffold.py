"""Distribution checks for agent-scaffold; execution tests own its behavior."""
from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'agent-scaffold'
REQUIRED_PATHS = ('SKILL.md', 'NOTICE.md', 'references/testing-conventions.md', 'references/project-conventions.md', 'agent-scaffold.sh', 'scripts/harness-core.py', 'scripts/managed-assets.json', 'assets/scaffold/AGENTS.harness.md', 'assets/runtime/hooks/hook-paths.py')
# The adapted testing guidance carries upstream MIT attribution. Generic validation
# only routes a shipped NOTICE.md; hold its provenance and license text here, as the
# `tdd` and `domain-modeling` contracts already do for their own notices.
NOTICE_MARKERS = (
    "mattpocock/skills",
    "skills/engineering/tdd/",
    "MIT License",
    "Copyright (c) 2026 Matt Pocock",
    "The above copyright notice and this permission notice shall be included",
)


def validate_agent_scaffold_contract(skill_dir: Path | None = None) -> None:
    root = skill_dir or SKILLS_DIR / SKILL
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required payload: {missing}")
        return
    notice = " ".join((root / "NOTICE.md").read_text(encoding="utf-8").split())
    missing_notice = [marker for marker in NOTICE_MARKERS if marker not in notice]
    if missing_notice:
        errors.append(
            f"{SKILL}/NOTICE.md: upstream provenance and MIT notice missing: {missing_notice}"
        )


def validate(*, readme_text: str | None = None) -> None:
    validate_agent_scaffold_contract()
