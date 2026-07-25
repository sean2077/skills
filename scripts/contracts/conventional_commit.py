"""Contract guards for the `conventional-commit` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`conventional-commit` skill contract changes.
"""

from __future__ import annotations

import re
from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = "conventional-commit"


def validate_conventional_commit_contract(skill_dir: Path | None = None) -> None:
    """Keep commit mode rooted and prove the committed snapshot matches the reviewed index."""
    skill_dir = skill_dir or SKILLS_DIR / "conventional-commit"
    skill = skill_dir / "SKILL.md"
    staging = skill_dir / "references" / "staging-safety.md"
    if not skill.exists() or not staging.exists():
        return
    skill_text = skill.read_text(encoding="utf-8")
    staging_text = staging.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^## Workflow[ \t]*\r?\n(.*?)(?=^## |\Z)", skill_text)
    workflow = match.group(1) if match else ""
    root = "git rev-parse --show-toplevel"
    preflight = "git -C <repo-root> symbolic-ref --quiet --short HEAD"
    detached = "Exit status 1 means detached HEAD"
    git_error = "any other nonzero status is a Git preflight"
    operation_status = "git -C <repo-root> status --long --branch"
    in_progress = "in-progress merge"
    stage = "stage the exact intended"
    required = (root, preflight, detached, git_error, operation_status, in_progress, stage)
    missing = [value for value in required if value not in workflow]
    ordered = not missing and [workflow.index(value) for value in required] == sorted(
        workflow.index(value) for value in required
    )
    if missing or not ordered:
        errors.append("conventional-commit: attached-HEAD preflight must precede commit-mode staging")
    reference_contract = (
        "git -C <repo-root> status --short",
        "git -C <repo-root> add -A -- .",
        "Exit status 1 means HEAD is detached",
        "Any other nonzero status is a Git error",
        "git diff --cached --name-only",
        "git diff --cached --check",
        "unrelated paths are already staged",
        "A named path does not authorize every hunk",
        "git -C <repo-root> diff --cached -- <paths>",
        "git -C <repo-root> diff -- <paths>",
        "mixes intended and unrelated hunks",
        "without modifying the working tree or unrelated pre-existing index state",
        "actual cached patch",
        "An attached HEAD proves only",
        "git -C <repo-root> status --long --branch",
        "in-progress merge, rebase, cherry-pick, revert, bisect, or unresolved conflict",
        "Ordinary commit mode never continues or completes those operations",
    )
    normalized_staging = " ".join(staging_text.split())
    missing_reference = [
        value for value in reference_contract if value not in normalized_staging
    ]
    if missing_reference:
        errors.append(
            "conventional-commit/references/staging-safety.md: path/hunk staging boundary lost fixtures: "
            f"{missing_reference}"
        )
    snapshot_contract = (
        "git -C <repo-root> rev-parse --verify --quiet HEAD",
        "git -C <repo-root> write-tree",
        "reviewed index",
        "git -C <repo-root> rev-parse 'HEAD^{tree}'",
        "git -C <repo-root> rev-list --parents -n 1 HEAD",
        "equal `<expected-tree>`",
        "exactly `<base>` as its sole parent",
        "unborn branch it must have no parent",
        "without attempting history rewriting",
    )
    missing_snapshot = [
        value for value in snapshot_contract if value not in normalized_staging
    ]
    if missing_snapshot:
        errors.append(
            "conventional-commit/references/staging-safety.md: committed-snapshot "
            f"verification boundary lost fixtures: {missing_snapshot}"
        )


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `conventional-commit` contract."""
    validate_conventional_commit_contract()
