from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from p0_runtime.common import (  # noqa: E402
    HarnessError,
    changed_paths,
    match_any,
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


# A fixture teardown removes a live Git repository: `run_suite` materializes a
# detached worktree whose administration stays in the fixture repository's `.git`,
# and Python 3.8's POSIX `rmtree` lists a directory before removing each entry, so
# an entry that appears in that window makes the final `rmdir` report ENOTEMPTY.
# The assertions have already run by then, so retry a bounded number of times
# (the mitigation `worktree.sh` uses for the same removal race) instead of failing
# a passing test; a tree that is really not removable still raises.
TRANSIENT_REMOVAL_ERRNOS = (errno.ENOTEMPTY, errno.EBUSY)
REMOVAL_ATTEMPTS = 3
REMOVAL_RETRY_DELAY_SECONDS = 0.2


def cleanup_fixture(directory: tempfile.TemporaryDirectory) -> None:
    for attempt in range(1, REMOVAL_ATTEMPTS + 1):
        try:
            directory.cleanup()
            if not os.path.exists(directory.name):
                return
        except OSError as exc:
            if getattr(exc, "errno", None) not in TRANSIENT_REMOVAL_ERRNOS or attempt == REMOVAL_ATTEMPTS:
                raise
        if attempt < REMOVAL_ATTEMPTS:
            time.sleep(REMOVAL_RETRY_DELAY_SECONDS)
    raise OSError(errno.ENOTEMPTY, "fixture directory survived cleanup attempts", directory.name)


class CommonSecurityTest(unittest.TestCase):
    def test_atomic_json_failure_preserves_original_and_removes_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            write_json_atomic(path, {"value": "original"})
            original = path.read_bytes()
            with mock.patch("p0_runtime.common.os.replace", side_effect=OSError("injected failure")):
                with self.assertRaises(OSError):
                    write_json_atomic(path, {"value": "new"})
            self.assertEqual(original, path.read_bytes())
            self.assertEqual([path], list(Path(temp).iterdir()))

    def test_recursive_glob_matches_nested_paths_only_when_requested(self) -> None:
        self.assertTrue(match_any("src/api/internal/model.py", ["src/**"]))
        self.assertTrue(match_any("src/model.py", ["src/*"]))
        self.assertFalse(match_any("src/api/model.py", ["src/*"]))


    def test_rename_reports_source_and_destination_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            init_repo(repo)
            before = repository_snapshot(repo)
            (repo / "allowed").mkdir()
            git(repo, "mv", "README.md", "allowed/README.md")
            git(repo, "commit", "-m", "rename")
            self.assertEqual(changed_paths(before, repository_snapshot(repo)), ["README.md", "allowed/", "allowed/README.md"])

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


class FixtureCleanupTest(unittest.TestCase):
    def test_transient_removal_race_is_retried(self) -> None:
        real_rmtree = shutil.rmtree
        removals = []

        def flaky_rmtree(path, *args, **kwargs):
            removals.append(str(path))
            if len(removals) == 1:
                raise OSError(errno.ENOTEMPTY, "Directory not empty")
            return real_rmtree(path, *args, **kwargs)

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with mock.patch("shutil.rmtree", side_effect=flaky_rmtree):
            cleanup_fixture(directory)
        self.assertEqual(len(removals), 2)
        self.assertFalse(os.path.exists(directory.name))

    def test_unremovable_fixture_still_fails_the_test(self) -> None:
        def broken_rmtree(path, *args, **kwargs):
            raise OSError(errno.ENOTEMPTY, "Directory not empty")

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with mock.patch("shutil.rmtree", side_effect=broken_rmtree), mock.patch("time.sleep"):
            with self.assertRaises(OSError) as caught:
                cleanup_fixture(directory)
        self.assertEqual(caught.exception.errno, errno.ENOTEMPTY)
        self.assertTrue(os.path.exists(directory.name))


class SkillEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        init_repo(self.repo)
        shutil.copytree(ROOT / "evals", self.repo / "evals")
        # This control file is compared byte-for-byte with a fresh worktree.
        # Do not inherit the machine's checkout EOL for copied LF inputs.
        (self.repo / ".gitattributes").write_bytes(b"evals/**/suite.json text eol=lf\n")
        skill = self.repo / "skills" / "tdd"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: tdd\n---\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "eval fixture")
        self.manifest = self.repo / "evals" / "examples" / "tdd" / "suite.json"

    def tearDown(self) -> None:
        cleanup_fixture(self.temp)

    def load_manifest(self) -> dict:
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def save_manifest(self, data: dict) -> None:
        self.manifest.write_bytes((json.dumps(data, sort_keys=True) + "\n").encode("utf-8"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "update eval contract")

    def make_protocol_script(self, name: str, body: str) -> Path:
        path = self.repo / "evals" / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_manifest_bytes_survive_native_checkout_policies(self) -> None:
        data = self.load_manifest()
        data["suite_id"] = "eol-control"
        self.save_manifest(data)
        before = self.manifest.read_bytes()
        self.assertNotIn(b"\r\n", before)
        for mode in ("true", "input", "false"):
            with self.subTest(autocrlf=mode):
                git(self.repo, "config", "core.autocrlf", mode)
                result = run_suite(
                    self.manifest,
                    Path(self.temp.name) / (mode + ".json"),
                    case_filter=["positive-red-green"],
                )
                self.assertTrue(result["passed"])
                self.assertEqual(before, self.manifest.read_bytes())

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

    def test_baseline_execution_must_be_valid_but_may_fail_task_oracle(self) -> None:
        result = run_suite(
            self.manifest, Path(self.temp.name) / "baseline-validity.json",
            case_filter=["positive-red-green"],
        )
        pair = result["cases"][0]
        budgets = {"absolute": {}, "relative": {}}
        for boundary in ("adapter_completed", "trigger", "scope"):
            baseline = json.loads(json.dumps(pair["baseline"]))
            if boundary == "adapter_completed":
                baseline["adapter"]["status"] = "failed"
            else:
                baseline[boundary]["passed"] = False
            with self.subTest(boundary=boundary):
                comparison = compare_pair(baseline, pair["treatment"], budgets)
                self.assertFalse(comparison["passed"])
                self.assertFalse(comparison["correctness"]["checks"][boundary])
        # A functioning control may get the task wrong: that is valid evidence
        # of a treatment improvement, unlike an invalid execution or scope.
        baseline = json.loads(json.dumps(pair["baseline"]))
        baseline["verifier"]["passed"] = False
        self.assertTrue(compare_pair(baseline, pair["treatment"], budgets)["passed"])
        result["cases"][0]["baseline"]["adapter"]["status"] = "failed"
        with self.assertRaises(HarnessError):
            validate_result(result)

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


if __name__ == "__main__":
    unittest.main()
