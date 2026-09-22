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

    def test_three_conditions_share_fixture_not_candidate(self):
        runs = {}
        for condition in ("none", "brief", "skill"):
            path = self.root / condition
            runs[condition] = runner.prepare_run("spec-preservation", path, condition)
            self.assertEqual((path / "guidance").exists(), condition == "skill")
            self.assertEqual("Read relevant references" in (path / "prompt.txt").read_text(), condition == "skill")
        self.assertEqual(len({r["fixture_digest"] for r in runs.values()}), 1)
        self.assertEqual(len({r["state"]["base"] for r in runs.values()}), 1)
        self.assertIsNone(runs["none"]["skill_revision"])
        with self.assertRaisesRegex(ValueError, "exists"):
            runner.prepare_run("spec-preservation", self.root / "skill", "skill")

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
