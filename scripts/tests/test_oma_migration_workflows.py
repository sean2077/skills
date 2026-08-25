#!/usr/bin/env python3
"""Behavioral and adversarial regressions for the migrated workflow runtimes."""

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
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Union
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "generate_workflow_runtimes.py"
COMMON = ROOT / "scripts" / "workflow_runtime" / "common.py"
AUTO = ROOT / "skills" / "autopilot" / "scripts" / "autopilot_state.py"
INTERVIEW = ROOT / "skills" / "deep-interview" / "scripts" / "interview_state.py"
RALPH = ROOT / "skills" / "ralph" / "scripts" / "ralph_state.py"
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

    def write_json(self, name: str, payload: Dict[str, Any]) -> Path:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def state_path(self, workflow: str, run_id: str = "default", session: str = "current") -> Path:
        return self.repo / ".agent-workflows" / workflow / session / (run_id + ".json")

    def topology_file(
        self,
        name: str,
        components: Sequence[Dict[str, Any]],
        deferrals: Optional[Sequence[Dict[str, str]]] = None,
    ) -> Path:
        return self.write_json(
            name,
            {
                "schema": "agent-interview-topology/2",
                "components": list(components),
                "deferrals": list(deferrals or []),
            },
        )

    def round_file(
        self,
        name: str,
        round_value: int,
        scores: Dict[str, Dict[str, float]],
        *,
        answer: str = "[from-user] observed answer",
        pressure_pass: bool = False,
        challenge: Optional[str] = None,
        entities: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Path:
        payload: Dict[str, Any] = {
            "schema": "agent-interview-round/2",
            "round": round_value,
            "question": "Decision-bearing question %d?" % round_value,
            "answer": answer,
            "pressure_pass": pressure_pass,
            "component_scores": scores,
            "ontology": {"entities": list(entities or [])},
        }
        if challenge is not None:
            payload["challenge_mode_used"] = challenge
        return self.write_json(name, payload)

    @staticmethod
    def active_component(component_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": component_id,
            "name": name or component_id.upper(),
            "description": "%s boundary" % component_id,
            "status": "active",
            "evidence": ["[from-user] requested"],
        }

    def complete_one_round_interview(self, run_id: str = "spec") -> int:
        self.run_cli(INTERVIEW, "start", "--id", run_id, "--idea", "ordered API")
        topology = self.topology_file("%s-topology.json" % run_id, [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            run_id,
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        score = self.round_file(
            "%s-round.json" % run_id,
            1,
            {"api": {"goal": 1.0, "constraints": 1.0, "criteria": 1.0}},
            pressure_pass=True,
            entities=[{"name": "Request", "type": "entity", "fields": ["id"], "relationships": []}],
        )
        self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            run_id,
            "--expected-revision",
            "2",
            "--input",
            str(score),
        )
        return 3

    @staticmethod
    def valid_spec(*, remaining_gaps: bool = False) -> str:
        suffix = "\n# Remaining Gaps\nLatency under cross-region failover remains to be measured.\n" if remaining_gaps else ""
        return (
            "# Status\nPending approval\n\n"
            "# Goal\nPreserve request ordering.\n\n"
            "# Topology\nOne API request boundary.\n\n"
            "# Constraints\nNo breaking response change.\n\n"
            "# Non-goals\nNo UI redesign.\n\n"
            "# Decision Boundaries\nOwner: API maintainer. Revisit trigger: protocol changes.\n\n"
            "# Acceptance Criteria\nConcurrent requests retain their documented order.\n\n"
            "# Ontology\nRequest means one ordered API unit.\n\n"
            "# Open Assumptions\nThe transport preserves connection identity.\n"
            + suffix
        )

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
        for script in (AUTO, INTERVIEW, RALPH):
            source = script.read_text(encoding="utf-8")
            self.assertIn("Generated by scripts/generate_workflow_runtimes.py", source)
            compile(source, str(script), "exec")

    def test_read_only_discovery_has_no_filesystem_side_effects(self) -> None:
        for script in (AUTO, INTERVIEW, RALPH):
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
        outputs = []
        payload, cp = self.run_cli(
            RALPH,
            "start",
            "--id",
            "compact",
            "--goal",
            "bounded context",
            "--max-rounds",
            "8",
            "--stall-window",
            "8",
        )
        outputs.append(cp.stdout)
        revision = payload["revision"]
        for round_value in range(1, 7):
            payload, cp = self.run_cli(
                RALPH,
                "next",
                "--id",
                "compact",
                "--expected-revision",
                str(revision),
            )
            revision = payload["revision"]
            outputs.append(cp.stdout)
            payload, cp = self.run_cli(
                RALPH,
                "check",
                "--id",
                "compact",
                "--expected-revision",
                str(revision),
                "--round",
                str(round_value),
                "--verifier-exit",
                "1",
                "--signature",
                "different-%d" % round_value,
                "--note",
                "n" * 1800,
            )
            revision = payload["revision"]
            outputs.append(cp.stdout)
        for output in outputs:
            self.assertLess(len(output.encode("utf-8")), 1400)
            self.assertNotIn('"state"', output)
            self.assertNotIn('"history"', output)
        compact, compact_cp = self.run_cli(RALPH, "status", "--id", "compact")
        full, full_cp = self.run_cli(RALPH, "status", "--id", "compact", "--full")
        self.assertNotIn("state", compact)
        self.assertIn("state", full)
        self.assertGreater(len(full_cp.stdout), len(compact_cp.stdout) * 8)
        history, _ = self.run_cli(RALPH, "history", "--id", "compact", "--tail", "2")
        self.assertEqual(history["tail"], 2)
        self.assertEqual([row["round"] for row in history["history"]], [5, 6])
        invalid, _ = self.run_cli(RALPH, "history", "--id", "compact", "--tail", "21", expected=2)
        self.assertEqual(invalid["error"], "invalid_tail")

        self.run_cli(INTERVIEW, "start", "--id", "long-answer", "--idea", "compact interview")
        topology = self.topology_file("long-topology.json", [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "long-answer",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        round_input = self.round_file(
            "long-round.json",
            1,
            {"api": {"goal": 0.2, "constraints": 0.2, "criteria": 0.2}},
            answer="[from-user] " + ("evidence " * 650),
        )
        _, compact_round = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "long-answer",
            "--expected-revision",
            "2",
            "--input",
            str(round_input),
        )
        _, full_round = self.run_cli(INTERVIEW, "status", "--id", "long-answer", "--full")
        self.assertLess(len(compact_round.stdout.encode("utf-8")), 1500)
        self.assertGreater(len(full_round.stdout), len(compact_round.stdout) * 4)

    def test_corrupt_state_is_structured_and_backup_recovery_is_monotonic(self) -> None:
        self.run_cli(AUTO, "start", "--id", "recover", "--goal", "recover safely")
        self.run_cli(AUTO, "advance", "--id", "recover", "--expected-revision", "1", "--to", "plan")
        path = self.state_path("autopilot", "recover")
        path.write_text(
            json.dumps(
                {
                    "schema": "agent-workflow/autopilot/2",
                    "workflow": "autopilot",
                    "id": "recover",
                    "session": "current",
                    "revision": 9,
                }
            ),
            encoding="utf-8",
        )
        error, cp = self.run_cli(AUTO, "status", "--id", "recover", expected=6)
        self.assertEqual(error["error"], "corrupt_state")
        self.assertNotIn("KeyError", cp.stderr)
        doctor, _ = self.run_cli(AUTO, "doctor", "--id", "recover", expected=6)
        self.assertTrue(doctor["health"]["backup"]["valid"])
        recovered, _ = self.run_cli(AUTO, "recover", "--id", "recover")
        self.assertEqual(recovered["revision"], 10)
        self.assertEqual(recovered["stage"], "clarify")
        self.run_cli(AUTO, "advance", "--id", "recover", "--expected-revision", "10", "--to", "plan")
        rolled_back, _ = self.run_cli(AUTO, "recover", "--id", "recover", "--force")
        self.assertEqual(rolled_back["revision"], 12)
        self.assertEqual(rolled_back["stage"], "clarify")

        self.run_cli(RALPH, "start", "--id", "derived", "--goal", "validate derived state")
        self.run_cli(RALPH, "next", "--id", "derived", "--expected-revision", "1")
        ralph_path = self.state_path("ralph", "derived")
        ralph_state = json.loads(ralph_path.read_text(encoding="utf-8"))
        ralph_state["round"] = 0
        ralph_path.write_text(json.dumps(ralph_state), encoding="utf-8")
        derived_error, _ = self.run_cli(RALPH, "status", "--id", "derived", expected=6)
        self.assertEqual(derived_error["error"], "corrupt_state")

        self.complete_one_round_interview("formula-corrupt")
        interview_path = self.state_path("deep-interview", "formula-corrupt")
        interview_state = json.loads(interview_path.read_text(encoding="utf-8"))
        interview_state["rounds"][0]["dimension_totals"]["goal"] = 0.5
        interview_path.write_text(json.dumps(interview_state), encoding="utf-8")
        formula_error, _ = self.run_cli(INTERVIEW, "status", "--id", "formula-corrupt", expected=6)
        self.assertEqual(formula_error["error"], "corrupt_state")

    def test_nonstandard_json_numbers_are_rejected(self) -> None:
        for index, literal in enumerate(("NaN", "Infinity", "-Infinity")):
            with self.subTest(literal=literal):
                run_id = "nonfinite-%d" % index
                self.run_cli(AUTO, "start", "--id", run_id, "--goal", "strict JSON")
                path = self.state_path("autopilot", run_id)
                raw = path.read_text(encoding="utf-8").rstrip()
                self.assertTrue(raw.endswith("}"))
                path.write_text(raw[:-1] + ',\n  "unvalidated_probe": ' + literal + "\n}\n", encoding="utf-8")
                error, cp = self.run_cli(AUTO, "status", "--id", run_id, "--full", expected=6)
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

    def test_doctor_and_unlock_handle_stale_and_live_locks(self) -> None:
        self.run_cli(RALPH, "start", "--id", "locked", "--goal", "lock safety")
        lock = self.state_path("ralph", "locked").with_suffix(".json.lock")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).replace(microsecond=0).isoformat()
        lock.write_text(json.dumps({"pid": 99999999, "created_at": old, "cwd": str(self.repo)}), encoding="utf-8")
        doctor, _ = self.run_cli(RALPH, "doctor", "--id", "locked", expected=6)
        self.assertTrue(doctor["health"]["lock"]["exists"])
        removed, _ = self.run_cli(RALPH, "unlock", "--id", "locked", "--stale-after", "0")
        self.assertTrue(removed["changed"])
        healthy, _ = self.run_cli(RALPH, "doctor", "--id", "locked")
        self.assertTrue(healthy["ok"])

        lock.write_text(json.dumps({"pid": os.getpid(), "created_at": old, "cwd": str(self.repo)}), encoding="utf-8")
        live, _ = self.run_cli(RALPH, "unlock", "--id", "locked", "--stale-after", "0", expected=5)
        self.assertEqual(live["error"], "lock_owner_alive")
        self.run_cli(RALPH, "unlock", "--id", "locked", "--force")
        invalid, _ = self.run_cli(RALPH, "unlock", "--id", "locked", "--stale-after", "-1", expected=2)
        self.assertEqual(invalid["error"], "invalid_bounds")

    def test_sessions_list_latest_and_non_git_root(self) -> None:
        self.run_cli(RALPH, "start", "--id", "same", "--session", "alpha", "--goal", "alpha goal")
        self.run_cli(RALPH, "start", "--id", "same", "--session", "beta", "--goal", "beta goal")
        alpha, _ = self.run_cli(RALPH, "status", "--session", "alpha", "--latest", "--full")
        beta, _ = self.run_cli(RALPH, "status", "--session", "beta", "--latest", "--full")
        self.assertEqual(alpha["state"]["goal"], "alpha goal")
        self.assertEqual(beta["state"]["goal"], "beta goal")
        listing, _ = self.run_cli(RALPH, "list", "--all-sessions")
        self.assertEqual(listing["count"], 2)
        self.assertEqual(listing["total"], 2)
        self.assertFalse(listing["truncated"])
        self.assertEqual({row["session"] for row in listing["runs"]}, {"alpha", "beta"})
        self.run_cli(RALPH, "start", "--id", "third", "--session", "gamma", "--goal", "gamma goal")
        limited, _ = self.run_cli(RALPH, "list", "--all-sessions", "--limit", "2")
        self.assertEqual(limited["count"], 2)
        self.assertEqual(limited["total"], 3)
        self.assertTrue(limited["truncated"])
        invalid_limit, _ = self.run_cli(RALPH, "list", "--limit", "0", expected=2)
        self.assertEqual(invalid_limit["error"], "invalid_limit")
        reserved_id, _ = self.run_cli(RALPH, "start", "--id", "con", "--goal", "portable", expected=2)
        self.assertEqual(reserved_id["error"], "invalid_id")
        reserved_session, _ = self.run_cli(
            RALPH, "start", "--id", "portable", "--session", "nul", "--goal", "portable session"
        )
        self.assertTrue(reserved_session["session"].startswith("session-"))
        normalized, _ = self.run_cli(
            RALPH,
            "start",
            "--id",
            "normalized",
            "--session",
            "Host Session With Spaces/Unicode 测试",
            "--goal",
            "normalize",
        )
        self.assertTrue(normalized["session"].startswith("session-"))

        root = self.tmp_path / "plain root 非git"
        child = root / "nested"
        child.mkdir(parents=True)
        started, _ = self.run_cli(AUTO, "start", "--goal", "plain workspace", "--root", str(root), cwd=child)
        self.assertEqual(started["binding"]["ok"], True)
        full, _ = self.run_cli(AUTO, "status", "--root", str(root), "--full", cwd=self.tmp_path)
        self.assertEqual(full["state"]["binding"]["vcs"], "none")
        self.assertEqual(Path(full["state"]["binding"]["worktree"]), root.resolve())
        self.assertTrue((root / ".agent-workflows" / "autopilot" / "current" / "default.json").is_file())

    def test_worktree_binding_requires_explicit_rebind(self) -> None:
        self.run_cli(RALPH, "start", "--id", "owner", "--goal", "bind ownership")
        other = self.tmp_path / "other worktree 测试"
        self.git("worktree", "add", "-q", "-b", "workflow-other", str(other))
        status, _ = self.run_cli(RALPH, "status", "--id", "owner", cwd=other)
        self.assertFalse(status["binding"]["ok"])
        conflict, _ = self.run_cli(
            RALPH,
            "next",
            "--id",
            "owner",
            "--expected-revision",
            "1",
            cwd=other,
            expected=5,
        )
        self.assertEqual(conflict["error"], "binding_mismatch")
        rebound, _ = self.run_cli(
            RALPH,
            "rebind",
            "--id",
            "owner",
            "--expected-revision",
            "1",
            cwd=other,
        )
        self.assertEqual(rebound["revision"], 2)
        opened, _ = self.run_cli(
            RALPH,
            "next",
            "--id",
            "owner",
            "--expected-revision",
            "2",
            cwd=other,
        )
        self.assertEqual(opened["stage"], "round_pending")
        back_status, _ = self.run_cli(RALPH, "status", "--id", "owner", cwd=self.repo)
        self.assertFalse(back_status["binding"]["ok"])

    def test_concurrent_mutations_have_one_winner(self) -> None:
        self.run_cli(RALPH, "start", "--id", "race", "--goal", "serialize")
        command = [
            sys.executable,
            str(RALPH),
            "next",
            "--id",
            "race",
            "--expected-revision",
            "1",
        ]
        processes = [
            subprocess.Popen(
                command,
                cwd=str(self.repo),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.process_env(),
            )
            for _ in range(2)
        ]
        results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        self.assertEqual(sorted(result[2] for result in results), [0, 5])
        loser = next(result for result in results if result[2] == 5)
        loser_payload = json.loads((loser[0].strip() or loser[1].strip()).splitlines()[-1])
        self.assertIn(loser_payload["error"], {"locked", "revision_conflict"})
        status, _ = self.run_cli(RALPH, "status", "--id", "race")
        self.assertEqual(status["revision"], 2)
        self.assertFalse(self.state_path("ralph", "race").with_suffix(".json.lock").exists())

    def test_autopilot_validates_plan_paths_and_terminal_policy(self) -> None:
        self.run_cli(AUTO, "start", "--id", "ship", "--goal", "ship safely")
        self.run_cli(AUTO, "advance", "--id", "ship", "--expected-revision", "1", "--to", "plan")
        missing, _ = self.run_cli(
            AUTO,
            "plan",
            "--id",
            "ship",
            "--expected-revision",
            "2",
            "--path",
            "missing-plan.md",
            expected=2,
        )
        self.assertEqual(missing["error"], "invalid_artifact")
        outside = self.tmp_path / "outside-plan.md"
        outside.write_text("outside\n", encoding="utf-8")
        escaped, _ = self.run_cli(
            AUTO,
            "plan",
            "--id",
            "ship",
            "--expected-revision",
            "2",
            "--path",
            str(outside),
            expected=2,
        )
        self.assertEqual(escaped["error"], "unsafe_artifact")
        plan = self.repo / "计划 file.md"
        plan.write_text("# Plan\nOne bounded slice.\n", encoding="utf-8")
        self.run_cli(AUTO, "plan", "--id", "ship", "--expected-revision", "2", "--path", plan.name)
        self.run_cli(AUTO, "advance", "--id", "ship", "--expected-revision", "3", "--to", "verify")
        first, _ = self.run_cli(
            AUTO,
            "verify",
            "--id",
            "ship",
            "--expected-revision",
            "4",
            "--exit-code",
            "1",
            "--summary",
            "first failure",
        )
        self.assertEqual(first["stage"], "implement")
        self.run_cli(AUTO, "advance", "--id", "ship", "--expected-revision", "5", "--to", "verify")
        blocked, _ = self.run_cli(
            AUTO,
            "verify",
            "--id",
            "ship",
            "--expected-revision",
            "6",
            "--exit-code",
            "1",
            "--summary",
            "second failure",
        )
        self.assertEqual(blocked["status"], "blocked")

        terminal, _ = self.run_cli(AUTO, "finish", "--id", "ship", "--expected-revision", "7", expected=4)
        self.assertEqual(terminal["error"], "terminal")

        self.run_cli(AUTO, "start", "--id", "green", "--goal", "verified path")
        self.run_cli(AUTO, "advance", "--id", "green", "--expected-revision", "1", "--to", "plan")
        self.run_cli(AUTO, "plan", "--id", "green", "--expected-revision", "2", "--path", plan.name)
        self.run_cli(AUTO, "advance", "--id", "green", "--expected-revision", "3", "--to", "verify")
        verified, _ = self.run_cli(
            AUTO,
            "verify",
            "--id",
            "green",
            "--expected-revision",
            "4",
            "--exit-code",
            "0",
            "--summary",
            "all checks passed",
        )
        self.assertEqual(verified["stage"], "deliver")
        done, _ = self.run_cli(AUTO, "finish", "--id", "green", "--expected-revision", "5")
        self.assertEqual(done["status"], "done")

    def test_worktree_root_alias_accepts_bound_input_and_artifact_files(self) -> None:
        alias = self.tmp_path / "repo-alias"
        try:
            alias.symlink_to(self.repo, target_is_directory=True)
        except OSError as exc:
            self.skipTest("worktree-root symlink unavailable: %s" % exc)

        self.run_cli(AUTO, "start", "--id", "alias-plan", "--goal", "accept a root alias")
        self.run_cli(AUTO, "advance", "--id", "alias-plan", "--expected-revision", "1", "--to", "plan")
        plan = self.repo / "alias-plan.md"
        plan.write_text("# Plan\nUse the bound worktree.\n", encoding="utf-8")
        descendant_alias = self.repo / "descendant-alias"
        descendant_alias.symlink_to(self.repo, target_is_directory=True)
        rejected, _ = self.run_cli(
            AUTO,
            "plan",
            "--id",
            "alias-plan",
            "--expected-revision",
            "2",
            "--path",
            str(descendant_alias / plan.name),
            expected=2,
        )
        self.assertEqual(rejected["error"], "unsafe_artifact")
        planned, _ = self.run_cli(
            AUTO,
            "plan",
            "--id",
            "alias-plan",
            "--expected-revision",
            "2",
            "--path",
            str(alias / plan.name),
        )
        self.assertEqual(planned["metrics"]["plan_path"], plan.name)

        self.run_cli(INTERVIEW, "start", "--id", "alias-input", "--idea", "accept a root alias")
        topology = self.topology_file("alias-topology.json", [self.active_component("api")])
        accepted, _ = self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "alias-input",
            "--expected-revision",
            "1",
            "--input",
            str(alias / topology.name),
        )
        self.assertEqual(accepted["stage"], "interviewing")

    def test_ralph_pass_stall_plateau_exhaustion_and_pending_round(self) -> None:
        self.run_cli(RALPH, "start", "--id", "pass", "--goal", "green", "--max-rounds", "2")
        self.run_cli(RALPH, "next", "--id", "pass", "--expected-revision", "1")
        pending, _ = self.run_cli(RALPH, "next", "--id", "pass", "--expected-revision", "2", expected=5)
        self.assertEqual(pending["error"], "round_pending")
        passed, _ = self.run_cli(
            RALPH,
            "check",
            "--id",
            "pass",
            "--expected-revision",
            "2",
            "--round",
            "1",
            "--verifier-exit",
            "0",
        )
        self.assertEqual(passed["status"], "passed")

        self.run_cli(
            RALPH,
            "start",
            "--id",
            "stall",
            "--goal",
            "fix",
            "--max-rounds",
            "5",
            "--stall-window",
            "2",
        )
        revision = 1
        for round_value in (1, 2):
            opened, _ = self.run_cli(
                RALPH, "next", "--id", "stall", "--expected-revision", str(revision)
            )
            revision = opened["revision"]
            stalled, _ = self.run_cli(
                RALPH,
                "check",
                "--id",
                "stall",
                "--expected-revision",
                str(revision),
                "--round",
                str(round_value),
                "--verifier-exit",
                "1",
                "--signature",
                "same-root-cause",
            )
            revision = stalled["revision"]
        self.assertEqual(stalled["status"], "stalled")

        self.run_cli(
            RALPH,
            "start",
            "--id",
            "plateau",
            "--goal",
            "score",
            "--max-rounds",
            "5",
            "--keep-policy",
            "score-improvement",
            "--plateau-window",
            "2",
        )
        revision = 1
        for round_value, score in ((1, 0.5), (2, 0.5), (3, 0.5)):
            opened, _ = self.run_cli(
                RALPH, "next", "--id", "plateau", "--expected-revision", str(revision)
            )
            revision = opened["revision"]
            plateau, _ = self.run_cli(
                RALPH,
                "check",
                "--id",
                "plateau",
                "--expected-revision",
                str(revision),
                "--round",
                str(round_value),
                "--verifier-exit",
                "1",
                "--signature",
                "score-%d" % round_value,
                "--score",
                str(score),
            )
            revision = plateau["revision"]
        self.assertEqual(plateau["status"], "plateaued")
        self.assertEqual(plateau["metrics"]["best_round"], 1)

        self.run_cli(RALPH, "start", "--id", "budget", "--goal", "one", "--max-rounds", "1")
        self.run_cli(RALPH, "next", "--id", "budget", "--expected-revision", "1")
        exhausted, _ = self.run_cli(
            RALPH,
            "check",
            "--id",
            "budget",
            "--expected-revision",
            "2",
            "--round",
            "1",
            "--verifier-exit",
            "1",
            "--signature",
            "still failing",
        )
        self.assertEqual(exhausted["status"], "exhausted")

    def test_deep_interview_brownfield_formula_topology_and_rotation(self) -> None:
        self.run_cli(
            INTERVIEW,
            "start",
            "--id",
            "formula",
            "--idea",
            "brownfield API",
            "--type",
            "brownfield",
            "--threshold",
            "0.1",
        )
        topology = self.topology_file(
            "formula-topology.json",
            [
                self.active_component("a", "API"),
                self.active_component("b", "Storage"),
                {
                    "id": "ui",
                    "name": "UI",
                    "description": "deferred interface",
                    "status": "deferred",
                    "evidence": ["[from-user] later"],
                },
            ],
            [{"component_id": "ui", "reason": "outside this decision"}],
        )
        locked, _ = self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "formula",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        self.assertEqual(locked["metrics"]["weakest"]["component_id"], "a")
        score = self.round_file(
            "formula-round.json",
            1,
            {
                "a": {"goal": 0.8, "constraints": 0.7, "criteria": 0.9, "context": 0.6},
                "b": {"goal": 0.5, "constraints": 0.9, "criteria": 0.4, "context": 0.8},
            },
            answer="[from-code] request and storage boundaries inspected",
            entities=[{"name": "Request", "type": "entity", "fields": ["id"], "relationships": ["stored by Storage"]}],
        )
        scored, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "formula",
            "--expected-revision",
            "2",
            "--input",
            str(score),
        )
        self.assertAlmostEqual(scored["metrics"]["ambiguity"], 0.46, places=6)
        self.assertEqual(scored["metrics"]["weakest"]["component_id"], "b")
        self.assertEqual(scored["metrics"]["weakest"]["dimension"], "criteria")
        full, _ = self.run_cli(INTERVIEW, "status", "--id", "formula", "--full")
        self.assertEqual(
            full["state"]["rounds"][0]["dimension_totals"],
            {"goal": 0.5, "constraints": 0.7, "criteria": 0.4, "context": 0.6},
        )
        self.assertEqual(full["state"]["topology"]["deferrals"][0]["component_id"], "ui")

        self.run_cli(INTERVIEW, "start", "--id", "rotate", "--idea", "rotation")
        rotate_topology = self.topology_file(
            "rotate-topology.json", [self.active_component("a"), self.active_component("b")]
        )
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "rotate",
            "--expected-revision",
            "1",
            "--input",
            str(rotate_topology),
        )
        rotate_round = self.round_file(
            "rotate-round.json",
            1,
            {
                "a": {"goal": 0.2, "constraints": 0.8, "criteria": 0.8},
                "b": {"goal": 0.2, "constraints": 0.8, "criteria": 0.8},
            },
        )
        rotated, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "rotate",
            "--expected-revision",
            "2",
            "--input",
            str(rotate_round),
        )
        self.assertEqual(rotated["metrics"]["weakest"]["component_id"], "b")
        self.assertEqual(rotated["metrics"]["weakest"]["dimension"], "goal")

    def test_deep_interview_cadence_guard_requires_user_decision(self) -> None:
        self.run_cli(
            INTERVIEW,
            "start",
            "--id",
            "cadence",
            "--idea",
            "inspect facts before asking",
            "--threshold",
            "0.05",
        )
        topology = self.topology_file("cadence-topology.json", [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "cadence",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        revision = 2
        for round_value in (1, 2):
            round_input = self.round_file(
                "cadence-round-%d.json" % round_value,
                round_value,
                {"api": {"goal": 0.2 * round_value, "constraints": 0.2, "criteria": 0.2}},
                answer="[from-code][auto-confirmed] inspected fact %d" % round_value,
            )
            result, _ = self.run_cli(
                INTERVIEW,
                "score",
                "--id",
                "cadence",
                "--expected-revision",
                str(revision),
                "--input",
                str(round_input),
            )
            revision = result["revision"]
        self.assertTrue(result["metrics"]["cadence_user_required"])
        self.assertIn("[from-user]", result["next_action"])

        rejected_input = self.round_file(
            "cadence-round-3-auto.json",
            3,
            {"api": {"goal": 0.6, "constraints": 0.4, "criteria": 0.4}},
            answer="[from-research] another discoverable fact",
        )
        rejected, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "cadence",
            "--expected-revision",
            str(revision),
            "--input",
            str(rejected_input),
            expected=2,
        )
        self.assertEqual(rejected["error"], "cadence_user_required")

        user_input = self.round_file(
            "cadence-round-3-user.json",
            3,
            {"api": {"goal": 0.6, "constraints": 0.4, "criteria": 0.4}},
            answer="[from-user] choose the strict rollback contract",
        )
        accepted, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "cadence",
            "--expected-revision",
            str(revision),
            "--input",
            str(user_input),
        )
        self.assertFalse(accepted["metrics"]["cadence_user_required"])

    def test_deep_interview_ontology_stall_and_repeated_ontologist_escalation(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "stall", "--idea", "stalled ontology", "--threshold", "0.05")
        topology = self.topology_file("stall-topology.json", [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "stall",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        revision = 2
        result: Dict[str, Any] = {}
        for round_value, value in ((1, 0.10), (2, 0.12), (3, 0.14)):
            round_input = self.round_file(
                "stall-round-%d.json" % round_value,
                round_value,
                {"api": {"goal": value, "constraints": value, "criteria": value}},
                entities=[{"name": "Request", "type": "entity", "fields": ["id"], "relationships": []}],
            )
            result, _ = self.run_cli(
                INTERVIEW,
                "score",
                "--id",
                "stall",
                "--expected-revision",
                str(revision),
                "--input",
                str(round_input),
            )
            revision = result["revision"]
        self.assertTrue(result["metrics"]["stall_escalation"])
        self.assertEqual(result["metrics"]["challenge_suggestion"], "ontologist")
        self.assertEqual(result["metrics"]["ontology_stability"], 1.0)

        no_challenge = self.round_file(
            "stall-round-4-no-challenge.json",
            4,
            {"api": {"goal": 0.16, "constraints": 0.16, "criteria": 0.16}},
        )
        required, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "stall",
            "--expected-revision",
            str(revision),
            "--input",
            str(no_challenge),
            expected=2,
        )
        self.assertEqual(required["error"], "challenge_required")
        for round_value, value in ((4, 0.16), (5, 0.18)):
            round_input = self.round_file(
                "stall-round-%d-ontologist.json" % round_value,
                round_value,
                {"api": {"goal": value, "constraints": value, "criteria": value}},
                challenge="ontologist",
            )
            result, _ = self.run_cli(
                INTERVIEW,
                "score",
                "--id",
                "stall",
                "--expected-revision",
                str(revision),
                "--input",
                str(round_input),
            )
            revision = result["revision"]
        full, _ = self.run_cli(INTERVIEW, "status", "--id", "stall", "--full")
        self.assertEqual(full["state"]["challenge_modes_used"], ["ontologist"])
        self.assertEqual(full["state"]["rounds"][-1]["challenge_mode_used"], "ontologist")

    def test_deep_interview_round_guards(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "cap", "--idea", "bounded interview", "--threshold", "0.01")
        topology = self.topology_file("cap-topology.json", [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "cap",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        revision = 2
        result: Dict[str, Any] = {}
        stall = False
        for round_value in range(1, 21):
            round_input = self.round_file(
                "cap-round-%02d.json" % round_value,
                round_value,
                {"api": {"goal": 0.2, "constraints": 0.2, "criteria": 0.2}},
                challenge="ontologist" if stall else None,
            )
            result, _ = self.run_cli(
                INTERVIEW,
                "score",
                "--id",
                "cap",
                "--expected-revision",
                str(revision),
                "--input",
                str(round_input),
            )
            revision = result["revision"]
            stall = bool(result["metrics"]["stall_escalation"])
        self.assertIn("soft round guard", " ".join(result["metrics"]["warnings"]))
        self.assertIn("hard round cap", " ".join(result["metrics"]["warnings"]))
        overflow = self.round_file(
            "cap-round-21.json",
            21,
            {"api": {"goal": 0.2, "constraints": 0.2, "criteria": 0.2}},
            challenge="ontologist",
        )
        capped, _ = self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "cap",
            "--expected-revision",
            str(revision),
            "--input",
            str(overflow),
            expected=4,
        )
        self.assertEqual(capped["error"], "round_limit")

    def test_deep_interview_spec_gate_approval_digest_and_recrystallization(self) -> None:
        revision = self.complete_one_round_interview("spec")
        missing, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--spec-path",
            "missing-spec.md",
            expected=2,
        )
        self.assertEqual(missing["error"], "invalid_artifact")
        invalid_spec = self.repo / "invalid-spec.md"
        invalid_spec.write_text("# Status\nPending approval\n\n# Goal\nOnly a goal.\n", encoding="utf-8")
        invalid, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--spec-path",
            invalid_spec.name,
            expected=2,
        )
        self.assertEqual(invalid["error"], "invalid_spec")
        spec = self.repo / "approved spec 测试.md"
        spec.write_text(self.valid_spec(), encoding="utf-8")
        crystallized, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--spec-path",
            spec.name,
        )
        revision = crystallized["revision"]
        before_approval, _ = self.run_cli(
            INTERVIEW,
            "complete",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            expected=5,
        )
        self.assertEqual(before_approval["error"], "approval_required")
        approved, _ = self.run_cli(
            INTERVIEW,
            "approve",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--evidence",
            "[from-user] approved in this conversation",
        )
        revision = approved["revision"]
        spec.write_text(self.valid_spec() + "\nAdditional approved-scope clarification.\n", encoding="utf-8")
        changed, _ = self.run_cli(
            INTERVIEW,
            "complete",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            expected=5,
        )
        self.assertEqual(changed["error"], "spec_changed")
        recrystallized, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--spec-path",
            spec.name,
        )
        self.assertFalse(recrystallized["metrics"]["approved"])
        revision = recrystallized["revision"]
        approved, _ = self.run_cli(
            INTERVIEW,
            "approve",
            "--id",
            "spec",
            "--expected-revision",
            str(revision),
            "--evidence",
            "[from-user] re-approved changed digest",
        )
        completed, _ = self.run_cli(
            INTERVIEW,
            "complete",
            "--id",
            "spec",
            "--expected-revision",
            str(approved["revision"]),
        )
        self.assertEqual(completed["status"], "completed")
        terminal, _ = self.run_cli(
            INTERVIEW,
            "abort",
            "--id",
            "spec",
            "--expected-revision",
            str(completed["revision"]),
            "--reason",
            "too late",
            expected=4,
        )
        self.assertEqual(terminal["error"], "terminal")

        abort_revision = self.complete_one_round_interview("spec-abort")
        abort_spec = self.repo / "abort-spec.md"
        abort_spec.write_text(self.valid_spec(), encoding="utf-8")
        abort_crystallized, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "spec-abort",
            "--expected-revision",
            str(abort_revision),
            "--spec-path",
            abort_spec.name,
        )
        aborted, _ = self.run_cli(
            INTERVIEW,
            "abort",
            "--id",
            "spec-abort",
            "--expected-revision",
            str(abort_crystallized["revision"]),
            "--reason",
            "user stopped before approval",
        )
        self.assertEqual(aborted["status"], "aborted")
        preserved, _ = self.run_cli(INTERVIEW, "status", "--id", "spec-abort", "--full")
        self.assertEqual(preserved["state"]["spec_path"], abort_spec.name)

    def test_deep_interview_waiver_preserves_remaining_gaps(self) -> None:
        self.run_cli(INTERVIEW, "start", "--id", "waive", "--idea", "time-boxed decision", "--threshold", "0.05")
        topology = self.topology_file("waive-topology.json", [self.active_component("api")])
        self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "waive",
            "--expected-revision",
            "1",
            "--input",
            str(topology),
        )
        score = self.round_file(
            "waive-round.json",
            1,
            {"api": {"goal": 0.2, "constraints": 0.2, "criteria": 0.2}},
            pressure_pass=True,
        )
        self.run_cli(
            INTERVIEW,
            "score",
            "--id",
            "waive",
            "--expected-revision",
            "2",
            "--input",
            str(score),
        )
        waived, _ = self.run_cli(
            INTERVIEW,
            "waive",
            "--id",
            "waive",
            "--expected-revision",
            "3",
            "--reason",
            "user accepted the recorded ambiguity for this time-box",
        )
        spec = self.repo / "waived.md"
        spec.write_text(self.valid_spec(), encoding="utf-8")
        missing_gaps, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "waive",
            "--expected-revision",
            str(waived["revision"]),
            "--spec-path",
            spec.name,
            expected=2,
        )
        self.assertEqual(missing_gaps["error"], "invalid_spec")
        spec.write_text(self.valid_spec(remaining_gaps=True), encoding="utf-8")
        accepted, _ = self.run_cli(
            INTERVIEW,
            "crystallize",
            "--id",
            "waive",
            "--expected-revision",
            str(waived["revision"]),
            "--spec-path",
            spec.name,
        )
        self.assertTrue(accepted["metrics"]["gate_waived"])

    @unittest.skipIf(os.name == "nt", "symlink creation privileges vary on Windows")
    def test_symlinked_state_and_artifact_paths_are_rejected(self) -> None:
        outside = self.tmp_path / "outside"
        outside.mkdir()
        state_link = self.repo / ".agent-workflows"
        state_link.symlink_to(outside, target_is_directory=True)
        unsafe, _ = self.run_cli(RALPH, "start", "--id", "unsafe", "--goal", "reject", expected=6)
        self.assertEqual(unsafe["error"], "unsafe_state_root")
        self.assertFalse((outside / "ralph").exists())
        state_link.unlink()
        state_link.symlink_to(self.tmp_path / "missing-state-root", target_is_directory=True)
        dangling, _ = self.run_cli(RALPH, "start", "--id", "dangling", "--goal", "reject", expected=6)
        self.assertEqual(dangling["error"], "unsafe_state_root")
        state_link.unlink()

        self.run_cli(AUTO, "start", "--id", "artifact", "--goal", "safe artifact")
        self.run_cli(AUTO, "advance", "--id", "artifact", "--expected-revision", "1", "--to", "plan")
        target = outside / "plan.md"
        target.write_text("outside\n", encoding="utf-8")
        link = self.repo / "linked-plan.md"
        link.symlink_to(target)
        rejected, _ = self.run_cli(
            AUTO,
            "plan",
            "--id",
            "artifact",
            "--expected-revision",
            "2",
            "--path",
            link.name,
            expected=2,
        )
        self.assertEqual(rejected["error"], "unsafe_artifact")

        self.run_cli(INTERVIEW, "start", "--id", "input-link", "--idea", "reject input links")
        topology_target = self.topology_file("topology-target.json", [self.active_component("api")])
        topology_link = self.repo / "topology-link.json"
        topology_link.symlink_to(topology_target)
        input_rejected, _ = self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "input-link",
            "--expected-revision",
            "1",
            "--input",
            str(topology_link),
            expected=2,
        )
        self.assertEqual(input_rejected["error"], "invalid_input_file")

        outside_topology = self.tmp_path / "outside-topology.json"
        outside_topology.write_text(
            json.dumps({"schema": "agent-interview-topology/2", "components": [self.active_component("api")]}),
            encoding="utf-8",
        )
        outside_rejected, _ = self.run_cli(
            INTERVIEW,
            "topology",
            "--id",
            "input-link",
            "--expected-revision",
            "1",
            "--input",
            str(outside_topology),
            expected=2,
        )
        self.assertEqual(outside_rejected["error"], "invalid_input_file")


if __name__ == "__main__":
    unittest.main(verbosity=2)
