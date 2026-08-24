#!/usr/bin/env python3
"""Focused regression tests for scripts/catalog_health.py."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import catalog_health


class CatalogHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repo = Path(self.temporary_directory.name)
        (self.repo / "skills").mkdir()

    def write_skill(self, name: str, description: str) -> Path:
        skill_dir = self.repo / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        escaped = description.replace("'", "''")
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: '{escaped}'\n---\n\n# {name}\n",
            encoding="utf-8",
        )
        return skill_dir

    def errors(self):
        return catalog_health.validate_catalog(self.repo)[0]

    def test_clean_catalog_passes(self) -> None:
        self.write_skill("analyze", "Use for read-only repository explanation.")
        self.write_skill("code-review", "Use to review a concrete patch for defects.")
        errors, total_chars, longest = catalog_health.validate_catalog(self.repo)
        self.assertEqual(errors, [])
        self.assertEqual(total_chars, 84)
        self.assertEqual(longest, 43)

    def test_crlf_frontmatter_is_supported(self) -> None:
        skill_dir = self.repo / "skills" / "crlf"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_bytes(
            b"---\r\nname: crlf\r\n"
            b"description: Use when checking CRLF portability.\r\n"
            b"---\r\n\r\n# crlf\r\n"
        )
        self.assertEqual(self.errors(), [])

    def test_description_over_budget_fails(self) -> None:
        source = self.write_skill(
            "oversized", "x" * (catalog_health.MAX_DESCRIPTION_CHARS + 1)
        )
        self.assertIn(
            f"{source / 'SKILL.md'}: description is 321 characters; maximum is 320",
            self.errors(),
        )

    def test_duplicate_description_fails_after_normalization(self) -> None:
        self.write_skill("first", "Use when one route should remain distinct.")
        second = self.write_skill("second", "  use   WHEN one route should remain distinct.  ")
        self.assertTrue(
            any(
                str(second / "SKILL.md") in error and "duplicates" in error
                for error in self.errors()
            )
        )

    def test_multiline_description_is_rejected(self) -> None:
        skill_dir = self.repo / "skills" / "folded"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: folded\ndescription: >\n"
            "  Use when routing metadata wraps.\n---\n\n# folded\n",
            encoding="utf-8",
        )
        self.assertTrue(any("one physical line" in error for error in self.errors()))

    def test_non_directory_catalog_entry_is_rejected(self) -> None:
        stray = self.repo / "skills" / "README.md"
        stray.write_text("not a skill\n", encoding="utf-8")
        self.assertTrue(any(str(stray) in error for error in self.errors()))

    def test_symlink_skills_root_is_rejected(self) -> None:
        real = self.repo / "published"
        real.mkdir()
        skills = self.repo / "skills"
        skills.rmdir()
        try:
            skills.symlink_to(real.name, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlink creation is unavailable: {exc}")
        self.assertTrue(any(str(skills) in error for error in self.errors()))

    def test_symlink_skill_root_is_rejected(self) -> None:
        real = self.write_skill("real", "Use when checking a real skill fixture.")
        alias = self.repo / "skills" / "alias"
        try:
            alias.symlink_to(real.name, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlink creation is unavailable: {exc}")
        self.assertTrue(any(str(alias) in error for error in self.errors()))

    def test_symlink_payload_is_rejected(self) -> None:
        skill_dir = self.write_skill("linked", "Use when checking a linked payload fixture.")
        target = skill_dir / "target.txt"
        target.write_text("target\n", encoding="utf-8")
        link = skill_dir / "link.txt"
        try:
            link.symlink_to(target.name)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")
        self.assertTrue(any(str(link) in error for error in self.errors()))

    @unittest.skipIf(os.name == "nt", "FIFO fixtures are POSIX-only")
    def test_special_payload_entry_is_rejected(self) -> None:
        skill_dir = self.write_skill("special", "Use when checking a special payload fixture.")
        fifo = skill_dir / "fixture.fifo"
        os.mkfifo(fifo)
        self.addCleanup(lambda: fifo.unlink(missing_ok=True))
        self.assertTrue(any(str(fifo) in error for error in self.errors()))

    def test_cli_reports_compact_stats(self) -> None:
        self.write_skill("clean", "Use when checking compact CLI output.")
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"SKILLS_REPO": str(self.repo)}):
            with contextlib.redirect_stdout(output):
                status = catalog_health.main()
        self.assertEqual(status, 0)
        self.assertIn("1 skills", output.getvalue())
        self.assertIn("longest", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
