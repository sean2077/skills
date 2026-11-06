#!/usr/bin/env python3
"""Exercise worktree cleanup against real Git state and Windows directory locks.

The injected Git failure covers a partial removal boundary on every platform;
the native Windows cases additionally hold an actual process current directory.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "skills/agent-scaffold/assets/runtime/worktree.sh"
INSTALLED = Path(".agents/tools/worktree.sh")


class WorktreeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="scaffold cleanup ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.primary = self.base / "project space"
        self.primary.mkdir()
        self.origin = self.base / "origin.git"
        self.bash = shutil.which("bash")
        self.real_git = shutil.which("git")
        self.assertIsNotNone(self.bash, "Git Bash/POSIX bash is required")
        self.assertIsNotNone(self.real_git, "Git is required")
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(("GIT_", "WORKTREE_")) or key in ("BASH_ENV", "ENV", "CDPATH"):
                self.env.pop(key)
        self.env.update({
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
            "WORKTREE_REMOVE_RETRIES": "0", "WORKTREE_REMOVE_RETRY_DELAY_SECONDS": "0",
        })
        self.git(self.primary, "init", "-q", "-b", "main")
        for key, value in (
            ("user.name", "Worktree Test"),
            ("user.email", "worktree@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.autocrlf", "false"),
            ("core.symlinks", "true"),
            ("core.hooksPath", (self.base / "empty-hooks").as_posix()),
        ):
            self.git(self.primary, "config", key, value)
        self.helper = self.primary / INSTALLED
        self.helper.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, self.helper)
        self.write(self.primary / ".gitignore", ".worktrees/\n")
        self.write(self.primary / "nested/base.txt", "base\n")
        self.git(self.primary, "add", ".")
        self.git(self.primary, "commit", "-qm", "fixture")
        self.git(self.base, "init", "--bare", "-q", str(self.origin))
        self.git(self.primary, "remote", "add", "origin", str(self.origin))
        self.git(self.primary, "push", "-qu", "origin", "main")

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def git(self, cwd, *args):
        result = subprocess.run(
            [self.real_git, "-C", str(cwd), *args], env=self.env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def invoke(self, *args, cwd=None, extra_env=None):
        env = self.env.copy()
        env.update(extra_env or {})
        return subprocess.run(
            [self.bash, self.helper.as_posix(), *args],
            cwd=str(cwd or self.primary), env=env, input="",
            capture_output=True, text=True, encoding="utf-8", timeout=45,
        )

    def assert_code(self, result, expected):
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    def task(self, name="task space", *, detached=False):
        target = self.primary / ".worktrees" / name
        args = ["worktree", "add", "-q"]
        args += ["--detach"] if detached else ["-b", "fix/task"]
        self.git(self.primary, *args, str(target), "main")
        if not detached:
            self.write(target / "change.txt", "task commit\n")
            self.git(target, "add", "change.txt")
            self.git(target, "commit", "-qm", "task change")
        return target

    def orphan(self, name="orphan space"):
        target = self.primary / ".worktrees" / name
        target.mkdir(parents=True)
        return target

    def state(self):
        return (
            self.git(self.primary, "for-each-ref", "--format=%(refname) %(objectname)"),
            self.git(self.primary, "worktree", "list", "--porcelain", "-z"),
            self.git(self.origin, "for-each-ref", "--format=%(refname) %(objectname)"),
        )

    def assert_refused_unchanged(self, target, *, cwd=None):
        before = self.state()
        result = self.invoke("cleanup", "--dir", str(target), cwd=cwd)
        self.assert_code(result, 2)
        self.assertEqual(self.state(), before)

    def test_done_from_target_root_stops_before_merge_push_or_removal(self):
        target = self.task()
        before = self.state()
        result = self.invoke("done", cwd=target)
        self.assert_code(result, 2)
        self.assertEqual(self.state(), before)
        self.assertEqual((target / "change.txt").read_bytes(), b"task commit\n")

    def test_done_from_target_descendant_stops_before_merge_push_or_removal(self):
        target = self.task()
        before = self.state()
        result = self.invoke("done", "--dir", target.as_posix(), cwd=target / "nested")
        self.assert_code(result, 2)
        self.assertEqual(self.state(), before)
        self.assertTrue((target / ".git").is_file())

    def test_detached_done_from_target_preserves_registration(self):
        target = self.task(detached=True)
        before = self.state()
        result = self.invoke("done", "--dir", target.as_posix(), cwd=target)
        self.assert_code(result, 2)
        self.assertEqual(self.state(), before)
        self.assertTrue((target / ".git").is_file())

    def test_done_from_stable_directory_still_integrates_and_removes(self):
        target = self.task()
        result = self.invoke("done", "--dir", target.as_posix())
        self.assert_code(result, 0)
        self.assertFalse(target.exists())
        self.assertEqual(self.git(self.primary, "branch", "--list", "fix/task"), "")
        self.assertEqual(
            self.git(self.primary, "rev-parse", "main"),
            self.git(self.origin, "rev-parse", "main"),
        )
        self.assertEqual((self.primary / "change.txt").read_bytes(), b"task commit\n")

    def test_cleanup_empty_residue_is_idempotent_without_git_side_effects(self):
        target = self.orphan()
        self.git(self.primary, "branch", "retained-review-branch")
        before = self.state()
        for _ in range(2):
            result = self.invoke("cleanup", "--dir", target.as_posix())
            self.assert_code(result, 0)
            self.assertFalse(target.exists())
            self.assertEqual(self.state(), before)

    def test_cleanup_from_residue_requires_leaving_the_owning_shell_directory(self):
        target = self.orphan()
        self.assert_refused_unchanged(target, cwd=target)
        self.assertTrue(target.is_dir())

    def test_cleanup_refuses_registered_worktree_even_if_directory_is_missing(self):
        target = self.task()
        self.assert_refused_unchanged(target)
        shutil.rmtree(target)
        self.assert_refused_unchanged(target)
        if os.name == "nt":
            self.assert_refused_unchanged(target.as_posix().swapcase())

    def test_cleanup_preserves_nonempty_and_git_marker_residue(self):
        for index, filename in enumerate(("notes.txt", ".hidden", ".git", "nested/notes.txt")):
            with self.subTest(filename=filename):
                target = self.orphan("nonempty-" + str(index))
                marker = target / filename
                self.write(marker, "must survive\n")
                self.assert_refused_unchanged(target)
                self.assertEqual(marker.read_bytes(), b"must survive\n")

    def test_cleanup_rejects_primary_outside_nested_and_traversal_targets(self):
        target = self.orphan()
        outside = self.base / "unrelated empty"
        outside.mkdir()
        nested = target / "child"
        nested.mkdir()
        prefix_sibling = self.primary / ".worktrees-other" / "empty"
        prefix_sibling.mkdir(parents=True)
        traversal = str(target / "child") + "/../.."
        candidates = (
            self.primary, self.primary / ".worktrees", outside, nested,
            prefix_sibling, traversal, self.base / "missing outside",
            self.primary / ".worktrees" / "missing parent" / "missing child",
        )
        for candidate in candidates:
            with self.subTest(path=str(candidate)):
                self.assert_refused_unchanged(candidate)
        self.assertTrue(outside.is_dir())
        self.assertTrue(nested.is_dir())
        self.assertTrue(prefix_sibling.is_dir())

    def test_cleanup_requires_explicit_absolute_directory(self):
        target = self.orphan()
        before = self.state()
        for args in (
            ("cleanup",), ("cleanup", "--dir"),
            ("cleanup", "--dir", ".worktrees/orphan space"),
            ("cleanup", "--dir", target.as_posix(), "--force"),
        ):
            with self.subTest(args=args):
                self.assert_code(self.invoke(*args), 2)
                self.assertTrue(target.is_dir())
                self.assertEqual(self.state(), before)

    def test_cleanup_rejects_line_break_paths_without_removing_another_directory(self):
        for index, suffix in enumerate(("\n", "\r", "\r\n")):
            with self.subTest(suffix=repr(suffix)):
                sibling = self.orphan("line-break-" + str(index))
                target = Path(str(sibling) + suffix)
                # POSIX permits these as distinct directories. Windows rejects
                # such names, but must still preserve the ordinary sibling.
                if os.name != "nt":
                    target.mkdir()
                self.assert_refused_unchanged(target)
                self.assertTrue(sibling.is_dir())
                if os.name != "nt":
                    self.assertTrue(target.is_dir())

    def test_cleanup_refuses_symlinks_including_dangling_targets(self):
        external = self.base / "external empty"
        external.mkdir()
        link = self.primary / ".worktrees" / "linked"
        link.parent.mkdir()
        try:
            link.symlink_to(external, target_is_directory=True)
        except OSError as exc:
            self.skipTest("real symlink creation unavailable: " + str(exc))
        for candidate in (link.as_posix(), link.as_posix() + "/"):
            self.assert_refused_unchanged(candidate)
            self.assertTrue(link.is_symlink())
            self.assertTrue(external.is_dir())
        external.rmdir()
        self.assert_refused_unchanged(link)
        self.assertTrue(link.is_symlink())

    def test_cleanup_refuses_symlinked_worktree_base(self):
        storage = self.base / "external storage"
        storage.mkdir()
        wt_base = self.primary / ".worktrees"
        try:
            wt_base.symlink_to(storage, target_is_directory=True)
        except OSError as exc:
            self.skipTest("real symlink creation unavailable: " + str(exc))
        target = wt_base / "empty"
        target.mkdir()
        self.assert_refused_unchanged(target)
        self.assertTrue(wt_base.is_symlink())
        self.assertTrue((storage / "empty").is_dir())

    def test_done_partial_removal_reports_pending_and_retains_branch_for_recovery(self):
        target = self.task()
        shim_dir = self.base / "git shim"
        shim = shim_dir / "git"
        self.write(shim, """#!/usr/bin/env bash
args=("$@")
command_index=0
[[ "${args[0]:-}" != -C ]] || command_index=2
if [[ "${args[$command_index]:-}" == worktree && "${args[$((command_index + 1))]:-}" == remove ]]; then
    "${TEST_REAL_GIT:?}" "$@" || exit $?
    target="${args[$((command_index + 2))]}"
    mkdir -p "$target"
    printf 'late data\\n' > "$target/keep.txt"
    exit 1
fi
exec "${TEST_REAL_GIT:?}" "$@"
""")
        shim.chmod(0o755)
        result = self.invoke("done", "--dir", target.as_posix(), "--no-push", extra_env={
            "PATH": str(shim_dir) + os.pathsep + self.env["PATH"],
            "TEST_REAL_GIT": Path(self.real_git).as_posix(),
        })
        self.assert_code(result, 3)
        self.assertFalse((target / ".git").exists())
        self.assertEqual((target / "keep.txt").read_bytes(), b"late data\n")
        self.assertNotEqual(self.git(self.primary, "branch", "--list", "fix/task"), "")
        before = self.state()
        self.assert_refused_unchanged(target)
        (target / "keep.txt").unlink()
        self.assert_code(self.invoke("cleanup", "--dir", target.as_posix()), 0)
        self.assertFalse(target.exists())
        self.assertEqual(self.state(), before)

    @contextmanager
    def cwd_holder(self, target):
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", "import sys; print('ready', flush=True); sys.stdin.read(1)"],
            cwd=str(target), env=self.env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        )
        ready = queue.Queue()
        reader = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            self.assertEqual(ready.get(timeout=15), "ready\n", "native CWD holder failed to start")
            yield
        finally:
            try:
                process.communicate(input="\n", timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=15)
            reader.join(timeout=1)

    @unittest.skipUnless(os.name == "nt", "requires native Windows process-CWD locking")
    def test_windows_parent_cwd_lock_blocks_done_before_any_mutation(self):
        target = self.task()
        before = self.state()
        with self.cwd_holder(target):
            result = self.invoke("done", "--dir", target.as_posix())
            self.assert_code(result, 2)
            self.assertEqual(self.state(), before)
            self.assertTrue((target / ".git").is_file())
        self.assert_code(self.invoke("done", "--dir", target.as_posix()), 0)
        self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "nt", "requires native Windows process-CWD locking")
    def test_windows_locked_orphan_is_pending_then_recoverable(self):
        target = self.orphan()
        before = self.state()
        with self.cwd_holder(target):
            # This establishes that the fixture owns a real OS directory lock.
            with self.assertRaises(PermissionError):
                target.rmdir()
            result = self.invoke("cleanup", "--dir", target.as_posix())
            self.assert_code(result, 3)
            self.assertTrue(target.is_dir())
            self.assertEqual(self.state(), before)
        for _ in range(2):
            self.assert_code(self.invoke("cleanup", "--dir", target.as_posix()), 0)
            self.assertFalse(target.exists())
            self.assertEqual(self.state(), before)

    @unittest.skipUnless(os.name == "nt", "Windows directory junctions require native Windows")
    def test_windows_cleanup_refuses_junction_even_with_empty_target(self):
        target = self.base / "junction destination"
        target.mkdir()
        link = self.primary / ".worktrees" / "junction"
        link.parent.mkdir()
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_refused_unchanged(link)
        self.assertTrue(link.is_dir())
        self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
