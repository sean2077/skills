#!/usr/bin/env python3
"""Exercise checkout-local scaffold hooks with real Git worktrees, not host mocks.

These tests establish filesystem/Git behavior; they do not certify any ADE's
instruction discovery, permission prompts, or live session continuation.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "skills/agent-scaffold/assets/runtime/hooks/hook-paths.py"
INSTALLED = Path(".agents/tools/hooks/hook-paths.py")


class WorkspaceEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="scaffold-entry-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.primary = self.base / "project space"
        self.primary.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith("GIT_") or key.startswith("WORKTREE_") or key == "CLAUDE_PROJECT_DIR":
                self.env.pop(key)
        self.env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
        self.git(self.primary, "init", "-q")
        self.git(self.primary, "config", "user.name", "Workspace Test")
        self.git(self.primary, "config", "user.email", "workspace@example.invalid")
        self.git(self.primary, "config", "commit.gpgsign", "false")
        self.git(self.primary, "config", "core.autocrlf", "false")
        self.git(self.primary, "config", "core.symlinks", "true")
        # Pin the ignore source to an empty file. Without this the fixture
        # inherits the developer's global/XDG excludes, where `.worktrees/` is a
        # common entry; the guard exempts ignored paths, so the deliberately
        # unregistered .worktrees/ directory below would be allowed instead of
        # blocked and the isolation test would fail for environmental reasons.
        excludes = self.base / "empty-excludes"
        excludes.write_bytes(b"")
        self.git(self.primary, "config", "core.excludesFile", str(excludes))
        self.write(self.primary / INSTALLED, SOURCE.read_text(encoding="utf-8"))
        self.write(self.primary / "AGENTS.md", "# Primary contract\n")
        self.write(self.primary / ".agents/skills/local/SKILL.md", "primary skill\n")
        self.write(self.primary / ".gitignore", "ignored.txt\n")
        self.write(self.primary / "src/file.txt", "primary code\n")
        self.git(self.primary, "add", ".")
        self.git(self.primary, "commit", "-qm", "fixture")
        self.internal = self.primary / ".worktrees/task space"
        self.external = self.base / "host cache/task space"
        self.git(self.primary, "worktree", "add", "-qb", "task-internal", str(self.internal))
        self.git(self.primary, "worktree", "add", "-qb", "task-external", str(self.external))

    def git(self, cwd, *args):
        result = subprocess.run(
            ["git", "-C", str(cwd), *args], env=self.env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def guard(self, entry, cwd, target, expected, *, claude=False, grok=False):
        env = self.env.copy()
        if claude:
            env["CLAUDE_PROJECT_DIR"] = str(entry)
        payload = (
            {"workspaceRoot": str(cwd), "toolInput": {"file_path": str(target)}}
            if grok else {"cwd": str(cwd), "tool_input": {"file_path": str(target)}}
        )
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(entry / INSTALLED), "--guard"],
            input=json.dumps(payload), cwd=str(cwd), env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def patch_hook(self, source, target, *, mode="guard", envelope="codex"):
        patch = "*** Begin Patch\n*** Update File: %s\n*** Move to: %s\n@@\n-old\n+new\n*** End Patch\n" % (source, target)
        data = {"cwd": str(self.external), "tool_input": {"patch": patch}}
        if envelope == "grok":
            data = {"workspaceRoot": str(self.external), "toolInput": {"input": patch}}
        elif envelope == "string":
            data["tool_input"] = patch
        env = dict(self.env, AUTHORITY_DOC_MAX_ROOT="1")
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(self.external / INSTALLED), "--" + mode],
            input=json.dumps(data), cwd=str(self.external), env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )

    def test_patch_rename_checks_both_source_and_destination(self):
        for envelope in ("codex", "grok", "string"):
            for src, dst, expected in (
                ("src/file.txt", str(self.primary / "renamed.txt"), 2),
                ("src/file.txt", os.path.relpath(self.primary / "renamed.txt", self.external), 2),
                (str(self.primary / "src/file.txt"), "renamed.txt", 2),
                ("src/file.txt", "src/renamed.txt", 0),
                ("src/file.txt", str(self.primary / "ignored.txt"), 0),
            ):
                with self.subTest(envelope=envelope, src=src, dst=dst):
                    result = self.patch_hook(src, dst, envelope=envelope)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    def test_rename_to_authority_document_reaches_budget_check(self):
        self.write(self.external / "AGENTS.md", "# Contract\nline two\nline three\n")
        result = self.patch_hook("notes.md", "AGENTS.md", mode="budget")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertIn("budget", result.stdout)

    def test_primary_entry_can_target_internal_and_external_worktrees(self):
        for task in (self.internal, self.external):
            for claude in (False, True):
                with self.subTest(task=task, claude=claude):
                    self.guard(self.primary, self.primary, task / "src/file.txt", 0, claude=claude)
                    self.guard(self.primary, task / "src", "file.txt", 0, claude=claude)

    def test_task_entry_can_edit_own_checkout_from_subdirectories(self):
        for task in (self.internal, self.external):
            for claude in (False, True):
                with self.subTest(task=task, claude=claude):
                    self.guard(task, task, "src/file.txt", 0, claude=claude)
                    self.guard(task, task / "src", "file.txt", 0, claude=claude)
                    self.guard(task, task / "src", "new/deep/file.txt", 0, claude=claude)

    def test_primary_edits_remain_blocked_from_every_entry(self):
        for entry in (self.primary, self.internal, self.external):
            for claude in (False, True):
                with self.subTest(entry=entry, claude=claude):
                    self.guard(entry, entry, self.primary / "src/file.txt", 2, claude=claude)
                    relative = os.path.relpath(self.primary / "AGENTS.md", entry / "src")
                    self.guard(entry, entry / "src", relative, 2, claude=claude)

    def test_directory_name_is_not_git_isolation(self):
        # Intentionally not ignored: an ordinary .worktrees/ subdirectory is
        # still the primary checkout, while the registered one next to it is not.
        fake = self.primary / ".worktrees/not-linked/file.txt"
        self.write(fake, "not a worktree\n")
        self.guard(self.primary, self.primary, fake, 2)
        self.guard(self.primary, self.primary, self.internal / "src/file.txt", 0)

    def test_alternate_payload_and_existing_ignored_file_boundary(self):
        self.guard(self.primary, self.external / "src", "file.txt", 0, grok=True)
        self.guard(self.external, self.external, self.primary / "src/file.txt", 2, grok=True)
        self.guard(self.primary, self.primary, "ignored.txt", 0)

    def test_checks_do_not_create_or_reassign_workspaces(self):
        before_registry = self.git(self.primary, "worktree", "list", "--porcelain")
        before_config = (self.primary / ".git/config").read_bytes()
        before_refs = self.git(self.primary, "show-ref")
        before_status = [self.git(p, "status", "--porcelain") for p in (self.primary, self.internal, self.external)]
        for task in (self.internal, self.external):
            self.guard(self.primary, self.primary, task / "src/file.txt", 0)
            self.guard(task, task, self.primary / "src/file.txt", 2)
        self.assertEqual(before_registry, self.git(self.primary, "worktree", "list", "--porcelain"))
        self.assertEqual(before_config, (self.primary / ".git/config").read_bytes())
        self.assertEqual(before_refs, self.git(self.primary, "show-ref"))
        self.assertEqual(before_status, [self.git(p, "status", "--porcelain") for p in (self.primary, self.internal, self.external)])

    def test_tracked_relative_projections_follow_task_revision(self):
        # Real links are required, matching the scaffold's existing platform gate.
        projection = self.primary / ".claude/skills/local"
        projection.parent.mkdir(parents=True)
        try:
            (self.primary / "CLAUDE.md").symlink_to("AGENTS.md")
            projection.symlink_to("../../.agents/skills/local", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"real symlink creation unavailable: {exc}")
        self.git(self.primary, "add", "CLAUDE.md", ".claude")
        self.git(self.primary, "commit", "-qm", "tracked projections")
        revision = self.git(self.primary, "rev-parse", "HEAD").strip()
        self.git(self.external, "merge", "--ff-only", revision)
        self.write(self.external / "AGENTS.md", "# Task contract\n")
        self.write(self.external / ".agents/skills/local/SKILL.md", "task skill\n")
        self.git(self.external, "add", "AGENTS.md", ".agents/skills/local/SKILL.md")
        self.git(self.external, "commit", "-qm", "task-specific context")
        self.assertTrue((self.external / "CLAUDE.md").is_symlink())
        self.assertEqual((self.external / "CLAUDE.md").read_text(encoding="utf-8"), "# Task contract\n")
        self.assertEqual((self.external / ".claude/skills/local/SKILL.md").read_text(encoding="utf-8"), "task skill\n")
        self.assertEqual((self.primary / "AGENTS.md").read_text(encoding="utf-8"), "# Primary contract\n")
        self.assertEqual((self.primary / ".agents/skills/local/SKILL.md").read_text(encoding="utf-8"), "primary skill\n")

    def test_vendored_hook_matches_catalog_source(self):
        self.assertEqual(SOURCE.read_bytes(), (REPO / INSTALLED).read_bytes())


if __name__ == "__main__":
    unittest.main()
