"""Distribution checks for semver-release; execution tests own its behavior."""
from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'semver-release'
REQUIRED_PATHS = ('SKILL.md', 'references/automated-release-flow.md', 'references/changelog.md', 'references/publishing.md', 'references/version-selection.md', 'references/version-files.md', 'references/prerelease-promotion.md', 'scripts/release-plan.py', 'scripts/extract-changelog.py')


def validate_semver_release_contract(skill_dir: Path | None = None) -> None:
    root = skill_dir or SKILLS_DIR / SKILL
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required payload: {missing}")


def validate(*, readme_text: str | None = None) -> None:
    validate_semver_release_contract()
