from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from p0_runtime.common import HarnessError  # noqa: E402
from p0_runtime.skill_eval import EXIT_ADAPTER, EXIT_VERIFIER, ProtocolFailure, run_suite  # noqa: E402


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
    git(path, "config", "user.name", "P0 Hardening Test")
    git(path, "config", "user.email", "p0-hardening@example.invalid")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-m", "initial")
    return git(path, "rev-parse", "HEAD").stdout.strip()


class SkillEvalHardeningTest(unittest.TestCase):
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
        self.temp.cleanup()

    def load_manifest(self) -> dict:
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def save_manifest(self, data: dict) -> None:
        self.manifest.write_bytes((json.dumps(data, sort_keys=True) + "\n").encode("utf-8"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "update eval contract")

    def write_script(self, name: str, source: str) -> Path:
        path = self.repo / "evals" / name
        path.write_text(source, encoding="utf-8")
        return path

    def test_adapter_repository_mutation_fails_closed(self) -> None:
        self.write_script(
            "mutating_adapter.py",
            """import json, pathlib, sys
request=json.load(sys.stdin)
repo=pathlib.Path(__file__).resolve().parents[1]
(repo/'adapter-owned-repo-file.txt').write_text('bad', encoding='utf-8')
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':request['run_id'],'mode':request['mode'],'selected':False,'status':'completed','metrics':{'input_tokens':0,'output_tokens':0,'tool_calls':0,'wall_time_seconds':0,'interventions':0}},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/mutating_adapter.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "result.json", case_filter=["negative-doc-only"])
        self.assertEqual(caught.exception.code, EXIT_ADAPTER)
        self.assertIn("outside the isolated fixture", str(caught.exception))

    def test_verifier_repository_mutation_fails_closed(self) -> None:
        self.write_script(
            "mutating_verifier.py",
            """import json, pathlib, sys
request=json.load(sys.stdin)
repo=pathlib.Path(__file__).resolve().parents[1]
(repo/'verifier-owned-repo-file.txt').write_text('bad', encoding='utf-8')
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':request['run_id'],'passed':True,'checks':[{'name':'deterministic','passed':True,'message':'ok'}]},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["verifier"]["command"] = ["{python}", "{repo}/evals/mutating_verifier.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "result.json", case_filter=["negative-doc-only"])
        self.assertEqual(caught.exception.code, EXIT_VERIFIER)
        self.assertIn("outside the isolated fixture", str(caught.exception))

    def test_adapter_must_report_complete_metrics_and_no_secret_metadata(self) -> None:
        self.write_script(
            "bad_metrics.py",
            """import json,sys
r=json.load(sys.stdin)
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'mode':r['mode'],'selected':False,'status':'completed','metrics':{'input_tokens':0}},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/bad_metrics.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "metrics.json", case_filter=["negative-doc-only"])
        self.assertEqual(caught.exception.code, EXIT_ADAPTER)

        self.write_script(
            "secret_metadata.py",
            """import json,sys
r=json.load(sys.stdin)
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'mode':r['mode'],'selected':False,'status':'completed','metrics':{'input_tokens':0,'output_tokens':0,'tool_calls':0,'wall_time_seconds':0,'interventions':0},'metadata':{'api_token':'do-not-retain'}},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/secret_metadata.py"]
        self.save_manifest(data)
        with self.assertRaises(ProtocolFailure) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "secret.json", case_filter=["negative-doc-only"])
        self.assertEqual(caught.exception.code, EXIT_ADAPTER)

    def test_repository_snapshot_is_part_of_pair_comparability(self) -> None:
        result = run_suite(self.manifest, Path(self.temp.name) / "result.json", case_filter=["positive-red-green"])
        pair = result["cases"][0]
        baseline = pair["baseline"]
        treatment = pair["treatment"]
        self.assertEqual(baseline["repository_snapshot_digest"], treatment["repository_snapshot_digest"])
        self.assertTrue(pair["comparison"]["passed"])
        self.assertEqual(len(baseline["repository_snapshot_digest"]), 64)

    def test_dirty_fixture_is_ignored_by_materialized_revision(self) -> None:
        fixture = self.repo / "evals" / "examples" / "tdd" / "fixture" / "src" / "calc.py"
        fixture.write_text("def add(left, right):\n    return 999\n", encoding="utf-8")
        result = run_suite(
            self.manifest,
            Path(self.temp.name) / "pinned.json",
            case_filter=["positive-red-green"],
        )
        self.assertTrue(result["passed"])
        self.assertTrue(result["revision_materialized"])
        self.assertEqual(result["repository_revision"], git(self.repo, "rev-parse", "HEAD").stdout.strip())

    def test_dirty_head_manifest_is_rejected(self) -> None:
        data = self.load_manifest()
        data["cases"][0]["prompt"] = "uncommitted control change"
        self.manifest.write_text(json.dumps(data) + "\n", encoding="utf-8")
        with self.assertRaises(HarnessError) as caught:
            run_suite(self.manifest, Path(self.temp.name) / "dirty-manifest.json")
        self.assertEqual(caught.exception.code, 3)
        self.assertIn("commit suite changes", str(caught.exception))

    def test_adapter_receives_absolute_paths_from_pinned_repository(self) -> None:
        self.write_script(
            "absolute_paths_adapter.py",
            """import json,pathlib,sys
r=json.load(sys.stdin)
repo=pathlib.Path(r['repository_root'])
assert repo.is_absolute() and repo.is_dir()
if r['mode']=='baseline':
 assert r['skill_path'] is None
else:
 skill=pathlib.Path(r['skill_path'])
 assert skill.is_absolute() and skill.is_dir() and repo in skill.parents
if r['mode']=='treatment' and r['case']['kind']=='positive':
 (pathlib.Path(r['workspace'])/'src'/'calc.py').write_text('def add(left, right):\\n    return left + right\\n', encoding='utf-8')
json.dump({'schema_version':1,'contract':'agent-skill-eval/v1','run_id':r['run_id'],'mode':r['mode'],'selected':r['mode']=='treatment' and r['case']['kind']=='positive','status':'completed','metrics':{'input_tokens':0,'output_tokens':0,'tool_calls':0,'wall_time_seconds':0,'interventions':0},'metadata':{'absolute_paths':True}},sys.stdout)
""",
        )
        data = self.load_manifest()
        data["adapter"]["command"] = ["{python}", "{repo}/evals/absolute_paths_adapter.py"]
        self.save_manifest(data)
        result = run_suite(
            self.manifest,
            Path(self.temp.name) / "absolute-paths.json",
            case_filter=["positive-red-green"],
        )
        self.assertTrue(result["passed"])
        self.assertTrue(result["cases"][0]["treatment"]["adapter"]["metadata"]["absolute_paths"])


if __name__ == "__main__":
    unittest.main()
