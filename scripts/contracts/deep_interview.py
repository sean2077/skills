"""Distribution inventory for deep-interview; runtime behavior is tested by execution."""

from __future__ import annotations

from catalog_core import SKILLS_DIR, errors

SKILL = "deep-interview"
REQUIRED_PATHS = ('SKILL.md', 'references/persistent-runtime.md', 'references/resume-and-recovery.md', 'scripts/interview_state.py')


def validate(*, readme_text: str | None = None) -> None:
    missing = [path for path in REQUIRED_PATHS if not (SKILLS_DIR / SKILL / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required runtime payload: {missing}")
