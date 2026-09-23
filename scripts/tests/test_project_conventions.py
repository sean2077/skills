#!/usr/bin/env python3
"""Real installer preservation checks, not a model test of semantic adaptation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "skills/agent-scaffold/agent-scaffold.sh"


class ProjectConventionPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="project conventions ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "project space"
        self.root.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GIT_", "WORKTREE_", "AGENT_SCAFFOLD_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_OPTIONAL_LOCKS="0")
        self.git("init", "-q", "-b", "main")
        for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid"),
                           ("core.autocrlf", "false"), ("core.symlinks", "true"),
                           ("commit.gpgsign", "false")):
            self.git("config", key, value)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                       env=self.env, stderr=subprocess.PIPE, timeout=30)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def snapshot(self):
        # No symlink traversal and no Git metadata. Index bytes are checked separately.
        result = {}
        for base, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in dirs + files:
                path = Path(base) / name
                relative = path.relative_to(self.root).as_posix()
                if path.is_symlink():
                    result[relative] = ("link", os.readlink(path))
                elif path.is_file():
                    result[relative] = ("file", path.read_bytes())
                else:
                    result[relative] = ("directory",)
        return result

    def invoke(self, mode, *, expected=0, cwd=None):
        args = ["bash", INSTALLER.as_posix(), mode, "--profile", "light"]
        if mode in ("plan", "doctor", "verify"):
            args.append("--json")
        cp = subprocess.run(args, cwd=str(cwd or self.root), env=self.env,
                            capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertEqual(expected, cp.returncode, cp.stdout + cp.stderr)
        if mode in ("plan", "doctor", "verify"):
            data = json.loads(cp.stdout)
            self.assertEqual("harness-assets", data["scope"])
            self.assertEqual("not-assessed", data["project_guidance"])
            return data
        return cp

    def seed(self, docs="doc", tools="scripts"):
        self.write("AGENTS.md", "# 工程约定\n\n[开发入口](%s/开发.md)\n" % docs)
        self.write(docs + "/开发.md", "# 开发\n沿用当前布局。\n")
        self.write("docs/generated/api.md", "generated from schema; do not edit\n")
        self.write("website/config.json", json.dumps({"content": docs}, ensure_ascii=False) + "\n")
        self.write(".editorconfig", "[*]\nindent_size = 3\n")
        self.write("package.json", '{"scripts":{"check":"echo offline-only"}}\n')
        if tools:
            self.write(tools + "/check.py", "raise SystemExit(0)\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture layout")

    def test_read_only_modes_do_not_initialize_project_content(self):
        self.seed()
        before = self.snapshot()
        index = (self.root / ".git/index").read_bytes()
        self.invoke("plan")
        self.invoke("doctor")
        self.invoke("verify", expected=1)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(index, (self.root / ".git/index").read_bytes())

    def test_installer_preserves_multiple_layouts_and_has_no_policy_defaults(self):
        for docs, tools in (("doc", "tool"), ("handbook/pages", "scripts"),
                            ("guide/content", "build-aux"), ("Docs", None)):
            with self.subTest(docs=docs, tools=tools):
                # Independent repositories, so prior layout cannot influence discovery.
                self.root = Path(self.temp.name).resolve() / docs.replace("/", "-")
                self.root.mkdir()
                self.git("init", "-q", "-b", "main")
                for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid"),
                                   ("core.autocrlf", "false"), ("core.symlinks", "true")):
                    self.git("config", key, value)
                self.seed(docs, tools)
                before = self.snapshot()
                index = (self.root / ".git/index").read_bytes()
                # Untracked project work and the existing index must survive.
                self.write("local-note.md", "uncommitted note\n")
                self.invoke("apply", cwd=self.root / docs)
                after = self.snapshot()
                for name, value in before.items():
                    if name == "AGENTS.md":
                        self.assertTrue((self.root / name).read_bytes().startswith(value[1]))
                    else:
                        self.assertEqual(value, after[name], name)
                self.assertEqual(index, (self.root / ".git/index").read_bytes())
                for name in ("tools", "tool", "scripts", "doc", "docs", "DEVELOPMENT.md"):
                    if name not in before:
                        self.assertNotIn(name, after)
                self.assertTrue(self.invoke("verify")["ok"])
                self.invoke("upgrade")
                self.assertEqual(after, self.snapshot())

    def test_upgrade_adopts_user_routes_without_resurrecting_old_guides(self):
        self.seed()
        self.invoke("apply")
        (self.root / "doc").rename(self.root / "handbook")
        self.write("CONTRIBUTING.md", "# Development\nOwner consolidated the guide here.\n")
        (self.root / "handbook/开发.md").unlink()
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.write("AGENTS.md", text.replace("doc/开发.md", "CONTRIBUTING.md"))
        self.write(".editorconfig", "[*]\nindent_size = 7\n")
        self.write("scripts/check.py", "# user-selected implementation\nraise SystemExit(0)\n")
        self.git("add", "CONTRIBUTING.md")
        before = self.snapshot()
        index = (self.root / ".git/index").read_bytes()
        self.invoke("upgrade")
        self.assertEqual(before, self.snapshot())
        self.assertEqual(index, (self.root / ".git/index").read_bytes())
        self.assertFalse((self.root / "doc").exists())
        self.assertFalse((self.root / "handbook/开发.md").exists())
        self.assertTrue(self.invoke("verify")["ok"])

    def test_installer_does_not_write_through_external_document_symlink(self):
        self.seed()
        outside = Path(self.temp.name) / "external guide"
        outside.mkdir()
        (outside / "owner.md").write_bytes(b"external source\n")
        (self.root / "external-docs").symlink_to(outside, target_is_directory=True)
        self.invoke("apply")
        self.assertEqual(["owner.md"], [p.name for p in outside.iterdir()])
        self.assertEqual(b"external source\n", (outside / "owner.md").read_bytes())
        self.assertTrue((self.root / "external-docs").is_symlink())


if __name__ == "__main__":
    unittest.main(verbosity=2)
