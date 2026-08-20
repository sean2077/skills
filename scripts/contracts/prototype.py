"""Semantic contract for the `prototype` catalog skill."""

from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'prototype'
REQUIRED_PATHS = ['SKILL.md', 'references/experiment-design.md']
REQUIRED_TEXT = ['falsifiable question', 'supported`, `refuted`, or `inconclusive', 'Do not silently ship prototype code']
FORBIDDEN_TEXT = ("oma ", ".oma/", "oh-my-agents")


def validate(*, readme_text: str | None = None) -> None:
    skill_dir = SKILLS_DIR / SKILL
    missing = [relative for relative in REQUIRED_PATHS if not (skill_dir / relative).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required migration payload: {missing}")
        return
    text = "\n".join((skill_dir / relative).read_text(encoding="utf-8") for relative in REQUIRED_PATHS)
    absent = [fixture for fixture in REQUIRED_TEXT if fixture not in text]
    if absent:
        errors.append(f"{SKILL}: semantic migration fixtures missing: {absent}")
    lowered = text.lower()
    found = [fixture for fixture in FORBIDDEN_TEXT if fixture.lower() in lowered]
    if found:
        errors.append(f"{SKILL}: migrated payload retains retired runtime dependency: {found}")
