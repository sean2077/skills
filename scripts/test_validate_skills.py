#!/usr/bin/env python
"""Focused fixtures for resident-context and on-demand reference validation."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import validate_skills as validator


class CategoryReferenceTests(unittest.TestCase):
    def validate(self, skill_text: str, references: dict[str, str], *, legacy_root: bool = False) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            skill_dir = Path(temporary) / "fixture-skill"
            skill_dir.mkdir()
            for relative, content in references.items():
                path = skill_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            if legacy_root:
                (skill_dir / "reference.md").write_text("legacy\n", encoding="utf-8")
            validator.errors.clear()
            validator.validate_category_references(skill_dir, skill_text)
            return list(validator.errors)

    def validate_resident(self, skill_text: str, frontmatter: dict[str, object]) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            skill_dir = Path(temporary) / "fixture-skill"
            skill_dir.mkdir()
            validator.errors.clear()
            validator.validate_resident_contract(skill_dir, skill_text, frontmatter)
            return list(validator.errors)

    def test_valid_multiple_categories(self) -> None:
        errors = self.validate(
            "## On-demand references\n[Alpha](references/alpha-model.md) [Beta](references/beta-workflow.md#details)",
            {
                "references/alpha-model.md": "# Alpha\n\nRead this when alpha applies.\n",
                "references/beta-workflow.md": "# Beta\n\nRead this only when beta applies.\n",
            },
        )
        self.assertEqual(errors, [])

    def test_equivalent_reference_load_boundaries_are_accepted(self) -> None:
        introductions = (
            "Consult this when selecting a release base.",
            "Open this only for a breaking migration.",
            "Use this after the semantic boundary is stable.",
            "Load this when another tool needs the schema.",
        )
        for introduction in introductions:
            with self.subTest(introduction=introduction):
                errors = self.validate(
                    "## On-demand references\n[Alpha](references/alpha.md)",
                    {"references/alpha.md": f"# Alpha\n\n{introduction}\n"},
                )
                self.assertEqual(errors, [])

    def test_reference_router_heading_is_required(self) -> None:
        errors = self.validate(
            "[Alpha](references/alpha.md)",
            {"references/alpha.md": "# Alpha\n\nRead this when alpha applies.\n"},
        )
        self.assertTrue(any("On-demand references" in error for error in errors))

    def test_reference_load_boundary_is_required(self) -> None:
        errors = self.validate(
            "## On-demand references\n[Alpha](references/alpha.md)",
            {"references/alpha.md": "# Alpha\n\nAlways load this document.\n"},
        )
        self.assertTrue(any("conditional load boundary" in error for error in errors))

    def test_missing_link_target(self) -> None:
        errors = self.validate("[Missing](references/missing.md)", {})
        self.assertTrue(any("does not exist" in error for error in errors))

    def test_orphan_category(self) -> None:
        errors = self.validate("# Router\n", {"references/orphan.md": "# Orphan\n"})
        self.assertTrue(any("orphan reference" in error for error in errors))

    def test_forbidden_generic_name(self) -> None:
        errors = self.validate(
            "[Misc](references/misc.md)",
            {"references/misc.md": "# Misc\n"},
        )
        self.assertTrue(any("catch-all" in error for error in errors))

    def test_root_legacy_reference(self) -> None:
        errors = self.validate("# Router\n", {}, legacy_root=True)
        self.assertTrue(any("root-level reference.md" in error for error in errors))

    def test_dangling_legacy_router_link(self) -> None:
        errors = self.validate("[Legacy](reference.md)", {})
        self.assertTrue(any("must route references directly" in error for error in errors))

    def test_non_category_filename_is_rejected(self) -> None:
        errors = self.validate(
            "[Upper](references/Upper.MD)",
            {"references/Upper.MD": "# Upper\n"},
        )
        self.assertTrue(any("lowercase kebab-case" in error for error in errors))

    def test_resident_frontmatter_rejects_extra_fields(self) -> None:
        errors = self.validate_resident(
            "---\nname: fixture-skill\ndescription: fixture\ncompatibility: git\n---\n",
            {"name": "fixture-skill", "description": "fixture", "compatibility": "git"},
        )
        self.assertTrue(any("only name + description" in error for error in errors))

    def test_trigger_section_is_not_resident(self) -> None:
        errors = self.validate_resident(
            "---\nname: fixture-skill\ndescription: fixture\n---\n\n## When To Use\n",
            {"name": "fixture-skill", "description": "fixture"},
        )
        self.assertTrue(any("trigger boundaries belong in frontmatter" in error for error in errors))

    def test_resident_line_budget_routes_detail_to_references(self) -> None:
        skill_text = "\n".join(["---", "name: fixture-skill", "description: fixture", "---"] + ["detail"] * 101)
        errors = self.validate_resident(
            skill_text,
            {"name": "fixture-skill", "description": "fixture"},
        )
        self.assertTrue(any("resident SKILL.md" in error and "lines" in error for error in errors))

    def test_cli_rejects_unknown_options_even_when_help_is_present(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = validator.cli(["--help", "--write-anyway"])
        self.assertEqual(result, 2)
        self.assertIn("--write-anyway", stderr.getvalue())

    def test_cli_accepts_one_help_option(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = validator.cli(["--help"])
        self.assertEqual(result, 0)
        self.assertIn("Validate the skills catalog", stdout.getvalue())


class ConventionalCommitContractTests(unittest.TestCase):
    def valid_files(self) -> dict[str, str]:
        return {
            "SKILL.md": (
                "## Workflow\n"
                "git rev-parse --show-toplevel\n"
                "git -C <repo-root> symbolic-ref --quiet --short HEAD\n"
                "Exit status 1 means detached HEAD; any other nonzero status is a Git preflight "
                "error. Run git -C <repo-root> status --long --branch and stop for an "
                "in-progress merge. Then stage the exact intended changes.\n"
            ),
            "references/staging-safety.md": (
                "git -C <repo-root> status --short\n"
                "git -C <repo-root> add -A -- .\n"
                "Exit status 1 means HEAD is detached. Any other nonzero status is a Git error.\n"
                "git diff --cached --name-only\n"
                "git diff --cached --check\n"
                "Stop when unrelated paths are already staged.\n"
                "A named path does not authorize every hunk. Inspect "
                "git -C <repo-root> diff --cached -- <paths> and "
                "git -C <repo-root> diff -- <paths>. If a path mixes intended and unrelated "
                "hunks, select only the authorized patch without modifying the working tree or "
                "unrelated pre-existing index state. Inspect the actual cached patch.\n"
                "An attached HEAD proves only that a branch is named. Run "
                "git -C <repo-root> status --long --branch and stop for an in-progress merge, "
                "rebase, cherry-pick, revert, bisect, or unresolved conflict. Ordinary commit "
                "mode never continues or completes those operations.\n"
            ),
        }

    def validate(self, *, staging_text: str | None = None) -> list[str]:
        files = self.valid_files()
        if staging_text is not None:
            files["references/staging-safety.md"] = staging_text
        with tempfile.TemporaryDirectory() as temporary:
            skill_dir = Path(temporary) / "conventional-commit"
            for relative, content in files.items():
                path = skill_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            validator.errors.clear()
            validator.validate_conventional_commit_contract(skill_dir)
            return list(validator.errors)

    def test_valid_path_and_hunk_scope_contract(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_mixed_hunk_boundary_is_required(self) -> None:
        staging = self.valid_files()["references/staging-safety.md"].replace(
            "If a path mixes intended and unrelated hunks, ",
            "If every change in a path is intended, ",
        )
        errors = self.validate(staging_text=staging)
        self.assertTrue(
            any("path/hunk staging boundary lost fixtures" in error for error in errors)
        )

    def test_in_progress_operation_boundary_is_required(self) -> None:
        staging = self.valid_files()["references/staging-safety.md"].replace(
            "Ordinary commit mode never continues or completes those operations.",
            "Continue the current operation when the index is clean.",
        )
        errors = self.validate(staging_text=staging)
        self.assertTrue(
            any("path/hunk staging boundary lost fixtures" in error for error in errors)
        )


class ProjectDocsOrganizerContractTests(unittest.TestCase):
    METHOD_HEADINGS = (
        "Reader role",
        "Task or journey",
        "Domain capability, ownership, and language",
        "Product, subsystem, or interface surface",
        "Content purpose or information type",
        "Lifecycle or authority",
    )
    METHOD_FIELDS = (
        "- **Signals**: signal",
        "- **Ask**: question",
        "- **Fits when**: fit",
        "- **Fails when**: failure",
        "- **Axis role**: role",
        "- **Micro-example**: example",
    )

    def valid_files(self) -> dict[str, str]:
        cards = "\n".join(
            f"## {heading}\n" + "\n".join(self.METHOD_FIELDS) for heading in self.METHOD_HEADINGS
        )
        return {
            "SKILL.md": (
                "The target project owns its information architecture. Prefer the smallest structure and "
                "preserve a coherent established convention. Select one primary axis per tree level. "
                "Write a documentation IA decision record. Present two or three candidates and wait for "
                "the user before mutation. No empty category is allowed. Resolve the target project root."
            ),
            "references/information-architecture.md": (
                "Reader-route separation. Vocabulary and ownership cohesion. Lifecycle consistency. "
                "Stability under change. Duplication pressure. Choose one primary axis and retain "
                "secondary lenses. Run a representative placement test. Present two or three candidates "
                "and wait for the user before mutation. Treat the absence of a convention as permission "
                "to choose, not evidence for numbering. Require stable sibling order and weigh "
                "path/link churn."
            ),
            "references/classification-methods.md": cards,
            "references/numbering-patterns.md": (
                "Keep numbering disabled by default. Enable it only for stable sibling order that improves "
                "an observed reader route and outweighs path/link churn. A coherent established convention "
                "or documentation generator owns ordering or navigation. Use `10-`, `20-`, and `00-` as "
                "sibling-local position, not category meaning. Add nested numbers only for a genuine reading "
                "or execution order."
            ),
            "references/migration-and-links.md": (
                "Build the migration map. Before deleting, gather evidence. Run "
                "rg -n -F 'old/path.md' <project-root>. Coordinate external wikis or issue trackers. "
                "Finish with git diff --check."
            ),
        }

    def validate(
        self,
        *,
        overrides: dict[str, str] | None = None,
        removed: set[str] | None = None,
        extras: dict[str, str] | None = None,
        readme_text: str | None = None,
    ) -> list[str]:
        files = self.valid_files()
        files.update(overrides or {})
        for relative in removed or set():
            files.pop(relative, None)
        files.update(extras or {})
        with tempfile.TemporaryDirectory() as temporary:
            skill_dir = Path(temporary) / "project-docs-organizer"
            for relative, content in files.items():
                path = skill_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            validator.errors.clear()
            validator.validate_project_docs_organizer_contract(
                skill_dir,
                readme_text=(
                    readme_text
                    if readme_text is not None
                    else (
                        "| [project-docs-organizer](skills/project-docs-organizer/) | "
                        "Evidence-gated local numbering. | Documentation |"
                    )
                ),
            )
            return list(validator.errors)

    def test_valid_evidence_led_contract(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_missing_required_reference_is_rejected(self) -> None:
        errors = self.validate(removed={"references/classification-methods.md"})
        self.assertTrue(any("missing required files" in error for error in errors))

    def test_legacy_zone_catalog_is_rejected(self) -> None:
        errors = self.validate(
            extras={"references/zone-catalog.md": "# Optional Documentation Zone Catalog\n"}
        )
        self.assertTrue(any("retired references/zone-catalog.md" in error for error in errors))

    def test_incomplete_method_card_set_is_rejected(self) -> None:
        methods = self.valid_files()["references/classification-methods.md"].replace(
            "## Lifecycle or authority", "## Records"
        )
        errors = self.validate(overrides={"references/classification-methods.md": methods})
        self.assertTrue(any("method-card set is incomplete" in error for error in errors))

    def test_method_fields_are_validated_inside_each_card(self) -> None:
        methods = self.valid_files()["references/classification-methods.md"]
        methods = methods.replace("- **Signals**: signal\n", "", 1).replace(
            "## Task or journey\n",
            "## Task or journey\n- **Signals**: duplicate\n",
            1,
        )
        errors = self.validate(overrides={"references/classification-methods.md": methods})
        self.assertTrue(
            any("Reader role method card" in error and "Signals (0)" in error for error in errors)
        )
        self.assertTrue(
            any("Task or journey method card" in error and "Signals (2)" in error for error in errors)
        )

    def test_empty_method_field_is_rejected(self) -> None:
        methods = self.valid_files()["references/classification-methods.md"].replace(
            "- **Ask**: question",
            "- **Ask**:",
            1,
        )
        errors = self.validate(overrides={"references/classification-methods.md": methods})
        self.assertTrue(any("Ask (empty)" in error for error in errors))

    def test_method_card_directory_examples_reject_every_fence_form(self) -> None:
        methods = self.valid_files()["references/classification-methods.md"]
        for fence in ("```", "```markdown", "~~~text"):
            with self.subTest(fence=fence):
                invalid = methods.replace(
                    "- **Micro-example**: example",
                    f"- **Micro-example**: example\n{fence}\ndocs/\n  users/\n{fence[:3]}",
                    1,
                )
                errors = self.validate(
                    overrides={"references/classification-methods.md": invalid}
                )
                self.assertTrue(any("micro-example must be prose" in error for error in errors))

    def test_method_card_unfenced_directory_tree_is_rejected(self) -> None:
        methods = self.valid_files()["references/classification-methods.md"].replace(
            "- **Micro-example**: example",
            "- **Micro-example**: example\ndocs/\n  users/\n  maintainers/",
            1,
        )
        errors = self.validate(overrides={"references/classification-methods.md": methods})
        self.assertTrue(any("micro-example must be prose" in error for error in errors))

    def test_global_number_range_semantics_are_rejected(self) -> None:
        numbering = (
            self.valid_files()["references/numbering-patterns.md"]
            + " The developer area is `2x`."
        )
        errors = self.validate(overrides={"references/numbering-patterns.md": numbering})
        self.assertTrue(any("retired zone-template semantics" in error for error in errors))

    def test_reworded_fixed_numeric_ranges_are_rejected(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"]
        for rule in (
            "Reserve 20-29 for development.",
            "Iteration uses 30–39.",
            "Maintenance occupies 4x.",
            "Reference occupies 60 to 69.",
            "The complete catalog spans 00-94.",
        ):
            with self.subTest(rule=rule):
                errors = self.validate(
                    overrides={"references/numbering-patterns.md": numbering + " " + rule}
                )
                self.assertTrue(any("fixed numeric range notation" in error for error in errors))

    def test_numeric_quantity_outside_numbering_rules_is_not_a_fixed_range(self) -> None:
        skill = self.valid_files()["SKILL.md"] + " Present 2-3 candidates for a tied decision."
        errors = self.validate(overrides={"SKILL.md": skill})
        self.assertFalse(any("fixed numeric range notation" in error for error in errors))

    def test_forced_numbering_without_opt_outs_is_rejected(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"].replace(
            "coherent established convention", "project exception"
        ).replace(
            "documentation generator owns ordering or navigation", "the project is large"
        )
        errors = self.validate(overrides={"references/numbering-patterns.md": numbering})
        self.assertTrue(any("evidence and opt-out numbering contract" in error for error in errors))

    def test_default_on_numbering_is_rejected_across_contract(self) -> None:
        for relative, rule in (
            ("SKILL.md", "Enable numbering by default when no convention exists."),
            (
                "references/information-architecture.md",
                "Otherwise use local numbering by default.",
            ),
            (
                "references/numbering-patterns.md",
                "The skill provides optional default-on local numbering.",
            ),
        ):
            with self.subTest(relative=relative):
                invalid = self.valid_files()[relative] + " " + rule
                errors = self.validate(overrides={relative: invalid})
                self.assertTrue(
                    any("default-on numbering contradicts the evidence gate" in error for error in errors)
                )

    def test_stale_readme_summary_is_rejected_by_domain_contract(self) -> None:
        errors = self.validate(
            readme_text=(
                "| [project-docs-organizer](skills/project-docs-organizer/) | Use optional "
                "default-on local numbering when no coherent convention governs. | Documentation |"
            )
        )
        self.assertTrue(
            any("default-on numbering contradicts the evidence gate" in error for error in errors)
        )

    def test_explicit_default_on_rejections_are_not_false_positives(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"]
        for rule in (
            "Do not enable numbering by default.",
            "Never use local numbering by default.",
        ):
            with self.subTest(rule=rule):
                errors = self.validate(
                    overrides={"references/numbering-patterns.md": numbering + " " + rule}
                )
                self.assertFalse(
                    any("default-on numbering contradicts the evidence gate" in error for error in errors)
                )

    def test_contradictory_forced_numbering_rules_are_rejected(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"]
        for rule in (
            "Always number every project.",
            "Numeric prefixes are mandatory for all documentation trees.",
            "Every repository must use numbering.",
            "Numbering cannot be disabled.",
            "All documentation trees are numbered.",
            "Numbering applies to every project.",
        ):
            with self.subTest(rule=rule):
                errors = self.validate(
                    overrides={"references/numbering-patterns.md": numbering + " " + rule}
                )
                self.assertTrue(
                    any("unconditional numbering mandate" in error for error in errors)
                )

    def test_explicit_numbering_opt_out_phrasings_are_not_false_positives(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"]
        for rule in (
            "Numbering is not mandatory.",
            "Do not always number every project.",
            "Not every repository must use numbering.",
            "Do not enable numbering for every project.",
            "Do not number every project.",
            "Not all documentation trees are numbered.",
            "Numbering does not apply to every project.",
        ):
            with self.subTest(rule=rule):
                errors = self.validate(
                    overrides={"references/numbering-patterns.md": numbering + " " + rule}
                )
                self.assertFalse(
                    any("unconditional numbering mandate" in error for error in errors)
                )


class PublicSummaryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        validator.errors.clear()

    def test_tooling_readme_summary_cannot_reactivate_retired_checker(self) -> None:
        validator.validate_tooling_conventions_contract(
            readme_text=(
                "| [tooling-conventions](skills/tooling-conventions/) | Run "
                "scripts/manifest-check.sh for every tool surface. | Shell |"
            )
        )
        self.assertTrue(
            any(
                "retired flat-surface contract remains active" in error
                for error in validator.errors
            )
        )


if __name__ == "__main__":
    unittest.main()
