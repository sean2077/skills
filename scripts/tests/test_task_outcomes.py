"""Deterministic tests of actual task artifacts. Reference actions are NOT model trials."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/tasks"))
import cases
import runner
import import_claude


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="outcome space ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def fixture(self, case):
        workspace = self.root / case
        return workspace, cases.prepare(workspace, case)

    def passed(self, workspace, case, state, trace=None):
        checks = cases.verify(workspace, case, state, trace)
        return all(c["passed"] for c in checks), checks

    def test_mixed_hunk_commit_preserves_actual_index_and_worktree(self):
        workspace, state = self.fixture("commit-hunks")
        self.assertFalse(self.passed(workspace, "commit-hunks", state)[0])
        # Reference action prepares just the authorized tree, then restores the remaining index.
        original_index = (workspace / ".git/index").read_bytes()
        cases.git(workspace, "read-tree", "HEAD")
        cases.write(workspace, "config.py", cases.COMMITTED)
        cases.git(workspace, "add", "config.py")
        cases.git(workspace, "commit", "-qm", "feat: enable feature")
        (workspace / ".git/index").write_bytes(original_index)
        cases.write(workspace, "config.py", cases.REMAINING_INDEX)
        cases.git(workspace, "add", "config.py")
        cases.write(workspace, "config.py", cases.WORKING)
        self.assertTrue(*self.passed(workspace, "commit-hunks", state))
        cases.git(workspace, "add", ".")
        cases.git(workspace, "commit", "-qm", "bad: include all")
        self.assertFalse(self.passed(workspace, "commit-hunks", state)[0])

    def test_spec_oracle_preserves_requirements_not_incidental_headings(self):
        workspace, state = self.fixture("spec-preservation")
        path = workspace / "spec.md"
        text = path.read_text().replace("This thing does the thing we discussed.", "Implement a request service using the contracts below.")
        path.write_text(text.replace("## Overview", "## Implementation context"))
        self.assertTrue(*self.passed(workspace, "spec-preservation", state))
        path.write_text(text.replace("250 ms", "500 ms"))
        self.assertFalse(self.passed(workspace, "spec-preservation", state)[0])
        path.write_text(text.replace("status: draft", "status: approved"))
        self.assertFalse(self.passed(workspace, "spec-preservation", state)[0])

    def test_docs_migration_incoming_and_outgoing_links(self):
        workspace, state = self.fixture("docs-move")
        (workspace / "docs").mkdir()
        (workspace / "setup.md").rename(workspace / "docs/setup.md")
        for name in ("README.md", "operations.md"):
            path = workspace / name
            path.write_text(path.read_text().replace("setup.md", "docs/setup.md"))
        path = workspace / "docs/setup.md"
        path.write_text(path.read_text().replace("](operations.md)", "](../operations.md)"))
        self.assertTrue(*self.passed(workspace, "docs-move", state))
        path.write_text(path.read_text().replace("## Authentication", "## Login"))
        self.assertFalse(self.passed(workspace, "docs-move", state)[0])

    def test_scaffold_guidance_needs_real_routes_and_project_commands(self):
        workspace, state = self.fixture("scaffold-guidance")
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        cases.write(workspace, "AGENTS.md", (workspace / "AGENTS.md").read_text() + "\n[Start here](doc/development.md)\n")
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        page = "# Working on this project\nRun `python tools/check.py --unit` from the repository root for offline checks; vendor integration is separate.\nGenerate docs/generated/api.md with `python scripts/render_api.py` from api/schema.json.\nUser docs live in website/content/. [Draft proposal](proposal.md).\nSubmit changes through a PR; do not merge automatically.\n"
        cases.write(workspace, "doc/development.md", page)
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        for original, replacement in (("tools/check.py", "tools/fake.py"), ("api/schema.json", "unknown.json"),
                                      ("do not merge automatically", "merge automatically"),
                                      ("(proposal.md)", "(missing.md)"), ("(proposal.md)", "(proposal.md#missing)")):
            with self.subTest(original=original):
                cases.write(workspace, "doc/development.md", page.replace(original, replacement))
                self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        cases.write(workspace, "doc/development.md", page.replace("# Working on this project", "# 开发入口"))
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        # A directory route is a valid way to name a docs owner; only a fragment on it is not.
        linked = page.replace("website/content/.", "[website/content/](../website/content/).")
        cases.write(workspace, "doc/development.md", linked)
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        cases.write(workspace, "doc/development.md", linked.replace("../website/content/)", "../website/content/#top)"))
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        cases.write(workspace, "doc/development.md", page)
        cases.write(workspace, "docs/generated/api.md", "modified output\n")
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        cases.write(workspace, "docs/generated/api.md", "# Generated API\nDo not hand-edit.\n")
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        # Naming the directory without its trailing slash is the same owner fact.
        cases.write(workspace, "doc/development.md", page.replace("website/content/.", "website/content is the directory."))
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        # The task forbids extra files and new/empty directories; enforce it.
        cases.write(workspace, "doc/notes.md", "unrequested page\n")
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        (workspace / "doc/notes.md").unlink()
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))
        (workspace / "onboarding").mkdir()
        self.assertFalse(self.passed(workspace, "scaffold-guidance", state)[0])
        (workspace / "onboarding").rmdir()
        self.assertTrue(*self.passed(workspace, "scaffold-guidance", state))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
    def test_link_traversal_accepts_a_symlinked_workspace_root(self) -> None:
        # macOS /tmp and /var, or a linked checkout, must not look like escaping links.
        real = self.root / "root-real"
        (real / "docs").mkdir(parents=True)
        (real / "AGENTS.md").write_bytes(b"[Guide](docs/guide.md)\n")
        (real / "docs" / "guide.md").write_bytes(b"# Guide\n")
        link = self.root / "root-link"
        try:
            link.symlink_to(real, target_is_directory=True)
        except OSError as exc:  # pragma: no cover - platform capability
            self.skipTest("symlink creation unsupported: %s" % exc)
        self.assertEqual({"AGENTS.md": "[Guide](docs/guide.md)\n", "docs/guide.md": "# Guide\n"},
                         cases.reachable_guidance(link))
        outside = self.root / "outside.md"
        outside.write_bytes(b"outside\n")
        os.symlink(outside, real / "escape.md")
        (real / "AGENTS.md").write_bytes(b"[Escape](escape.md)\n")
        with self.assertRaisesRegex(ValueError, "symlinked result"):
            cases.reachable_guidance(link)

    def test_scaffold_upgrade_repairs_routes_not_deleted_templates(self):
        workspace, state = self.fixture("scaffold-upgrade-guidance")
        self.assertFalse(self.passed(workspace, "scaffold-upgrade-guidance", state)[0])
        path = workspace / "AGENTS.md"
        cases.write(workspace, "AGENTS.md", path.read_text().replace("(doc/development.md)", "(CONTRIBUTING.md)"))
        self.assertTrue(*self.passed(workspace, "scaffold-upgrade-guidance", state))
        cases.write(workspace, "doc/development.md", "recreated old template\n")
        self.assertFalse(self.passed(workspace, "scaffold-upgrade-guidance", state)[0])

    def test_retired_docs_fixture_rejects_skill_condition_before_writes(self):
        out = self.root / "retired-treatment"
        for case in ("docs-move", "spec-preservation", "commit-hunks", "tdd-negative-input"):
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, "none/brief"):
                runner.prepare_run(case, out, "skill")
            self.assertFalse(out.exists())
        for condition in ("none", "brief"):
            result = runner.prepare_run("docs-move", self.root / condition, condition)
            self.assertIsNone(result["skill_digest"])

    def test_plan_retirement_pair_differs_only_by_the_installed_guide(self):
        bare, bare_state = self.fixture("plan-retirement")
        guided, guided_state = self.fixture("plan-retirement-installed-guide")
        self.assertEqual(cases.CASES["plan-retirement"], cases.CASES["plan-retirement-installed-guide"])
        skill = ROOT / "skills/agent-scaffold"
        self.assertEqual((skill / "assets/conventions/docs.md").read_bytes(),
                         (guided / ".agents/conventions/docs.md").read_bytes())
        contract = (guided / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(1, contract.count("`.agents/conventions/docs.md`"))
        self.assertIn("<!-- agent-scaffold:domains=docs -->", contract)
        bare_contract = (bare / "AGENTS.md").read_text(encoding="utf-8")
        route = contract.index("`.agents/conventions/docs.md`")
        start = contract.rfind("\n### ", 0, route) + 1
        end = contract.index("\n### ", route) + 1
        # Only the route section differs, not the rest of the harness/authority rules.
        self.assertEqual(bare_contract, contract[:start] + contract[end:])
        self.assertNotIn("`.agents/conventions/docs.md`", bare_contract)
        self.assertIn("<!-- agent-scaffold:domains=docs -->", bare_contract)
        tracked = lambda root: set(cases.git(root, "ls-files").decode().splitlines())
        self.assertEqual({".agents/conventions/docs.md"}, tracked(guided) - tracked(bare))
        self.assertEqual({"AGENTS.md"}, {p for p in tracked(bare)
                                         if (bare / p).read_bytes() != (guided / p).read_bytes()})
        self.assertIn(".agents/conventions/docs.md", guided_state["protected"])
        self.assertFalse([p for p in bare_state["protected"] if p.startswith("docs/")])

    def test_plan_retirement_keeps_history_and_stops_instructions(self):
        for case in ("plan-retirement", "plan-retirement-installed-guide"):
            with self.subTest(case=case):
                workspace, state = self.fixture(case)
                plan = workspace / "docs/plans/balance-cache.md"
                original = plan.read_text(encoding="utf-8")
                def result():
                    return self.passed(workspace, case, state)
                self.assertFalse(result()[0])  # Untouched steps still instruct readers.
                marked = original.replace("# Plan: balance cache\n", "# Plan: balance cache\n\nStatus: implemented "
                                          "and deployed; the current design is in [Architecture](../ARCHITECTURE.md).\n")
                plan.write_text(marked, encoding="utf-8")
                self.assertTrue(*result())
                for before, after in ((cases.PLAN_MEASUREMENT, "p95 balance read is now 3.1 ms."),
                                      (cases.PLAN_RATIONALE, ""), ("(../ARCHITECTURE.md)", "(../README.md)")):
                    plan.write_text(marked.replace(before, after), encoding="utf-8")
                    self.assertFalse(result()[0], before)
                plan.write_text(marked.replace("Status: implemented", "Note: shipped"), encoding="utf-8")
                self.assertTrue(*result())  # Equivalent explicit completion wording remains valid.
                plan.write_text(marked.replace("Status: implemented", "This plan is implemented"), encoding="utf-8")
                self.assertTrue(*result())  # Ordinary prose needs no prescribed field or heading.
                # The rationale's meaning must survive; its exact words need not.
                plan.write_text(marked.replace(cases.PLAN_RATIONALE, "Write-through was chosen because readers "
                                               "must *never* observe a stale balance."), encoding="utf-8")
                self.assertTrue(*result())
                plan.write_text(marked.replace(cases.PLAN_RATIONALE, "We chose write-through for speed.\n\n"
                                               "Readers must never observe a stale balance."), encoding="utf-8")
                self.assertFalse(result()[0])  # Decision and reason split apart lose the rationale.
                architecture = workspace / "docs/ARCHITECTURE.md"
                owner = architecture.read_text(encoding="utf-8")
                plan.write_text(marked, encoding="utf-8")
                architecture.write_text(owner.replace("src/cache.py.", "`src/cache.py`."), encoding="utf-8")
                self.assertTrue(*result())  # Code formatting does not change the owner's statement.
                architecture.write_text(owner.replace("src/cache.py.", "src/cache.py, so readers never "
                                                      "observe a stale balance."), encoding="utf-8")
                self.assertTrue(*result())  # Extending the owner's sentence keeps its statement.
                architecture.write_text(owner.replace("src/cache.py.", "[`src/cache.py`](../src/cache.py)."),
                                        encoding="utf-8")
                self.assertTrue(*result())  # Linking the source file keeps the statement.
                architecture.write_text(owner.replace("write-through", "write-back"), encoding="utf-8")
                self.assertFalse(result()[0])
                architecture.write_text(owner, encoding="utf-8")
                # Moving the history to the owner and removing the plan is also valid.
                plan.unlink(); plan.parent.rmdir()
                self.assertFalse(result()[0])  # Rationale and dated evidence were lost.
                architecture = workspace / "docs/ARCHITECTURE.md"
                architecture.write_text(architecture.read_text(encoding="utf-8") + "\n## History\n\n"
                                        + cases.PLAN_RATIONALE + "\n\n" + cases.PLAN_MEASUREMENT + "\n",
                                        encoding="utf-8")
                self.assertFalse(result()[0])  # The documentation map still links the removed plan.
                readme = workspace / "docs/README.md"
                readme.write_text(readme.read_text(encoding="utf-8").replace(
                    "- [Balance-cache plan](plans/balance-cache.md)\n", ""), encoding="utf-8")
                self.assertTrue(*result())
                cases.write(workspace, "src/cache.py", "CACHE = None\n")
                self.assertFalse(result()[0])

    def test_retirement_status_reads_negation_and_deferral_per_clause(self):
        retired = ("Status: completed. The steps below are historical and must not be run.",
                   "Status: implemented and deployed; do not follow the next steps.",
                   "Implemented in September; this plan no longer needs action and isn't a to-do list.",
                   "**Status:** Implemented — kept for history, not as instructions.",
                   "This plan is implemented and must not be followed.",
                   "Not a to-do list: implemented in September.", "Note: shipped", "status: done")
        live = ("Status: not implemented", "Status: not yet completed", "Status: isn't done",
                "Status: to be completed after review", "Status: pending; will be implemented next sprint",
                "Status: pending until completed", "Once implemented, archive this plan.",
                "The plan has not been fully implemented.", "Awaiting deployment before it is completed",
                "Status: implementation pending", "Status: unimplemented", "Status: in progress")
        for line in retired + live:
            with self.subTest(line=line):
                self.assertEqual(line in retired, cases.retired_plan_header("# Plan\n\n" + line + "\n"))

    def test_plan_retirement_rejects_negation_paraphrases_and_orphan_history(self):
        for case in ("plan-retirement", "plan-retirement-installed-guide"):
            with self.subTest(case=case):
                workspace, state = self.fixture(case)
                plan = workspace / "docs/plans/balance-cache.md"
                original = plan.read_text(encoding="utf-8")
                def passed(text):
                    plan.write_text(text + "\n[Current owner](../ARCHITECTURE.md)\n", encoding="utf-8")
                    return self.passed(workspace, case, state)[0]
                for status in ("Status: not implemented", "Status: not yet completed",
                               "Status: pending until completed", "# This plan is not retired",
                               "Status: to be completed after review",
                               "Status: pending; will be implemented next sprint"):
                    self.assertFalse(passed(original.replace("# Plan: balance cache\n",
                                                            "# Plan: balance cache\n\n" + status + "\n")), status)
                # A retirement status followed by a warning is the guide's own advice, not a negation.
                for status in ("Status: completed. The steps below are historical and must not be run.",
                               "This plan is implemented and must not be followed."):
                    self.assertTrue(passed(original.replace("# Plan: balance cache\n",
                                                           "# Plan: balance cache\n\n" + status + "\n")), status)
                paraphrased = original.replace(cases.PLAN_STEPS[0], "1. Build the balance cache now.").replace(
                    cases.PLAN_STEPS[1], "2. Run `python tools/purge.py --all` after deployment.")
                self.assertFalse(passed(paraphrased))
                self.assertTrue(passed(original.replace("# Plan: balance cache\n",
                                                       "# Plan: balance cache\n\nStatus: shipped\n")))
                # Keeping the evidence somewhere unlinked must not pass preservation.
                archived = "# History\n" + cases.PLAN_RATIONALE + "\n" + cases.PLAN_MEASUREMENT + "\n"
                cases.write(workspace, "docs/orphan.md", archived)
                stripped = original.replace(cases.PLAN_RATIONALE, "").replace(cases.PLAN_MEASUREMENT, "")
                self.assertFalse(passed(stripped.replace("# Plan: balance cache\n",
                                                        "# Plan: balance cache\n\nStatus: completed\n")))

    def test_selected_conventions_require_scope_and_real_project_guidance(self):
        workspace, state = self.fixture("scaffold-selected-guidance")
        def result():
            return self.passed(workspace, "scaffold-selected-guidance", state)
        self.assertFalse(result()[0])
        self.assertFalse(result()[0])  # The recorded choice alone cannot certify authored guidance.
        original = (workspace / "AGENTS.md").read_text()
        cases.write(workspace, "AGENTS.md", original + "\n[Guide](guide/development.md)\n")
        self.assertFalse(result()[0])
        guide = ("# 开发\nExisting owner guidance.\n" + "\n".join(cases.CONVENTION_CLAUSES)
                 + "\n[Spec](../spec.md) [Language](../language.md) [Checks](../quality.py)\n")
        cases.write(workspace, "guide/development.md", guide)
        self.assertTrue(*result())
        linked = (workspace / "AGENTS.md").read_text()
        record = "<!-- agent-scaffold:domains=" + ",".join(cases.SELECTED_DOMAINS) + " -->"
        for domains in (cases.SELECTED_DOMAINS + ["release"], [], cases.SELECTED_DOMAINS[:-1]):
            with self.subTest(domains=domains):
                edited = "<!-- agent-scaffold:domains=" + (",".join(domains) or "none") + " -->"
                cases.write(workspace, "AGENTS.md", linked.replace(record, edited))
                self.assertFalse(result()[0])
        cases.write(workspace, "AGENTS.md", linked + "\n" + cases.SELECTED_BLOCK)
        self.assertFalse(result()[0])  # A second managed block is not the recorded one.
        cases.write(workspace, "AGENTS.md", linked)
        self.assertTrue(*result())
        cases.write(workspace, ".agents/scaffold.json", '{"schema_version": 1, "domains": []}')
        self.assertFalse(result()[0])  # A parallel selection record is a control file.
        (workspace / ".agents/scaffold.json").unlink(); (workspace / ".agents").rmdir()
        for before, after in (("250 ms", "500 ms"), ("../language.md", "../language.md#missing"),
                              ("Existing owner guidance.", "")):
            cases.write(workspace, "guide/development.md", guide.replace(before, after))
            self.assertFalse(result()[0])
        cases.write(workspace, "guide/development.md", guide.replace("# 开发", "# Working here"))
        self.assertTrue(*result())
        cases.write(workspace, "release.md", "replaced the excluded release policy\n")
        self.assertFalse(result()[0])

    def test_testing_guidance_preserves_policy_sources_and_discovery(self):
        workspace, state = self.fixture("scaffold-testing-guidance")
        def result():
            return self.passed(workspace, "scaffold-testing-guidance", state)
        self.assertFalse(result()[0])
        entry = (workspace / "AGENTS.md").read_text() + "\n[Testing](handbook/development.md)\n"
        cases.write(workspace, "AGENTS.md", entry)
        self.assertFalse(result()[0])  # A new link alone is not completed guidance.
        guide = ("# 开发与测试\nSubmit through a PR; never auto-merge.\n\n"
                 + "\n\n".join(cases.TESTING_CLAUSES)
                 + "\nRun `python -m unittest discover -s spec -p '*_spec.py'`.\n"
                 + "[Contract](../protocol.md) · [Example](../spec/encoder_spec.py)\n")
        cases.write(workspace, "handbook/development.md", guide)
        self.assertTrue(*result())
        # Each owner-defined requirement has its own falsifying example.
        for clause in cases.TESTING_CLAUSES:
            with self.subTest(clause=clause):
                cases.write(workspace, "handbook/development.md", guide.replace(clause, ""))
                self.assertFalse(result()[0])
        for old, new in (("-s spec", "-s tests"), ("*_spec.py", "test_*.py"),
                         ("../protocol.md", "../protocol.md#missing"),
                         ("../spec/encoder_spec.py", "../missing.py"),
                         ("never auto-merge", "auto-merge")):
            with self.subTest(old=old):
                cases.write(workspace, "handbook/development.md", guide.replace(old, new))
                self.assertFalse(result()[0])
        # Equivalent headings/quote style are not the test contract.
        cases.write(workspace, "handbook/development.md", guide.replace("# 开发与测试", "# Test guide").replace("'*_spec.py'", '\"*_spec.py\"'))
        self.assertTrue(*result())
        for fence in ("```bash", "~~~sh"):
            with self.subTest(command_format=fence):
                command = "python -m unittest discover -s spec -p '*_spec.py'"
                formatted = guide.replace("`" + command + "`", "\n" + fence + "\n" + command + "\n" + fence[:3] + "\n")
                cases.write(workspace, "handbook/development.md", formatted)
                self.assertTrue(*result())
                cases.write(workspace, "handbook/development.md", formatted.replace("-s spec", "-s tests"))
                self.assertFalse(result()[0])
        # A shell prompt marker is presentation; it must not hide the real argv.
        command = "python -m unittest discover -s spec -p '*_spec.py'"
        for prompt in ("$ ", "> ", "PS> "):
            with self.subTest(prompt=prompt):
                cases.write(workspace, "handbook/development.md", guide.replace(
                    "`" + command + "`", "```bash\n" + prompt + command + "\n```"))
                self.assertTrue(*result())
                cases.write(workspace, "handbook/development.md", guide.replace(
                    "`" + command + "`", "```bash\n" + prompt + command.replace("-s spec", "-s tests") + "\n```"))
                self.assertFalse(result()[0])
        cases.write(workspace, "handbook/development.md", guide)
        for relative in ("TESTING.md", "tests/placeholder.py", "tools/test.sh"):
            with self.subTest(added=relative):
                cases.write(workspace, relative, "unrequested content\n")
                self.assertFalse(result()[0])
                (workspace / relative).unlink()
                parent = (workspace / relative).parent
                if parent != workspace:
                    parent.rmdir()
        (workspace / "tests").mkdir()
        self.assertFalse(result()[0])
        (workspace / "tests").rmdir()
        # Unrelated inline code is not another malformed test command.
        cases.write(workspace, "handbook/development.md", "A lone quote is `\"`.\n" + guide)
        self.assertTrue(*result())
        path = workspace / ".coveragerc"
        original = path.read_bytes()
        cases.write(workspace, ".coveragerc", "[report]\nfail_under = 1\n")
        self.assertFalse(result()[0])
        path.write_bytes(original)
        cases.write(workspace, "spec/encoder_spec.py", "# silently removed existing tests\n")
        self.assertFalse(result()[0])

    def test_mock_unknown_write_is_observed_without_blind_retry(self):
        workspace, state = self.fixture("lark-unknown-write")
        def invoke(*args):
            return subprocess.run([sys.executable, "lark_mock.py", *args], cwd=workspace,
                                  capture_output=True, env=cases.environment(), timeout=20)
        self.assertEqual(invoke("send", "--as", "user", "--to", "oc_fixture", "--text", "ready").returncode, 1)
        self.assertEqual(invoke("get", "--as", "user", "--id", "om_fixture").returncode, 0)
        self.assertTrue(*self.passed(workspace, "lark-unknown-write", state))
        invoke("send", "--as", "user", "--to", "oc_fixture", "--text", "ready")
        self.assertFalse(self.passed(workspace, "lark-unknown-write", state)[0])

    def test_mock_count_requires_collection_observation_and_correct_result(self):
        workspace, state = self.fixture("lark-invented-syntax")
        def invoke(*args):
            return subprocess.run([sys.executable, "lark_mock.py", *args], cwd=workspace,
                                  capture_output=True, text=True, env=cases.environment(), timeout=20)
        cases.write(workspace, "answer.json", '{"awaiting_reply_count": 2}')
        self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])
        self.assertEqual(invoke("--help").returncode, 0)
        self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])
        self.assertEqual(invoke("get", "--as", "user", "--id", "om_fixture").returncode, 0)
        self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])
        result = invoke("list", "--as", "user")
        self.assertEqual(result.returncode, 0)
        observed = json.loads(result.stdout)["messages"]
        cases.write(workspace, "answer.json", json.dumps({
            "awaiting_reply_count": sum(message["awaiting_reply"] for message in observed)
        }))
        self.assertTrue(*self.passed(workspace, "lark-invented-syntax", state))
        for wrong in (0, 1, 3, True, "2"):
            with self.subTest(answer=wrong):
                cases.write(workspace, "answer.json", json.dumps({"awaiting_reply_count": wrong}))
                self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])

    def test_mock_oracle_rejects_unsupported_flags_identity_and_ids(self):
        workspace, state = self.fixture("lark-invented-syntax")
        def invoke(*args):
            return subprocess.run([sys.executable, "lark_mock.py", *args], cwd=workspace,
                                  capture_output=True, env=cases.environment(), timeout=20)
        self.assertEqual(invoke("list", "--as", "user").returncode, 0)
        cases.write(workspace, "answer.json", '{"awaiting_reply_count": 2}')
        self.assertTrue(*self.passed(workspace, "lark-invented-syntax", state))
        log = workspace / "lark-events.jsonl"
        clean_log = log.read_bytes()
        for arguments in (
            ("list", "--as", "user", "--awaiting-reply"),
            ("list", "--as", "bot"),
            ("get", "--as", "user", "--id", "invented_id"),
        ):
            with self.subTest(arguments=arguments):
                log.write_bytes(clean_log)
                self.assertEqual(invoke(*arguments).returncode, 2)
                self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])
        log.write_bytes(clean_log)
        cases.write(workspace, "lark_mock.py", "print('modified mock')\n")
        self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])

    def test_mock_count_rejects_ambiguous_json_results(self):
        workspace, state = self.fixture("lark-invented-syntax")
        subprocess.run([sys.executable, "lark_mock.py", "list", "--as", "user"],
                       cwd=workspace, capture_output=True, env=cases.environment(), check=True, timeout=20)
        for answer in (
            '{"awaiting_reply_count":999,"awaiting_reply_count":2}',
            '{"awaiting_reply_count":2,"extra":{"value":1,"value":2}}',
            '{"awaiting_reply_count":2,"extra":NaN}',
            '{"awaiting_reply_count":2,"extra":Infinity}',
        ):
            with self.subTest(answer=answer):
                cases.write(workspace, "answer.json", answer)
                self.assertFalse(self.passed(workspace, "lark-invented-syntax", state)[0])
        cases.write(workspace, "answer.json", '{"awaiting_reply_count":2}')
        self.assertTrue(*self.passed(workspace, "lark-invented-syntax", state))

    def invoke_stateful_mock(self, workspace, *arguments):
        return subprocess.run([sys.executable, "lark_mock.py", *arguments], cwd=workspace,
                              capture_output=True, text=True, env=cases.environment(), timeout=20)

    def replace_task(self, workspace, payload):
        result = self.invoke_stateful_mock(workspace, "replace", "--as", "user", "--id",
                                           "task_fixture", "--json", json.dumps(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIs(json.loads(result.stdout)["ok"], True)
        return result

    def test_stateful_update_reads_then_preserves_real_stored_object(self):
        workspace, state = self.fixture("lark-stateful-update")
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])
        result = self.invoke_stateful_mock(workspace, "read", "--as", "user", "--id", "task_fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)["data"]
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        self.assertTrue(*self.passed(workspace, "lark-stateful-update", state))
        # A focused readback is allowed, but is not a mandatory extra call.
        self.invoke_stateful_mock(workspace, "read", "--as", "user", "--id", "task_fixture")
        self.assertTrue(*self.passed(workspace, "lark-stateful-update", state))
        stored = workspace / "task-state.json"
        stored.write_text(json.dumps({**payload, "assignee": "ou_someone_else"}))
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])

    def test_stateful_update_tolerates_read_only_command_list_discovery(self):
        workspace, state = self.fixture("lark-stateful-update")
        for arguments in (("--help",), ("help",)):
            with self.subTest(arguments=arguments):
                result = self.invoke_stateful_mock(workspace, *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIs(json.loads(result.stdout)["ok"], True)
        payload = json.loads(self.invoke_stateful_mock(
            workspace, "read", "--as", "user", "--id", "task_fixture").stdout)["data"]
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        self.assertTrue(*self.passed(workspace, "lark-stateful-update", state))

    def test_stateful_update_does_not_accept_a_command_list_as_state(self):
        workspace, state = self.fixture("lark-stateful-update")
        self.invoke_stateful_mock(workspace, "--help")
        payload = copy.deepcopy(state["initial_task"])
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])

    def test_stateful_update_rejects_blind_write_even_with_later_read(self):
        workspace, state = self.fixture("lark-stateful-update")
        payload = copy.deepcopy(state["initial_task"])
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])
        self.invoke_stateful_mock(workspace, "read", "--as", "user", "--id", "task_fixture")
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])

    def test_stateful_update_rejects_successful_but_destructive_replacements(self):
        workspace, state = self.fixture("lark-stateful-update")
        expected = copy.deepcopy(state["initial_task"])
        expected["description"] += "\nReviewed."
        variants = []
        for key in ("assignee", "due", "settings"):
            missing = copy.deepcopy(expected); missing.pop(key)
            variants.append(missing)
        for key, value in (("assignee", "ou_other"), ("due", "2026-12-01"),
                           ("description", "Reviewed.")):
            variants.append({**expected, key: value})
        changed_type = copy.deepcopy(expected)
        changed_type["settings"]["notify"] = 1  # Python True == 1 is not JSON type preservation.
        variants.append(changed_type)
        reordered = copy.deepcopy(expected)
        reordered["settings"]["labels"].reverse()
        variants.append(reordered)
        for payload in variants:
            with self.subTest(payload=payload):
                cases.write(workspace, "task-state.json", json.dumps(state["initial_task"]))
                (workspace / "lark-events.jsonl").unlink(missing_ok=True)
                self.invoke_stateful_mock(workspace, "read", "--as", "user", "--id", "task_fixture")
                self.replace_task(workspace, payload)  # Accepted by the mock; wrong business result.
                self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])
                self.replace_task(workspace, expected)
                self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])

    def test_stateful_cached_update_does_not_require_redundant_read(self):
        workspace, state = self.fixture("lark-stateful-update-cached")
        payload = json.loads((workspace / "cached-state.json").read_text())
        payload["description"] += "\nReviewed."
        # Semantically identical object key order is irrelevant.
        self.replace_task(workspace, dict(reversed(list(payload.items()))))
        self.assertTrue(*self.passed(workspace, "lark-stateful-update-cached", state))
        events = (workspace / "lark-events.jsonl").read_text().splitlines()
        self.assertEqual(len(events), 1)
        original = (workspace / "cached-state.json").read_bytes()
        cases.write(workspace, "cached-state.json", "{}")
        self.assertFalse(self.passed(workspace, "lark-stateful-update-cached", state)[0])
        (workspace / "cached-state.json").write_bytes(original)
        cases.write(workspace, "mock-help.md", "invented contract")
        self.assertFalse(self.passed(workspace, "lark-stateful-update-cached", state)[0])

    def test_stateful_update_rejects_noop_unsupported_calls_and_tampering(self):
        workspace, state = self.fixture("lark-stateful-update")
        self.invoke_stateful_mock(workspace, "read", "--as", "user", "--id", "task_fixture")
        cases.write(workspace, "answer.json", '{"success":true}')
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])
        payload = copy.deepcopy(state["initial_task"])
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        self.assertTrue(*self.passed(workspace, "lark-stateful-update", state))
        log = workspace / "lark-events.jsonl"
        clean = log.read_bytes()
        for args in (("read", "--as", "bot", "--id", "task_fixture"),
                     ("read", "--as", "user", "--id", "invented"),
                     ("replace", "--as", "user", "--id", "task_fixture", "--data", "{}")):
            with self.subTest(args=args):
                log.write_bytes(clean)
                self.assertEqual(self.invoke_stateful_mock(workspace, *args).returncode, 2)
                self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])
        log.write_bytes(clean)
        cases.write(workspace, "lark_mock.py", "print('pretend success')\n")
        self.assertFalse(self.passed(workspace, "lark-stateful-update", state)[0])

    def test_stateful_update_rejects_ambiguous_payloads_and_logs(self):
        workspace, state = self.fixture("lark-stateful-update-cached")
        payload = copy.deepcopy(state["initial_task"])
        payload["description"] += "\nReviewed."
        self.replace_task(workspace, payload)
        log = workspace / "lark-events.jsonl"
        clean = log.read_bytes()
        for value in ('{}', 'null', '[]', '{"x":1,"x":2}', 'NaN'):
            with self.subTest(log=value):
                log.write_bytes(clean + value.encode() + b"\n")
                self.assertFalse(self.passed(workspace, "lark-stateful-update-cached", state)[0])
        log.write_bytes(clean)
        for body in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.subTest(payload=body):
                log.write_bytes(clean)
                self.invoke_stateful_mock(workspace, "replace", "--as", "user", "--id",
                                          "task_fixture", "--json", body)
                self.assertFalse(self.passed(workspace, "lark-stateful-update-cached", state)[0])

    def test_actual_red_green_requires_trace_and_same_tests(self):
        workspace, state = self.fixture("tdd-negative-input")
        tests = cases.BASE_TEST + '\n    def test_negative_value(self):\n        with self.assertRaises(ValueError):\n            cap(-1, 10)\n'
        cases.write(workspace, "test_cap.py", tests)
        def invoke():
            cp = subprocess.run([sys.executable, "check.py"], cwd=workspace, env=cases.environment(),
                                capture_output=True, text=True, timeout=20)
            return cp.returncode, {"tool": "Bash", "command": "python check.py", "output": cp.stdout + cp.stderr}
        red_rc, red = invoke()
        self.assertEqual(red_rc, 1)
        cases.write(workspace, "cap.py", 'def cap(value, limit):\n    if value < 0:\n        raise ValueError("negative")\n    return min(value, limit)\n')
        green_rc, green = invoke()
        self.assertEqual(green_rc, 0)
        self.assertTrue(*self.passed(workspace, "tdd-negative-input", state, [red, green]))
        self.assertFalse(self.passed(workspace, "tdd-negative-input", state)[0])
        self.assertFalse(self.passed(workspace, "tdd-negative-input", state, [green])[0])
        self.assertFalse(self.passed(workspace, "tdd-negative-input", state, [green, red])[0])
        cases.write(workspace, "check.py", "raise SystemExit(0)\n")
        self.assertFalse(self.passed(workspace, "tdd-negative-input", state, [red, green])[0])

    def test_scaffold_fixture_controls_round_trip_through_json(self):
        for case in ("scaffold-guidance", "scaffold-upgrade-guidance",
                     "scaffold-testing-guidance", "scaffold-selected-guidance"):
            with self.subTest(case=case):
                output = self.root / (case + "-persisted")
                prepared = runner.prepare_run(case, output, "none")
                self.assertEqual(prepared, runner.load(output / "fixture.json"))
                # Assess re-loads the JSON, not the original in-memory state.
                result = runner.assess(output)
                self.assertFalse(result["passed"])  # No guidance has been authored yet.
                if "editable" in prepared["state"]:
                    self.assertIsInstance(prepared["state"]["editable"], list)
                    self.assertTrue(cases.guidance_changed_paths(output / "workspace", prepared["state"])
                                    <= set(prepared["state"]["editable"]))
                # An initially broken reader route may stop before the scope assertion;
                # persisted controls must still reproduce every in-memory oracle result.
                self.assertEqual(cases.verify(output / "workspace", case, prepared["state"]),
                                 result["checks"])

    def test_three_conditions_share_fixture_not_candidate(self):
        runs = {}
        for condition in ("none", "brief", "skill"):
            path = self.root / condition
            runs[condition] = runner.prepare_run("scaffold-guidance", path, condition)
            self.assertEqual((path / "guidance").exists(), condition == "skill")
            self.assertEqual("Read relevant references" in (path / "prompt.txt").read_text(), condition == "skill")
        self.assertEqual(len({r["fixture_digest"] for r in runs.values()}), 1)
        self.assertEqual(len({r["state"]["base"] for r in runs.values()}), 1)
        self.assertIsNone(runs["none"]["skill_revision"])
        with self.assertRaisesRegex(ValueError, "exists"):
            runner.prepare_run("scaffold-guidance", self.root / "skill", "skill")

    def test_payload_exports_committed_references_and_old_revisions(self):
        repository = self.root / "source"
        cases.prepare(repository, "spec-preservation")
        cases.write(repository, "skills/example/SKILL.md", "old instructions\n")
        cases.write(repository, "skills/example/references/details.md", "details\n")
        cases.git(repository, "add", "."); cases.git(repository, "commit", "-qm", "old skill")
        old = cases.git(repository, "rev-parse", "HEAD").decode().strip()
        cases.write(repository, "skills/example/SKILL.md", "new instructions\n")
        cases.git(repository, "add", "."); cases.git(repository, "commit", "-qm", "new skill")
        new = cases.git(repository, "rev-parse", "HEAD").decode().strip()
        with mock.patch.object(runner, "ROOT", repository):
            first = runner.export_skill("example", old, self.root / "old")
            second = runner.export_skill("example", new, self.root / "new")
            self.assertNotEqual(first, second)
            self.assertEqual((self.root / "old/SKILL.md").read_bytes(), b"old instructions\n")
            self.assertTrue((self.root / "new/references/details.md").is_file())
            with self.assertRaises(ValueError):
                runner.export_skill("not-a-skill", old, self.root / "missing")

    def test_failed_or_unknown_host_measurements_do_not_become_savings(self):
        host = {"name":"fixture", "version":"1", "model":"fixed", "configuration":"clean", "cache":"cold"}
        raw = {"status":"completed", "host":host, "metrics":{}, "trace":[]}
        driver = runner.validate_driver(raw, 2.5, "fixed")
        self.assertIsNone(driver["metrics"]["input_tokens"])
        self.assertEqual(driver["metrics"]["wall_time_seconds"], 2.5)
        for value in (False, -1, float("nan"), "10", 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner.validate_driver({**raw,"metrics":{"input_tokens":value}}, 0, "fixed")
        with self.assertRaises(ValueError):
            runner.validate_driver(raw, 0, "another-model")
        result = {"contract":runner.CONTRACT,"case":"one", "fixture_digest":"same", "evaluator_digest":"same",
                  "platform":"same", "python":"same", "execution":"completed","host":host,"checks":[{"name":"output","passed":True}],"passed":True,"metrics":driver["metrics"]}
        self.assertIsNone(runner.compare(result, result)["metric_deltas"]["input_tokens"])
        with self.assertRaises(ValueError):
            runner.compare(result, {**result, "execution":"failed"})
        with self.assertRaises(ValueError):
            runner.compare(result, {**result, "host":{**host,"cache":"warm"}})
        with self.assertRaises(ValueError):
            runner.compare(result, {**result, "passed":False})

    def test_driver_execution_is_bounded_write_once_and_reports_real_oracle(self):
        output = self.root / "driver-run"
        runner.prepare_run("spec-preservation", output, "none")
        command = [sys.executable, str(Path(__file__).resolve()), "--synthetic-driver"]
        # A completed adapter cannot supply a task pass without changing the actual artifact.
        result = runner.execute(output, command, "test", 10)
        self.assertFalse(result["passed"])
        self.assertIsNone(result["metrics"]["input_tokens"])
        with self.assertRaisesRegex(ValueError, "already attempted"):
            runner.execute(output, command, "test", 10)

    def test_import_cli_stream_pairs_real_tool_outputs_not_final_prose(self):
        path = self.root / "stream.jsonl"
        events = [
            {"type":"assistant", "message":{"model":"fixed","content":[{"type":"tool_use","id":"1","name":"Bash","input":{"command":"python check.py"}}]}},
            {"type":"user", "message":{"content":[{"type":"tool_result","tool_use_id":"1","content":"observed stdout"}]}},
            {"type":"result","is_error":False,"result":"I passed every test", "usage":{"input_tokens":12,"output_tokens":3}}
        ]
        def parse():
            path.write_text("\n".join(json.dumps(x) for x in events))
            return import_claude.parse_stream(path, "observed-version", "fixed", "bare", "cold", 2, 0)
        result = parse()
        self.assertEqual(result["trace"][0]["output"], "observed stdout")
        self.assertEqual(result["metrics"]["input_tokens"], 12)
        events[1]["message"]["content"][0]["tool_use_id"] = "unknown"
        with self.assertRaises(ValueError): parse()
        events.pop()
        with self.assertRaises(ValueError): parse()

    def test_artifact_escape_and_modified_oracles_rejected(self):
        workspace, state = self.fixture("lark-unknown-write")
        cases.write(workspace, "lark_mock.py", "print('pretend success')\n")
        self.assertFalse(self.passed(workspace, "lark-unknown-write", state)[0])
        with self.assertRaises(ValueError): cases.read(workspace, "../outside")
        try: (workspace / "link").symlink_to(workspace / "lark_mock.py")
        except OSError: self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError): cases.read(workspace, "link")


if __name__ == "__main__":
    if sys.argv[1:] == ["--synthetic-driver"]:
        print(json.dumps({"status": "completed", "host": {"name": "synthetic", "version": "1",
                         "model": "test", "configuration": "test", "cache": "none"},
                         "metrics": {}, "trace": []}))
    else:
        unittest.main(verbosity=2)
