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

This module owns only catalog-wide rules that apply to every skill. Targeted
per-skill contracts in `scripts/contracts/<skill>.py` are optional and reserved
for executable or high-risk invariants; prompt-only semantics stay in SKILL.md
and evaluations.

Install the pinned validation dependency first. Exit 0 = clean, 1 = errors.
Warnings never fail.

    python -m pip install -r requirements-validation.txt
    python scripts/validate_skills.py            # validate this repo
    SKILLS_REPO=/path/to/repo python scripts/validate_skills.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contracts
from catalog_core import (
    ALLOWED_FRONTMATTER_FIELDS,
    GROUPING_MANIFEST,
    MARKETPLACE,
    METADATA_PROSE_CHARS_PER_SKILL,
    README,
    RELEASE_WORKFLOW,
    REPO,
    RESIDENT_SKILL_MAX_CHARS,
    RESIDENT_SKILL_MAX_LINES,
    SKILLS_DIR,
    VALIDATE_WORKFLOW,
    errors,
    parse_frontmatter,
    readme_skill_rows,
    warnings,
)

# Re-exported so `import validate_skills` stays the single entry point for the
# regression suite and for any external caller pinned to the flat module API.
from contracts.agent_scaffold import validate_agent_scaffold_contract
from contracts.conventional_commit import validate_conventional_commit_contract
from contracts.project_docs_organizer import (
    markdown_h2_sections,
    method_example_is_tree,
    validate_project_doc_method_cards,
    validate_project_doc_numbering_semantics,
    validate_project_docs_organizer_contract,
)
from contracts.semver_release import (
    validate_semver_automation_contract,
    validate_semver_publication_boundary,
    validate_semver_release_contract,
)
from contracts.tooling_conventions import (
    TOOLING_FORCED_SCRIPT_CONTRACT,
    validate_tooling_conventions_contract,
    validate_tooling_script_contract_semantics,
)

__all__ = [
    "TOOLING_FORCED_SCRIPT_CONTRACT",
    "cli",
    "errors",
    "main",
    "markdown_h2_sections",
    "method_example_is_tree",
    "parse_frontmatter",
    "readme_skill_rows",
    "report",
    "validate_agent_scaffold_contract",
    "validate_category_references",
    "validate_conventional_commit_contract",
    "validate_grouping_manifest",
    "validate_npx_discovery_contract",
    "validate_npx_payload_contract",
    "validate_project_doc_method_cards",
    "validate_project_doc_numbering_semantics",
    "validate_project_docs_organizer_contract",
    "validate_readme_catalog_count",
    "validate_repository_release_automation_contract",
    "validate_resident_contract",
    "validate_semver_automation_contract",
    "validate_semver_publication_boundary",
    "validate_semver_release_contract",
    "validate_targeted_contract_coverage",
    "validate_tooling_conventions_contract",
    "validate_tooling_script_contract_semantics",
    "warnings",
]


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


# Stop at cancel-in-progress rather than at whitespace: a group value contains
# `${{ ... }}` expressions, so \S+ would truncate it at the first inner space.
CONCURRENCY_GROUP = re.compile(r"concurrency: group: (.+?) cancel-in-progress:")


def validate_concurrency_isolation(normalized_validate: str, normalized_release: str) -> None:
    """Keep the reusable validation workflow out of its caller's concurrency group.

    `github.workflow` resolves to the CALLER's name inside a called workflow, so
    deriving validate.yml's group from it made the group identical to release.yml's
    own `release-<ref>`. The reusable call then queued behind its own caller, which
    sets cancel-in-progress: false, and the whole release run failed to start.
    """
    validate_group = CONCURRENCY_GROUP.search(normalized_validate)
    release_group = CONCURRENCY_GROUP.search(normalized_release)
    if not validate_group or not release_group:
        errors.append(
            "both workflows must declare a concurrency group so a superseded run "
            "cannot keep burning the matrix"
        )
        return

    if "github.workflow" in validate_group.group(1):
        errors.append(
            "validate.yml concurrency group must not use `github.workflow`: inside a "
            "workflow_call it resolves to the caller, colliding with release.yml's group"
        )
    if validate_group.group(1) == release_group.group(1):
        errors.append(
            "validate.yml and release.yml declare the same concurrency group "
            f"({validate_group.group(1)}); the reusable call would deadlock behind its caller"
        )


def validate_repository_release_automation_contract(
    validate_text: str | None = None, release_text: str | None = None
) -> None:
    """Keep this catalog's tag publisher reusable, ordered, and fail-closed."""

    missing_paths = [
        path.relative_to(REPO).as_posix()
        for path in (VALIDATE_WORKFLOW, RELEASE_WORKFLOW)
        if not path.is_file()
    ]
    if (validate_text is None or release_text is None) and missing_paths:
        errors.append(f"repository release automation is missing required workflows: {missing_paths}")
        return

    if validate_text is None:
        validate_text = VALIDATE_WORKFLOW.read_text(encoding="utf-8")
    if release_text is None:
        release_text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    normalized_validate = " ".join(validate_text.split())
    normalized_release = " ".join(release_text.split())
    required_validate = (
        # Trunk-only push + pull_request: every origin ref stays covered exactly
        # once. Matching "**" here would double-run the full matrix per PR branch.
        "push: branches: [main]",
        "pull_request:",
        "workflow_call:",
        "permissions: contents: read",
    )
    if 'branches: ["**"]' in normalized_validate:
        errors.append(
            "validate.yml must not run the full matrix on every branch push: "
            'pull_request already covers PR branches, so `branches: ["**"]` doubles each PR run'
        )
    validate_concurrency_isolation(normalized_validate, normalized_release)
    required_release = (
        'push: tags: ["v*"]',
        "permissions: contents: read",
        "uses: ./.github/workflows/validate.yml",
        "needs: validate",
        "contents: write",
        "tag_pattern=",
        'git rev-parse "$GITHUB_REF_NAME^{commit}"',
        "skills/semver-release/scripts/extract-changelog.py",
        '--tag "$GITHUB_REF_NAME"',
        '--output "$RUNNER_TEMP/release-notes.md"',
        "Inspect existing release",
        "id: release_state",
        "exists=true",
        "if: steps.release_state.outputs.exists != 'true'",
        'release create "$GITHUB_REF_NAME"',
        "--verify-tag",
        '--notes-file "$RUNNER_TEMP/release-notes.md"',
        'gh "${args[@]}"',
        "--prerelease --latest=false",
        "Verify GitHub Release",
        "expected_notes=",
        "actual_notes=",
    )
    missing = {
        "validate.yml": [value for value in required_validate if value not in normalized_validate],
        "release.yml": [value for value in required_release if value not in normalized_release],
    }
    missing = {label: values for label, values in missing.items() if values}
    if missing:
        errors.append(f"repository release automation lost required fixtures: {missing}")

    forbidden = ("--generate-notes", "pull_request_target:")
    found = [value for value in forbidden if value in normalized_release]
    if found:
        errors.append(
            "repository release automation must remain changelog-backed and least-privilege: "
            f"{found}"
        )

    extract = normalized_release.find("skills/semver-release/scripts/extract-changelog.py")
    publish = normalized_release.find('release create "$GITHUB_REF_NAME"')
    verify = normalized_release.find("Verify GitHub Release")
    if extract < 0 or publish < 0 or verify < 0 or not extract < publish < verify:
        errors.append(
            "repository release automation must extract notes before publishing and verify afterward"
        )


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


def validate_npx_payload_contract(workflow_text: str | None = None) -> None:
    """Require CI to compare every installed skill file with the catalog source."""
    if workflow_text is None:
        workflow = REPO / ".github" / "workflows" / "validate.yml"
        if not workflow.exists():
            return
        workflow_text = workflow.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^\s*- name: Smoke-test installed skill payloads\s*$"
        r"(.*?)(?=^\s*- name:|\Z)",
        workflow_text,
    )
    payload_step = match.group(1) if match else ""
    required = {
        "iterate every catalog skill": r'for source_skill in "\$repo"/skills/\*; do',
        "derive installed skill path": (
            r'installed_skill="\$fixture/\.agents/skills/\$skill"'
        ),
        "compare the complete source inventory": (
            r'expected=.*cd "\$source_skill".*find \. -type f -print \| sort'
        ),
        "compare the complete installed inventory": (
            r'actual=.*cd "\$installed_skill".*find \. -type f -print \| sort'
        ),
        "diff complete skill payload bytes": (
            r'diff -ru "\$source_skill" "\$installed_skill"'
        ),
    }
    missing = [label for label, pattern in required.items() if not re.search(pattern, payload_step)]
    if missing:
        errors.append(
            "CI npx install smoke must compare every installed skill payload with its "
            f"catalog source; missing={missing}"
        )


def validate_readme_catalog_count(readme_text: str, skill_count: int) -> None:
    """Keep any catalog count declared in the README aligned with skills/.

    The count is repository-derived inventory data, not prose opinion: once the
    README states it, adding or removing a skill must update it in the same
    change. A README that declares no count has nothing to drift.
    """
    match = re.search(r"catalog of (\d+) reusable", readme_text)
    if match is None:
        return
    declared = int(match.group(1))
    if declared != skill_count:
        errors.append(
            f"README declares a catalog of {declared} skills but skills/ contains "
            f"{skill_count}; update the declared count in the same change"
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


def validate_targeted_contract_coverage(
    skill_names: set[str], covered: set[str], required: set[str] | frozenset[str]
) -> None:
    """Reject missing required contracts and modules for absent catalog skills."""
    missing = sorted(required - covered)
    if missing:
        errors.append(f"required targeted contracts are missing: {missing}")
    unregistered = sorted((covered & skill_names) - required)
    if unregistered:
        errors.append(f"targeted contracts are not registered as required: {unregistered}")
    orphaned = sorted(covered - skill_names)
    if orphaned:
        errors.append(
            f"scripts/contracts/ declares contracts for missing skills: {orphaned}"
        )


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
    validate_readme_catalog_count(readme, len(skill_dirs))
    validate_npx_discovery_contract()
    validate_npx_payload_contract()
    validate_repository_release_automation_contract()

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

    # Prompt-only skills need no contract. Every targeted module is explicit and fail-closed.
    covered = set(contracts.run_all(readme_text=readme))
    validate_targeted_contract_coverage(
        {d.name for d in skill_dirs}, covered, contracts.REQUIRED_SKILLS
    )

    # Reverse coverage: a README link must point at a real skill directory.
    for m in re.finditer(r"\(skills/([A-Za-z0-9_-]+)/\)", readme):
        linked = m.group(1)
        if not (SKILLS_DIR / linked).is_dir():
            errors.append(f"README links `skills/{linked}/` but that skill directory does not exist")

    # Stale install paths: don't advertise the marketplace flow without a manifest.
    # `MARKETPLACE` intentionally names a file this repo does not ship — these two
    # guards exist so README can never advertise the marketplace install flow
    # without the manifest that flow requires.
    if "/plugin install" in readme and not MARKETPLACE.exists():
        errors.append("README advertises `/plugin install` but `.claude-plugin/marketplace.json` does not exist")
    if ".claude-plugin/marketplace.json" in readme and not MARKETPLACE.exists():
        errors.append("README references `.claude-plugin/marketplace.json` which does not exist")

    return report()


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
