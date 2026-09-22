"""Contract guards for the `tooling-conventions` catalog skill.

Loaded and dispatched by `contracts.run_all()`; edit this file alone when the
`tooling-conventions` skill contract changes.
"""

from __future__ import annotations

import shlex

from catalog_core import README, REPO, SKILLS_DIR, dirty_load, errors, readme_skill_rows

SKILL = "tooling-conventions"


def _literal_false(value: object) -> bool:
    """Report a condition that statically disables a job or step.

    A condition is caller-owned policy, so only a literal `false` is read; an
    expression such as `!cancelled()` stays enabled.
    """
    if value is False:
        return True
    if isinstance(value, str):
        condition = value.strip()
        if condition.startswith("${{") and condition.endswith("}}"):
            condition = condition[3:-2].strip()
        return condition.lower() == "false"
    return False


def validate_inventory_ci(workflow_text: str) -> None:
    """Require the dedicated suite invocation, not its name, comment, or example."""
    try:
        if dirty_load is None:
            raise ValueError("StrictYAML is required for workflow validation")
        workflow = dirty_load(workflow_text, allow_flow_style=True).data
    except Exception as exc:
        # StrictYAML validation and underlying scanner/parser errors have
        # different base classes. Only catch broadly around the YAML parser.
        errors.append("tooling-conventions: invalid inventory CI workflow: " + str(exc)[:200])
        return
    try:
        for job in workflow.get("jobs", {}).values():
            if _literal_false(job.get("if")):
                continue
            for step in job.get("steps", []):
                if _literal_false(step.get("if")):
                    continue
                run = step.get("run")
                if not isinstance(run, str):
                    continue
                # Parse a dedicated step, not shell fragments or heredoc contents.
                try:
                    argv = shlex.split(run, comments=True)
                except ValueError:
                    continue
                if argv == ["bash", "scripts/tests/test-tooling-inventory.sh"]:
                    return
    except (AttributeError, TypeError):
        pass
    errors.append(
        "tooling-conventions: CI must run 'bash scripts/tests/test-tooling-inventory.sh' "
        "as its own enabled step"
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
    # CI executes the inventory behavior suite, including literal pathspecs,
    # interpreter fallback, neutral scans and bytecode-free syntax checks.
    # Fixture captions and equivalent shell/Python spellings are not interfaces.
    workflow = REPO / ".github" / "workflows" / "validate.yml"
    validate_inventory_ci(workflow.read_text(encoding="utf-8") if workflow.is_file() else "")

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
