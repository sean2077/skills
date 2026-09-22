"""Upstream attribution invariants for an adapted catalog skill.

Generic catalog validation owns frontmatter, budgets, links, reachability and
inventory. This module keeps the MIT notice and its provenance markers, which a
generic rule cannot know, without asserting reworded prose.
"""

from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = "domain-modeling"
REQUIRED_PATHS = (
    "SKILL.md",
    "NOTICE.md",
    "references/context-topology.md",
    "references/elicitation-and-migration.md",
)
NOTICE_MARKERS = (
    "mattpocock/skills",
    "skills/engineering/domain-modeling/",
    "MIT License",
    "Copyright (c) 2026 Matt Pocock",
    "The above copyright notice and this permission notice shall be included",
)


def validate_domain_modeling_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Preserve the installed payload and upstream attribution during rewrites."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    missing = [name for name in REQUIRED_PATHS if not (skill_dir / name).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required skill payload files: {missing}")
        return
    notice = " ".join((skill_dir / "NOTICE.md").read_text(encoding="utf-8").split())
    missing_notice = [marker for marker in NOTICE_MARKERS if marker not in notice]
    if missing_notice:
        errors.append(
            f"{SKILL}/NOTICE.md: upstream provenance and MIT notice missing: {missing_notice}"
        )


def validate(*, readme_text: str | None = None) -> None:
    """Registered entry point; keep the common contract-dispatch signature."""
    validate_domain_modeling_contract(readme_text=readme_text)