#!/usr/bin/env python3
"""Real selection persistence and preflight, separate from dialogue/model evaluation."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import test_project_conventions as preservation
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("selection_core", ROOT / "skills/agent-scaffold/scripts/harness-core.py")
CORE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CORE)


class GuidanceSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="choice space ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.path = self.root / CORE.GUIDANCE_FILE

    def record(self, text):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_bytes(text.encode())

    def test_absence_is_pending_with_all_defaults_and_no_writes(self):
        before = list(self.root.iterdir())
        report = CORE.guidance_selection(self.root)
        self.assertEqual("pending", report["status"])
        self.assertIsNone(report["domains"])
        self.assertEqual(list(CORE.GUIDANCE_DOMAINS), report["defaults"])
        self.assertEqual(before, list(self.root.iterdir()))

    def test_all_and_none_are_both_recorded_choices(self):
        for arg, expected in (("all", list(CORE.GUIDANCE_DOMAINS)), ("none", [])):
            CORE.save_guidance_selection(self.root, arg)
            result = CORE.guidance_selection(self.root)
            self.assertEqual("recorded", result["status"])
            self.assertEqual(expected, result["domains"])
            self.assertIsNone(result["defaults"])

    def test_explicit_subset_persists_without_rewriting_or_reprompting(self):
        CORE.save_guidance_selection(self.root, "git,docs,testing")
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        for _ in range(3):
            self.assertEqual(["docs", "testing", "git"], CORE.guidance_selection(self.root)["domains"])
            CORE.save_guidance_selection(self.root, "testing,git,docs")
        self.assertEqual(before, (self.path.read_bytes(), self.path.stat().st_mtime_ns))

    def test_preview_does_not_replace_accepted_selection(self):
        CORE.save_guidance_selection(self.root, "docs")
        before = self.path.read_bytes()
        self.assertEqual("proposed", CORE.guidance_selection(self.root, "all")["status"])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(["docs"], CORE.load_guidance_selection(self.root))

    def test_new_upstream_domain_is_not_silently_selected(self):
        CORE.save_guidance_selection(self.root, "all")
        saved = CORE.load_guidance_selection(self.root)
        with mock.patch.object(CORE, "GUIDANCE_DOMAINS", CORE.GUIDANCE_DOMAINS + ("new-domain",)):
            result = CORE.guidance_selection(self.root)
            self.assertEqual("recorded", result["status"])
            self.assertEqual(saved, result["domains"])
            self.assertIsNone(result["defaults"])

    def test_invalid_records_are_not_treated_as_new_installations(self):
        invalid = ('{}', '[]', '{bad', '{"schema_version":true,"domains":[]}',
                   '{"schema_version":2,"domains":[]}', '{"schema_version":1,"domains":"all"}',
                   '{"schema_version":1,"domains":["docs","docs"]}',
                   '{"schema_version":1,"domains":["docs"],"domains":[]}',
                   '{"schema_version":1,"domains":["unknown"]}',
                   '{"schema_version":1,"domains":[false]}',
                   '{"schema_version":1,"domains":[],"extra":null}',
                   '{"schema_version":NaN,"domains":[]}', ' ' * 16385)
        for text in invalid:
            with self.subTest(text=text[:90]):
                self.record(text)
                with self.assertRaises(CORE.CoreError):
                    CORE.guidance_selection(self.root)
                with self.assertRaises(CORE.CoreError):
                    CORE.save_guidance_selection(self.root, "all")
                self.assertEqual(text.encode(), self.path.read_bytes())

    def test_argument_validation_is_exact(self):
        for value in ('', 'all,docs', 'none,git', 'docs,docs', 'doc', 'docs,', ',docs', 'unknown', 'docs,,tools'):
            with self.subTest(value=value), self.assertRaises(CORE.CoreError):
                CORE.parse_domains(value)
        self.assertEqual(["docs", "git"], CORE.parse_domains(" git , docs "))

    def test_selection_write_failure_preserves_previous_record(self):
        CORE.save_guidance_selection(self.root, "docs")
        original = self.path.read_bytes()
        with mock.patch.object(CORE.os, "replace", side_effect=OSError("injected failure")):
            with self.assertRaises(OSError):
                CORE.save_guidance_selection(self.root, "all")
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_file_and_parent_aliases_cannot_redirect_preferences(self):
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "selection.json"
        sentinel.write_text('{"schema_version":1,"domains":["docs"]}')
        self.path.parent.mkdir()
        try:
            self.path.symlink_to(sentinel)
        except OSError as exc:
            self.skipTest("no native symlink capability: " + str(exc))
        with self.assertRaises(CORE.CoreError):
            CORE.save_guidance_selection(self.root, "all")
        self.path.unlink(); self.path.parent.rmdir()
        self.path.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(CORE.CoreError):
            CORE.save_guidance_selection(self.root, "all")
        self.assertEqual('{"schema_version":1,"domains":["docs"]}', sentinel.read_text())
        self.assertEqual([sentinel], list(outside.iterdir()))

    def test_optional_managed_terminology_follows_saved_choice(self):
        source = ROOT / "skills/agent-scaffold/assets/scaffold/AGENTS.harness.md"
        for domains, present in ((None, True), ([], False), (["docs"], False), (["terminology"], True)):
            with self.subTest(domains=domains):
                rendered = CORE.render_agents_template(source, "default", domains)
                self.assertEqual(present, "### Project terminology" in rendered)
                self.assertNotIn(CORE.TERMINOLOGY_START, rendered)
                self.assertIn("### Authority documents", rendered)
                self.assertIn("### Worktree-per-change", rendered)

    def test_actual_install_upgrade_and_preview_preserve_selection(self):
        fixture = preservation.ProjectConventionPreservationTests("runTest")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.seed()
        before = fixture.snapshot()
        planned = fixture.invoke("plan", extra=("--domains", "none"))
        self.assertEqual("proposed", planned["guidance_selection"]["status"])
        self.assertEqual(before, fixture.snapshot())
        fixture.invoke("apply", extra=("--domains", "docs,testing,git"))
        saved = (fixture.root / CORE.GUIDANCE_FILE).read_bytes()
        contract = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("### Project terminology", contract)
        self.assertIn("工程约定", contract)
        self.assertEqual("recorded", fixture.invoke("verify")["guidance_selection"]["status"])
        after = fixture.snapshot()
        fixture.invoke("upgrade")
        self.assertEqual(after, fixture.snapshot())
        self.assertEqual(saved, (fixture.root / CORE.GUIDANCE_FILE).read_bytes())
        fixture.invoke("upgrade", extra=("--domains", "all"))
        self.assertIn("### Project terminology", (fixture.root / "AGENTS.md").read_text())
        self.assertTrue(fixture.invoke("verify")["ok"])

    def test_asset_only_legacy_update_does_not_accept_defaults(self):
        fixture = preservation.ProjectConventionPreservationTests("runTest")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.seed()
        fixture.invoke("apply")
        fixture.invoke("upgrade")
        result = fixture.invoke("plan")["guidance_selection"]
        self.assertEqual("pending", result["status"])
        self.assertFalse((fixture.root / CORE.GUIDANCE_FILE).exists())

    def test_invalid_selection_fails_before_asset_mutation(self):
        fixture = preservation.ProjectConventionPreservationTests("runTest")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.seed()
        fixture.write(CORE.GUIDANCE_FILE, '{"schema_version":1,"domains":["unknown"]}')
        before = fixture.snapshot()
        fixture.invoke("apply", expected=2, extra=("--domains", "all"))
        self.assertEqual(before, fixture.snapshot())
        self.assertEqual("invalid", fixture.invoke("plan")["guidance_selection"]["status"])
        self.assertEqual("invalid", fixture.invoke("verify", expected=1)["guidance_selection"]["status"])


if __name__ == "__main__":
    unittest.main()
