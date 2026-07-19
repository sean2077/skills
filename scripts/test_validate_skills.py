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
        "**Signals**: signal",
        "**Ask**: question",
        "**Fits when**: fit",
        "**Fails when**: failure",
        "**Axis role**: role",
        "**Micro-example**: example",
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
                "and wait for the user before mutation. Otherwise enable numbering by default."
            ),
            "references/classification-methods.md": cards,
            "references/numbering-patterns.md": (
                "Enable numbering by default only when no coherent established convention applies. "
                "Keep it off when a documentation generator owns ordering or navigation. Use `10-`, "
                "`20-`, and `00-` as sibling-local position, not category meaning. Add nested numbers "
                "only for a genuine reading or execution order."
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
            validator.validate_project_docs_organizer_contract(skill_dir)
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

    def test_global_number_range_semantics_are_rejected(self) -> None:
        numbering = (
            self.valid_files()["references/numbering-patterns.md"]
            + " The developer area is `2x`."
        )
        errors = self.validate(overrides={"references/numbering-patterns.md": numbering})
        self.assertTrue(any("retired zone-template semantics" in error for error in errors))

    def test_forced_numbering_without_opt_outs_is_rejected(self) -> None:
        numbering = self.valid_files()["references/numbering-patterns.md"].replace(
            "coherent established convention", "project exception"
        ).replace(
            "documentation generator owns ordering or navigation", "the project is large"
        )
        errors = self.validate(overrides={"references/numbering-patterns.md": numbering})
        self.assertTrue(any("default and opt-out numbering contract" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
