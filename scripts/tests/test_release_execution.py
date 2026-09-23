"""Execute real release workflow shell steps against a local Git repo and mock gh."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from strictyaml import dirty_load

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/tasks"))
from cases import environment, git, write

MOCK_GH = r'''import json, os, sys
from pathlib import Path
# Match the CLI's LF output rather than Python's Windows newline translation.
sys.stdout.reconfigure(newline="\n")
args = sys.argv[1:]
with Path(os.environ["GH_RECORD"]).open("a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
if args[:2] == ["release", "create"]:
    data = {"tagName":args[2], "isDraft":False, "isPrerelease":"--prerelease" in args,
            "body":Path(args[args.index("--notes-file")+1]).read_text(encoding="utf-8"),
            "url":"https://example.invalid/release/" + args[2]}
    Path(os.environ["GH_STATE"]).write_text(json.dumps(data), encoding="utf-8")
    raise SystemExit(0)
if args[:2] == ["release", "view"] and Path(os.environ["GH_STATE"]).exists():
    data = json.loads(Path(os.environ["GH_STATE"]).read_text())
    data.update(json.loads(os.environ.get("GH_WRONG", "{}")))
    if "--json" in args:
        value = data[args[args.index("--json")+1]]
        print(str(value).lower() if isinstance(value, bool) else value)
    raise SystemExit(0)
raise SystemExit(1)
'''


class ReleaseExecutionTests(unittest.TestCase):
    def setUp(self):
        self.bash_bin = shutil.which("bash")
        self.assertIsNotNone(self.bash_bin, "Git Bash/POSIX bash is required for release tests")
        self.temp = tempfile.TemporaryDirectory(prefix="release-check-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Release Fixture")
        git(self.repo, "config", "user.email", "release@example.invalid")
        git(self.repo, "config", "commit.gpgsign", "false")
        self.source = ROOT / "scripts/release/extract-changelog.py"
        target = self.repo / "scripts/release/extract-changelog.py"
        target.parent.mkdir(parents=True); shutil.copyfile(self.source, target)
        write(self.repo, "CHANGELOG.md", "# Changelog\n\n## [v1.0.0] — 2026-09-22\n\n### Changed\n\n- Verified release.\n")
        git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "fixture")
        git(self.repo, "tag", "v1.0.0")
        # The workflow verifies trunk reachability, so the fixture needs a trunk ref.
        git(self.repo, "branch", "-M", "main")
        bare = self.root / "origin.git"
        bare.mkdir()
        git(bare, "init", "-q", "--bare")
        git(self.repo, "remote", "add", "origin", bare.as_posix())
        git(self.repo, "push", "-q", "origin", "main")
        self.mock = self.root / "mock-gh.py"; self.mock.write_text(MOCK_GH)
        self.record = self.root / "gh-record.jsonl"
        self.env = environment()
        self.env.update(GITHUB_REF_NAME="v1.0.0", GITHUB_REPOSITORY="fixture/repository",
                        RUNNER_TEMP=self.root.as_posix(), GH_RECORD=str(self.record),
                        GH_STATE=str(self.root / "gh-state.json"), TEST_PYTHON=Path(sys.executable).as_posix(),
                        TEST_GH=self.mock.as_posix())
        self.workflow = dirty_load((ROOT / ".github/workflows/release.yml").read_text(), allow_flow_style=True).data
        self.steps = self.workflow["jobs"]["release"]["steps"]
        self.shell = [step["run"] for step in self.steps if "run" in step]
        self.extract = next(s for s in self.shell if "extract-changelog.py" in s)
        self.publish = next(s for s in self.shell if "release create" in s)
        self.verify = next(s for s in self.shell if "--json body" in s)

    def bash(self, script, **env):
        prefix = 'python() { "$TEST_PYTHON" "$@"; }; gh() { "$TEST_PYTHON" "$TEST_GH" "$@"; };\n'
        return subprocess.run([self.bash_bin, "-e", "-c", prefix + script], cwd=self.repo,
                              env={**self.env, **env}, capture_output=True, text=True, timeout=30)

    def test_real_scripts_publish_exact_tag_notes_and_check_result(self):
        self.assertLess(self.shell.index(self.extract), self.shell.index(self.publish))
        self.assertLess(self.shell.index(self.publish), self.shell.index(self.verify))
        cp = self.bash(self.extract + "\n" + self.publish + "\n" + self.verify)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        calls = [json.loads(s) for s in self.record.read_text().splitlines()]
        self.assertEqual(calls[0][:3], ["release", "create", "v1.0.0"])
        self.assertIn("--verify-tag", calls[0]); self.assertIn("--latest", calls[0])
        self.assertTrue(all(c[2] == "v1.0.0" for c in calls))
        for mismatch in ({"body":"wrong"}, {"tagName":"v2.0.0"}, {"isDraft":True}, {"isPrerelease":True}):
            with self.subTest(mismatch=mismatch):
                self.assertNotEqual(self.bash(self.verify, GH_WRONG=json.dumps(mismatch)).returncode, 0)

    def test_bad_tag_or_missing_notes_stops_before_publisher(self):
        for tag in ("v01.0.0", "v2.0.0"):
            with self.subTest(tag=tag):
                cp = self.bash(self.extract + "\n" + self.publish, GITHUB_REF_NAME=tag)
                self.assertNotEqual(cp.returncode, 0)
                self.assertFalse(self.record.exists())
        write(self.repo, "CHANGELOG.md", "# Changelog\n\nNo matching release\n")
        cp = self.bash(self.extract + "\n" + self.publish)
        self.assertNotEqual(cp.returncode, 0)
        self.assertFalse(self.record.exists())

    def test_tag_outside_the_trunk_is_rejected_before_publishing(self):
        write(self.repo, "CHANGELOG.md", "# Changelog\n\n## [v1.2.0] — 2026-09-22\n\n- Branch release.\n")
        git(self.repo, "checkout", "-q", "-b", "feature/experiment")
        git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "branch work")
        git(self.repo, "tag", "v1.2.0")

        cp = self.bash(self.extract + "\n" + self.publish, GITHUB_REF_NAME="v1.2.0")

        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("not reachable from main", cp.stderr)
        self.assertFalse(self.record.exists())

    def test_prerelease_flags_and_moved_tag(self):
        write(self.repo, "CHANGELOG.md", "# Changelog\n\n## [v1.1.0-rc.1] — 2026-09-22\n\n- Candidate.\n")
        git(self.repo, "tag", "v1.1.0-rc.1")
        cp = self.bash(self.extract + "\n" + self.publish + "\n" + self.verify, GITHUB_REF_NAME="v1.1.0-rc.1")
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        args = json.loads(self.record.read_text().splitlines()[0])
        self.assertIn("--prerelease", args); self.assertIn("--latest=false", args)
        git(self.repo, "add", "."); git(self.repo, "commit", "-qm", "moved head")
        self.record.unlink()
        cp = self.bash(self.extract + "\n" + self.publish)
        self.assertNotEqual(cp.returncode, 0)
        self.assertFalse(self.record.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
