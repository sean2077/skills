#!/usr/bin/env python3
"""Behavioral regressions for versioned approval and shared state safety."""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_workflow_runtimes.py"
COMMON = ROOT / "scripts" / "workflow_runtime" / "common.py"
INTERVIEW = ROOT / "skills" / "deep-interview" / "scripts" / "interview_state.py"
EXPECTED_RESPONSE_SCHEMA = "agent-workflow-response/2"

ExpectedRc = Union[int, Sequence[int]]


class RuntimeTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.class_tmp = tempfile.TemporaryDirectory(prefix="agent workflow suite ")
        cls.template = Path(cls.class_tmp.name) / "template repo"
        cls.template.mkdir()
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "user.name", "Workflow Test"],
            ["git", "config", "user.email", "workflow@example.invalid"],
        ):
            subprocess.run(command, cwd=str(cls.template), check=True, timeout=30, env=env)
        (cls.template / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=str(cls.template), check=True, timeout=30, env=env)
        subprocess.run(
            ["git", "commit", "-qm", "seed"], cwd=str(cls.template), check=True, timeout=30, env=env
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.class_tmp.cleanup()

    def setUp(self) -> None:
        self.tmp_path = Path(tempfile.mkdtemp(prefix="case ", dir=self.class_tmp.name))
        self.repo = self.tmp_path / "repo with space 测试"
        shutil.copytree(self.template, self.repo, symlinks=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def git(self, *args: str, cwd: Optional[Path] = None) -> str:
        cp = subprocess.run(
            ["git", *args],
            cwd=str(cwd or self.repo),
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30,
            env=self.process_env(),
        )
        return cp.stdout.strip()

    @staticmethod
    def process_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        # Keep the default-session assertions deterministic even when the host
        # test runner exports a Claude/Codex session identifier.
        for name in ("AGENT_WORKFLOW_SESSION", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):
            env.pop(name, None)
        env["AGENT_WORKFLOW_SESSION"] = "current"
        if extra:
            env.update(extra)
        return env

    def run_cli(
        self,
        script: Path,
        *args: str,
        cwd: Optional[Path] = None,
        expected: ExpectedRc = 0,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], subprocess.CompletedProcess[str]]:
        if os.environ.get("WORKFLOW_TEST_TRACE") == "1":
            print("RUN", script.name, *args, file=sys.stderr, flush=True)
        cp = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(cwd or self.repo),
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=self.process_env(env),
        )
        expected_values = (expected,) if isinstance(expected, int) else tuple(expected)
        self.assertIn(
            cp.returncode,
            expected_values,
            msg="command=%r\nstdout=%s\nstderr=%s" % ([str(script), *args], cp.stdout, cp.stderr),
        )
        self.assertNotIn("Traceback (most recent call last)", cp.stdout + cp.stderr)
        raw = cp.stdout.strip() if cp.stdout.strip() else cp.stderr.strip()
        self.assertTrue(raw, msg="runtime emitted no JSON response")
        payload = json.loads(raw.splitlines()[-1])
        self.assertEqual(payload.get("schema"), EXPECTED_RESPONSE_SCHEMA)
        if os.environ.get("WORKFLOW_TEST_TRACE") == "1":
            print("DONE", script.name, cp.returncode, payload.get("error") or payload.get("stage"), file=sys.stderr, flush=True)
        return payload, cp

    def state_path(self, workflow: str, run_id: str = "default", session: str = "current") -> Path:
        return self.repo / ".agent-workflows" / workflow / session / (run_id + ".json")

    def test_generated_runtimes_are_current_and_compile(self) -> None:
        cp = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=self.process_env(),
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + cp.stderr)
        for script in (INTERVIEW,):
            source = script.read_text(encoding="utf-8")
            self.assertIn("Generated by scripts/generate_workflow_runtimes.py", source)
            compile(source, str(script), "exec")

    def test_read_only_discovery_has_no_filesystem_side_effects(self) -> None:
        for script in (INTERVIEW,):
            payload, _ = self.run_cli(script, "status", "--id", "missing", expected=3)
            self.assertEqual(payload["error"], "not_found")
            listing, _ = self.run_cli(script, "list")
            self.assertEqual(listing["count"], 0)
            doctor, _ = self.run_cli(script, "doctor", "--id", "missing", expected=6)
            self.assertFalse(doctor["ok"])
            unlocked, _ = self.run_cli(script, "unlock", "--id", "missing")
            self.assertFalse(unlocked["changed"])
        self.assertFalse((self.repo / ".agent-workflows").exists())

    def test_compact_output_and_bounded_history_avoid_context_growth(self) -> None:
        payload, cp = self.run_cli(INTERVIEW, "start", "--id", "compact", "--idea", "a" * 2000)
        outputs = [cp.stdout]
        revision = payload["revision"]
        spec = self.repo / "compact.md"
        # Repeated specification snapshots exercise the shared history/output bounds
        # without relying on a retired loop runtime.
        for index in range(6):
            spec.write_text("Acceptance revision %d.\n" % index, encoding="utf-8")
            payload, cp = self.run_cli(
                INTERVIEW, "crystallize", "--id", "compact",
                "--expected-revision", str(revision), "--spec-path", spec.name,
            )
            revision = payload["revision"]
            outputs.append(cp.stdout)
        for output in outputs:
            self.assertLess(len(output.encode("utf-8")), 1500)
            self.assertNotIn('"state"', output)
            self.assertNotIn('"history"', output)
        compact, short = self.run_cli(INTERVIEW, "status", "--id", "compact")
        full, long = self.run_cli(INTERVIEW, "status", "--id", "compact", "--full")
        self.assertNotIn("state", compact)
        self.assertEqual(len(full["state"]["initial_idea"]), 2000)
        self.assertEqual(len(full["state"]["history"]), 6)
        self.assertGreater(len(long.stdout), len(short.stdout) * 2)
        history, _ = self.run_cli(INTERVIEW, "history", "--id", "compact", "--tail", "2")
        self.assertEqual(history["tail"], 2)
        self.assertEqual([row["revision"] for row in history["history"]], [6, 7])
        invalid, _ = self.run_cli(INTERVIEW, "history", "--id", "compact", "--tail", "21", expected=2)
        self.assertEqual(invalid["error"], "invalid_tail")

    def test_nonstandard_json_numbers_are_rejected(self) -> None:
        for index, literal in enumerate(("NaN", "Infinity", "-Infinity")):
            with self.subTest(literal=literal):
                run_id = "nonfinite-%d" % index
                self.run_cli(INTERVIEW, "start", "--id", run_id, "--idea", "strict JSON")
                path = self.state_path("deep-interview", run_id)
                raw = path.read_text(encoding="utf-8").rstrip()
                self.assertTrue(raw.endswith("}"))
                path.write_text(raw[:-1] + ',\n  "unvalidated_probe": ' + literal + "\n}\n", encoding="utf-8")
                error, cp = self.run_cli(INTERVIEW, "status", "--id", run_id, "--full", expected=6)
                self.assertEqual(error["error"], "corrupt_state")
                self.assertNotIn(literal, cp.stdout + cp.stderr)

    def test_shared_json_output_and_atomic_write_boundaries(self) -> None:
        spec = importlib.util.spec_from_file_location("workflow_common_under_test", COMMON)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)

        with self.assertRaises(ValueError):
            common.emit({"value": float("nan")}, stream=io.StringIO())

        target = self.repo / "atomic-state.json"
        with mock.patch.object(common, "fsync_directory") as sync_directory:
            common.atomic_write(target, b"{}\n")
        self.assertEqual(target.read_bytes(), b"{}\n")
        sync_directory.assert_called_once_with(target.parent)

    def test_artifact_read_is_bounded_if_file_grows_after_stat(self):
        spec = importlib.util.spec_from_file_location("workflow_common_bounds", COMMON)
        common = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(common)
        path = self.repo / "growing-spec.txt"
        path.write_bytes(b"short")
        state = {"binding": {"worktree": str(self.repo)}}
        stream = io.BytesIO(b"x" * 100)
        with mock.patch.object(Path, "open", return_value=stream):
            with self.assertRaises(common.WorkflowError) as caught:
                common.resolve_artifact_path(state, str(path), label="spec", max_bytes=10)
        self.assertEqual(caught.exception.kind, "artifact_too_large")

    def test_doctor_and_unlock_handle_stale_and_live_locks(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "locked", "--idea", "lock safety")
        lock = self.state_path("deep-interview", "locked").with_suffix(".json.lock")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).replace(microsecond=0).isoformat()
        lock.write_text(json.dumps({"pid": 99999999, "created_at": old, "cwd": str(self.repo)}), encoding="utf-8")
        doctor, _ = self.run_cli(INTERVIEW, "doctor", "--id", "locked", expected=6)
        self.assertTrue(doctor["health"]["lock"]["exists"])
        removed, _ = self.run_cli(INTERVIEW, "unlock", "--id", "locked", "--stale-after", "0")
        self.assertTrue(removed["changed"])
        healthy, _ = self.run_cli(INTERVIEW, "doctor", "--id", "locked")
        self.assertTrue(healthy["ok"])

        lock.write_text(json.dumps({"pid": os.getpid(), "created_at": old, "cwd": str(self.repo)}), encoding="utf-8")
        live, _ = self.run_cli(INTERVIEW, "unlock", "--id", "locked", "--stale-after", "0", expected=5)
        self.assertEqual(live["error"], "lock_owner_alive")
        self.run_cli(INTERVIEW, "unlock", "--id", "locked", "--force")
        invalid, _ = self.run_cli(INTERVIEW, "unlock", "--id", "locked", "--stale-after", "-1", expected=2)
        self.assertEqual(invalid["error"], "invalid_bounds")

    def test_sessions_list_latest_and_non_git_root(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "same", "--session", "alpha", "--idea", "alpha goal")
        self.run_cli(INTERVIEW, "start", "--id", "same", "--session", "beta", "--idea", "beta goal")
        alpha, _ = self.run_cli(INTERVIEW, "status", "--session", "alpha", "--latest", "--full")
        beta, _ = self.run_cli(INTERVIEW, "status", "--session", "beta", "--latest", "--full")
        self.assertEqual(alpha["state"]["initial_idea"], "alpha goal")
        self.assertEqual(beta["state"]["initial_idea"], "beta goal")
        listing, _ = self.run_cli(INTERVIEW, "list", "--all-sessions")
        self.assertEqual(listing["count"], 2)
        self.assertEqual(listing["total"], 2)
        self.assertFalse(listing["truncated"])
        self.assertEqual({row["session"] for row in listing["runs"]}, {"alpha", "beta"})
        self.run_cli(INTERVIEW, "start", "--id", "third", "--session", "gamma", "--idea", "gamma goal")
        limited, _ = self.run_cli(INTERVIEW, "list", "--all-sessions", "--limit", "2")
        self.assertEqual(limited["count"], 2)
        self.assertEqual(limited["total"], 3)
        self.assertTrue(limited["truncated"])
        invalid_limit, _ = self.run_cli(INTERVIEW, "list", "--limit", "0", expected=2)
        self.assertEqual(invalid_limit["error"], "invalid_limit")
        reserved_id, _ = self.run_cli(INTERVIEW, "start", "--id", "con", "--idea", "portable", expected=2)
        self.assertEqual(reserved_id["error"], "invalid_id")
        reserved_session, _ = self.run_cli(
            INTERVIEW, "start", "--id", "portable", "--session", "nul", "--idea", "portable session"
        )
        self.assertTrue(reserved_session["session"].startswith("session-"))
        normalized, _ = self.run_cli(
            INTERVIEW,
            "start",
            "--id",
            "normalized",
            "--session",
            "Host Session With Spaces/Unicode 测试",
            "--idea",
            "normalize",
        )
        self.assertTrue(normalized["session"].startswith("session-"))

        root = self.tmp_path / "plain root 非git"
        child = root / "nested"
        child.mkdir(parents=True)
        started, _ = self.run_cli(INTERVIEW, "start", "--idea", "plain workspace", "--root", str(root), cwd=child)
        self.assertEqual(started["binding"]["ok"], True)
        full, _ = self.run_cli(INTERVIEW, "status", "--root", str(root), "--full", cwd=self.tmp_path)
        self.assertEqual(full["state"]["binding"]["vcs"], "none")
        self.assertEqual(Path(full["state"]["binding"]["worktree"]), root.resolve())
        self.assertTrue((root / ".agent-workflows" / "deep-interview" / "current" / "default.json").is_file())

    def test_worktree_binding_requires_explicit_rebind(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "owner", "--idea", "bind ownership")
        other = self.tmp_path / "other worktree 测试"
        self.git("worktree", "add", "-q", "-b", "workflow-other", str(other))
        spec = other / "spec.md"
        spec.write_text("Acceptance in the assigned worktree.\n", encoding="utf-8")
        status, _ = self.run_cli(INTERVIEW, "status", "--id", "owner", cwd=other)
        self.assertFalse(status["binding"]["ok"])
        conflict, _ = self.run_cli(
            INTERVIEW, "crystallize", "--id", "owner", "--expected-revision", "1",
            "--spec-path", spec.name, cwd=other, expected=5,
        )
        self.assertEqual(conflict["error"], "binding_mismatch")
        unchanged, _ = self.run_cli(INTERVIEW, "status", "--id", "owner")
        self.assertEqual(unchanged["revision"], 1)
        rebound, _ = self.run_cli(
            INTERVIEW, "rebind", "--id", "owner", "--expected-revision", "1", cwd=other,
        )
        self.assertEqual(rebound["revision"], 2)
        snapshot, _ = self.run_cli(
            INTERVIEW, "crystallize", "--id", "owner", "--expected-revision", "2",
            "--spec-path", spec.name, cwd=other,
        )
        self.assertEqual(snapshot["stage"], "crystallized")
        back_status, _ = self.run_cli(INTERVIEW, "status", "--id", "owner", cwd=self.repo)
        self.assertFalse(back_status["binding"]["ok"])

    def test_concurrent_mutations_have_one_winner(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "race", "--idea", "serialize")
        spec = self.repo / "race.md"
        spec.write_text("Only one snapshot may own a revision.\n", encoding="utf-8")
        command = [
            sys.executable, str(INTERVIEW), "crystallize", "--id", "race",
            "--expected-revision", "1", "--spec-path", spec.name,
        ]
        processes = [
            subprocess.Popen(
                command, cwd=str(self.repo), text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.process_env(),
            )
            for _ in range(2)
        ]
        results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        self.assertEqual(sorted(result[2] for result in results), [0, 5])
        loser = next(result for result in results if result[2] == 5)
        loser_payload = json.loads((loser[0].strip() or loser[1].strip()).splitlines()[-1])
        self.assertIn(loser_payload["error"], {"locked", "revision_conflict"})
        status, _ = self.run_cli(INTERVIEW, "status", "--id", "race", "--full")
        self.assertEqual(status["revision"], 2)
        self.assertEqual(len(status["state"]["history"]), 1)
        self.assertFalse(self.state_path("deep-interview", "race").with_suffix(".json.lock").exists())

    def start_spec(self, content="The API preserves request order.", run_id="spec"):
        self.run_cli(INTERVIEW, "start", "--id", run_id, "--idea", "ordered API")
        path = self.repo / (run_id + ".md")
        path.write_bytes(content.encode("utf-8"))
        snapshot, _ = self.run_cli(INTERVIEW, "crystallize", "--id", run_id,
                                   "--expected-revision", "1", "--spec-path", path.name)
        self.assertEqual(snapshot["stage"], "crystallized")
        return path

    def test_spec_approval_and_recrystallization(self):
        path = self.start_spec()
        missing, _ = self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "2", expected=5)
        self.assertEqual(missing["error"], "approval_required")
        approved, _ = self.run_cli(INTERVIEW, "approve", "--id", "spec", "--expected-revision", "2", "--evidence", "User approved the presented spec")
        self.assertEqual(approved["stage"], "approved")
        path.write_bytes(path.read_bytes() + b" Additional acceptance.\n")
        changed, _ = self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "3", expected=5)
        self.assertEqual(changed["error"], "spec_changed")
        self.run_cli(INTERVIEW, "crystallize", "--id", "spec", "--expected-revision", "3", "--spec-path", path.name)
        pending, _ = self.run_cli(INTERVIEW, "status", "--id", "spec", "--full")
        self.assertIsNone(pending["state"]["approval"])
        self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "4", expected=5)
        self.run_cli(INTERVIEW, "approve", "--id", "spec", "--expected-revision", "4", "--evidence", "ok, updated spec")
        complete, _ = self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "5")
        self.assertTrue(complete["terminal"])
        self.assertEqual(complete["stage"], "completed")
        self.run_cli(INTERVIEW, "crystallize", "--id", "spec", "--expected-revision", "6", "--spec-path", path.name, expected=4)
        history, _ = self.run_cli(INTERVIEW, "history", "--id", "spec", "--tail", "2")
        self.assertEqual([row["phase"] for row in history["history"]], ["approved", "completed"])

    def test_approval_requires_unchanged_original_bytes_including_eol(self):
        for stage in ("approve", "complete"):
            with self.subTest(stage=stage):
                path = self.start_spec("规格：保持顺序。\n", stage)
                revision = 2
                if stage == "complete":
                    self.run_cli(INTERVIEW, "approve", "--id", stage, "--expected-revision", "2", "--evidence", "approve LF artifact")
                    revision = 3
                path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
                args = ("--evidence", "approve LF artifact") if stage == "approve" else ()
                changed, _ = self.run_cli(INTERVIEW, stage, "--id", stage, "--expected-revision", str(revision), *args, expected=5)
                self.assertEqual(changed["error"], "spec_changed")
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
                self.run_cli(INTERVIEW, stage, "--id", stage, "--expected-revision", str(revision), *args)

    def test_spec_format_is_project_owned_and_no_scoring_commands(self):
        self.start_spec("A plain-text spec without prescribed headings or a score.")
        self.run_cli(INTERVIEW, "approve", "--id", "spec", "--expected-revision", "2", "--evidence", "   ", expected=2)
        for command in ("score", "topology", "gate", "waive"):
            self.run_cli(INTERVIEW, command, expected=2)
        state, _ = self.run_cli(INTERVIEW, "status", "--id", "spec", "--full")
        self.assertEqual(state["revision"], 2)
        self.assertNotIn("rounds", state["state"])
        self.assertNotIn("threshold", state["state"])
        self.run_cli(INTERVIEW, "start", "--idea", "old flags", "--depth", "deep", expected=2)
        self.assertFalse(self.state_path("deep-interview").exists())

    def test_spec_paths_and_empty_or_non_utf8_files_are_rejected(self):
        self.run_cli(INTERVIEW, "start", "--idea", "safe artifact")
        outside = self.tmp_path / "outside.md"; outside.write_bytes(b"outside")
        for name, data in (("empty.md", b"  "), ("binary.md", b"\xff"), ("large.md", b"x" * (1024 * 1024 + 1))):
            path = self.repo / name; path.write_bytes(data)
        for path in (outside, self.repo, self.repo / "missing.md", self.repo / "empty.md", self.repo / "binary.md", self.repo / "large.md"):
            with self.subTest(path=path.name):
                self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "1", "--spec-path", str(path), expected=2)
        state, _ = self.run_cli(INTERVIEW, "status")
        self.assertEqual(state["revision"], 1)

    def test_symlinked_state_and_artifact_paths_are_rejected(self):
        outside = self.tmp_path / "outside"; outside.mkdir()
        root = self.repo / ".agent-workflows"
        try:
            root.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("platform lacks symlink capability")
        self.run_cli(INTERVIEW, "start", "--idea", "unsafe state", expected=6)
        self.assertFalse(list(outside.iterdir()))
        root.unlink()
        self.run_cli(INTERVIEW, "start", "--idea", "safe artifact")
        original = self.repo / "original.md"; original.write_bytes(b"spec")
        link = self.repo / "link.md"; link.symlink_to(original)
        self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "1", "--spec-path", str(link), expected=2)
        dangling = self.repo / "dangling.md"; dangling.symlink_to(self.repo / "missing.md")
        self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "1", "--spec-path", str(dangling), expected=2)
        state = self.state_path("deep-interview")
        saved = self.repo / "state-copy.json"; saved.write_bytes(state.read_bytes())
        state.unlink(); state.symlink_to(saved)
        self.run_cli(INTERVIEW, "status", expected=6)

    def test_worktree_root_alias_accepts_artifact_but_not_nested_symlinks(self):
        alias = self.tmp_path / "alias"
        try:
            alias.symlink_to(self.repo, target_is_directory=True)
        except OSError:
            self.skipTest("platform lacks symlink capability")
        self.run_cli(INTERVIEW, "start", "--idea", "root alias")
        (self.repo / "spec.md").write_bytes(b"valid spec")
        self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "1", "--spec-path", str(alias / "spec.md"))
        nested = self.repo / "nested"; nested.symlink_to(self.repo, target_is_directory=True)
        self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "2", "--spec-path", str(nested / "spec.md"), expected=2)

    def test_corrupt_state_and_monotonic_backup_recovery(self):
        path = self.start_spec()
        state_path = self.state_path("deep-interview", "spec")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["revision"] = 9; state["spec_sha256"] = "bad"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        self.run_cli(INTERVIEW, "status", "--id", "spec", expected=6)
        doctor, _ = self.run_cli(INTERVIEW, "doctor", "--id", "spec", expected=6)
        self.assertTrue(doctor["health"]["backup"]["valid"])
        recovered, _ = self.run_cli(INTERVIEW, "recover", "--id", "spec")
        self.assertEqual(recovered["revision"], 10)
        self.assertEqual(recovered["stage"], "drafting")
        self.run_cli(INTERVIEW, "crystallize", "--id", "spec", "--expected-revision", "10", "--spec-path", path.name)
        rolled, _ = self.run_cli(INTERVIEW, "recover", "--id", "spec", "--force")
        self.assertEqual(rolled["revision"], 12)
        self.assertEqual(rolled["stage"], "drafting")

    def test_old_interview_schema_is_preserved_not_reinterpreted(self):
        self.run_cli(INTERVIEW, "start", "--idea", "old run")
        path = self.state_path("deep-interview")
        state = json.loads(path.read_text(encoding="utf-8"))
        state["schema"] = "agent-workflow/deep-interview/2"
        original = json.dumps(state).encode("utf-8"); path.write_bytes(original)
        self.run_cli(INTERVIEW, "status", expected=6)
        self.run_cli(INTERVIEW, "start", "--idea", "overwrite attempt", expected=5)
        self.run_cli(INTERVIEW, "crystallize", "--expected-revision", "1", "--spec-path", "spec.md", expected=6)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(path.with_suffix(".json.bak").exists())

    def test_approval_digest_state_corruption_and_abort(self):
        self.start_spec()
        self.run_cli(INTERVIEW, "approve", "--id", "spec", "--expected-revision", "2", "--evidence", "approved")
        path = self.state_path("deep-interview", "spec"); original = path.read_bytes()
        state = json.loads(original); state["approval"]["spec_sha256"] = "0" * 64
        path.write_text(json.dumps(state), encoding="utf-8")
        self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "3", expected=6)
        path.write_bytes(original)
        aborted, _ = self.run_cli(INTERVIEW, "abort", "--id", "spec", "--expected-revision", "3", "--reason", "User cancelled")
        self.assertEqual(aborted["stage"], "aborted")
        self.run_cli(INTERVIEW, "complete", "--id", "spec", "--expected-revision", "4", expected=4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
