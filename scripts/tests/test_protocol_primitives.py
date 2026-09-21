"""Regression coverage for workflow-neutral coordination and compact evidence."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from p0_runtime.common import HarnessError, discover_git_context
from p0_runtime.workctl import (
    _latest_verification_passed, TaskStore, init_task, acquire_owner, release_owner,
    transition_task, create_workspace, claim_paths, verify_task,
)
from scripts.tests.test_p0_agent_workflows import init_repo
import subprocess


class ProtocolPrimitivesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="protocol v2 ")
        self.repo = Path(self.temp.name) / "repo"
        init_repo(self.repo)
        self.context = discover_git_context(self.repo)
        self.store, _ = init_task(self.context, "task", "Coordination only")
        _, self.token = acquire_owner(self.store, 1, "session-42", 60, "test")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args, expected=0):
        env = dict(os.environ, PYTHONUTF8="1", WORKCTL_LEASE_TOKEN=self.token)
        result = subprocess.run(
            [sys.executable, str(ROOT / "skills/work-protocol/scripts/workctl.py"), *args],
            cwd=self.repo, env=env, text=True, encoding="utf-8", capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_typed_consistent_verification(self):
        bad = [
            {}, {"exit_code": False}, {"exit_code": True}, {"exit_code": "0"},
            {"exit_code": 0.0}, {"exit_code": -1}, {"exit_code": 256},
            {"passed": 1}, {"passed": "true"}, {"passed": None},
            {"status": ["passed"]}, {"status": "unknown"},
            {"passed": False, "exit_code": 0}, {"passed": True, "exit_code": 1},
            {"status": "failed", "passed": True}, {"status": "success", "exit_code": 2},
        ]
        good = [{"passed": True}, {"exit_code": 0}, {"status": "success"},
                {"status": "passed", "passed": True, "exit_code": 0}]
        for index, payload in enumerate(bad + good):
            with self.subTest(payload=payload):
                events = [{"seq": 1, "kind": "test", "payload": payload}]
                self.assertEqual(_latest_verification_passed(events), index >= len(bad))

    def test_completion_rejects_contradictions_and_stale_stages(self):
        self.store.append_evidence(2, "test", "test", {"passed": False, "exit_code": 0}, self.token)
        with self.assertRaises(HarnessError):
            transition_task(self.store, 3, self.token, "done", "test", "contradictory")
        self.store.append_evidence(3, "test", "test", {"exit_code": 0}, self.token)
        transition_task(self.store, 4, self.token, "audit", "test", "new stage")
        with self.assertRaises(HarnessError):
            transition_task(self.store, 5, self.token, "done", "test", "stale")
        self.store.append_evidence(5, "test", "test", {"passed": True}, self.token)
        result = transition_task(self.store, 6, self.token, "done", "test", "observed")
        self.assertEqual(result["phase"], "done")
        self.assertTrue(verify_task(self.store)["ok"])
        with self.assertRaises(HarnessError):
            transition_task(self.store, 7, self.token, "implement", "test", "reopen")
        with self.assertRaises(HarnessError):
            self.store.append_evidence(7, "test", "test", {"passed": False}, self.token)
        release_owner(self.store, 7, self.token, "test")

    def test_completion_checks_current_workspace_scope(self):
        target = Path(self.temp.name) / "writer"
        create_workspace(self.store, 2, self.token, "writer", "writer", target, "test", None, "test-writer", "HEAD")
        claim_paths(self.store, 3, self.token, "writer", ["src/**"], "test")
        (target / "outside.txt").write_bytes(b"outside claimed scope")
        self.store.append_evidence(4, "test", "test", {"passed": True}, self.token)
        with self.assertRaisesRegex(HarnessError, "workspace verification"):
            transition_task(self.store, 5, self.token, "done", "test", "claimed success")
        self.assertEqual(self.store.read()[0]["phase"], "active")

    def test_terminal_tasks_do_not_create_workspaces(self):
        transition_task(self.store, 2, self.token, "cancelled", "test", "cancel")
        target = Path(self.temp.name) / "must-not-exist"
        with self.assertRaises(HarnessError):
            create_workspace(self.store, 3, self.token, "new", "writer", target, "test", None, "new-writer", "HEAD")
        self.assertFalse(target.exists())

    def test_reserved_events_and_secrets_are_rejected_before_mutation(self):
        for kind, payload in (("state-transition", {"target": "verifying"}), ("owner-release", {}),
                              ("workspace-create", {}), ("note", {"api_token": "secret"})):
            with self.subTest(kind=kind), self.assertRaises(HarnessError):
                self.store.append_evidence(2, "test", kind, payload, self.token)
        self.assertEqual(self.store.read()[0]["version"], 2)

    def test_old_registry_is_not_silently_adopted(self):
        old = self.context.common_dir / "agent-work-v1/tasks/old.json"
        old.parent.mkdir(parents=True); old.write_bytes(b'{"contract":"agent-work/v1"}')
        with self.assertRaisesRegex(HarnessError, "previous runtime"):
            init_task(self.context, "old", "new title")
        with self.assertRaises(HarnessError):
            TaskStore.for_existing(self.repo, "old")
        self.assertEqual(old.read_bytes(), b'{"contract":"agent-work/v1"}')
        self.assertFalse((self.repo / ".agents/work/old").exists())

    def test_evidence_file_returns_compact_receipt_and_full_is_explicit(self):
        path = self.repo / "result.json"
        path.write_text(json.dumps({"passed": True, "detail": "x" * 100000}), encoding="utf-8")
        result = self.cli("evidence", "task", "--kind", "test", "--payload-file", str(path), "--expect-version", "2")
        data = json.loads(result.stdout)
        self.assertLess(len(result.stdout), 300)
        self.assertNotIn("event", data)
        self.assertEqual(data["receipt"]["seq"], 3)
        full = self.cli("evidence", "task", "--kind", "test", "--payload-file", str(path), "--expect-version", "3", "--full")
        self.assertEqual(len(json.loads(full.stdout)["event"]["payload"]["detail"]), 100000)
        self.cli("evidence", "task", "--kind", "test", "--payload-file", str(path), "--payload", "{}", "--expect-version", "4", expected=2)
        self.assertEqual(self.store.read()[0]["version"], 4)

    def test_evidence_input_rejects_nonfinite_duplicates_and_oversized_files(self):
        path = self.repo / "evidence input.json"
        for raw in (b'{"passed":false,"passed":true}', b'{"nested":{"n":1,"n":2}}',
                    b'{"n":NaN}', b'{"n":Infinity}', b'\xff', b' ' * (1024 * 1024 + 1)):
            with self.subTest(raw=raw[:60]):
                path.write_bytes(raw)
                result = self.cli("evidence", "task", "--kind", "test", "--payload-file", str(path), "--expect-version", "2", expected=2)
                self.assertFalse(json.loads(result.stdout)["ok"])
                self.assertNotIn("Traceback", result.stderr)
        self.cli("evidence", "task", "--kind", "test", "--payload", '{"passed":false,"passed":true}', "--expect-version", "2", expected=2)
        self.cli("evidence", "task", "--kind", "test", "--payload-file", str(self.repo), "--expect-version", "2", expected=2)
        self.cli("evidence", "task", "--kind", "test", "--payload", '[]', "--expect-version", "2", expected=3)
        self.assertEqual(self.store.read()[0]["version"], 2)

    def test_terminal_workspace_cleanup_and_lease_release(self):
        target = Path(self.temp.name) / "cleanup-writer"
        self.cli("workspace", "create", "task", "writer", "--role", "writer", "--path", str(target), "--branch", "cleanup-writer", "--expect-version", "2")
        self.cli("transition", "task", "cancelled", "--expect-version", "3")
        self.cli("workspace", "remove", "task", "writer", "--expect-version", "4")
        self.assertFalse(target.exists())
        self.cli("owner", "release", "task", "--expect-version", "5")
        self.assertTrue(verify_task(self.store)["ok"])

    def test_failed_registration_preserves_concurrent_work(self):
        target = Path(self.temp.name) / "writer"
        def fail(*args, **kwargs):
            (target / "new-work.txt").write_bytes(b"another writer's work")
            raise HarnessError("simulated stale version")
        with mock.patch.object(self.store, "mutate", side_effect=fail):
            with self.assertRaisesRegex(HarnessError, "stale version"):
                create_workspace(self.store, 2, self.token, "writer", "writer", target, "test", None, "unregistered-writer", "HEAD")
        self.assertEqual((target / "new-work.txt").read_bytes(), b"another writer's work")
        self.assertEqual(self.store.read()[0]["version"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
