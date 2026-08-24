#!/usr/bin/env python
"""Focused regressions for the stack-neutral TDD skill contract."""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from catalog_core import errors  # noqa: E402
from contracts.tdd import (  # noqa: E402
    CROSS_STACK_MARKERS,
    REFERENCE_FILES,
    validate_tdd_contract,
    validate_tdd_semantics,
)

TDD_DIR = REPO_ROOT / "skills" / "tdd"
README_TEXT = (REPO_ROOT / "README.md").read_text(encoding="utf-8")


@contextmanager
def copied_skill() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "tdd"
        shutil.copytree(TDD_DIR, target)
        yield target


class TddContractTests(unittest.TestCase):
    def setUp(self) -> None:
        errors.clear()

    def tearDown(self) -> None:
        errors.clear()

    def validate(self, skill_dir: Path = TDD_DIR, readme_text: str = README_TEXT) -> list[str]:
        errors.clear()
        validate_tdd_contract(skill_dir, readme_text=readme_text)
        return list(errors)

    def test_current_payload_satisfies_contract(self) -> None:
        self.assertEqual([], self.validate())

    def test_every_required_payload_file_is_guarded(self) -> None:
        required = ("SKILL.md", "NOTICE.md", *REFERENCE_FILES)
        for relative in required:
            with self.subTest(relative=relative), copied_skill() as skill_dir:
                (skill_dir / relative).unlink()
                found = self.validate(skill_dir)
                self.assertTrue(
                    any("missing required skill payload files" in item for item in found)
                )

    def test_frontmatter_keeps_explicit_trigger_and_non_trigger_boundaries(self) -> None:
        with copied_skill() as skill_dir:
            path = skill_dir / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            mutated, replacements = re.subn(
                r"(?m)^description:.*$",
                'description: "Use for all implementation work."',
                text,
                count=1,
            )
            self.assertEqual(1, replacements)
            path.write_text(
                mutated,
                encoding="utf-8",
            )
            found = self.validate(skill_dir)
        self.assertTrue(any("explicit trigger and non-trigger boundary" in item for item in found))

    def test_resident_cycle_fixture_cannot_silently_disappear(self) -> None:
        with copied_skill() as skill_dir:
            path = skill_dir / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace("REFACTOR only while green.", "Refactor when convenient."),
                encoding="utf-8",
            )
            found = self.validate(skill_dir)
        self.assertTrue(any("resident trigger, ownership, cycle" in item for item in found))

    def test_resident_and_public_contract_reject_stack_defaults(self) -> None:
        defaults = (
            "Run npm test for every cycle.",
            "Run go test ./... for every cycle.",
            "Run cargo test for every cycle.",
            "Run ./gradlew test for every cycle.",
            "Run dotnet test for every cycle.",
            "Run bundle exec rspec for every cycle.",
            "Run mix test for every cycle.",
            "Run flutter test for every cycle.",
            "Run xcodebuild for every cycle.",
        )
        for default in defaults:
            with self.subTest(default=default), copied_skill() as skill_dir:
                skill_path = skill_dir / "SKILL.md"
                skill_path.write_text(
                    skill_path.read_text(encoding="utf-8") + f"\n{default}\n",
                    encoding="utf-8",
                )
                found = self.validate(skill_dir)
            self.assertTrue(
                any("resident/public contract must stay stack-neutral" in item for item in found)
            )

        found = self.validate(
            readme_text=README_TEXT.replace(
                "| [tdd](skills/tdd/)",
                "| [tdd](skills/tdd/) Node.js",
            )
        )
        self.assertTrue(
            any("resident/public contract must stay stack-neutral" in item for item in found)
        )

    def test_cross_stack_coverage_cannot_collapse_to_one_ecosystem(self) -> None:
        marker = CROSS_STACK_MARKERS[-1]
        with copied_skill() as skill_dir:
            path = skill_dir / "references" / "cross-stack-execution.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(marker, "target systems"),
                encoding="utf-8",
            )
            found = self.validate(skill_dir)
        self.assertTrue(any("cross-ecosystem discovery coverage" in item for item in found))
        self.assertTrue(any(marker in item for item in found))

    def test_upstream_rigid_rules_are_rejected_individually(self) -> None:
        dogmas = (
            "Confirm the seams with the user before continuing.",
            "No test is written at an unconfirmed seam.",
            "Tests live at seams, never against internals.",
            "One logical assertion per test.",
            "Mock at system boundaries only.",
            "Refactoring is not part of the loop.",
            "Always use an integration test.",
        )
        for dogma in dogmas:
            with self.subTest(dogma=dogma):
                errors.clear()
                validate_tdd_semantics(dogma, source="fixture")
                self.assertTrue(errors, dogma)

    def test_later_positive_dogma_is_not_hidden_by_an_earlier_rejection(self) -> None:
        text = (
            "Do not require one logical assertion per test. "
            "One logical assertion per test."
        )
        errors.clear()
        validate_tdd_semantics(text, source="fixture")
        self.assertTrue(errors)

    def test_explicit_rejection_of_a_dogma_does_not_false_positive(self) -> None:
        text = (
            "Do not require one logical assertion per test. "
            "Reject the claim that refactoring is not part of the loop. "
            "Never mandate that tests live at seams, never against internals."
        )
        errors.clear()
        validate_tdd_semantics(text, source="fixture")
        self.assertEqual([], errors)

    def test_notice_keeps_upstream_license_identity(self) -> None:
        with copied_skill() as skill_dir:
            path = skill_dir / "NOTICE.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Copyright (c) 2026 Matt Pocock", "Copyright removed"
                ),
                encoding="utf-8",
            )
            found = self.validate(skill_dir)
        self.assertTrue(any("upstream provenance and MIT notice" in item for item in found))

    def test_external_sibling_skill_coupling_is_rejected(self) -> None:
        couplings = (
            "Call the Skill tool before continuing.",
            "Invoke `codebase-design` first.",
            "Hand refactoring to the `code-review` skill.",
            "Always read `CONTEXT.md` before testing.",
        )
        for coupling in couplings:
            with self.subTest(coupling=coupling), copied_skill() as skill_dir:
                path = skill_dir / "SKILL.md"
                path.write_text(
                    path.read_text(encoding="utf-8") + f"\n{coupling}\n",
                    encoding="utf-8",
                )
                found = self.validate(skill_dir)
            self.assertTrue(any("external sibling-skill" in item for item in found))


if __name__ == "__main__":
    unittest.main()
