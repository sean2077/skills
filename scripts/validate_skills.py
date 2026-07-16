#!/usr/bin/env python
"""Validate the skills catalog.

Catches the drift classes that have actually bitten this repo: a skill missing
from the README, a deleted install path still advertised, frontmatter that lost
its `name`/`description`, YAML frontmatter that `npx skills` cannot parse, a
`name` that no longer matches its directory, the `{{ARGUMENTS}}` moustache
placeholder (Claude Code substitutes `$ARGUMENTS`), and category reference links
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
# Coarse repo-local prose budget, not a host token limit. It scales with the
# catalog so adding a well-scoped skill does not consume another skill's share.
METADATA_PROSE_CHARS_PER_SKILL = 512

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


REFERENCE_LINK = re.compile(r"\]\((references/[^)\s#]+\.md)(?:#[^)]+)?\)")
LEGACY_REFERENCE_LINK = re.compile(r"\]\((?:\./)?reference\.md(?:#[^)]+)?\)", re.IGNORECASE)
REFERENCE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.md")
FORBIDDEN_REFERENCE_NAMES = {"reference.md", "references.md", "misc.md", "all.md", "readme.md"}


def validate_category_references(skill_dir: Path, skill_text: str) -> None:
    """Require direct, category-named, non-dangling on-demand reference routing."""
    skill_name = skill_dir.name
    legacy_candidates = [path for path in skill_dir.iterdir() if path.name.lower() == "reference.md"]
    if legacy_candidates:
        errors.append(f"{skill_name}: root-level reference.md is forbidden; use references/<category>.md")
    if LEGACY_REFERENCE_LINK.search(skill_text):
        errors.append(f"{skill_name}: SKILL.md must route references directly to references/<category>.md")

    references_dir = skill_dir / "references"
    reference_files = (
        {path for path in references_dir.rglob("*") if path.is_file() or path.is_symlink()}
        if references_dir.is_dir()
        else set()
    )
    linked: set[Path] = set()
    for relative in REFERENCE_LINK.findall(skill_text):
        relative_path = Path(relative)
        if relative_path.parent != Path("references"):
            errors.append(f"{skill_name}: reference link must target references/<category>.md: {relative}")
            continue
        lower_name = relative_path.name.lower()
        if relative_path.name != lower_name or not REFERENCE_NAME.fullmatch(relative_path.name):
            errors.append(f"{skill_name}: reference link filename must be lowercase kebab-case: {relative}")
        if lower_name in FORBIDDEN_REFERENCE_NAMES:
            errors.append(f"{skill_name}: reference link uses a forbidden catch-all name: {relative}")
        target = skill_dir / relative
        linked.add(target)
        if not target.is_file():
            errors.append(f"{skill_name}: SKILL.md reference link does not exist: {relative}")

    for path in sorted(reference_files):
        relative = path.relative_to(skill_dir).as_posix()
        if path.parent != references_dir:
            errors.append(f"{skill_name}: nested reference categories are unsupported: {relative}")
        lower_name = path.name.lower()
        if path.name != lower_name or not REFERENCE_NAME.fullmatch(path.name):
            errors.append(f"{skill_name}: reference filename must be lowercase kebab-case: {relative}")
        if lower_name in FORBIDDEN_REFERENCE_NAMES:
            errors.append(f"{skill_name}: catch-all reference filename is forbidden: {relative}")
        if path not in linked:
            errors.append(f"{skill_name}: orphan reference is not linked directly from SKILL.md: {relative}")

    if linked and not references_dir.is_dir():
        errors.append(f"{skill_name}: SKILL.md links references/ but the directory does not exist")


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
    metadata_prose_chars = 0

    validate_grouping_manifest(skill_dirs)
    validate_npx_discovery_contract()

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
        if isinstance(name, str):
            metadata_prose_chars += len(name)
        if not isinstance(name, str) or not name:
            errors.append(f"{dir_name}: frontmatter is missing `name`")
        elif name != dir_name:
            errors.append(f"{dir_name}: `name: {name}` does not match directory name `{dir_name}`")
        elif len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(f"{dir_name}: `name` must be 1-64 lowercase letters/numbers/hyphen segments")

        desc = fm.get("description", "")
        if isinstance(desc, str):
            metadata_prose_chars += len(desc)
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

        validate_category_references(d, text)

        if "allowed-tools" in fm:
            errors.append(
                f"{dir_name}: catalog skills must not declare `allowed-tools`; defer approvals to the host"
            )

        # README coverage
        if readme and f"(skills/{dir_name}/)" not in readme:
            errors.append(f"{dir_name}: not linked from the README skills table (expected a `(skills/{dir_name}/)` link)")

    metadata_prose_budget = len(skill_dirs) * METADATA_PROSE_CHARS_PER_SKILL
    if metadata_prose_chars > metadata_prose_budget:
        errors.append(
            "catalog routing metadata exceeds the repo-local prose budget: "
            f"{metadata_prose_chars} chars > {metadata_prose_budget} "
            f"({METADATA_PROSE_CHARS_PER_SKILL} per skill)"
        )

    validate_agent_scaffold_contract()
    validate_tooling_conventions_contract()
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


def validate_npx_discovery_contract() -> None:
    """Require CI to compare pinned npx discovery with the catalog exactly."""
    workflow = REPO / ".github" / "workflows" / "validate.yml"
    if not workflow.exists():
        return
    workflow_text = workflow.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\s*- name: Smoke-test real npx skills discovery\s*$"
        r"(.*?)(?=^\s*- name:|\Z)",
        workflow_text,
    )
    discovery_step = match.group(1) if match else ""
    required = {
        "capture pinned CLI output": (
            r"output=.*NO_COLOR=1\s+DISABLE_TELEMETRY=1\s+"
            r"npx --yes skills@1\.5\.17 add \. -l.*2>&1"
        ),
        "preserve CLI failure status": (
            r"status=\$\?[\s\S]*if \[ [\"']?\$status[\"']? -ne 0 \]; then"
        ),
        "extract names independently of the UI border": (
            r"actual=.*sed -n [\"']s/\^\.\*    "
        ),
        "derive expected names from skills/": r"expected=.*python -c.*Path",
        "compare the two sets exactly": (
            r"if \[ [\"']?\$actual[\"']? != [\"']?\$expected[\"']? \]; then"
        ),
    }
    missing = [label for label, pattern in required.items() if not re.search(pattern, discovery_step)]
    if missing:
        errors.append(
            "CI npx discovery must assert that the pinned CLI returns the exact catalog skill set; "
            f"missing={missing}"
        )


def validate_agent_scaffold_contract() -> None:
    """Keep Python 3.8+ a hard prerequisite throughout the selected router."""
    skill = SKILLS_DIR / "agent-scaffold" / "SKILL.md"
    if not skill.exists():
        return
    skill_text = skill.read_text(encoding="utf-8")
    stale_optional_python = {
        "retrofit fallback": r"without\s+python\s+the installer flags them instead",
        "workflow skip": r"subagents when python is unavailable",
        "conditional generator install": r"when\s+python\s+is\s+available\s+—\s+installs",
    }
    required_python_contract = {
        "hard prerequisite": (
            r"The harness requires\s+\*\*git, Python 3\.8\+, and Bash 3\.2\+\*\*\."
        ),
        "unconditional generator install": (
            r"installs\s+and\s+runs\s+the\s+subagent\s+generator"
        ),
    }
    found = [
        label
        for label, pattern in stale_optional_python.items()
        if re.search(pattern, skill_text, flags=re.IGNORECASE)
    ]
    missing = [
        label
        for label, pattern in required_python_contract.items()
        if not re.search(pattern, skill_text)
    ]
    if found or missing:
        errors.append(
            "agent-scaffold/SKILL.md: Python 3.8+ is a hard prerequisite; "
            f"missing={missing}, stale_optional={found}"
        )


def validate_tooling_conventions_contract() -> None:
    """Keep Python syntax checks compile-accurate without bytecode residue."""
    skill_dir = SKILLS_DIR / "tooling-conventions"
    paths = {
        "SKILL.md": skill_dir / "SKILL.md",
        "references/verification.md": skill_dir / "references" / "verification.md",
        "manifest.schema.md": skill_dir / "manifest.schema.md",
        "manifest-check.sh": skill_dir / "manifest-check.sh",
    }
    if any(not path.exists() for path in paths.values()):
        return
    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    memory_compile = (
        "python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), "
        "sys.argv[1], \"exec\")'"
    )
    for label in ("references/verification.md", "manifest-check.sh"):
        if memory_compile not in texts[label]:
            errors.append(f"tooling-conventions/{label}: in-memory Python compile command is missing")
    if "in-memory Python compile" not in texts["SKILL.md"]:
        errors.append("tooling-conventions/SKILL.md: no-bytecode Python verification route is missing")
    stale = [label for label, value in texts.items() if "py_compile" in value]
    if stale:
        errors.append(f"tooling-conventions: py_compile bytecode-producing guidance remains in {stale}")

    workflow = REPO / ".github" / "workflows" / "validate.yml"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    fixture_contract = (
        "valid path-雪.py",
        "manifest check left Python bytecode residue",
        "return 1",
    )
    missing_fixture = [value for value in fixture_contract if value not in workflow_text]
    if missing_fixture:
        errors.append(
            "tooling-conventions: bytecode-residue CI fixture is incomplete: "
            f"{missing_fixture}"
        )


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
    reference_paths = {
        "references/version-selection.md": SKILLS_DIR / "semver-release" / "references" / "version-selection.md",
        "references/version-files.md": SKILLS_DIR / "semver-release" / "references" / "version-files.md",
        "references/changelog.md": SKILLS_DIR / "semver-release" / "references" / "changelog.md",
        "references/prerelease-promotion.md": SKILLS_DIR / "semver-release" / "references" / "prerelease-promotion.md",
    }
    if not skill.exists() or any(not path.exists() for path in reference_paths.values()):
        return
    skill_text = skill.read_text(encoding="utf-8")
    reference_texts = {label: path.read_text(encoding="utf-8") for label, path in reference_paths.items()}
    selection_text = reference_texts["references/version-selection.md"]
    version_files_text = reference_texts["references/version-files.md"]
    promotion_text = reference_texts["references/prerelease-promotion.md"]
    combined = skill_text + "".join(reference_texts.values())
    bump_contract = (
        "BREAKING CHANGE:",
        "BREAKING-CHANGE:",
        "case-insensitive",
        "remains uppercase",
    )
    for label, text in (("SKILL.md", skill_text), ("references/version-selection.md", selection_text)):
        missing_bump = [value for value in bump_contract if value not in text]
        if missing_bump:
            errors.append(f"semver-release/{label}: bump inference contract lost fixtures: {missing_bump}")
    required = ("1.2.0-beta.1", "1.2.0b1", "1.2.0rc1", "project(... VERSION 1.2.0)")
    missing = [value for value in required if value not in combined]
    if missing:
        errors.append(f"semver-release: prerelease ecosystem contract lost fixtures: {missing}")
    python_boundary_skill = (
        "explicit repository-defined Python mapping",
        "stop before writing release files, committing, tagging, or pushing",
    )
    missing_python_skill = [value for value in python_boundary_skill if value not in skill_text]
    if missing_python_skill:
        errors.append(
            "semver-release/SKILL.md: Python prerelease mapping boundary lost fixtures: "
            f"{missing_python_skill}"
        )
    python_boundary_reference = (
        "`alpha.N` → `aN`",
        "`beta.N` → `bN`",
        "`rc.N` → `rcN`",
        "`v1.2.0-canary.1` remains a valid SemVer tag",
        "historical base selection",
        "non-Python ecosystems",
    )
    missing_python_reference = [
        value for value in python_boundary_reference if value not in version_files_text
    ]
    if missing_python_reference:
        errors.append(
            "semver-release/references/version-files.md: Python prerelease mapping boundary lost fixtures: "
            f"{missing_python_reference}"
        )
    shared_base_contract = (
        "HEAD-reachable",
        "SemVer 2.0.0 precedence",
        "no HEAD-reachable valid SemVer base",
    )
    for label, text in (("SKILL.md", skill_text), ("references/version-selection.md", selection_text)):
        missing_base = [value for value in shared_base_contract if value not in text]
        if missing_base:
            errors.append(f"semver-release/{label}: base-selection contract lost fixtures: {missing_base}")
    equal_precedence = (
        "When highest-precedence tags differ only by build metadata, use their shared commit as "
        "`<base>` only if they all resolve to that commit; otherwise stop and report the ambiguity."
    )
    peel_commit = "git rev-parse '<tag>^{commit}'"
    for label, text in (("SKILL.md", skill_text), ("references/version-selection.md", selection_text)):
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
        "shallow repository",
        "git rev-list --max-parents=0 HEAD",
        "git cat-file -p <root>",
        "commit headers before the first blank line",
        "repository-level `true` is not sufficient",
    )
    missing_reference_base = [value for value in reference_base_contract if value not in selection_text]
    if missing_reference_base:
        errors.append(
            "semver-release/references/version-selection.md: SemVer precedence contract lost fixtures: "
            f"{missing_reference_base}"
        )
    promotion_contract = "previous HEAD-reachable stable release, or repo root if none exists"
    if promotion_contract not in promotion_text:
        errors.append("semver-release/references/prerelease-promotion.md: stable-base contract is missing")
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
    sync_invariant = (
        "Ecosystem synchronization must not create the release commit, tag, or push, "
        "or refresh unrelated dependencies."
    )
    if sync_invariant not in skill_text:
        errors.append("semver-release/SKILL.md: bounded ecosystem synchronization invariant is missing")
    npm_sync_contract = (
        "existing `package-lock.json`",
        "`preversion`, `version`, and `postversion`",
        "npm version <version> --no-git-tag-version --ignore-scripts",
        "`package.json.version`",
        "`package-lock.json.version`",
        "`package-lock.json.packages[\"\"].version`",
    )
    missing_npm_sync = [value for value in npm_sync_contract if value not in version_files_text]
    npm_sync_ordered = not missing_npm_sync and [version_files_text.index(value) for value in npm_sync_contract] == sorted(
        version_files_text.index(value) for value in npm_sync_contract
    )
    if missing_npm_sync or not npm_sync_ordered:
        errors.append("semver-release/references/version-files.md: bounded npm synchronization contract is missing")
    cargo_sync_contract = (
        "authoritative version source",
        "`version.workspace = true`",
        "`[workspace.package].version`",
        "existing `Cargo.lock`",
        "cargo update --workspace",
        "cargo metadata --locked --format-version 1",
        "unrelated dependency versions remain locked",
    )
    missing_cargo_sync = [value for value in cargo_sync_contract if value not in version_files_text]
    cargo_sync_ordered = not missing_cargo_sync and [
        version_files_text.index(value) for value in cargo_sync_contract
    ] == sorted(version_files_text.index(value) for value in cargo_sync_contract)
    if missing_cargo_sync or not cargo_sync_ordered:
        errors.append("semver-release/references/version-files.md: bounded Cargo synchronization contract is missing")
    for line in version_files_text.splitlines():
        command = line.strip()
        if re.match(r"^npm version(?:\s|$)", command) and (
            "--no-git-tag-version" not in command or "--ignore-scripts" not in command
        ):
            errors.append("semver-release/references/version-files.md: npm command can own Git or lifecycle side effects")
            break
    if re.search(r"(?m)^\s*cargo update\s*$", version_files_text):
        errors.append("semver-release/references/version-files.md: bare cargo update can refresh dependencies")
    if "cargo metadata --locked --no-deps --format-version 1" in version_files_text:
        errors.append("semver-release/references/version-files.md: --no-deps metadata does not validate Cargo.lock")
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
