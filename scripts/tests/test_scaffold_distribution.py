#!/usr/bin/env python3
"""Retained distribution and attribution checks; not model-performance claims."""
from __future__ import annotations
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog_core import errors
from contracts.agent_scaffold import (REQUIRED_PATHS, NOTICE_MARKERS, MIT_LICENSE_TEXT,
                                      validate_agent_scaffold_contract)
from validate_skills import validate_category_references


class ScaffoldDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(errors.clear)
        errors.clear()
        self.skill = Path(self.temp.name) / "agent-scaffold"
        shutil.copytree(ROOT / "skills/agent-scaffold", self.skill)

    def test_independent_install_has_contained_references(self):
        validate_agent_scaffold_contract(self.skill)
        validate_category_references(self.skill, (self.skill / "SKILL.md").read_text())
        self.assertEqual([], errors)
        self.assertEqual([self.skill], list(Path(self.temp.name).iterdir()))

    def test_required_distribution_files_are_checked(self):
        for relative in REQUIRED_PATHS:
            with self.subTest(path=relative):
                path = self.skill / relative
                data = path.read_bytes()
                path.unlink()
                errors.clear()
                validate_agent_scaffold_contract(self.skill)
                self.assertTrue(errors)
                path.write_bytes(data)

    def test_both_adaptations_retain_attribution(self):
        path = self.skill / "NOTICE.md"
        text = " ".join(path.read_text().split())
        for marker in NOTICE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
                path.write_text(text.replace(marker, "removed"))
                errors.clear()
                validate_agent_scaffold_contract(self.skill)
                self.assertTrue(errors)

    def test_partial_license_cannot_pass_by_markers_only(self):
        path = self.skill / "NOTICE.md"
        text = " ".join(path.read_text().split())
        self.assertIn(MIT_LICENSE_TEXT, text)
        fragment = "including without limitation the rights to use, copy, modify, merge, publish,"
        self.assertIn(fragment, text)
        path.write_text(text.replace(fragment, ""))
        validate_agent_scaffold_contract(self.skill)
        self.assertTrue(any("complete MIT" in error for error in errors))

    def test_equivalent_skill_prose_does_not_fail_distribution(self):
        (self.skill / "SKILL.md").write_text("# Alternate task guidance\nEquivalent meaning.\n")
        validate_agent_scaffold_contract(self.skill)
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
