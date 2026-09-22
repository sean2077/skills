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
# Provenance, the license name, and the copyright holder: a rewrite must keep these.
PROVENANCE_MARKERS = (
    "mattpocock/skills",
    "skills/engineering/domain-modeling/",
    "MIT License",
    "Copyright (c) 2026 Matt Pocock",
    "The above copyright notice and this permission notice shall be included",
)
# The complete upstream MIT text, whitespace-normalized. Anchors would pass a notice
# with sentences deleted between them, so the license body is pinned as one string.
MIT_LICENSE_TEXT = (
    'Permission is hereby granted, free of charge, to any person obtaining a copy of this software '
    'and associated documentation files (the "Software"), to deal in the Software without '
    "restriction, including without limitation the rights to use, copy, modify, merge, publish, "
    "distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the "
    "Software is furnished to do so, subject to the following conditions: The above copyright "
    "notice and this permission notice shall be included in all copies or substantial portions of "
    'the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR '
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A "
    "PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE "
    "LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR "
    "OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER "
    "DEALINGS IN THE SOFTWARE."
)
NOTICE_MARKERS = PROVENANCE_MARKERS


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
    if MIT_LICENSE_TEXT not in notice:
        missing_notice.append("the complete MIT license text")
    if missing_notice:
        errors.append(
            f"{SKILL}/NOTICE.md: upstream provenance and MIT notice missing: {missing_notice}"
        )


def validate(*, readme_text: str | None = None) -> None:
    """Registered entry point; keep the common contract-dispatch signature."""
    validate_domain_modeling_contract(readme_text=readme_text)