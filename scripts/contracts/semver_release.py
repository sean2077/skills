"""Contract guards for the `semver-release` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`semver-release` skill contract changes.
"""

from __future__ import annotations

import json
import re

from catalog_core import README, REPO, SKILLS_DIR, errors, readme_skill_rows

SKILL = "semver-release"


def validate_semver_publication_boundary(
    skill_text: str, publishing_text: str, public_summary: str
) -> None:
    """Keep release completion policy-derived instead of forge-mandatory."""
    normalized_skill = " ".join(skill_text.split())
    normalized_publishing = " ".join(publishing_text.split())
    normalized_public = " ".join(public_summary.split())
    skill_contract = (
        "repository-owned completion boundary",
        "Stop at a verified pushed tag only when policy makes it terminal",
        "Create a direct forge release only when the forge is the established release surface",
        "every applicable downstream publisher identity",
        "URLs or identities that the selected boundary actually exposes",
    )
    publishing_contract = (
        "Tag-only or external handoff",
        "Tag-triggered release workflow",
        "Project-owned direct publisher",
        "Direct forge release",
        "absence of a tag workflow does not authorize a new forge release",
        "gh release create <exact-tag>",
        "--verify-tag",
        "local and remote tags exist and peel to that release commit",
        "Only the evidence for the selected boundary is mandatory",
        "distinct states",
    )
    missing_skill = [value for value in skill_contract if value not in normalized_skill]
    missing_publishing = [
        value for value in publishing_contract if value not in normalized_publishing
    ]
    if missing_skill or missing_publishing or "policy-derived publication verification" not in normalized_public:
        errors.append(
            "semver-release: repository-owned publication boundary lost fixtures: "
            f"skill={missing_skill}, publishing={missing_publishing}, public_summary="
            f"{'present' if 'policy-derived publication verification' in normalized_public else 'missing'}"
        )
    forbidden = (
        "A pushed tag is not completion",
        "otherwise create the forge release",
        "through a verified forge release",
        "Use this only when no tag-triggered release owner exists",
    )
    combined = " ".join((normalized_skill, normalized_publishing, normalized_public))
    found = [value for value in forbidden if value in combined]
    if found:
        errors.append(
            "semver-release: publication policy must not require a universal forge surface: "
            f"{found}"
        )


def validate_semver_automation_contract(
    skill_text: str,
    automation_text: str,
    changelog_text: str,
    publishing_text: str,
    extractor_text: str,
    public_summary: str,
) -> None:
    """Keep preferred automation opt-in, format-neutral, and fail-closed."""

    normalized = {
        "skill": " ".join(skill_text.split()),
        "automation": " ".join(automation_text.split()),
        "changelog": " ".join(changelog_text.split()),
        "publishing": " ".join(publishing_text.split()),
        "extractor": " ".join(extractor_text.split()),
        "public": " ".join(public_summary.split()),
    }
    required = {
        "skill": (
            "Prefer changelog-backed tag-triggered automation",
            "ask once whether to retain or migrate",
            "this gate also applies to a mature alternative",
            "Make no infrastructure change without an answer",
            "The analyzer models `v`-prefixed SemVer tags",
            "create `release: <exact-tag>`",
        ),
        "automation": (
            "Preferred Automated Release Flow",
            "Adoption offer",
            "including a mature alternative",
            "present one concrete current-versus-preferred comparison and ask once whether to retain",
            "Maturity alone is not a retention decision",
            "make no changelog-authority, workflow, permission, publisher, or release-surface change",
            "`v1.2.3`, `1.2.3`, `release-1.2.3`",
            "opaque exact string",
            "before any forge Release creation",
            "Do not generate fallback notes",
            "scripts/extract-changelog.py",
            "gh release create",
            "--notes-file",
            "Do not reconstruct it from a package version or assume a `v` prefix",
        ),
        "changelog": (
            "## [<exact-tag>] — YYYY-MM-DD",
            "`## [v1.2.3] — 2026-07-21`",
            "`## [1.3.0-rc.1] — 2026-07-21`",
            "`## [release-1.2.3] — 2026-07-21`",
            "trimmed body after the one matching heading",
            "next level-two heading",
            "Do not include the release heading itself",
            "never falls back to generated notes",
        ),
        "publishing": (
            "Preferred changelog-backed workflow",
            "Workflow-owned generated notes",
            "After the owner explicitly retains an established workflow",
            "before any forge Release creation",
            "do not fall back to generated notes",
        ),
        "extractor": (
            "def extract_notes",
            "def write_notes",
            "CANONICAL_HEADING_RE",
            "--changelog",
            "--tag",
            "--output",
            "complete repository tag, matched exactly",
            "os.replace",
        ),
        "public": ("preferred changelog-backed tag workflow",),
    }
    missing = {
        label: [value for value in values if value not in normalized[label]]
        for label, values in required.items()
    }
    missing = {label: values for label, values in missing.items() if values}
    if missing:
        errors.append(f"semver-release: preferred automation contract lost fixtures: {missing}")

    automation = normalized["automation"]
    extractor_call = automation.find("scripts/extract-changelog.py")
    publisher_call = automation.find("gh release create")
    if extractor_call < 0 or publisher_call < 0 or extractor_call > publisher_call:
        errors.append(
            "semver-release/references/automated-release-flow.md: notes validation must precede publication"
        )

    forbidden = {
        "automation": ("--generate-notes",),
        "extractor": ('startswith("v")', "removeprefix(\"v\")", "parse_semver"),
    }
    found = {
        label: [value for value in values if value in normalized[label]]
        for label, values in forbidden.items()
    }
    found = {label: values for label, values in found.items() if values}
    if found:
        errors.append(
            "semver-release: preferred automation must not add a generated-notes fallback or tag-prefix assumption: "
            f"{found}"
        )


def validate_semver_release_contract(readme_text: str | None = None) -> None:
    """Guard bump inference and package identity across release ecosystems."""
    skill_dir = SKILLS_DIR / "semver-release"
    skill = skill_dir / "SKILL.md"
    reference_paths = {
        "references/version-selection.md": skill_dir / "references" / "version-selection.md",
        "references/version-files.md": skill_dir / "references" / "version-files.md",
        "references/changelog.md": skill_dir / "references" / "changelog.md",
        "references/automated-release-flow.md": skill_dir / "references" / "automated-release-flow.md",
        "references/prerelease-promotion.md": skill_dir / "references" / "prerelease-promotion.md",
        "references/publishing.md": skill_dir / "references" / "publishing.md",
    }
    planner = skill_dir / "scripts" / "release-plan.py"
    extractor = skill_dir / "scripts" / "extract-changelog.py"
    required_paths = {
        "SKILL.md": skill,
        **reference_paths,
        "scripts/release-plan.py": planner,
        "scripts/extract-changelog.py": extractor,
    }
    missing_paths = [label for label, path in required_paths.items() if not path.exists()]
    if missing_paths:
        errors.append(f"semver-release: missing required files: {missing_paths}")
        return
    skill_text = skill.read_text(encoding="utf-8")
    reference_texts = {label: path.read_text(encoding="utf-8") for label, path in reference_paths.items()}
    selection_text = reference_texts["references/version-selection.md"]
    version_files_text = reference_texts["references/version-files.md"]
    promotion_text = reference_texts["references/prerelease-promotion.md"]
    changelog_text = reference_texts["references/changelog.md"]
    automation_text = reference_texts["references/automated-release-flow.md"]
    publishing_text = reference_texts["references/publishing.md"]
    planner_text = planner.read_text(encoding="utf-8")
    extractor_text = extractor.read_text(encoding="utf-8")
    if readme_text is None:
        readme_text = README.read_text(encoding="utf-8") if README.exists() else ""
    validate_semver_publication_boundary(
        skill_text,
        publishing_text,
        readme_skill_rows(readme_text, "semver-release"),
    )
    validate_semver_automation_contract(
        skill_text,
        automation_text,
        changelog_text,
        publishing_text,
        extractor_text,
        readme_skill_rows(readme_text, "semver-release"),
    )
    combined = skill_text + "".join(reference_texts.values()) + extractor_text
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
        "merge, rebase/am, cherry-pick, revert, bisect, or sequencer operation in progress",
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
        "git status --long --branch",
        "never turn its pending commit into a release commit",
        "multi-parent commit without its own",
        '`kind: "merge"`',
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
        "create `release: <exact-tag>`",
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
    planner_contract = (
        "schema_version",
        "parse_semver",
        "compare_semver",
        "GIT_OPERATION_MARKERS",
        "git_path",
        "active_git_operations",
        "operation-state",
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
        "test_clean_attached_merge_still_requires_attention",
        "test_stale_rebase_head_without_active_rebase_is_ignored",
        "test_active_rebase_directory_requires_attention",
        "test_nonconventional_merge_does_not_mask_child_inference",
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


def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `semver-release` contract."""
    validate_semver_release_contract(readme_text=readme_text)
