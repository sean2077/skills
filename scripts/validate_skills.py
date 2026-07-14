#!/usr/bin/env python3
"""Validate the skills catalog.

Catches the drift classes that have actually bitten this repo: a skill missing
from the README, a deleted install path still advertised, frontmatter that lost
its `name`/`description`, YAML frontmatter that `npx skills` cannot parse, a
`name` that no longer matches its directory, the `{{ARGUMENTS}}` moustache
placeholder (Claude Code substitutes `$ARGUMENTS`), and a `reference.md` link
with no shipped file. Warnings flag softer hygiene: missing or over-broad
(`Bash`, `Bash(bash:*)`) `allowed-tools`, and an over-long description.

No third-party dependencies. Exit 0 = clean, 1 = errors. Warnings never fail.

    python3 scripts/validate_skills.py            # validate this repo
    SKILLS_REPO=/path/to/repo python3 scripts/validate_skills.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("SKILLS_REPO", Path(__file__).resolve().parent.parent))
SKILLS_DIR = REPO / "skills"
README = REPO / "README.md"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
GROUPING_MANIFEST = REPO / ".claude-plugin" / "plugin.json"

errors: list[str] = []
warnings: list[str] = []


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Read top-level `key: value` pairs from a leading `---` block.

    Deliberately minimal (no YAML dep): every skill here uses single-line scalar
    fields. Returns None when there is no closed frontmatter block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return None  # never closed


def plain_scalar_hazards(text: str) -> list[str]:
    """Find single-line values that are not valid YAML plain scalars."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    hazards: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            continue
        key, raw_value = m.group(1), m.group(2).strip()
        if not raw_value or raw_value[0] in {"'", '"', "|", ">"}:
            continue
        if re.search(r":\s", raw_value):
            hazards.append(f"`{key}` is an unquoted YAML scalar containing `: `; quote it so `npx skills` can parse the frontmatter")
    return hazards


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
        fm = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{dir_name}: SKILL.md has no valid `---` frontmatter block")
            continue

        for hazard in plain_scalar_hazards(text):
            errors.append(f"{dir_name}: {hazard}")

        # The minimal parser reads single-line scalars only; reject YAML block scalars
        # explicitly rather than silently treating `|` / `>` as the field value.
        bad_block = [k for k in ("name", "description") if fm.get(k, "") in {"|", ">", "|-", ">-", "|+", ">+"}]
        if bad_block:
            errors.append(f"{dir_name}: {', '.join(bad_block)} use(s) a YAML block scalar the minimal parser cannot read — inline as single-line scalars (or switch to a YAML parser)")
            continue

        name = fm.get("name", "")
        if not name:
            errors.append(f"{dir_name}: frontmatter is missing `name`")
        elif name != dir_name:
            errors.append(f"{dir_name}: `name: {name}` does not match directory name `{dir_name}`")

        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{dir_name}: frontmatter is missing a non-empty `description`")
        elif len(desc) > 1024:
            warnings.append(f"{dir_name}: description is {len(desc)} chars (>1024); trigger descriptions read best when concise")

        # Claude Code substitutes `$ARGUMENTS`; the moustache form is never expanded.
        if "{{ARGUMENTS}}" in text:
            errors.append(f"{dir_name}: SKILL.md uses `{{{{ARGUMENTS}}}}` — Claude Code substitutes `$ARGUMENTS`")

        # A SKILL.md that routes to `reference.md` must actually ship it (no dangling link).
        if "reference.md" in text and not (d / "reference.md").exists():
            errors.append(f"{dir_name}: SKILL.md links `reference.md` but {dir_name}/reference.md does not exist")

        # `allowed-tools` pre-approves (suppresses prompts) for the listed tools.
        tools = [t.strip() for t in fm.get("allowed-tools", "").split(",") if t.strip()]
        if "allowed-tools" not in fm:
            warnings.append(f"{dir_name}: no `allowed-tools` in frontmatter — every tool call prompts; declare a scoped set (e.g. `Read, Edit, Write, Grep, Glob, Bash(git:*)`)")
        # Bare `Bash` pre-approves arbitrary shell; `Bash(bash:*)`/`Bash(sh:*)` are nearly as broad.
        if "Bash" in tools:
            warnings.append(f"{dir_name}: `allowed-tools` pre-approves bare `Bash` (arbitrary shell, no prompt) — scope it (e.g. `Bash(git *)`) or drop it unless arbitrary shell is intended")
        broad = [t for t in tools if t.startswith("Bash(bash") or t.startswith("Bash(sh")]
        if broad:
            warnings.append(f"{dir_name}: `allowed-tools` pre-approves {', '.join(broad)} (a shell interpreter — nearly as broad as bare `Bash`); intended only when the skill runs bundled scripts")

        # README coverage
        if readme and f"(skills/{dir_name}/)" not in readme:
            errors.append(f"{dir_name}: not linked from the README skills table (expected a `(skills/{dir_name}/)` link)")

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
