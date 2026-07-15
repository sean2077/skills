#!/usr/bin/env python
"""Validate the skills catalog.

Catches the drift classes that have actually bitten this repo: a skill missing
from the README, a deleted install path still advertised, frontmatter that lost
its `name`/`description`, YAML frontmatter that `npx skills` cannot parse, a
`name` that no longer matches its directory, the `{{ARGUMENTS}}` moustache
placeholder (Claude Code substitutes `$ARGUMENTS`), and a `reference.md` link
with no shipped file. Errors reject `allowed-tools` entries that pre-approve an
unrestricted shell; warnings flag softer hygiene such as a missing field or an
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


_BROAD_SHELL_RULE = re.compile(
    r"(?<!\S)(?P<rule>"
    r"(?:Bash|PowerShell)(?:\(\*\))?"
    r"|(?:Bash|PowerShell)\((?i:(?:ba|da|z|k)?sh|fish|pwsh|powershell(?:\.exe)?|cmd(?:\.exe)?)"
    r"(?::\*| \*|\*)\)"
    r")(?!\S)"
)


def broad_shell_preapprovals(allowed: str) -> list[str]:
    """Return permission rules that grant an unrestricted shell."""
    return [match.group("rule") for match in _BROAD_SHELL_RULE.finditer(allowed)]


def validate_shell_preapproval_classifier() -> None:
    """Pin host-equivalent unsafe rules without rejecting scoped commands."""
    unsafe = (
        "Bash",
        "Bash(*)",
        "Bash(bash:*)",
        "Bash(bash *)",
        "Bash(sh:*)",
        "Bash(sh *)",
        "PowerShell",
        "PowerShell(*)",
    )
    safe = ("Bash(git:*)", "Bash(shellcheck:*)", "Bash(shasum:*)", "Bash(bashtop:*)")
    missed = [rule for rule in unsafe if not broad_shell_preapprovals(rule)]
    rejected = [rule for rule in safe if broad_shell_preapprovals(rule)]
    if missed or rejected:
        errors.append(
            "allowed-tools shell classifier drifted"
            f"; missed unsafe fixtures: {missed}; rejected scoped fixtures: {rejected}"
        )


def main() -> int:
    validate_shell_preapproval_classifier()
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

        # `allowed-tools` pre-approves (suppresses prompts) for the listed tools.
        allowed = fm.get("allowed-tools", "")
        if allowed and not isinstance(allowed, str):
            errors.append(f"{dir_name}: `allowed-tools` must be a space-separated string")
            allowed = ""
        if "," in allowed:
            errors.append(f"{dir_name}: `allowed-tools` must be space-separated, not comma-separated")
        if "allowed-tools" not in fm:
            warnings.append(f"{dir_name}: no `allowed-tools` in frontmatter — every tool call prompts; declare a scoped space-separated set when pre-approval is intended")
        # A broad shell rule can execute arbitrary command text without another
        # permission boundary. Catalog skills may scope individual commands,
        # but must not pre-approve a shell or its interpreter.
        broad = broad_shell_preapprovals(allowed)
        if broad:
            errors.append(f"{dir_name}: `allowed-tools` must not pre-approve unrestricted shells: {', '.join(broad)}")

        # README coverage
        if readme and f"(skills/{dir_name}/)" not in readme:
            errors.append(f"{dir_name}: not linked from the README skills table (expected a `(skills/{dir_name}/)` link)")

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


def validate_semver_release_contract() -> None:
    """Guard the package-identity rules that distinguish prerelease ecosystems."""
    skill = SKILLS_DIR / "semver-release" / "SKILL.md"
    reference = SKILLS_DIR / "semver-release" / "reference.md"
    if not skill.exists() or not reference.exists():
        return
    combined = skill.read_text(encoding="utf-8") + reference.read_text(encoding="utf-8")
    required = ("1.2.0-beta.1", "1.2.0b1", "1.2.0rc1", "project(... VERSION 1.2.0)")
    missing = [value for value in required if value not in combined]
    if missing:
        errors.append(f"semver-release: prerelease ecosystem contract lost fixtures: {missing}")
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
