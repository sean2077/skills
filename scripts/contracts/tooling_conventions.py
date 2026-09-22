"""Contract guards for the `tooling-conventions` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`tooling-conventions` skill contract changes.
"""

from __future__ import annotations

from catalog_core import README, REPO, SKILLS_DIR, errors, readme_skill_rows

SKILL = "tooling-conventions"


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
        'compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], "exec")'
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
        "python3 fallback did not complete the inventory check",
        "py -3 fallback did not complete the inventory check",
        "expected missing Python preflight to exit 2",
        "expected a glob-metacharacter executable Python CLI to exit 1",
        "glob-metacharacter file name borrowed another tracked file's mode",
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
    checker_contract = (
        'SKIP_RE="${INVENTORY_CHECK_SKIP:-a^}"',
        'python_compatible "$PYTHON_BIN"',
        "elif python_compatible python3; then",
        "elif python_compatible py -3; then",
        'PYTHONUTF8=1 "${PYTHON_CMD[@]}" -c',
        'echo "python 3.8+ interpreter unavailable for syntax check: $path',
        ':(literal)$pathspec',
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

    # Placement and decision-artifact policy is semantic, not a fixed sentence.
    # Keep the executable inventory and migration boundaries below.
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



def validate(*, readme_text: str | None = None) -> None:
    """Entry point for the `tooling-conventions` contract."""
    validate_tooling_conventions_contract(readme_text=readme_text)
