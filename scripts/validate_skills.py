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
ALLOWED_FRONTMATTER_FIELDS = {"name", "description"}
RESIDENT_SKILL_MAX_LINES = 100
RESIDENT_SKILL_MAX_CHARS = 8000

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
REFERENCE_LOAD_BOUNDARY = re.compile(
    r"^(?:read|consult|open|load|use) this (?:only )?(?:when|for|after)\b",
    re.IGNORECASE | re.MULTILINE,
)
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
    if reference_files and not re.search(r"(?mi)^## On-demand references\s*$", skill_text):
        errors.append(f"{skill_name}: SKILL.md must route references under `## On-demand references`")
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
        try:
            reference_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{skill_name}: cannot read reference {relative}: {exc}")
        else:
            if not REFERENCE_LOAD_BOUNDARY.search(reference_text[:600]):
                errors.append(
                    f"{skill_name}: reference must state its conditional load boundary near the top: {relative}"
                )

    if linked and not references_dir.is_dir():
        errors.append(f"{skill_name}: SKILL.md links references/ but the directory does not exist")


def validate_resident_contract(skill_dir: Path, skill_text: str, frontmatter: dict[str, object]) -> None:
    """Keep resident skill context routing-oriented and host-neutral."""
    skill_name = skill_dir.name
    extra_fields = sorted(set(frontmatter) - ALLOWED_FRONTMATTER_FIELDS)
    if extra_fields:
        errors.append(
            f"{skill_name}: frontmatter fields must be only name + description; extra={extra_fields}"
        )
    line_count = len(skill_text.splitlines())
    if line_count > RESIDENT_SKILL_MAX_LINES:
        errors.append(
            f"{skill_name}: resident SKILL.md is {line_count} lines "
            f"(>{RESIDENT_SKILL_MAX_LINES}); route detail to categorized references"
        )
    if len(skill_text) > RESIDENT_SKILL_MAX_CHARS:
        errors.append(
            f"{skill_name}: resident SKILL.md is {len(skill_text)} chars "
            f"(>{RESIDENT_SKILL_MAX_CHARS}); route detail to categorized references"
        )
    if re.search(r"(?mi)^## When To Use\s*$", skill_text):
        errors.append(
            f"{skill_name}: trigger boundaries belong in frontmatter description, not a resident `When To Use` section"
        )


def readme_skill_rows(readme_text: str, skill_name: str) -> str:
    """Return public catalog rows for one skill so domain guards cover that projection."""
    marker = f"[{skill_name}](skills/{skill_name}/)"
    return "\n".join(line for line in readme_text.splitlines() if marker in line)


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

        validate_resident_contract(d, text, fm)

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
    validate_tooling_conventions_contract(readme_text=readme)
    validate_conventional_commit_contract()
    validate_semver_release_contract()
    validate_project_docs_organizer_contract(readme_text=readme)

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


def validate_tooling_conventions_contract(*, readme_text: str | None = None) -> None:
    """Keep structural inventory checks deterministic and semantic policy project-owned."""
    skill_dir = SKILLS_DIR / "tooling-conventions"
    paths = {
        "SKILL.md": skill_dir / "SKILL.md",
        "references/verification.md": skill_dir / "references" / "verification.md",
        "references/classification-methods.md": skill_dir / "references" / "classification-methods.md",
        "references/inventory-contract.md": skill_dir / "references" / "inventory-contract.md",
        "references/migration-from-surface-manifest.md": (
            skill_dir / "references" / "migration-from-surface-manifest.md"
        ),
        "references/script-contract.md": skill_dir / "references" / "script-contract.md",
        "references/path-migrations.md": skill_dir / "references" / "path-migrations.md",
        "scripts/inventory-check.sh": skill_dir / "scripts" / "inventory-check.sh",
    }
    missing_paths = [label for label, path in paths.items() if not path.exists()]
    if missing_paths:
        errors.append(f"tooling-conventions: missing contextual-governance assets: {missing_paths}")
        return
    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    public_summary = readme_skill_rows(readme_text, "tooling-conventions")
    memory_compile = (
        "python -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), "
        "sys.argv[1], \"exec\")'"
    )
    for label in ("references/verification.md", "scripts/inventory-check.sh"):
        if memory_compile not in texts[label]:
            errors.append(f"tooling-conventions/{label}: in-memory Python compile command is missing")
    stale = [label for label, value in texts.items() if "py_compile" in value]
    if stale:
        errors.append(f"tooling-conventions: py_compile bytecode-producing guidance remains in {stale}")

    fixture = REPO / "scripts" / "tests" / "test-tooling-inventory.sh"
    fixture_text = fixture.read_text(encoding="utf-8") if fixture.exists() else ""
    fixture_contract = (
        "valid path-雪.py",
        "-dash.sh",
        "inventory check left Python bytecode residue",
        "structural findings above use exit 1",
        "Exact parent segments remain blocking",
        "invalid inventory path (must be normalized and relative)",
        "invalid audit_level for tool.sh: maybe",
        "expected invalid CLI arguments to exit 2",
        "failed to create temporary directory",
        "expected an unsafe temporary-directory result",
        "directory inventory row does not cover nested commands",
        "TOOLS_DIR did not override the inventory directory",
        "default skip policy hid a project-owned command",
        "expected missing Python preflight to exit 2",
    )
    missing_fixture = [value for value in fixture_contract if value not in fixture_text]
    if missing_fixture:
        errors.append(
            "tooling-conventions: structural-inventory CI fixture is incomplete: "
            f"{missing_fixture}"
        )
    workflow = REPO / ".github" / "workflows" / "validate.yml"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    if "bash scripts/tests/test-tooling-inventory.sh" not in workflow_text:
        errors.append("tooling-conventions: CI does not run the focused inventory-check suite")
    stale_compatibility = ("≥1 release", "at least one release")
    combined = "".join(texts.values()) + fixture_text
    found_stale = [value for value in stale_compatibility if value in combined]
    if found_stale:
        errors.append(f"tooling-conventions: generic compatibility-cycle guidance remains: {found_stale}")
    project_owned_contract = {
        "SKILL.md": ("target repository owns names and roots", "Tool Governance Decision Record"),
        "references/classification-methods.md": (
            "## Boundary lenses",
            "## Constraint lenses",
            "not required categories or directory names",
        ),
        "references/inventory-contract.md": (
            "Only `path` is required",
            "project-owned columns are opaque",
            "`tools/tools-inventory.tsv` is only the no-argument default",
            "When unset, reverse scan",
            "excludes nothing",
        ),
        "references/script-contract.md": (
            "Inventory registration, when adopted",
            "Do not create an inventory solely",
        ),
        "references/migration-from-surface-manifest.md": (
            "`public` / `helper`",
            "Project Tool Policy",
            "no compatibility wrapper",
        ),
    }
    for label, required_values in project_owned_contract.items():
        missing_values = [value for value in required_values if value not in texts[label]]
        if missing_values:
            errors.append(
                f"tooling-conventions/{label}: project-owned root/manifest boundary lost fixtures: "
                f"{missing_values}"
            )

    checker_contract = (
        'SKIP_RE="${INVENTORY_CHECK_SKIP:-a^}"',
        'echo "python interpreter unavailable for syntax check: $path" >&2',
    )
    missing_checker_contract = [
        value for value in checker_contract if value not in texts["scripts/inventory-check.sh"]
    ]
    if missing_checker_contract:
        errors.append(
            "tooling-conventions/scripts/inventory-check.sh: neutral-scan/preflight contract "
            f"is incomplete: {missing_checker_contract}"
        )
    if "(internal|vendor|tests?|legacy)" in texts["scripts/inventory-check.sh"]:
        errors.append(
            "tooling-conventions/scripts/inventory-check.sh: semantic directory exclusions "
            "remain in the structural checker"
        )

    required_boundary_phrases = (
        "There is no required `tools/`, `scripts/`, or `bin/` root",
        "no mandatory semantic inventory",
        "only the structural `path` contract is universal",
    )
    missing_boundary_phrases = [
        value for value in required_boundary_phrases if value not in texts["SKILL.md"]
    ]
    if missing_boundary_phrases:
        errors.append(
            "tooling-conventions/SKILL.md: project-owned placement/schema boundary is incomplete: "
            f"{missing_boundary_phrases}"
        )

    retired_paths = (
        skill_dir / "references" / "surface-taxonomy.md",
        skill_dir / "references" / "manifest-schema.md",
        skill_dir / "scripts" / "manifest-check.sh",
    )
    found_retired_paths = [str(path.relative_to(skill_dir)) for path in retired_paths if path.exists()]
    if found_retired_paths:
        errors.append(
            "tooling-conventions: retired flat-surface assets remain: "
            f"{found_retired_paths}"
        )

    non_migration_text = "".join(
        text
        for label, text in texts.items()
        if label != "references/migration-from-surface-manifest.md"
    ) + public_summary
    stale_flat_contract = (
        "scripts/manifest-check.sh",
        "references/surface-taxonomy.md",
        "references/manifest-schema.md",
        "MANIFEST_CHECK_SKIP",
        "surface_current",
    )
    found_flat_contract = [value for value in stale_flat_contract if value in non_migration_text]
    if found_flat_contract:
        errors.append(
            "tooling-conventions: retired flat-surface contract remains active: "
            f"{found_flat_contract}"
        )

    prohibited_active_contracts = {
        "exactly-one surface taxonomy": (
            "exactly one `surface`",
            "exactly-one `surface`",
            "one row per command surface",
            "Full surface taxonomy",
        ),
        "fixed directory layout": (
            "<tool-root>/<domain>/",
            "tools/public/",
            "tools/internal/",
            "placement guidance when the project has no stronger convention",
        ),
        "mandatory semantic schema": (
            "path\tsurface",
            "must have a 'path' and a 'surface'",
            "Core columns (every row)",
        ),
    }
    for contract_name, forbidden_values in prohibited_active_contracts.items():
        found_values = [value for value in forbidden_values if value in non_migration_text]
        if found_values:
            errors.append(
                f"tooling-conventions: reintroduced {contract_name}: {found_values}"
            )


def validate_conventional_commit_contract(skill_dir: Path | None = None) -> None:
    """Keep commit mode rooted and prevent staging changes on a detached HEAD."""
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
    stage = "stage the exact intended"
    required = (root, preflight, detached, git_error, stage)
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


def validate_semver_release_contract() -> None:
    """Guard bump inference and package identity across release ecosystems."""
    skill_dir = SKILLS_DIR / "semver-release"
    skill = skill_dir / "SKILL.md"
    reference_paths = {
        "references/version-selection.md": skill_dir / "references" / "version-selection.md",
        "references/version-files.md": skill_dir / "references" / "version-files.md",
        "references/changelog.md": skill_dir / "references" / "changelog.md",
        "references/prerelease-promotion.md": skill_dir / "references" / "prerelease-promotion.md",
        "references/publishing.md": skill_dir / "references" / "publishing.md",
    }
    planner = skill_dir / "scripts" / "release-plan.py"
    if not skill.exists() or not planner.exists() or any(not path.exists() for path in reference_paths.values()):
        return
    skill_text = skill.read_text(encoding="utf-8")
    reference_texts = {label: path.read_text(encoding="utf-8") for label, path in reference_paths.items()}
    selection_text = reference_texts["references/version-selection.md"]
    version_files_text = reference_texts["references/version-files.md"]
    promotion_text = reference_texts["references/prerelease-promotion.md"]
    changelog_text = reference_texts["references/changelog.md"]
    publishing_text = reference_texts["references/publishing.md"]
    planner_text = planner.read_text(encoding="utf-8")
    combined = skill_text + "".join(reference_texts.values())
    bump_contract = (
        "BREAKING CHANGE:",
        "BREAKING-CHANGE:",
        "case-insensitive",
        "remains uppercase",
    )
    missing_bump = [value for value in bump_contract if value not in selection_text]
    if missing_bump:
        errors.append(
            "semver-release/references/version-selection.md: bump inference contract lost fixtures: "
            f"{missing_bump}"
        )
    required = ("1.2.0-beta.1", "1.2.0b1", "1.2.0rc1", "project(... VERSION 1.2.0)")
    missing = [value for value in required if value not in combined]
    if missing:
        errors.append(f"semver-release: prerelease ecosystem contract lost fixtures: {missing}")
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
    missing_base = [value for value in shared_base_contract if value not in selection_text]
    if missing_base:
        errors.append(
            "semver-release/references/version-selection.md: base-selection contract lost fixtures: "
            f"{missing_base}"
        )
    equal_precedence = (
        "When highest-precedence tags differ only by build metadata, use their shared commit as "
        "`<base>` only if they all resolve to that commit; otherwise stop and report the ambiguity."
    )
    peel_commit = "git rev-parse '<tag>^{commit}'"
    if equal_precedence not in selection_text:
        errors.append("semver-release/references/version-selection.md: equal-precedence base rule is missing")
    if peel_commit not in selection_text:
        errors.append("semver-release/references/version-selection.md: annotated-tag commit resolution is missing")
    skill_router_contract = (
        "scripts/release-plan.py",
        "--json",
        "--target vX.Y.Z",
        "Resolve every `attention` result before mutation",
        "A valid exact version supplied by the user is the target",
    )
    missing_skill_router = [value for value in skill_router_contract if value not in skill_text]
    if missing_skill_router:
        errors.append(f"semver-release/SKILL.md: read-only planner route lost fixtures: {missing_skill_router}")
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
        "Stage every release file and no unrelated path",
        "git diff --cached --check",
        "create `release: vX.Y.Z`",
        "require a clean",
        "push the tag without force",
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
        "Ecosystem tools synchronize release files; they do not own the release commit, tag, or push, and"
    )
    if sync_invariant not in version_files_text:
        errors.append("semver-release/references/version-files.md: bounded synchronization invariant is missing")
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
    publishing_contract = (
        "Tag-triggered release workflow",
        "Direct forge release",
        "gh release create vX.Y.Z",
        "--verify-tag",
        "local and remote tags exist and peel to that release commit",
        "A release commit, pushed tag, CI run, forge release, and",
    )
    missing_publishing = [value for value in publishing_contract if value not in publishing_text]
    if missing_publishing:
        errors.append(
            "semver-release/references/publishing.md: publication ownership or verification lost fixtures: "
            f"{missing_publishing}"
        )
    planner_contract = (
        "schema_version",
        "parse_semver",
        "compare_semver",
        "complete-head-history",
        "reachable-semver-base",
        "BREAKING_FOOTER_RE",
        "requested_tag",
        "selected_tag",
        "release_notes_base",
        "The script never fetches, edits, commits, tags, or pushes.",
    )
    missing_planner = [value for value in planner_contract if value not in planner_text]
    if missing_planner:
        errors.append(
            "semver-release/scripts/release-plan.py: deterministic planner contract lost fixtures: "
            f"{missing_planner}"
        )
    changelog_authority_contract = (
        "repository's existing release-note contract wins",
        "Do not create `CHANGELOG.md` solely because this skill ran",
        "Fallback committed changelog",
    )
    missing_changelog_authority = [
        value for value in changelog_authority_contract if value not in changelog_text
    ]
    if missing_changelog_authority:
        errors.append(
            "semver-release/references/changelog.md: project-owned release-note boundary "
            f"lost fixtures: {missing_changelog_authority}"
        )
    planner_tests = REPO / "scripts" / "tests" / "test_semver_release_plan.py"
    planner_test_text = planner_tests.read_text(encoding="utf-8") if planner_tests.exists() else ""
    test_contract = (
        "test_infers_patch_without_mutating_repository",
        "test_breaking_footer_infers_major",
        "test_prerelease_requires_target",
        "test_equal_precedence_tags_on_different_commits_are_ambiguous",
        "test_no_commits_after_base_blocks_explicit_target",
        "test_unclassified_commit_requires_an_explicit_target",
        "test_equal_precedence_build_tags_on_one_commit_share_the_base",
        "test_known_prerelease_order_selects_the_stable_base",
        "test_numbered_prerelease_can_advance_explicitly",
        "test_detached_head_requires_attention",
        "test_real_shallow_boundary_blocks_base_selection",
    )
    missing_tests = [value for value in test_contract if value not in planner_test_text]
    if missing_tests:
        errors.append(f"semver-release: release planner regression suite is incomplete: {missing_tests}")
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


PROJECT_DOC_METHOD_CARDS = (
    "Reader role",
    "Task or journey",
    "Domain capability, ownership, and language",
    "Product, subsystem, or interface surface",
    "Content purpose or information type",
    "Lifecycle or authority",
)
PROJECT_DOC_METHOD_FIELDS = (
    "Signals",
    "Ask",
    "Fits when",
    "Fails when",
    "Axis role",
    "Micro-example",
)
PROJECT_DOC_H2 = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
PROJECT_DOC_METHOD_FIELD = re.compile(
    r"^-[ \t]+\*\*(Signals|Ask|Fits when|Fails when|Axis role|Micro-example)\*\*:"
    r"[ \t]*(.*)$",
    re.MULTILINE,
)
PROJECT_DOC_FENCE = re.compile(r"^[ \t]*(?:```|~~~)", re.MULTILINE)
PROJECT_DOC_TREE_ENTRY = re.compile(
    r"^\s*(?:[│├└─+|`\\-]+\s*)?[A-Za-z0-9_.-]+(?:/|\.mdx?)\s*$"
)
PROJECT_DOC_FIXED_RANGE = (
    re.compile(r"(?i)(?<![A-Za-z0-9])`?[0-9]+x`?(?![A-Za-z0-9])"),
    re.compile(
        r"(?i)(?<![0-9])`?[0-9]{1,2}\s*(?:-|–|—|\.\.|to|through)\s*"
        r"[0-9]{1,2}`?(?![0-9])"
    ),
)
PROJECT_DOC_FORCED_NUMBERING = (
    re.compile(
        r"(?i)(?<!not )(?<!never )\balways\s+(?:number|prefix)\b[^\n.!?]{0,80}"
    ),
    re.compile(
        r"(?i)\b(?:numbering|numeric prefixes?)\b[^\n.!?]{0,20}"
        r"\b(?:is|are|remain|remains|become|becomes)\s+"
        r"(?:(?:always|universally)\s+)?(?:required|mandatory)\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:every|all)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
        r"[^\n.!?]{0,60}\b(?:must|shall)\b[^\n.!?]{0,40}"
        r"\b(?:numbering|numbered|numeric prefixes?)\b"
    ),
    re.compile(
        r"(?i)\b(?:numbering|numeric prefixes?)\b[^\n.!?]{0,40}"
        r"\b(?:cannot|must not|may not|never)\s+be\s+disabled\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:enable|apply|add|use)\s+"
        r"(?:numbering|numeric prefixes?)\s+"
        r"(?:for|to|in)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )(?<!not always )(?<!never always )"
        r"\b(?:number|prefix)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
    re.compile(
        r"(?i)(?<!not )(?<!never )\b(?:every|all)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b[^\n.!?]{0,30}"
        r"\b(?:is|are|remain|remains|stay|stays)\s+(?:always\s+)?numbered\b"
    ),
    re.compile(
        r"(?i)\bnumbering\s+(?:always\s+)?(?:applies|is applied)\s+"
        r"(?:to|in)\s+(?:all|every)\s+"
        r"(?:project|repository|documentation tree|docs tree)s?\b"
    ),
)
PROJECT_DOC_DEFAULT_ON_NUMBERING = (
    re.compile(
        r"(?i)(?<!not )(?<!never )(?<!n't )\b(?:enable|use|apply)\s+"
        r"(?:local\s+)?numbering\s+by\s+default\b"
    ),
    re.compile(r"(?i)\boptional\s+default-on(?:\s+local)?\s+numbering\b"),
)


def markdown_h2_sections(text: str) -> dict[str, list[str]]:
    """Return level-two Markdown sections without treating deeper headings as peers."""
    matches = list(PROJECT_DOC_H2.finditer(text))
    sections: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.setdefault(match.group(1).strip(), []).append(text[match.end() : end])
    return sections


def method_example_is_tree(field_block: str) -> bool:
    """Reject fenced or visibly tree-shaped examples while allowing ordinary prose."""
    if PROJECT_DOC_FENCE.search(field_block) or any(
        marker in field_block for marker in ("├──", "└──", "│")
    ):
        return True
    tree_entries = [
        line for line in field_block.splitlines() if PROJECT_DOC_TREE_ENTRY.fullmatch(line)
    ]
    return len(tree_entries) >= 2


def validate_project_doc_method_cards(method_text: str) -> None:
    """Require the six method cards and their reasoning fields card by card."""
    sections = markdown_h2_sections(method_text)
    invalid_cards = [
        f"{title} ({len(sections.get(title, []))})"
        for title in PROJECT_DOC_METHOD_CARDS
        if len(sections.get(title, [])) != 1
    ]
    if invalid_cards:
        errors.append(
            "project-docs-organizer/references/classification-methods.md: "
            f"method-card set is incomplete or duplicated: {invalid_cards}"
        )

    for title in PROJECT_DOC_METHOD_CARDS:
        card_bodies = sections.get(title, [])
        if len(card_bodies) != 1:
            continue
        body = card_bodies[0]
        field_matches = list(PROJECT_DOC_METHOD_FIELD.finditer(body))
        field_counts = {
            field: sum(match.group(1) == field for match in field_matches)
            for field in PROJECT_DOC_METHOD_FIELDS
        }
        invalid_fields = [
            f"{field} ({count})" for field, count in field_counts.items() if count != 1
        ]
        empty_fields = [match.group(1) for match in field_matches if not match.group(2).strip()]
        invalid_fields.extend(f"{field} (empty)" for field in empty_fields)
        if invalid_fields:
            errors.append(
                "project-docs-organizer/references/classification-methods.md: "
                f"{title} method card must contain each reasoning field exactly once: "
                f"{invalid_fields}"
            )
            continue

        micro_index = next(
            index
            for index, match in enumerate(field_matches)
            if match.group(1) == "Micro-example"
        )
        micro_start = field_matches[micro_index].start()
        micro_end = (
            field_matches[micro_index + 1].start()
            if micro_index + 1 < len(field_matches)
            else len(body)
        )
        if method_example_is_tree(body[micro_start:micro_end]):
            errors.append(
                "project-docs-organizer/references/classification-methods.md: "
                f"{title} micro-example must be prose, not a directory tree"
            )


def validate_project_doc_numbering_semantics(
    numbering_text: str, *, combined_text: str | None = None
) -> None:
    """Reject global numeric taxonomies and unconditional or default-on numbering."""
    fixed_ranges = sorted(
        {
            match.group(0)
            for pattern in PROJECT_DOC_FIXED_RANGE
            for match in pattern.finditer(numbering_text)
        }
    )
    if fixed_ranges:
        errors.append(
            "project-docs-organizer: fixed numeric range notation is prohibited; "
            f"use sibling-local ordering tokens only: {fixed_ranges}"
        )

    forced_rules = sorted(
        {
            match.group(0).strip()
            for pattern in PROJECT_DOC_FORCED_NUMBERING
            for match in pattern.finditer(numbering_text)
        }
    )
    if forced_rules:
        errors.append(
            "project-docs-organizer/references/numbering-patterns.md: "
            f"unconditional numbering mandate contradicts project opt-outs: {forced_rules}"
        )
    default_on_rules = sorted(
        {
            match.group(0).strip()
            for pattern in PROJECT_DOC_DEFAULT_ON_NUMBERING
            for match in pattern.finditer(combined_text or numbering_text)
        }
    )
    if default_on_rules:
        errors.append(
            "project-docs-organizer: default-on numbering contradicts the evidence gate: "
            f"{default_on_rules}"
        )


def validate_project_docs_organizer_contract(
    skill_dir: Path | None = None, *, readme_text: str | None = None
) -> None:
    """Keep documentation structure evidence-led and local numbering project-owned."""
    skill_dir = skill_dir or SKILLS_DIR / "project-docs-organizer"
    paths = {
        "SKILL.md": skill_dir / "SKILL.md",
        "references/information-architecture.md": skill_dir / "references" / "information-architecture.md",
        "references/classification-methods.md": skill_dir / "references" / "classification-methods.md",
        "references/numbering-patterns.md": skill_dir / "references" / "numbering-patterns.md",
        "references/migration-and-links.md": skill_dir / "references" / "migration-and-links.md",
    }
    retired_zone_catalog = skill_dir / "references" / "zone-catalog.md"
    if retired_zone_catalog.exists():
        errors.append("project-docs-organizer: retired references/zone-catalog.md still exists")
    missing_files = [label for label, path in paths.items() if not path.exists()]
    if missing_files:
        errors.append(f"project-docs-organizer: missing required files: {missing_files}")
        return
    texts = {label: path.read_text(encoding="utf-8") for label, path in paths.items()}
    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    public_summary = readme_skill_rows(readme_text, "project-docs-organizer")
    normalized = {label: " ".join(text.split()) for label, text in texts.items()}
    normalized_skill = normalized["SKILL.md"]
    project_owned_contract = (
        "The target project owns its information architecture",
        "smallest structure",
        "preserve a coherent established convention",
        "one primary axis per tree level",
        "documentation IA decision record",
        "two or three candidates",
        "wait for the user before mutation",
        "No empty category",
        "Resolve the target project root",
    )
    missing = [value for value in project_owned_contract if value not in normalized_skill]
    if missing:
        errors.append(
            "project-docs-organizer/SKILL.md: project-owned information architecture lost fixtures: "
            f"{missing}"
        )
    architecture_contract = (
        "Reader-route separation",
        "Vocabulary and ownership cohesion",
        "Lifecycle consistency",
        "Stability under change",
        "Duplication pressure",
        "Choose one primary axis",
        "secondary lenses",
        "representative placement test",
        "two or three candidates",
        "wait for the user before mutation",
        "absence of a convention",
        "not evidence for numbering",
        "stable sibling",
        "path/link churn",
    )
    missing_architecture = [
        value
        for value in architecture_contract
        if value not in normalized["references/information-architecture.md"]
    ]
    if missing_architecture:
        errors.append(
            "project-docs-organizer/references/information-architecture.md: "
            f"evidence-led selection contract is incomplete: {missing_architecture}"
        )
    validate_project_doc_method_cards(texts["references/classification-methods.md"])
    numbering_contract = (
        "Keep numbering disabled by default",
        "stable sibling",
        "observed reader route",
        "path/link churn",
        "coherent established convention",
        "documentation generator owns ordering or navigation",
        "sibling-local position",
        "`10-`",
        "`20-`",
        "`00-`",
        "genuine reading or execution order",
        "not category meaning",
    )
    missing_numbering = [
        value
        for value in numbering_contract
        if value not in normalized["references/numbering-patterns.md"]
    ]
    if missing_numbering:
        errors.append(
            "project-docs-organizer/references/numbering-patterns.md: "
            f"evidence and opt-out numbering contract is incomplete: {missing_numbering}"
        )
    combined = "\n".join((*texts.values(), public_summary))
    validate_project_doc_numbering_semantics(
        texts["references/numbering-patterns.md"], combined_text=combined
    )
    stale_template_rules = (
        "## Default Zone Model",
        "# Optional Documentation Zone Catalog",
        "## Candidate zone catalog",
        "`00-start-here`",
        "`20-development-overview`",
        "The developer area is `2x`",
        "one-class-per-zone rule",
        "semantic numbered zones",
    )
    found_stale = [value for value in stale_template_rules if value in combined]
    if found_stale:
        errors.append(
            "project-docs-organizer: retired zone-template semantics remain: "
            f"{found_stale}"
        )
    migration_contract = (
        "Build the migration map",
        "Before deleting",
        "rg -n -F 'old/path.md' <project-root>",
        "external wikis or issue trackers",
        "git diff --check",
    )
    missing_migration = [
        value for value in migration_contract if value not in texts["references/migration-and-links.md"]
    ]
    if missing_migration:
        errors.append(
            "project-docs-organizer/references/migration-and-links.md: migration evidence lost fixtures: "
            f"{missing_migration}"
        )


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


def cli(argv: list[str]) -> int:
    """Run the no-argument validator CLI without masking invalid options."""
    if argv in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if argv:
        print("usage: python scripts/validate_skills.py [-h|--help]", file=sys.stderr)
        print(f"error: unknown or invalid argument(s): {' '.join(argv)}", file=sys.stderr)
        return 2
    return main()


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
