#!/usr/bin/env python3
"""Real selection persistence and preflight, separate from dialogue/model evaluation."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock
import test_project_conventions as preservation
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("selection_core", ROOT / "skills/agent-scaffold/scripts/harness-core.py")
CORE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CORE)
TEMPLATE = ROOT / "skills/agent-scaffold/assets/scaffold/AGENTS.harness.md"
RELEASE_ASSETS = ("runtime.release-guide", "runtime.release-plan", "runtime.release-changelog")
GUIDE_DOMAINS = ("docs", "tools", "testing", "specs", "terminology", "git", "environment")
GUIDE_ROUTES = {domain: ".agents/conventions/%s.md" % domain for domain in GUIDE_DOMAINS}
GUIDE_ROUTES["release"] = ".agents/tools/release/README.md"


def marker(text):
    found = re.findall(r"^<!-- agent-scaffold:domains=([^\n]*) -->$", text, re.MULTILINE)
    return found[0] if len(found) == 1 else None


def routes(text):
    return [domain for domain in CORE.GUIDANCE_DOMAINS if "`%s`" % GUIDE_ROUTES[domain] in text]


class GuidanceSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="choice space ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.agents = self.root / CORE.SELECTION_RECORD
        self.legacy = self.root / CORE.LEGACY_GUIDANCE_FILE

    def contract(self, domains, prose="# Project\n\n"):
        text = prose + CORE.render_agents_template(TEMPLATE, "default", domains)
        self.agents.write_bytes(text.encode())
        return text

    def record_legacy(self, text):
        self.legacy.parent.mkdir(exist_ok=True)
        self.legacy.write_bytes(text.encode())

    def replace_marker(self, value):
        text = self.agents.read_text(encoding="utf-8")
        self.agents.write_bytes(re.sub(r"(<!-- agent-scaffold:domains=)[^\n]*( -->)",
                                       lambda m: m.group(1) + value + m.group(2), text).encode())

    def test_absence_is_pending_with_all_defaults_and_no_writes(self):
        for contract in (False, True):
            with self.subTest(contract=contract):
                if contract:
                    self.contract(None)
                before = sorted(self.root.iterdir())
                report = CORE.guidance_selection(self.root)
                self.assertEqual("pending", report["status"])
                self.assertEqual(CORE.SELECTION_RECORD, report["path"])
                self.assertIsNone(report["domains"])
                self.assertEqual(list(CORE.GUIDANCE_DOMAINS), report["defaults"])
                self.assertEqual(before, sorted(self.root.iterdir()))
        self.assertIsNone(marker(self.agents.read_text(encoding="utf-8")))

    def test_all_and_none_are_both_recorded_in_the_managed_block(self):
        for domains, expected in ((list(CORE.GUIDANCE_DOMAINS), ",".join(CORE.GUIDANCE_DOMAINS)), ([], "none")):
            with self.subTest(domains=domains):
                text = self.contract(domains)
                self.assertEqual(expected, marker(CORE.extract_managed_block(text)))
                result = CORE.guidance_selection(self.root)
                self.assertEqual(("recorded", CORE.SELECTION_RECORD, domains, None),
                                 (result["status"], result["path"], result["domains"], result["defaults"]))

    def test_subset_is_recorded_in_canonical_order(self):
        text = self.contract(["git", "docs", "testing"])
        self.assertEqual("docs,testing,git", marker(text))
        self.assertEqual(["docs", "testing", "git"], CORE.load_guidance_selection(self.root))
        self.assertEqual(text, "# Project\n\n" + CORE.render_agents_template(TEMPLATE, "default",
                                                                            ["testing", "git", "docs"]))

    def test_preview_does_not_replace_accepted_selection(self):
        self.contract(["docs"])
        before = self.agents.read_bytes()
        self.assertEqual("proposed", CORE.guidance_selection(self.root, "all")["status"])
        self.assertEqual(before, self.agents.read_bytes())
        self.assertEqual(["docs"], CORE.load_guidance_selection(self.root))

    def test_new_upstream_domain_is_not_silently_selected(self):
        self.contract(list(CORE.GUIDANCE_DOMAINS))
        saved = CORE.load_guidance_selection(self.root)
        with mock.patch.object(CORE, "GUIDANCE_DOMAINS", CORE.GUIDANCE_DOMAINS + ("new-domain",)):
            result = CORE.guidance_selection(self.root)
            self.assertEqual("recorded", result["status"])
            self.assertEqual(saved, result["domains"])
            self.assertIsNone(result["defaults"])

    def test_invalid_markers_are_not_treated_as_new_installations(self):
        # "all" is never written, so a later upstream domain cannot be selected silently.
        for value in ("all", "", "docs,,git", "docs,docs", "unknown", "Docs", " docs", "docs;git"):
            with self.subTest(value=value):
                self.contract(["docs"])
                self.replace_marker(value)
                before = self.agents.read_bytes()
                with self.assertRaises(CORE.CoreError):
                    CORE.guidance_selection(self.root)
                self.assertEqual(before, self.agents.read_bytes())
        self.contract(["docs"])
        text = self.agents.read_text(encoding="utf-8")
        self.agents.write_bytes(text.replace("<!-- agent-scaffold:domains=docs -->",
                                             "<!-- agent-scaffold:domains=docs -->\n<!-- agent-scaffold:domains=git -->").encode())
        with self.assertRaises(CORE.CoreError):
            CORE.load_guidance_selection(self.root)

    def test_marker_outside_a_valid_block_is_no_record(self):
        # Malformed or missing block markers are reported by the contract checks instead.
        self.agents.write_bytes(b"# Project\n<!-- agent-scaffold:domains=docs -->\n")
        self.assertIsNone(CORE.load_guidance_selection(self.root))
        self.agents.write_bytes(b"<!-- agent-scaffold:start -->\n<!-- agent-scaffold:domains=docs -->\n")
        self.assertIsNone(CORE.load_guidance_selection(self.root))

    def test_invalid_legacy_records_are_not_treated_as_new_installations(self):
        invalid = ('{}', '[]', '{bad', '{"schema_version":true,"domains":[]}',
                   '{"schema_version":2,"domains":[]}', '{"schema_version":1,"domains":"all"}',
                   '{"schema_version":1,"domains":["docs","docs"]}',
                   '{"schema_version":1,"domains":["docs"],"domains":[]}',
                   '{"schema_version":1,"domains":["unknown"]}',
                   '{"schema_version":1,"domains":[false]}',
                   '{"schema_version":1,"domains":[],"extra":null}',
                   '{"schema_version":NaN,"domains":[]}', ' ' * 16385)
        self.contract(["docs"])
        for text in invalid:
            with self.subTest(text=text[:90]):
                self.record_legacy(text)
                with self.assertRaises(CORE.CoreError):
                    CORE.guidance_selection(self.root)
                with self.assertRaises(CORE.CoreError):
                    CORE.retire_legacy_selection(self.root)
                self.assertEqual(text.encode(), self.legacy.read_bytes())

    def test_legacy_record_is_read_until_retired_and_must_agree_with_the_marker(self):
        self.contract(None)
        self.record_legacy('{"schema_version":1,"domains":["git","docs"]}')
        result = CORE.guidance_selection(self.root)
        self.assertEqual(("recorded", CORE.LEGACY_GUIDANCE_FILE, ["docs", "git"]),
                         (result["status"], result["path"], result["domains"]))
        with self.assertRaises(CORE.CoreError):
            CORE.retire_legacy_selection(self.root)  # nothing records it in AGENTS.md yet
        self.assertTrue(self.legacy.is_file())
        self.contract(["docs"])
        with self.assertRaisesRegex(CORE.CoreError, "different selections"):
            CORE.guidance_selection(self.root)
        self.contract(["docs", "git"])
        self.assertEqual(CORE.SELECTION_RECORD, CORE.guidance_selection(self.root)["path"])
        self.assertTrue(CORE.retire_legacy_selection(self.root))
        self.assertFalse(self.legacy.exists())
        self.assertFalse(CORE.retire_legacy_selection(self.root))
        self.assertEqual(["docs", "git"], CORE.load_guidance_selection(self.root))

    def test_argument_validation_is_exact(self):
        for value in ('', 'all,docs', 'none,git', 'docs,docs', 'doc', 'docs,', ',docs', 'unknown', 'docs,,tools'):
            with self.subTest(value=value), self.assertRaises(CORE.CoreError):
                CORE.parse_domains(value)
        self.assertEqual(["docs", "git"], CORE.parse_domains(" git , docs "))

    def test_legacy_file_and_parent_aliases_are_not_followed(self):
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "selection.json"
        sentinel.write_text('{"schema_version":1,"domains":["docs"]}')
        self.contract(["docs"])
        self.legacy.parent.mkdir()
        try:
            self.legacy.symlink_to(sentinel)
        except OSError as exc:
            self.skipTest("no native symlink capability: " + str(exc))
        with self.assertRaises(CORE.CoreError):
            CORE.retire_legacy_selection(self.root)
        self.legacy.unlink(); self.legacy.parent.rmdir()
        self.legacy.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(CORE.CoreError):
            CORE.retire_legacy_selection(self.root)
        self.assertEqual('{"schema_version":1,"domains":["docs"]}', sentinel.read_text())
        self.assertEqual([sentinel], list(outside.iterdir()))

    def test_optional_managed_terminology_follows_saved_choice(self):
        for domains, present in ((None, True), ([], False), (["docs"], False), (["terminology"], True)):
            with self.subTest(domains=domains):
                rendered = CORE.render_agents_template(TEMPLATE, "default", domains)
                self.assertEqual(present, "### Project terminology" in rendered)
                self.assertNotIn(CORE.TERMINOLOGY_START, rendered)
                self.assertIn("### Authority documents", rendered)
                self.assertIn("### Worktree-per-change", rendered)

    def test_guide_routes_follow_the_selection(self):
        cases = ((None, []), ([], []), (["docs"], ["docs"]), (["release"], ["release"]),
                 (["environment", "git", "tools"], ["tools", "git", "environment"]),
                 (list(CORE.GUIDANCE_DOMAINS), list(CORE.GUIDANCE_DOMAINS)))
        for profile in ("default", "light"):
            for domains, expected in cases:
                with self.subTest(profile=profile, domains=domains):
                    rendered = CORE.render_agents_template(TEMPLATE, profile, domains)
                    self.assertEqual(expected, routes(rendered))
                    self.assertEqual(bool(expected), "### Convention guides" in rendered)
                    self.assertNotIn("agent-scaffold:domain=", rendered)
                    self.assertNotIn("agent-scaffold:conventions", rendered)
                    self.assertIn("### Sources and projections", rendered)

    def test_template_cannot_route_an_unknown_domain(self):
        broken = self.root / "AGENTS.harness.md"
        broken.write_text(TEMPLATE.read_text(encoding="utf-8").replace("domain=docs", "domain=wiki"),
                          encoding="utf-8")
        with self.assertRaisesRegex(CORE.CoreError, "unknown domain"):
            CORE.render_agents_template(broken, "default", ["docs"])

    def test_domain_assets_are_scoped_to_their_domains(self):
        manifest = CORE.load_manifest()
        guides = {"convention." + domain for domain in GUIDE_DOMAINS}
        for domains in (None, [], ["docs", "git"], ["release"], ["testing"], ["terminology"],
                        list(CORE.GUIDANCE_DOMAINS)):
            with self.subTest(domains=domains):
                ids = {item["id"] for item in CORE.active_assets(manifest, "default", domains)}
                lines = {item["id"] for item in CORE.active_line_invariants(manifest, "light", domains)}
                selected = set(domains or [])
                self.assertEqual({"convention." + d for d in selected if d != "release"}, ids & guides)
                self.assertEqual("release" in selected, set(RELEASE_ASSETS) <= ids)
                self.assertFalse("release" not in selected and set(RELEASE_ASSETS) & ids)
                self.assertEqual("release" in selected, "contract.gitattributes-release" in lines)
                self.assertEqual(bool(selected - {"release"}), "contract.gitattributes-conventions" in lines)
                self.assertEqual(bool(selected & {"testing", "terminology"}), "convention.notice" in ids)
                self.assertIn("runtime.subagent-generator", ids)

    def test_manifest_rejects_invalid_domain_scope(self):
        data = json.loads(CORE.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        for asset_id in ("runtime.release-plan", "convention.docs"):
            for value in ([], ["unknown"], ["release", "release"], "release"):
                with self.subTest(asset=asset_id, value=value):
                    broken = json.loads(json.dumps(data))
                    next(a for a in broken["assets"] if a["id"] == asset_id)["domains"] = value
                    path = self.root / "manifest.json"
                    path.write_text(json.dumps(broken), encoding="utf-8")
                    with self.assertRaises(CORE.CoreError):
                        CORE.load_manifest(path)


class InstallerSelectionTests(unittest.TestCase):
    def fixture(self):
        fixture = preservation.ProjectConventionPreservationTests("runTest")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.seed()
        return fixture

    def assert_installed(self, fixture, asset_ids):
        manifest = CORE.load_manifest()
        for asset_id in asset_ids:
            asset = CORE.asset_by_id(manifest, asset_id)
            self.assertEqual((CORE.SKILL_DIR / asset["source"]).read_bytes(),
                             (fixture.root / asset["target"]).read_bytes(), asset_id)

    def test_actual_install_upgrade_and_preview_preserve_selection(self):
        fixture = self.fixture()
        before = fixture.snapshot()
        planned = fixture.invoke("plan", extra=("--domains", "none"))
        self.assertEqual("proposed", planned["guidance_selection"]["status"])
        self.assertEqual(before, fixture.snapshot())
        fixture.invoke("apply", extra=("--domains", "docs,testing,git"))
        contract = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual("docs,testing,git", marker(contract))
        self.assertEqual(["docs", "testing", "git"], routes(contract))
        self.assertNotIn("### Project terminology", contract)
        self.assertIn("工程约定", contract)
        self.assert_installed(fixture, ("convention.docs", "convention.testing", "convention.git",
                                        "convention.notice"))
        self.assertEqual(["NOTICE.md", "docs.md", "git.md", "testing.md"],
                         sorted(p.name for p in (fixture.root / ".agents/conventions").iterdir()))
        self.assertFalse((fixture.root / CORE.LEGACY_GUIDANCE_FILE).exists())
        verified = fixture.invoke("verify")
        self.assertTrue(verified["ok"])
        self.assertEqual(("recorded", "AGENTS.md"), (verified["guidance_selection"]["status"],
                                                     verified["guidance_selection"]["path"]))
        after = fixture.snapshot()
        fixture.invoke("upgrade")
        self.assertEqual(after, fixture.snapshot())
        release = fixture.root / ".agents/tools/release"
        self.assertFalse(release.exists())
        fixture.invoke("upgrade", extra=("--domains", "all"))
        contract = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("### Project terminology", contract)
        # Release keeps its task-time guide; the resident contract only routes to it.
        self.assertEqual(list(CORE.GUIDANCE_DOMAINS), routes(contract))
        self.assertNotIn("release-plan.py", contract)
        self.assert_installed(fixture, RELEASE_ASSETS + tuple("convention." + d for d in GUIDE_DOMAINS))
        self.assertTrue(fixture.invoke("verify")["ok"])
        # Deselecting stops maintenance and routing; dormant copies stay project files.
        fixture.invoke("upgrade", extra=("--domains", "docs"))
        contract = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(["docs"], routes(contract))
        self.assertEqual(sorted(p.name for p in release.iterdir()),
                         ["README.md", "extract-changelog.py", "release-plan.py"])
        self.assertTrue((fixture.root / ".agents/conventions/testing.md").is_file())
        verified = fixture.invoke("verify")
        self.assertTrue(verified["ok"])
        self.assertFalse([c for c in verified["checks"] if c["id"] in RELEASE_ASSETS + ("convention.testing",)])

    def test_verify_rejects_edited_guides_and_removed_routes(self):
        fixture = self.fixture()
        fixture.invoke("apply", extra=("--domains", "testing"))
        guide = fixture.root / ".agents/conventions/testing.md"
        original = guide.read_bytes()
        guide.write_bytes(original + b"\nLocal override.\n")
        failed = {c["id"] for c in fixture.invoke("verify", expected=1)["checks"] if c["status"] == "fail"}
        self.assertEqual({"convention.testing"}, failed)
        guide.write_bytes(original)
        agents = fixture.root / "AGENTS.md"
        contract = agents.read_bytes()
        agents.write_bytes(contract.replace(b"- Tests: `.agents/conventions/testing.md`\n", b""))
        failed = {c["id"] for c in fixture.invoke("verify", expected=1)["checks"] if c["status"] == "fail"}
        self.assertEqual({"contract.agents-content"}, failed)
        fixture.invoke("upgrade")
        self.assertEqual(contract, agents.read_bytes())
        self.assertTrue(fixture.invoke("verify")["ok"])

    def test_upgrade_moves_a_legacy_record_into_the_managed_block(self):
        fixture = self.fixture()
        fixture.invoke("apply", extra=("--domains", "docs"))
        agents = fixture.root / "AGENTS.md"
        agents.write_bytes(agents.read_bytes().replace(b"<!-- agent-scaffold:domains=docs -->\n", b""))
        fixture.write(CORE.LEGACY_GUIDANCE_FILE, '{"schema_version": 1, "domains": ["docs", "git"]}\n')
        planned = fixture.invoke("plan")
        self.assertEqual(("recorded", CORE.LEGACY_GUIDANCE_FILE, ["docs", "git"]),
                         tuple(planned["guidance_selection"][k] for k in ("status", "path", "domains")))
        statuses = {c["id"]: c["status"] for c in planned["checks"]}
        self.assertEqual(("refresh", "refresh", "create"), (statuses["guidance.legacy-record"],
                                                            statuses["contract.agents"], statuses["convention.git"]))
        failed = {c["id"] for c in fixture.invoke("verify", expected=1)["checks"] if c["status"] == "fail"}
        self.assertIn("guidance.legacy-record", failed)
        output = fixture.invoke("upgrade").stdout
        self.assertIn("removed " + CORE.LEGACY_GUIDANCE_FILE, output)
        self.assertFalse((fixture.root / CORE.LEGACY_GUIDANCE_FILE).exists())
        self.assertEqual("docs,git", marker(agents.read_text(encoding="utf-8")))
        self.assert_installed(fixture, ("convention.docs", "convention.git"))
        self.assertTrue(fixture.invoke("verify")["ok"])

    def test_conflicting_records_fail_before_mutation(self):
        fixture = self.fixture()
        fixture.invoke("apply", extra=("--domains", "docs"))
        fixture.write(CORE.LEGACY_GUIDANCE_FILE, '{"schema_version": 1, "domains": ["git"]}\n')
        before = fixture.snapshot()
        for extra in ((), ("--domains", "all")):
            with self.subTest(extra=extra):
                fixture.invoke("upgrade", expected=2, extra=extra)
                self.assertEqual(before, fixture.snapshot())
        self.assertEqual("invalid", fixture.invoke("plan")["guidance_selection"]["status"])

    def test_asset_only_legacy_update_does_not_accept_defaults(self):
        fixture = self.fixture()
        fixture.invoke("apply")
        fixture.invoke("upgrade")
        result = fixture.invoke("plan")["guidance_selection"]
        self.assertEqual("pending", result["status"])
        contract = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIsNone(marker(contract))
        self.assertEqual([], routes(contract))
        self.assertFalse((fixture.root / CORE.LEGACY_GUIDANCE_FILE).exists())
        self.assertFalse((fixture.root / ".agents/tools/release").exists())
        self.assertFalse((fixture.root / ".agents/conventions").exists())

    def test_invalid_argument_is_a_usage_error_not_a_damaged_record(self):
        fixture = self.fixture()
        before = fixture.snapshot()
        plan = subprocess.run([fixture.bash_bin, preservation.INSTALLER.as_posix(), "plan", "--profile", "light",
                               "--domains", "docs,unknown", "--json"], cwd=str(fixture.root), env=fixture.env,
                              capture_output=True, text=True, encoding="utf-8", timeout=180)
        apply = fixture.invoke("apply", expected=2, extra=("--domains", "docs,unknown"))
        for mode, result in (("plan", plan), ("apply", apply)):
            with self.subTest(mode=mode):
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                output = result.stdout + result.stderr
                self.assertIn("--domains requires", output)
                self.assertNotIn("saved selection", output)
        self.assertEqual(before, fixture.snapshot())

    def test_invalid_selection_fails_before_asset_mutation(self):
        for label in ("legacy", "marker"):
            with self.subTest(record=label):
                fixture = self.fixture()
                if label == "legacy":
                    fixture.write(CORE.LEGACY_GUIDANCE_FILE, '{"schema_version":1,"domains":["unknown"]}')
                else:
                    fixture.invoke("apply", extra=("--domains", "docs"))
                    agents = fixture.root / "AGENTS.md"
                    agents.write_bytes(agents.read_bytes().replace(b"domains=docs", b"domains=all"))
                before = fixture.snapshot()
                fixture.invoke("apply", expected=2, extra=("--domains", "all"))
                self.assertEqual(before, fixture.snapshot())
                self.assertEqual("invalid", fixture.invoke("plan")["guidance_selection"]["status"])
                self.assertEqual("invalid", fixture.invoke("verify", expected=1)["guidance_selection"]["status"])


if __name__ == "__main__":
    unittest.main()
