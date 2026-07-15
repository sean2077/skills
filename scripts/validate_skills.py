#!/usr/bin/env python
"""Validate the skills catalog.

Catches the drift classes that have actually bitten this repo: a skill missing
from the README, a deleted install path still advertised, frontmatter that lost
its `name`/`description`, YAML frontmatter that `npx skills` cannot parse, a
`name` that no longer matches its directory, the `{{ARGUMENTS}}` moustache
placeholder (Claude Code substitutes `$ARGUMENTS`), and a `reference.md` link
with no shipped file. Catalog skills must leave tool approval to the host rather
than declaring `allowed-tools`; warnings flag softer hygiene such as an
over-long description.

Install the pinned validation dependency first. Exit 0 = clean, 1 = errors.
Warnings never fail.

    python -m pip install -r requirements-validation.txt
    python scripts/validate_skills.py            # validate this repo
    SKILLS_REPO=/path/to/repo python scripts/validate_skills.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    from strictyaml import YAMLValidationError, dirty_load
except ImportError:  # reported as a concise catalog error from main()
    YAMLValidationError = Exception  # type: ignore[assignment,misc]
    dirty_load = None

REPO = Path(os.environ.get("SKILLS_REPO", Path(__file__).resolve().parent.parent))
SKILLS_DIR = REPO / "skills"
README = REPO / "README.md"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
GROUPING_MANIFEST = REPO / ".claude-plugin" / "plugin.json"

errors: list[str] = []
warnings: list[str] = []


def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse a leading frontmatter block with a real strict YAML parser."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md has no opening `---` frontmatter delimiter")
    closing = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = index
            break
    if closing is None:
        raise ValueError("SKILL.md has no closing `---` frontmatter delimiter")
    if dirty_load is None:
        raise ValueError(
            "StrictYAML is unavailable — run `python -m pip install -r requirements-validation.txt`"
        )
    try:
        parsed = dirty_load("\n".join(lines[1:closing]), allow_flow_style=True).data
    except YAMLValidationError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc.context} {exc.problem}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return parsed


def main() -> int:
    if not SKILLS_DIR.is_dir():
        errors.append(f"no skills/ directory at {SKILLS_DIR}")
        return report()

    readme = README.read_text(encoding="utf-8") if README.exists() else ""
    if not readme:
        errors.append("README.md is missing or empty")

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        errors.append("no skill directories under skills/")

    validate_grouping_manifest(skill_dirs)

    for d in skill_dirs:
        dir_name = d.name
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{dir_name}: missing SKILL.md")
            continue

        text = skill_md.read_text(encoding="utf-8")
        try:
            fm = parse_frontmatter(text)
        except ValueError as exc:
            errors.append(f"{dir_name}: {exc}")
            continue

        name = fm.get("name", "")
        if not isinstance(name, str) or not name:
            errors.append(f"{dir_name}: frontmatter is missing `name`")
        elif name != dir_name:
            errors.append(f"{dir_name}: `name: {name}` does not match directory name `{dir_name}`")
        elif len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(f"{dir_name}: `name` must be 1-64 lowercase letters/numbers/hyphen segments")

        desc = fm.get("description", "")
        if not isinstance(desc, str) or not desc:
            errors.append(f"{dir_name}: frontmatter is missing a non-empty `description`")
        elif len(desc) > 1024:
            errors.append(f"{dir_name}: description is {len(desc)} chars (>1024 specification limit)")

        compatibility = fm.get("compatibility")
        if compatibility is not None and (
            not isinstance(compatibility, str) or not 1 <= len(compatibility) <= 500
        ):
            errors.append(f"{dir_name}: `compatibility` must be a non-empty string of at most 500 characters")

        # Claude Code substitutes `$ARGUMENTS`; the moustache form is never expanded.
        if "{{ARGUMENTS}}" in text:
            errors.append(f"{dir_name}: SKILL.md uses `{{{{ARGUMENTS}}}}` — Claude Code substitutes `$ARGUMENTS`")

        # A SKILL.md that routes to `reference.md` must actually ship it (no dangling link).
        if "reference.md" in text and not (d / "reference.md").exists():
            errors.append(f"{dir_name}: SKILL.md links `reference.md` but {dir_name}/reference.md does not exist")

        if "allowed-tools" in fm:
            errors.append(
                f"{dir_name}: catalog skills must not declare `allowed-tools`; defer approvals to the host"
            )

        # README coverage
        if readme and f"(skills/{dir_name}/)" not in readme:
            errors.append(f"{dir_name}: not linked from the README skills table (expected a `(skills/{dir_name}/)` link)")

    validate_conventional_commit_contract()
    validate_semver_release_contract()

    # Reverse coverage: a README link must point at a real skill directory.
    for m in re.finditer(r"\(skills/([A-Za-z0-9_-]+)/\)", readme):
        linked = m.group(1)
        if not (SKILLS_DIR / linked).is_dir():
            errors.append(f"README links `skills/{linked}/` but that skill directory does not exist")

    # Stale install paths: don't advertise the marketplace flow without a manifest.
    if "/plugin install" in readme and not MARKETPLACE.exists():
        errors.append("README advertises `/plugin install` but `.claude-plugin/marketplace.json` does not exist")
    if ".claude-plugin/marketplace.json" in readme and not MARKETPLACE.exists():
        errors.append("README references `.claude-plugin/marketplace.json` which does not exist")

    return report()


def validate_conventional_commit_contract() -> None:
    """Keep commit mode from staging changes on a detached HEAD."""
    skill = SKILLS_DIR / "conventional-commit" / "SKILL.md"
    if not skill.exists():
        return
    skill_text = skill.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^## Workflow[ \t]*\r?\n(.*?)(?=^## |\Z)", skill_text)
    workflow = match.group(1) if match else ""
    preflight = "git symbolic-ref --quiet --short HEAD"
    detached = (
        "On exit status 1, stop before staging and report that commit mode requires "
        "an attached branch because HEAD is detached."
    )
    git_error = "On any other nonzero status, stop before staging and report the Git preflight error."
    stage = "stage the intended files"
    required = (preflight, detached, git_error, stage)
    missing = [value for value in required if value not in workflow]
    ordered = not missing and [workflow.index(value) for value in required] == sorted(
        workflow.index(value) for value in required
    )
    if missing or not ordered:
        errors.append("conventional-commit: attached-HEAD preflight must precede commit-mode staging")


def validate_semver_release_contract() -> None:
    """Guard bump inference and package identity across release ecosystems."""
    skill = SKILLS_DIR / "semver-release" / "SKILL.md"
    reference = SKILLS_DIR / "semver-release" / "reference.md"
    if not skill.exists() or not reference.exists():
        return
    skill_text = skill.read_text(encoding="utf-8")
    reference_text = reference.read_text(encoding="utf-8")
    combined = skill_text + reference_text
    bump_contract = (
        "BREAKING CHANGE:",
        "BREAKING-CHANGE:",
        "case-insensitive",
        "remains uppercase",
    )
    for label, text in (("SKILL.md", skill_text), ("reference.md", reference_text)):
        missing_bump = [value for value in bump_contract if value not in text]
        if missing_bump:
            errors.append(f"semver-release/{label}: bump inference contract lost fixtures: {missing_bump}")
    required = ("1.2.0-beta.1", "1.2.0b1", "1.2.0rc1", "project(... VERSION 1.2.0)")
    missing = [value for value in required if value not in combined]
    if missing:
        errors.append(f"semver-release: prerelease ecosystem contract lost fixtures: {missing}")
    shared_base_contract = (
        "HEAD-reachable",
        "SemVer 2.0.0 precedence",
        "no HEAD-reachable valid SemVer base",
    )
    for label, text in (("SKILL.md", skill_text), ("reference.md", reference_text)):
        missing_base = [value for value in shared_base_contract if value not in text]
        if missing_base:
            errors.append(f"semver-release/{label}: base-selection contract lost fixtures: {missing_base}")
    equal_precedence = (
        "When highest-precedence tags differ only by build metadata, use their shared commit as "
        "`<base>` only if they all resolve to that commit; otherwise stop and report the ambiguity."
    )
    peel_commit = "git rev-parse '<tag>^{commit}'"
    for label, text in (("SKILL.md", skill_text), ("reference.md", reference_text)):
        if equal_precedence not in text:
            errors.append(f"semver-release/{label}: equal-precedence base rule is missing")
        if peel_commit not in text:
            errors.append(f"semver-release/{label}: annotated-tag commit resolution is missing")
    skill_base_contract = (
        "git rev-parse --is-shallow-repository",
        "git rev-list --max-parents=0 HEAD",
        "git cat-file -p <root>",
        "git tag --merged HEAD --list 'v[0-9]*'",
        "git merge-base --is-ancestor <base> HEAD",
        "do not sort or truncate before validation",
        "stop before base selection only if an apparent HEAD root has a raw `parent` header",
    )
    missing_skill_base = [value for value in skill_base_contract if value not in skill_text]
    if missing_skill_base:
        errors.append(f"semver-release/SKILL.md: base-selection workflow lost fixtures: {missing_skill_base}")
    reference_base_contract = (
        "`v01.2.3` and `v1.2.3-rc.01` are invalid",
        "`v1.1.0-rc.1 < v1.1.0`",
        "build metadata does not affect precedence",
        "Git's `version:refname` order is not SemVer precedence",
        "previous HEAD-reachable stable release, or repo root if none exists",
        "shallow repository",
        "git rev-list --max-parents=0 HEAD",
        "git cat-file -p <root>",
        "commit headers before the first blank line",
        "repository-level `true` is not sufficient",
    )
    missing_reference_base = [value for value in reference_base_contract if value not in reference_text]
    if missing_reference_base:
        errors.append(
            f"semver-release/reference.md: SemVer precedence contract lost fixtures: {missing_reference_base}"
        )
    release_stage_contract = (
        "git add -- CHANGELOG.md <all-version-files> <all-coupled-lockfiles> [release-notes]",
        "git diff --cached --check",
        "every file changed for the release must be staged",
        'git commit -m "release: vX.Y.Z"',
        "git status --porcelain # must be empty before tagging",
        'git tag -a vX.Y.Z -m "Release vX.Y.Z"',
    )
    missing_stage = [value for value in release_stage_contract if value not in skill_text]
    stage_ordered = not missing_stage and [skill_text.index(value) for value in release_stage_contract] == sorted(
        skill_text.index(value) for value in release_stage_contract
    )
    if missing_stage or not stage_ordered:
        errors.append(
            "semver-release/SKILL.md: complete release snapshot must be staged and clean before tagging"
        )
    stale_selector = "git tag --list 'v[0-9]*' --sort=-v:refname | head -10"
    if stale_selector in combined:
        errors.append("semver-release: stale Git version-sort base selector remains")
    if "git add CHANGELOG.md <version-file> [release-notes]" in skill_text:
        errors.append("semver-release/SKILL.md: partial release staging command remains")
    if "Prerelease suffixes generally do **not** go into the version file" in combined:
        errors.append("semver-release: stale tag-only prerelease guidance remains")


def validate_grouping_manifest(skill_dirs: list[Path]) -> None:
    """Keep npx skills grouping metadata aligned with the catalog."""
    if not GROUPING_MANIFEST.exists():
        errors.append("missing `.claude-plugin/plugin.json` grouping manifest")
        return

    try:
        manifest = json.loads(GROUPING_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid `.claude-plugin/plugin.json`: {exc}")
        return

    if manifest.get("name") != "sean2077-skills":
        errors.append("`.claude-plugin/plugin.json` name must be `sean2077-skills`")

    expected = [f"./skills/{skill_dir.name}" for skill_dir in skill_dirs]
    if manifest.get("skills") != expected:
        errors.append(
            "`.claude-plugin/plugin.json` skills must exactly match the sorted "
            f"skills/ catalog: expected {expected}"
        )


def report() -> int:
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    n = len([p for p in SKILLS_DIR.iterdir() if p.is_dir()]) if SKILLS_DIR.is_dir() else 0
    if errors:
        print(f"\nFAIL: {len(errors)} error(s), {len(warnings)} warning(s) across {n} skill(s)")
        return 1
    print(f"OK: {n} skill(s) validated, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        sys.exit(0)
    sys.exit(main())
