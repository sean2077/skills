#!/usr/bin/env python3
"""Check metadata distribution, copyable YAML, and scaffold ownership boundaries.

These tests do not claim that an Agent obeys the prose; live decision probes own
that separate evidence layer.
"""

import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

import strictyaml

ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = load_module("metadata_generator", ROOT / "scripts/generate_document_metadata.py")
CORE = load_module("metadata_scaffold_core", ROOT / "skills/agent-scaffold/scripts/harness-core.py")


class DistributionTests(unittest.TestCase):
    def test_checked_in_asset_and_dogfood_match_source(self):
        expected = GEN.HEADER.encode("utf-8") + GEN.SOURCE.read_bytes()
        self.assertEqual(expected, GEN.TARGET.read_bytes())
        self.assertEqual(expected, (ROOT / ".agents/document-metadata.md").read_bytes())
        self.assertNotIn(b"\r", expected)

    def test_check_is_read_only_for_missing_and_drifted_targets(self):
        with tempfile.TemporaryDirectory() as raw:
            source, target = Path(raw) / "source.md", Path(raw) / "target.md"
            source.write_bytes(b"# Contract\n")
            self.assertFalse(GEN.synchronize(source, target, check=True))
            self.assertFalse(target.exists())
            target.write_bytes(b"stale\n")
            self.assertFalse(GEN.synchronize(source, target, check=True))
            self.assertEqual(b"stale\n", target.read_bytes())

    def test_generation_is_byte_exact_and_idempotent(self):
        with tempfile.TemporaryDirectory() as raw:
            source, target = Path(raw) / "source.md", Path(raw) / "nested/target.md"
            source.write_bytes("# Metadata — 状态\n".encode("utf-8"))
            self.assertTrue(GEN.synchronize(source, target, check=False))
            expected = GEN.HEADER.encode("utf-8") + source.read_bytes()
            self.assertEqual(expected, target.read_bytes())
            before = target.stat().st_mtime_ns
            self.assertTrue(GEN.synchronize(source, target, check=False))
            self.assertTrue(GEN.synchronize(source, target, check=True))
            self.assertEqual(before, target.stat().st_mtime_ns)

    def test_generation_rejects_nonregular_output_without_touching_it(self):
        with tempfile.TemporaryDirectory() as raw:
            source, target = Path(raw) / "source.md", Path(raw) / "target.md"
            source.write_bytes(b"# Contract\n")
            target.mkdir()
            for check in (True, False):
                with self.assertRaises(ValueError):
                    GEN.synchronize(source, target, check=check)
            self.assertTrue(target.is_dir())

    def test_generation_does_not_follow_output_symlinks(self):
        with tempfile.TemporaryDirectory() as raw:
            source, target, outside = (Path(raw) / name for name in ("source.md", "target.md", "outside.md"))
            source.write_bytes(b"# Contract\n")
            outside.write_bytes(b"project owned\n")
            try:
                target.symlink_to(outside)
            except OSError as exc:
                self.skipTest("symlink capability unavailable: %s" % exc)
            for check in (True, False):
                with self.assertRaises(ValueError):
                    GEN.synchronize(source, target, check=check)
            self.assertEqual(b"project owned\n", outside.read_bytes())


class CopyableMetadataTests(unittest.TestCase):
    def test_examples_are_yaml_mappings_with_safe_lifecycle_defaults(self):
        examples = re.findall(r"```markdown\n---\n(.*?)\n---\n", GEN.SOURCE.read_text(encoding="utf-8"), re.S)
        self.assertEqual(3, len(examples))
        documents = []
        for example in examples:
            data = strictyaml.load(example).data
            self.assertEqual({"doc"}, set(data))
            doc = data["doc"]
            for field in ("schema", "type", "status", "authority", "scope"):
                self.assertIn(field, doc)
            self.assertEqual("1", doc["schema"])
            self.assertIsInstance(doc["scope"], list)
            self.assertTrue(all(isinstance(scope, str) and scope for scope in doc["scope"]))
            documents.append(doc)
        self.assertEqual(("draft", "informative"), (documents[0]["status"], documents[0]["authority"]))
        self.assertEqual(("needs-revision", "normative"), (documents[1]["status"], documents[1]["authority"]))
        self.assertEqual("2026-09-07", documents[1]["updated"])
        self.assertIsInstance(documents[1]["extensions"], dict)
        self.assertEqual(("active", "normative"), (documents[2]["status"], documents[2]["authority"]))


class ScaffoldMetadataTests(unittest.TestCase):
    def test_both_profiles_install_the_same_non_executable_contract(self):
        manifest = CORE.load_manifest()
        for profile in ("default", "light"):
            with self.subTest(profile=profile):
                item = next(item for item in CORE.active_assets(manifest, profile) if item["id"] == "policy.document-metadata")
                self.assertEqual("copy", item["strategy"])
                self.assertEqual(".agents/document-metadata.md", item["target"])
                self.assertFalse(item["executable"])
                self.assertEqual(GEN.TARGET, CORE.SKILL_DIR / item["source"])

    def test_plan_handles_missing_drifted_and_nonregular_metadata(self):
        manifest = CORE.load_manifest()
        for profile in ("default", "light"):
            with tempfile.TemporaryDirectory() as raw:
                target = Path(raw)
                installed = target / ".agents/document-metadata.md"
                for expected, mode in (("create", "apply"), ("refresh", "upgrade"), ("present", "apply"), ("attention", "apply")):
                    with self.subTest(profile=profile, state=expected):
                        plan = CORE.build_plan(target, profile, manifest)
                        record = next(item for item in plan["checks"] if item["id"] == "policy.document-metadata")
                        self.assertEqual(expected, record["status"])
                        self.assertEqual(mode, plan["apply_mode"])
                        if expected == "create":
                            self.assertFalse(installed.exists())
                            installed.parent.mkdir()
                            installed.write_bytes(b"old baseline\n")
                        elif expected == "refresh":
                            self.assertEqual(b"old baseline\n", installed.read_bytes())
                            installed.write_bytes(GEN.TARGET.read_bytes())
                        elif expected == "present":
                            installed.unlink()
                            installed.mkdir()
                        else:
                            self.assertFalse(plan["ok"])

    def test_missing_metadata_role_is_rejected(self):
        import json
        manifest = CORE.load_manifest()
        manifest["assets"] = [item for item in manifest["assets"] if item["id"] != "policy.document-metadata"]
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CORE.CoreError, "missing required managed asset"):
                CORE.load_manifest(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
