from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from p0_runtime.common import (  # noqa: E402
    FileMutex,
    HarnessError,
    match_any,
    patterns_overlap,
    read_json,
    repository_snapshot,
    safe_child,
    write_json_atomic,
)
from p0_runtime.skill_eval import (  # noqa: E402
    EXIT_ADAPTER,
    EXIT_VERIFIER,
    ProtocolFailure,
    _expand_command,
    compare_pair,
    run_suite,
    validate_manifest,
    validate_result,
)
from p0_runtime.workctl import (  # noqa: E402
    TaskStore,
    acquire_owner,
    claim_paths,
    create_workspace,
    handoff_owner,
    init_task,
    release_owner,
    remove_workspace,
    transition_task,
    verify_task,
    workspace_changed_paths,
)
from p0_runtime.common import discover_git_context, run_git  # noqa: E402


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )


def init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init")
    git(path, "config", "user.name", "P0 Test")
    git(path, "config", "user.email", "p0@example.invalid")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-m", "initial")
    return git(path, "rev-parse", "HEAD").stdout.strip()


class CommonSecurityTest(unittest.TestCase):
    def test_overlap_parent_child_and_glob(self) -> None:
        self.assertTrue(patterns_overlap("src/**", "src/api/file.py"))
        self.assertTrue(patterns_overlap("src/api", "src/api/file.py"))
        self.assertTrue(patterns_overlap("src/*/models.py", "src/api/**"))
        self.assertFalse(patterns_overlap("src/api/**", "tests/**"))

    def test_recursive_glob_matches_nested_paths_only_when_requested(self) -> None:
        self.assertTrue(match_any("src/api/internal/model.py", ["src/**"]))
        self.assertTrue(match_any("src/model.py", ["src/*"]))
        self.assertFalse(match_any("src/api/model.py", ["src/*"]))

    def test_live_process_lock_is_not_recovered_only_because_it_is_old(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "live.lock"
            write_json_atomic(
                lock,
                {"schema_version": 1, "token": "held", "pid": os.getpid(), "created_epoch": 0},
            )
            with self.assertRaises(HarnessError):
                with FileMutex(lock, timeout=0.02, stale_after=0):
                    pass
            self.assertTrue(lock.exists())

    def test_rename_reports_source_and_destination_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            base = init_repo(repo)
            (repo / "allowed").mkdir()
            git(repo, "mv", "README.md", "allowed/README.md")
            git(repo, "commit", "-m", "rename")
            self.assertEqual(workspace_changed_paths(repo, base), ["README.md", "allowed/README.md"])

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
    def test_safe_child_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            os.symlink(str(outside), str(root / "link"), target_is_directory=True)
            with self.assertRaises(HarnessError):
                safe_child(root, "link/secret", must_exist=False)

    def test_repository_snapshot_ignores_linked_worktree_git_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").write_text("gitdir: /outside/common/worktrees/test\n", encoding="utf-8")
            (root / "tracked.txt").write_text("content\n", encoding="utf-8")
            snapshot = repository_snapshot(root)
            self.assertNotIn(".git", snapshot)
            self.assertIn("tracked.txt", snapshot)


class SkillEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        init_repo(self.repo)
        shutil.copytree(ROOT / "evals", self.repo / "evals")
        skill = self.repo / "skills" / "tdd"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: tdd\n---\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "eval fixture")
        self.manifest = self.repo / "evals" / "examples" / "tdd" / "suite.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def load_manifest(self) -> dict:
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def save_manifest(self, data: dict) -> None:
        self.manifest.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "update eval contract")

    def make_protocol_script(self, name: str, body: str) -> Path:
        path = self.repo / "evals" / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_python_placeholder_accepts_symlinked_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            interpreter = Path(temp) / "python"
            try:
                interpreter.symlink_to(Path(sys.executable).resolve())
            except OSError as exc:
                self.skipTest("interpreter symlink unavailable: %s" % exc)
            with mock.patch("p0_runtime.skill_eval.sys.executable", str(interpreter)):
                expanded = _expand_command(
                    ["{python}"],
                    self.repo,
                    self.repo / "workspace",
                    "baseline",
                    "symlinked-python",
                )
        self.assertEqual(Path(expanded[0]), Path(sys.executable).resolve())

    def test_offline_ab_suite_passes(self) -> None:
        output = Path(self.temp.name) / "result.json"
        result = run_suite(self.manifest, output)
        self.assertTrue(result["passed"])
        self.assertEqual(result["summary"], {"total": 3, "passed": 3, "failed": 0})
        kinds = {item["case"]["kind"]: item for item in result["cases"]}
        self.assertTrue(kinds["positive"]["treatment"]["trigger"]["passed"])
        self.assertFalse(kinds["negative"]["treatment"]["adapter"]["selected"])
        self.assertFalse(kinds["confusable"]["treatment"]["adapter"]["selected"])
        self.assertEqual(validate_result(json.loads(output.read_text(encoding="utf-8")))["summary"], result["summary"])

        tampered = json.loads(output.read_text(encoding="utf-8"))
        tampered["summary"]["passed"] -= 1
        with self.assertRaises(HarnessError):
            validate_result(tampered)

        tampered = json.loads(output.read_text(encoding="utf-8"))
        tampered["cases"][0]["comparison"]["budget"]["checks"].append(
            {"metric": "input_tokens", "kind": "absolute", "passed": False, "actual": 999, "limit": 0}
        )
        with self.assertRaises(HarnessError):
            validate_result(tampered)

        tampered = json.loads(output.read_text(encoding="utf-8"))
        tampered["cases"][0]["case"]["prompt"] = "tampered after execution"
        with self.assertRaises(HarnessError):
            validate_result(tampered)

    def test_manifest_path_traversal_and_fixture_symlink_rejected(self) -> None:
        data = self.load_manifest()
        data["fixture"] = "../outside"
        with self.assertRaises(HarnessError):
            validate_manifest(data, self.repo)
        if hasattr(os, "symlink"):
            data = self.load_manifest()
            link = self.repo / "evals" / "examples" / "tdd" / "fixture" / "escape"
            os.symlink(str(Path(self.temp.name)), str(link), target_is_directory=True)
            self.save_manifest(data)
            with self.assertRaises(HarnessError):
                run_suite(self.manifest, Path(self.temp.name) / "symlink.json", case_filter=["positive-red-green"])

        data = self.load_manifest()
        data["cases"][0]["metadata"] = {"api_token": "must-not-be-retained"}
        with self.assertRaises(HarnessError):
            validate_manifest(data, self.repo)

    def test_malformed_adapter_output_fails_closed(self) -> None:
        script = self.make_protocol_script("bad_adapter.py", "print('not-json')\n")
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/bad_adapter.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "bad.json", case_filter=["positive-red-green"])
        self.assertEqual(caught.exception.code, EXIT_ADAPTER)

    def test_adapter_timeout_and_output_limit(self) -> None:
        script = self.make_protocol_script("sleep_adapter.py", "import time\ntime.sleep(2)\n")
        data = self.load_manifest()
        data["adapter"].update(
            {"command": ["{python}", "{repo}/evals/sleep_adapter.py"], "timeout_seconds": 0.1}
        )
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure):
            run_suite(self.manifest, Path(self.temp.name) / "timeout.json", case_filter=["positive-red-green"])
        self.make_protocol_script("large_adapter.py", "print('x' * 4096)\n")
        data = self.load_manifest()
        data["adapter"].update(
            {
                "command": ["{python}", "{repo}/evals/large_adapter.py"],
                "timeout_seconds": 5,
                "max_output_bytes": 1024,
            }
        )
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure):
            run_suite(self.manifest, Path(self.temp.name) / "large.json", case_filter=["positive-red-green"])

    def test_negative_trigger_leakage_is_a_gate_failure(self) -> None:
        self.make_protocol_script(
            "leaky_adapter.py",
            """import json,sys
r=json.load(sys.stdin)
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'mode':r['mode'],'selected':r['mode']=='treatment','status':'completed','metrics':{'input_tokens':0,'output_tokens':0,'tool_calls':0,'wall_time_seconds':0,'interventions':0}},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/leaky_adapter.py"]
        self.save_manifest(data)
        result = run_suite(
            self.manifest,
            Path(self.temp.name) / "leak.json",
            case_filter=["negative-doc-only"],
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["cases"][0]["comparison"]["correctness"]["checks"]["trigger"])

    def test_scope_violation_and_budget_regression_fail(self) -> None:
        self.make_protocol_script(
            "scope_adapter.py",
            """import json,pathlib,sys
r=json.load(sys.stdin)
if r['mode']=='treatment':
 p=pathlib.Path(r['workspace'])/'forbidden.txt';p.write_text('x')
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'mode':r['mode'],'selected':r['mode']=='treatment','status':'completed','metrics':{'input_tokens':1000 if r['mode']=='treatment' else 1,'output_tokens':0,'tool_calls':0,'wall_time_seconds':0,'interventions':0}},sys.stdout)
""",
        )
        self.make_protocol_script(
            "always_verifier.py",
            """import json,sys
r=json.load(sys.stdin)
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'passed':True,'checks':[{'name':'always','passed':True,'message':'fixture'}]},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/scope_adapter.py"]
        data["verifier"]["command"] = ["{python}", "{repo}/evals/always_verifier.py"]
        self.save_manifest(data)
        result = run_suite(
            self.manifest,
            Path(self.temp.name) / "scope.json",
            case_filter=["positive-red-green"],
        )
        comparison = result["cases"][0]["comparison"]
        self.assertFalse(comparison["passed"])
        self.assertFalse(comparison["correctness"]["checks"]["scope"])
        self.assertFalse(comparison["budget"]["passed"])

    def test_verifier_mutation_is_rejected(self) -> None:
        self.make_protocol_script(
            "mutating_verifier.py",
            """import json,pathlib,sys
r=json.load(sys.stdin)
(pathlib.Path(r['workspace'])/'verifier-write').write_text('bad')
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'passed':True,'checks':[{'name':'always','passed':True,'message':'fixture'}]},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["verifier"]["command"] = ["{python}", "{repo}/evals/mutating_verifier.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "mutate.json", case_filter=["positive-red-green"])
        self.assertEqual(caught.exception.code, EXIT_VERIFIER)

    def test_incomparable_pair_is_rejected(self) -> None:
        result = run_suite(
            self.manifest,
            Path(self.temp.name) / "pair.json",
            case_filter=["positive-red-green"],
        )
        baseline = result["cases"][0]["baseline"]
        treatment = dict(result["cases"][0]["treatment"])
        treatment["fixture_digest"] = "0" * 64
        with self.assertRaises(HarnessError):
            compare_pair(baseline, treatment, {"absolute": {}, "relative": {}})


class WorkProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.commit = init_repo(self.repo)
        self.context = discover_git_context(self.repo)
        self.store, self.state = init_task(self.context, "task-1", 1, "Test task")

    def tearDown(self) -> None:
        # Make reviewer directories writable so TemporaryDirectory can clean as an unprivileged user.
        for current, dirs, files in os.walk(self.temp.name):
            try:
                Path(current).chmod(0o700)
            except OSError:
                pass
            for name in files:
                try:
                    (Path(current) / name).chmod(0o600)
                except OSError:
                    pass
        self.temp.cleanup()

    def complete_artifacts(self) -> None:
        task_dir = self.store.task_dir()
        (task_dir / "brief.md").write_text(
            "# Test task\n\n## Goal\nDeliver the fixture.\n\n"
            "## Non-goals\nNo external effects.\n\n"
            "## Acceptance criteria\nDeterministic tests pass.\n\n"
            "## Authority and external effects\nRepository-only writes.\n",
            encoding="utf-8",
        )
        (task_dir / "plan.md").write_text(
            "# Plan\n\n## Slices\nImplement and verify.\n\n"
            "## Risks and dependencies\nGit is available.\n\n"
            "## Ownership\nOne loop owner.\n",
            encoding="utf-8",
        )

    def acquire(self, owner: str = "autopilot", version: int = 1):
        return acquire_owner(self.store, version, owner, 60, "test")

    def test_artifacts_and_linked_worktree_share_common_authority(self) -> None:
        task_dir = self.repo / ".agents" / "work" / "task-1"
        self.assertTrue((task_dir / "brief.md").exists())
        self.assertTrue((task_dir / "plan.md").exists())
        linked = Path(self.temp.name) / "linked"
        git(self.repo, "worktree", "add", "-b", "linked-test", str(linked), self.commit)
        linked_store = TaskStore.for_existing(linked, "task-1")
        self.assertEqual(linked_store.context.common_dir, self.store.context.common_dir)
        state, _ = linked_store.read()
        self.assertEqual(state["version"], 1)

    def test_single_owner_cas_and_token_handoff(self) -> None:
        results = []
        barrier = threading.Barrier(2)

        def contender(owner: str) -> None:
            barrier.wait()
            try:
                state, token = acquire_owner(self.store, 1, owner, 60, owner)
                results.append(("ok", owner, state["version"], token))
            except HarnessError as exc:
                results.append(("error", owner, exc.code, ""))

        threads = [threading.Thread(target=contender, args=(owner,)) for owner in ("autopilot", "ralph")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(1 for item in results if item[0] == "ok"), 1)
        winner = next(item for item in results if item[0] == "ok")
        old_token = winner[3]
        state, new_token = handoff_owner(self.store, 2, old_token, "pairroom", 60, "test")
        self.assertEqual(state["loop_owner"], "pairroom")
        with self.assertRaises(HarnessError):
            transition_task(self.store, 3, old_token, "planned", "test", "old token")
        state = release_owner(self.store, 3, new_token, "test")
        self.assertIsNone(state["loop_owner"])

    def test_expired_lease_requires_explicit_recovery(self) -> None:
        state, token = self.acquire()
        with FileMutex(self.store.lock_path):
            registry = self.store._read_registry()
            registry["lease"]["expires_epoch"] = time.time() - 1
            write_json_atomic(self.store.registry_path, registry)
        with self.assertRaises(HarnessError):
            acquire_owner(self.store, 2, "ralph", 60, "test", recover=False)
        state, recovered = acquire_owner(self.store, 2, "ralph", 60, "test", recover=True)
        self.assertEqual(state["loop_owner"], "ralph")
        self.assertNotEqual(token, recovered)

    def test_transition_graph_and_bounded_verify_retry(self) -> None:
        self.complete_artifacts()
        state, token = self.acquire()
        state = transition_task(self.store, 2, token, "planned", "test", "ready")
        state = transition_task(self.store, 3, token, "executing", "test", "start")
        state = transition_task(self.store, 4, token, "verifying", "test", "check")
        state = transition_task(self.store, 5, token, "executing", "test", "fix")
        self.assertEqual(state["verify_retry_count"], 1)
        state = transition_task(self.store, 6, token, "verifying", "test", "recheck")
        with self.assertRaises(HarnessError):
            transition_task(self.store, 7, token, "executing", "test", "too many")
        with self.assertRaises(HarnessError):
            transition_task(self.store, 7, token, "planned", "test", "invalid")

    def test_evidence_tamper_is_detected(self) -> None:
        state, token = self.acquire()
        path = self.store.evidence_path()
        lines = path.read_text(encoding="utf-8").splitlines()
        event = json.loads(lines[0])
        event["payload"]["title"] = "tampered"
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        result = verify_task(self.store)
        self.assertFalse(result["ok"])
        self.assertTrue(any("hash" in issue for issue in result["issues"]))

    def test_reviewer_requires_exact_commit_and_is_fixed(self) -> None:
        state, token = self.acquire()
        with self.assertRaises(HarnessError):
            create_workspace(
                self.store,
                2,
                token,
                "review-bad",
                "reviewer",
                Path(self.temp.name) / "review-bad",
                "test",
                "HEAD",
                None,
                "HEAD",
            )
        record = create_workspace(
            self.store,
            2,
            token,
            "review",
            "reviewer",
            Path(self.temp.name) / "review",
            "test",
            self.commit,
            None,
            "HEAD",
        )
        self.assertEqual(record["snapshot_commit"], self.commit)
        self.assertTrue(verify_task(self.store)["ok"])
        # Simulate a policy violation even when running as root, which can bypass mode bits.
        source = Path(record["path"]) / "README.md"
        source.chmod(0o600)
        source.write_text("dirty\n", encoding="utf-8")
        result = verify_task(self.store)
        self.assertFalse(result["ok"])
        self.assertTrue(any("dirty" in issue for issue in result["issues"]))
        remove_workspace(self.store, 3, token, "review", "test", "HEAD", True, "discard dirty review")

    def test_parallel_writers_claims_and_unique_integrator(self) -> None:
        state, token = self.acquire()
        first = create_workspace(
            self.store,
            2,
            token,
            "worker-a",
            "worker",
            Path(self.temp.name) / "worker-a",
            "test",
            None,
            "task-1-a",
            "HEAD",
        )
        second = create_workspace(
            self.store,
            3,
            token,
            "worker-b",
            "worker",
            Path(self.temp.name) / "worker-b",
            "test",
            None,
            "task-1-b",
            "HEAD",
        )
        claim_paths(self.store, 4, token, "worker-a", ["src/api/**"], "test")
        with self.assertRaises(HarnessError):
            claim_paths(self.store, 5, token, "worker-b", ["src/**"], "test")
        claim_paths(self.store, 5, token, "worker-b", ["tests/**"], "test")
        create_workspace(
            self.store,
            6,
            token,
            "integrator",
            "integrator",
            Path(self.temp.name) / "integrator",
            "test",
            None,
            "task-1-integrator",
            "HEAD",
        )
        with self.assertRaises(HarnessError):
            create_workspace(
                self.store,
                7,
                token,
                "integrator-2",
                "integrator",
                Path(self.temp.name) / "integrator-2",
                "test",
                None,
                "task-1-integrator-2",
                "HEAD",
            )

    def test_dirty_unmerged_cleanup_requires_explicit_reason(self) -> None:
        state, token = self.acquire()
        record = create_workspace(
            self.store,
            2,
            token,
            "worker",
            "worker",
            Path(self.temp.name) / "worker",
            "test",
            None,
            "task-1-worker",
            "HEAD",
        )
        (Path(record["path"]) / "dirty.txt").write_text("dirty", encoding="utf-8")
        with self.assertRaises(HarnessError):
            remove_workspace(self.store, 3, token, "worker", "test", "HEAD", False, "")
        with self.assertRaises(HarnessError):
            remove_workspace(self.store, 3, token, "worker", "test", "HEAD", True, "")
        remove_workspace(self.store, 3, token, "worker", "test", "HEAD", True, "explicit discard")


class GeneratedPayloadTest(unittest.TestCase):
    def test_generated_payloads_are_current_and_compile(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_p0_runtimes.py"), "--check"],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for entry in (
            ROOT / ".agents" / "skills" / "skill-eval" / "scripts" / "skill_eval.py",
            ROOT / "skills" / "work-protocol" / "scripts" / "workctl.py",
        ):
            help_result = subprocess.run(
                [sys.executable, str(entry), "--help"],
                cwd=str(ROOT),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(help_result.returncode, 0, help_result.stdout + help_result.stderr)

    def test_workctl_risk_entrypoint_is_side_effect_free(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            before = set(Path(temp).iterdir())
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "skills" / "work-protocol" / "scripts" / "workctl.py"),
                    "risk",
                    "--cross-session",
                ],
                cwd=temp,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["needed"])
            self.assertEqual(before, set(Path(temp).iterdir()))


if __name__ == "__main__":
    unittest.main()
