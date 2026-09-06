"""TDD distribution and attribution invariants, not a prose-based behavior oracle.

Generic catalog validation owns frontmatter, budgets, links and inventory.
Semantic routing belongs to real-host evaluation, not exact English phrases.
"""

from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = "tdd"
REFERENCE_FILES = (
    "references/test-design.md",
    "references/test-doubles-and-effects.md",
    "references/cross-stack-execution.md",
    "references/legacy-and-hard-cases.md",
)
NOTICE_MARKERS = (
    "mattpocock/skills",
    "skills/engineering/tdd/",
    "MIT License",
    "Copyright (c) 2026 Matt Pocock",
    "The above copyright notice and this permission notice shall be included",
)


def validate_tdd_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Preserve the installed payload and upstream attribution during rewrites."""
    skill_dir = skill_dir or SKILLS_DIR / SKILL
    required = ("SKILL.md", "NOTICE.md", *REFERENCE_FILES)
    missing = [name for name in required if not (skill_dir / name).is_file()]
    if missing:
        errors.append(f"tdd: missing required skill payload files: {missing}")
        return
    notice = " ".join((skill_dir / "NOTICE.md").read_text(encoding="utf-8").split())
    missing_notice = [marker for marker in NOTICE_MARKERS if marker not in notice]
    if missing_notice:
        errors.append(f"tdd/NOTICE.md: upstream provenance and MIT notice missing: {missing_notice}")


def validate(*, readme_text: str | None = None) -> None:
    """Registered entry point; keep the common contract-dispatch signature."""
    validate_tdd_contract(readme_text=readme_text)
