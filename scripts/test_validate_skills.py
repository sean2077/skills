#!/usr/bin/env python
"""Focused fixtures for category-based on-demand reference validation."""

from __future__ import annotations

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

    def test_valid_multiple_categories(self) -> None:
        errors = self.validate(
            "[Alpha](references/alpha-model.md) [Beta](references/beta-workflow.md#details)",
            {
                "references/alpha-model.md": "# Alpha\n",
                "references/beta-workflow.md": "# Beta\n",
            },
        )
        self.assertEqual(errors, [])

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


if __name__ == "__main__":
    unittest.main()
