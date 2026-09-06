#!/usr/bin/env python3
"""Distribution/attribution tests; do not mistake phrase matching for model behavior."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog_core import errors  # noqa: E402
from contracts.tdd import NOTICE_MARKERS, REFERENCE_FILES, validate_tdd_contract  # noqa: E402


class TddContractTests(unittest.TestCase):
    def setUp(self) -> None:
        errors.clear()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(errors.clear)
        self.skill = Path(temporary.name) / "tdd"
        shutil.copytree(ROOT / "skills" / "tdd", self.skill)

    def test_current_payload_satisfies_contract(self) -> None:
        validate_tdd_contract(self.skill)
        self.assertEqual([], errors)

    def test_missing_distribution_files_are_rejected(self) -> None:
        for relative in ("SKILL.md", "NOTICE.md", *REFERENCE_FILES):
            with self.subTest(relative=relative):
                path = self.skill / relative
                original = path.read_bytes()
                path.unlink()
                errors.clear()
                validate_tdd_contract(self.skill)
                self.assertTrue(any("missing required skill payload" in item for item in errors))
                path.write_bytes(original)

    def test_upstream_attribution_is_preserved(self) -> None:
        path = self.skill / "NOTICE.md"
        original = path.read_text(encoding="utf-8")
        for marker in NOTICE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, " ".join(original.split()))
                # Normalize wrapping only for this mutation, not the product notice.
                path.write_text(" ".join(original.split()).replace(marker, "REMOVED"), encoding="utf-8")
                errors.clear()
                validate_tdd_contract(self.skill)
                self.assertTrue(any("upstream provenance and MIT notice" in item for item in errors))

    def test_equivalent_prose_is_not_an_executable_failure(self) -> None:
        path = self.skill / "SKILL.md"
        text = path.read_text(encoding="utf-8").replace(
            "REFACTOR only while green.", "Refactor only after the relevant checks pass."
        )
        path.write_text(text, encoding="utf-8")
        validate_tdd_contract(self.skill, readme_text="A reworded catalog summary.")
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
