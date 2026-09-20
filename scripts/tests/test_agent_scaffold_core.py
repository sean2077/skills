#!/usr/bin/env python3
"""Unit tests for agent-scaffold's deterministic internal core."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
CORE_PATH = REPO / "skills/agent-scaffold/scripts/harness-core.py"
FIXTURES = Path(__file__).with_name("fixtures") / "agent-scaffold"
SPEC = importlib.util.spec_from_file_location("agent_scaffold_core", CORE_PATH)
assert SPEC and SPEC.loader
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)
SYMLINK_MANAGER_PATH = (
    REPO / "skills/agent-scaffold/assets/runtime/symlink-manager.py"
)
SYMLINK_SPEC = importlib.util.spec_from_file_location(
    "agent_scaffold_symlink_manager", SYMLINK_MANAGER_PATH
)
assert SYMLINK_SPEC and SYMLINK_SPEC.loader
SYMLINK_MANAGER = importlib.util.module_from_spec(SYMLINK_SPEC)
SYMLINK_SPEC.loader.exec_module(SYMLINK_MANAGER)


class ManagedAssetsTests(unittest.TestCase):
    def test_manifest_is_complete_and_profile_filtered(self):
        manifest = CORE.load_manifest()
        default_ids = {item["id"] for item in CORE.active_assets(manifest, "default")}
        light_ids = {item["id"] for item in CORE.active_assets(manifest, "light")}
        self.assertIn("runtime.worktree", default_ids)
        self.assertIn("runtime.trunk-guard", default_ids)
        self.assertIn("runtime.hook-launcher", default_ids)
        self.assertNotIn("runtime.worktree", light_ids)
        self.assertNotIn("runtime.trunk-guard", light_ids)
        self.assertIn("runtime.subagent-generator", light_ids)

    def test_duplicate_asset_id_is_rejected(self):
        manifest = CORE.load_manifest()
        manifest["assets"].append(dict(manifest["assets"][0]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CORE.CoreError, "duplicate managed asset id"):
                CORE.load_manifest(path)

    def test_required_semantic_role_is_rejected_when_missing(self):
        manifest = CORE.load_manifest()
        manifest["assets"] = [
            item for item in manifest["assets"] if item["id"] != "runtime.symlink-manager"
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CORE.CoreError, "missing required managed asset"):
                CORE.load_manifest(path)


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_replace_commits_exact_bytes_without_fixed_temp_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidate"
            target = root / "AGENTS.md"
            unrelated = root / "AGENTS.md.tmp"
            source.write_bytes(b"new\ncontent\n")
            target.write_bytes(b"old\n")
            unrelated.mkdir()
            (unrelated / "sentinel").write_text("keep\n", encoding="utf-8")

            CORE.atomic_replace_file(source, target)

            self.assertEqual(b"new\ncontent\n", target.read_bytes())
            self.assertEqual("keep\n", (unrelated / "sentinel").read_text(encoding="utf-8"))
            self.assertEqual([], list(root.glob(".AGENTS.md.agent-scaffold-*")))

    def test_atomic_replace_failure_preserves_previous_target_and_cleans_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidate"
            target = root / ".gitignore"
            source.write_bytes(b"new\n")
            target.write_bytes(b"old\n")

            with mock.patch.object(CORE.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaisesRegex(CORE.CoreError, "atomic replace failed"):
                    CORE.atomic_replace_file(source, target)

            self.assertEqual(b"old\n", target.read_bytes())
            self.assertEqual([], list(root.glob("..gitignore.agent-scaffold-*")))


class AtomicSymlinkTests(unittest.TestCase):
    def test_replace_failure_preserves_previous_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            link = root / "projection"
            previous = b"target\n"
            link.write_bytes(previous)
            try:
                with mock.patch.object(
                    SYMLINK_MANAGER.os,
                    "replace",
                    side_effect=OSError("interrupted"),
                ):
                    with self.assertRaisesRegex(
                        SYMLINK_MANAGER.ContractError,
                        "could not atomically replace projection",
                    ):
                        SYMLINK_MANAGER.create_relative_link(
                            link,
                            target,
                            "target",
                            "materialize-placeholder",
                        )
            except OSError as exc:
                self.skipTest(f"real symlink creation unavailable: {exc}")

            self.assertEqual(previous, link.read_bytes())
            self.assertFalse(link.is_symlink())
            self.assertEqual([], list(root.glob(".projection.agent-scaffold-link-*")))


class TargetInspectionTests(unittest.TestCase):
    def test_agents_render_cli_emits_platform_independent_lf(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "contract.agents")["source"]
        completed = subprocess.run(
            [
                sys.executable,
                str(CORE_PATH),
                "agents",
                "render",
                "--source",
                str(source),
                "--profile",
                "light",
            ],
            check=True,
            stdout=subprocess.PIPE,
        )
        self.assertIn(b"<!-- agent-scaffold:start", completed.stdout)
        self.assertNotIn(b"\r\n", completed.stdout)

    def test_managed_agents_template_uses_semantic_source_lines(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "contract.agents")["source"]
        previous_plain_line = None
        in_fence = False

        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                previous_plain_line = None
                continue
            if in_fence or not stripped:
                previous_plain_line = None
                continue
            if stripped.startswith(("#", "<!--", "|", "- ", "* ", "+ ", "> ")):
                previous_plain_line = None
                continue
            if line != stripped:
                self.fail(f"managed AGENTS prose continues on indented line {number}")
            if previous_plain_line is not None:
                self.fail(
                    "managed AGENTS prose is hard-wrapped across lines "
                    f"{previous_plain_line}-{number}"
                )
            previous_plain_line = number

    def test_plan_accepts_a_contract_target_text_placeholder(self):
        manifest = CORE.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_text("# Contract\n", encoding="utf-8")
            (target / "CLAUDE.md").write_text("AGENTS.md\n", encoding="utf-8")

            data = CORE.build_plan(target, "light", manifest)
            check = next(
                item for item in data["checks"] if item["id"] == "contract.claude-link"
            )
            self.assertEqual("refresh", check["status"])
            self.assertIn("target-text placeholder", check["detail"])

    def test_plan_reports_invalid_hook_json_as_attention(self):
        manifest = CORE.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            config = target / ".claude/settings.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"hooks":', encoding="utf-8")

            data = CORE.build_plan(target, "light", manifest)
            check = next(item for item in data["checks"] if item["id"] == "host.claude-hooks")
            self.assertEqual("attention", check["status"])
            self.assertIn("invalid JSON", check["detail"])
            self.assertFalse(data["ok"])

    def test_plan_reports_non_regular_runtime_as_attention(self):
        manifest = CORE.load_manifest()
        worktree = CORE.asset_by_id(manifest, "runtime.worktree")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / worktree["target"]).mkdir(parents=True)

            data = CORE.build_plan(target, "default", manifest)
            check = next(item for item in data["checks"] if item["id"] == "runtime.worktree")
            self.assertEqual("attention", check["status"])
            self.assertFalse(data["ok"])


class HookReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.user = {"type": "command", "command": "bash .agents/hooks/project-format.sh"}
        self.old_owned = {
            "type": "command",
            "command": "bash .agents/tools/hooks/authority_doc_budget.sh",
        }

    def test_merge_owns_only_current_exact_hook_identities(self):
        existing = {
            "other": {"keep": True},
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write",
                        "hooks": [self.user, self.old_owned],
                    }
                ]
            },
        }
        addition = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Edit|Write",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "bash .agents/tools/hooks/authority_doc_budget.sh --current",
                            }
                        ],
                    }
                ]
            }
        }
        merged = CORE.merge_hooks(existing, addition, self.root)
        commands = [
            hook["command"]
            for group in merged["hooks"]["PostToolUse"]
            for hook in group["hooks"]
        ]
        self.assertIn(self.user["command"], commands)
        self.assertNotIn(self.old_owned["command"], commands)
        self.assertIn("bash .agents/tools/hooks/authority_doc_budget.sh --current", commands)
        self.assertEqual({"keep": True}, merged["other"])

    def test_light_profile_filters_only_the_trunk_guard(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "host.claude-hooks")["source"]
        prepared = CORE.prepare_hooks(source, "light")
        commands = [
            hook["command"]
            for groups in prepared["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertFalse(any("--guard" in command for command in commands))
        self.assertTrue(any("--budget" in command for command in commands))

    def test_verify_compares_complete_managed_hook_objects(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "host.codex-hooks")["source"]
        expected = CORE.prepare_hooks(source, "default")
        wrong_type = json.loads(json.dumps(expected))
        wrong_type["hooks"]["PreToolUse"][0]["hooks"][0]["type"] = "http"
        self.assertFalse(CORE.verify_hooks(wrong_type, expected, self.root))

        wrong_status = json.loads(json.dumps(expected))
        wrong_status["hooks"]["PreToolUse"][0]["hooks"][0]["statusMessage"] = "stale"
        self.assertFalse(CORE.verify_hooks(wrong_status, expected, self.root))

    def test_merge_repairs_complete_managed_hook_identity(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "host.codex-hooks")["source"]
        expected = CORE.prepare_hooks(source, "default")
        existing = json.loads(json.dumps(expected))
        existing["hooks"]["PreToolUse"][0]["hooks"][0].update(
            {"type": "http", "statusMessage": "stale"}
        )

        merged = CORE.merge_hooks(existing, expected, self.root)

        self.assertTrue(CORE.verify_hooks(merged, expected, self.root))
        self.assertEqual(
            expected["hooks"]["PreToolUse"][0]["hooks"][0],
            merged["hooks"]["PreToolUse"][0]["hooks"][0],
        )

    def test_merge_removes_stale_managed_hook_from_wrong_event(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "host.codex-hooks")["source"]
        expected = CORE.prepare_hooks(source, "default")
        existing = {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [self.old_owned],
                    }
                ]
            }
        }

        merged = CORE.merge_hooks(existing, expected, self.root)

        self.assertNotIn("Stop", merged["hooks"])
        self.assertTrue(CORE.verify_hooks(merged, expected, self.root))

    def test_merge_replaces_split_quoted_hook_paths_command(self):
        manifest = CORE.load_manifest()
        source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, "host.claude-hooks")["source"]
        expected = CORE.prepare_hooks(source, "default")
        stale = (
            'python -X utf8 "${CLAUDE_PROJECT_DIR:-.}"'
            "/.agents/tools/hooks/hook-paths.py --budget"
        )
        existing = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Edit|MultiEdit|Write",
                        "hooks": [
                            {"type": "command", "command": stale, "timeout": 30},
                            self.user,
                        ],
                    }
                ]
            }
        }

        merged = CORE.merge_hooks(existing, expected, self.root)
        commands = [
            hook["command"]
            for group in merged["hooks"]["PostToolUse"]
            for hook in group["hooks"]
        ]

        self.assertNotIn(stale, commands)
        self.assertTrue(
            any(
                '"${CLAUDE_PROJECT_DIR:-.}/.agents/tools/hooks/hook-paths.py"' in command
                and "--budget" in command
                for command in commands
            )
        )
        self.assertIn(self.user["command"], commands)

    def test_light_profile_matches_guard_when_script_path_is_quoted(self):
        self.assertTrue(
            CORE.hook_command_has_script_flag(
                'python -X utf8 "${CLAUDE_PROJECT_DIR:-.}/.agents/tools/hooks/hook-paths.py" --guard',
                "hook-paths.py",
                "--guard",
            )
        )
        self.assertTrue(
            CORE.hook_command_has_script_flag(
                'python -X utf8 "${CLAUDE_PROJECT_DIR:-.}"/.agents/tools/hooks/hook-paths.py --guard',
                "hook-paths.py",
                "--guard",
            )
        )
        self.assertFalse(
            CORE.hook_command_has_script_flag(
                'python -X utf8 "${CLAUDE_PROJECT_DIR:-.}/.agents/tools/hooks/hook-paths.py" --budget',
                "hook-paths.py",
                "--guard",
            )
        )

    def test_hook_type_must_be_a_string(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hooks.json"
            path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Edit",
                                    "hooks": [{"type": 7, "command": "echo no"}],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CORE.CoreError, "type must be a string"):
                CORE.validate_hook_config(path, "hooks.json")

    def test_managed_host_assets_invoke_python_directly(self):
        manifest = CORE.load_manifest()
        for asset_id in ("host.claude-hooks", "host.codex-hooks"):
            source = CORE.SKILL_DIR / CORE.asset_by_id(manifest, asset_id)["source"]
            prepared = CORE.prepare_hooks(source, "default")
            commands = [
                hook["command"]
                for groups in prepared["hooks"].values()
                for group in groups
                for hook in group["hooks"]
            ]
            self.assertTrue(commands)
            quoted_script = (
                '"${CLAUDE_PROJECT_DIR:-.}/.agents/tools/hooks/hook-paths.py"'
            )
            split_quoted = (
                '"${CLAUDE_PROJECT_DIR:-.}"/.agents/tools/hooks/hook-paths.py'
            )
            for command in commands:
                self.assertTrue(command.startswith("python -X utf8 "))
                self.assertIn(quoted_script, command)
                self.assertNotIn(split_quoted, command)
                self.assertNotIn("hook-launcher.sh", command)
                self.assertNotIn("bash -lc", command)
            timeouts = [
                hook.get("timeout")
                for groups in prepared["hooks"].values()
                for group in groups
                for hook in group["hooks"]
            ]
            self.assertTrue(timeouts)
            self.assertTrue(all(timeout == 30 for timeout in timeouts))


class HookCommandShellTests(unittest.TestCase):
    """The script path must stay one argv on POSIX bash and Windows PowerShell."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "my project"
        script_dir = self.root / ".agents" / "tools" / "hooks"
        script_dir.mkdir(parents=True)
        self.script = script_dir / "hook-paths.py"
        self.script.write_text(
            "import sys\nprint(sys.argv[0])\nprint(sys.argv[-1])\n",
            encoding="utf-8",
        )
        self.root_posix = str(self.root).replace("\\", "/")
        self.script_posix = "{0}/.agents/tools/hooks/hook-paths.py".format(
            self.root_posix
        )

    @staticmethod
    def _bash_single_quote(value):
        return "'" + value.replace("'", "'\"'\"'") + "'"

    @staticmethod
    def _powershell_single_quote(value):
        return "'" + value.replace("'", "''") + "'"

    def _run_shell(self, command, shell):
        if shell == "powershell":
            return subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
            )
        return subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
        )

    def _shells(self):
        if sys.platform == "win32":
            return ["powershell"]
        if shutil.which("bash"):
            return ["bash"]
        return []

    def test_host_expanded_whole_path_quote_invokes_script(self):
        shells = self._shells()
        self.assertTrue(
            shells, "need bash or PowerShell to exercise hook argv quoting"
        )
        for shell in shells:
            if shell == "powershell":
                python = self._powershell_single_quote(sys.executable)
                command = '& {0} -X utf8 "{1}" --budget'.format(
                    python, self.script_posix
                )
            else:
                python = self._bash_single_quote(sys.executable)
                command = '{0} -X utf8 "{1}" --budget'.format(
                    python, self.script_posix
                )
            result = self._run_shell(command, shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = [line for line in result.stdout.splitlines() if line]
            self.assertGreaterEqual(len(lines), 2, result.stdout)
            self.assertEqual(
                os.path.normcase(os.path.abspath(lines[0])),
                os.path.normcase(os.path.abspath(str(self.script))),
            )
            self.assertEqual(lines[-1], "--budget")

    @unittest.skipUnless(
        sys.platform == "win32",
        "split quoting is valid bash concatenation and only splits on Windows",
    )
    def test_split_placeholder_quote_fails_on_powershell(self):
        python = self._powershell_single_quote(sys.executable)
        root = self._powershell_single_quote(self.root_posix)
        command = "& {0} -X utf8 {1}/.agents/tools/hooks/hook-paths.py --budget".format(
            python, root
        )
        result = self._run_shell(command, "powershell")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("__main__", result.stderr)


HOOK_PATHS_PATH = (
    REPO / "skills/agent-scaffold/assets/runtime/hooks/hook-paths.py"
)
HOOK_PATHS_SPEC = importlib.util.spec_from_file_location(
    "agent_scaffold_hook_paths", HOOK_PATHS_PATH
)
assert HOOK_PATHS_SPEC and HOOK_PATHS_SPEC.loader
HOOK_PATHS = importlib.util.module_from_spec(HOOK_PATHS_SPEC)
HOOK_PATHS_SPEC.loader.exec_module(HOOK_PATHS)


class HookPathTests(unittest.TestCase):
    def test_claude_tool_input_and_grok_tool_input_are_equivalent(self) -> None:
        claude = {"tool_input": {"file_path": r"C:\repo\AGENTS.md"}}
        grok = {
            "cwd": r"C:\repo",
            "workspaceRoot": r"C:\repo",
            "toolInput": {"file_path": r"C:\repo\AGENTS.md"},
        }
        self.assertEqual(HOOK_PATHS.paths(claude), [r"C:\repo\AGENTS.md"])
        self.assertEqual(HOOK_PATHS.paths(grok), [r"C:\repo\AGENTS.md"])

    def test_join_cwd_keeps_absolute_and_joins_relative(self) -> None:
        cwd = os.path.abspath(os.path.join("repo", "root"))
        relative = HOOK_PATHS.join_cwd(cwd, "AGENTS.md")
        self.assertEqual(relative, os.path.abspath(os.path.join(cwd, "AGENTS.md")))
        absolute = os.path.abspath(os.path.join(cwd, "docs", "AGENTS.md"))
        self.assertEqual(HOOK_PATHS.join_cwd(cwd, absolute), absolute)

    @unittest.skipUnless(os.name == "nt", "Git Bash drive paths are a Windows conversion")
    def test_filesystem_path_converts_git_bash_and_unc(self) -> None:
        self.assertEqual(HOOK_PATHS.filesystem_path("/c/Temp/x"), "C:\\Temp\\x")
        self.assertEqual(HOOK_PATHS.filesystem_path("C:/Temp/x"), "C:\\Temp\\x")
        self.assertEqual(
            HOOK_PATHS.filesystem_path("//server/share/x"),
            "\\\\server\\share\\x",
        )
        converted_tmp = HOOK_PATHS.filesystem_path("/tmp/example")
        self.assertFalse(converted_tmp.lower().replace("/", "\\").startswith("t:\\mp"))


class HookGuardBudgetTests(unittest.TestCase):
    def _run(self, mode, payload, env=None):
        merged = os.environ.copy()
        if env:
            merged.update(env)
        return subprocess.run(
            [sys.executable, str(HOOK_PATHS_PATH), mode],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=merged,
            timeout=20,
        )

    def _init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "t@t.t"], check=True
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", "tester"], check=True
        )

    def test_guard_blocks_primary_and_honors_env_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            self._init_repo(repo)
            agents = repo / "AGENTS.md"
            agents.write_text("# contract\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "AGENTS.md"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "base"], check=True
            )
            payload = {"cwd": str(repo), "tool_input": {"file_path": str(agents)}}
            blocked = self._run("--guard", payload, {"CLAUDE_PROJECT_DIR": str(repo)})
            self.assertEqual(blocked.returncode, 2)
            self.assertIn(
                "Only if the user explicitly authorized a trunk edit in this conversation:",
                blocked.stderr,
            )
            allowed = self._run(
                "--guard",
                payload,
                {
                    "CLAUDE_PROJECT_DIR": str(repo),
                    "WORKTREE_ALLOW_TRUNK_EDIT": "1",
                },
            )
            self.assertEqual(allowed.returncode, 0)

    def test_guard_allows_a_linked_worktree_without_git_ignore(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "repo"
            git_dir = primary / ".git"
            lane_git = git_dir / "worktrees" / "lane"
            lane = primary / ".worktrees" / "lane"
            git_dir.mkdir(parents=True)
            lane_git.mkdir(parents=True)
            lane.mkdir(parents=True)
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (lane_git / "commondir").write_text("../..\n", encoding="utf-8")
            (lane_git / "HEAD").write_text(
                "ref: refs/heads/fix/lane\n", encoding="utf-8"
            )
            (lane / ".git").write_text(
                "gitdir: %s\n" % lane_git.as_posix(), encoding="utf-8"
            )
            target = lane / "file.py"
            target.write_text("x\n", encoding="utf-8")
            ident = HOOK_PATHS.git_identity(str(target))
            self.assertIsNotNone(ident)
            self.assertFalse(HOOK_PATHS.is_primary(ident[1], ident[2]))
            result = self._run(
                "--guard",
                {"cwd": str(lane), "tool_input": {"file_path": str(target)}},
                {"CLAUDE_PROJECT_DIR": str(lane)},
            )
            self.assertEqual(result.returncode, 0)

    def test_budget_reports_nested_character_overage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            nested = repo / "docs" / "budget-fixture"
            nested.mkdir(parents=True)
            self._init_repo(repo)
            (repo / "AGENTS.md").write_text("# root\n", encoding="utf-8")
            contract = nested / "AGENTS.md"
            contract.write_text("nested\nentry\n", encoding="utf-8", newline="\n")
            result = self._run(
                "--budget",
                {"cwd": str(repo), "tool_input": {"file_path": str(contract)}},
                {
                    "CLAUDE_PROJECT_DIR": str(repo),
                    "AUTHORITY_DOC_MAX_ROOT": "9999",
                    "AUTHORITY_DOC_MAX_NESTED": "9999",
                    "AUTHORITY_DOC_MAX_ROOT_CHARS": "999999",
                    "AUTHORITY_DOC_MAX_NESTED_CHARS": "1",
                },
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("docs/budget-fixture/AGENTS.md", result.stdout)
            self.assertIn("13 characters (budget 1", result.stdout)

    def test_budget_skips_non_authority_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            self._init_repo(repo)
            readme = repo / "README.md"
            readme.write_text("hello\n", encoding="utf-8")
            result = self._run(
                "--budget",
                {"cwd": str(repo), "tool_input": {"file_path": str(readme)}},
                {"CLAUDE_PROJECT_DIR": str(repo)},
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


class StructuredReportTests(unittest.TestCase):
    def test_schema_v1_matches_the_golden_document(self):
        data = CORE.report(
            "plan",
            Path("<target>"),
            "light",
            [
                CORE.check_record(
                    "runtime.example",
                    "refresh",
                    ".agents/tools/example.py",
                    None,
                ),
                CORE.check_record(
                    "host.example",
                    "attention",
                    ".host/hooks.json",
                    "repair the JSON",
                    "invalid JSON",
                ),
            ],
            "upgrade",
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            CORE.render_report(data, True)
        self.assertEqual(
            (FIXTURES / "report-v1-plan.json").read_text(encoding="utf-8"),
            output.getvalue(),
        )

    def test_unknown_check_status_is_rejected(self):
        with self.assertRaisesRegex(CORE.CoreError, "unknown check status"):
            CORE.check_record("contract.example", "maybe", None, None)

    def test_plan_schema_and_upgrade_decision_share_one_model(self):
        manifest = CORE.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            data = CORE.build_plan(target, "default", manifest)
            self.assertEqual(1, data["schema_version"])
            self.assertEqual("apply", data["apply_mode"])
            self.assertTrue(all(set(("id", "status", "path", "fix")) <= set(item) for item in data["checks"]))

            worktree = CORE.asset_by_id(manifest, "runtime.worktree")
            installed = target / worktree["target"]
            installed.parent.mkdir(parents=True)
            installed.write_text("drift\n", encoding="utf-8")
            data = CORE.build_plan(target, "default", manifest)
            self.assertEqual("upgrade", data["apply_mode"])
            drift = next(item for item in data["checks"] if item["id"] == "runtime.worktree")
            self.assertEqual("refresh", drift["status"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                CORE.render_report(data, True)
            rendered = json.loads(output.getvalue())
            self.assertEqual(data, rendered)

    def test_verify_reports_managed_block_and_line_contract_drift(self):
        manifest = CORE.load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_text(
                "<!-- agent-scaffold:start -->\nBROKEN MANAGED CONTENT\n"
                "<!-- agent-scaffold:end -->\n",
                encoding="utf-8",
            )
            with mock.patch.object(CORE, "run_tool", return_value=(0, "")):
                data = CORE.build_verify(
                    target,
                    "light",
                    manifest,
                    CORE.SKILL_DIR
                    / CORE.asset_by_id(manifest, "runtime.symlink-manager")["source"],
                )

            content = next(
                item for item in data["checks"] if item["id"] == "contract.agents-content"
            )
            attributes = next(
                item for item in data["checks"] if item["id"] == "contract.gitattributes"
            )
            self.assertEqual("fail", content["status"])
            self.assertEqual("fail", attributes["status"])


class LineEndingPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="scaffold-eol-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / "repo space-雪"
        self.target.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "EOL Test")
        self.git("config", "user.email", "eol@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.safecrlf", "false")
        self.git("config", "core.eol", "crlf")
        self.git("config", "core.symlinks", "true")
        self.manifest = CORE.load_manifest()
        self.source = CORE.SKILL_DIR / CORE.asset_by_id(self.manifest, "contract.line-endings")["source"]

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout

    def policy(self, content=b""):
        path = self.target / ".gitattributes"
        path.write_bytes(content)
        path.write_bytes(CORE.line_endings_candidate(path, self.source))
        # The existing append-only runtime lines remain independently owned.
        for item in CORE.active_line_invariants(self.manifest, "default"):
            if item["target"] == ".gitattributes":
                data = path.read_bytes()
                path.write_bytes(data + (b"\n" if data and not data.endswith(b"\n") else b"")
                                 + ("\n".join(item["lines"]) + "\n").encode())

    def check(self, check_id):
        return next(item for item in CORE.line_endings_checks(self.target, "default", self.manifest)
                    if item["id"] == check_id)

    def test_prefix_preserves_project_bytes_bom_exceptions_and_idempotence(self):
        original = b'\xef\xbb\xbf# custom\r\n*.dat -text\r\n*.txt text eol=crlf'
        path = self.target / ".gitattributes"
        path.write_bytes(original)
        candidate = CORE.line_endings_candidate(path, self.source)
        self.assertEqual(original[:3] + self.source.read_bytes() + original[3:], candidate)
        path.write_bytes(candidate)
        self.assertEqual(candidate, CORE.line_endings_candidate(path, self.source))
        fields = self.git("check-attr", "-z", "eol", "--", "note.txt").split(b"\0")
        self.assertEqual(b"crlf", fields[2])

    def test_marker_refresh_is_lf_without_rewriting_project_crlf(self):
        path = self.target / ".gitattributes"
        authored = b"# keep\r\n*.bin -text\r\n"
        path.write_bytes(authored + self.source.read_bytes().replace(b"\n", b"\r\n"))
        candidate = CORE.line_endings_candidate(path, self.source)
        self.assertEqual(self.source.read_bytes() + authored, candidate)
        path.write_bytes(candidate)
        self.assertEqual(candidate, CORE.line_endings_candidate(path, self.source))

    def test_malformed_markers_raise_before_writes(self):
        path = self.target / ".gitattributes"
        fixtures = (
            CORE.EOL_START + b"\n",
            CORE.EOL_END + b"\n" + CORE.EOL_START + b"\n",
            self.source.read_bytes() * 2,
            CORE.EOL_START + b" extra\n" + CORE.EOL_END + b"\n",
        )
        for data in fixtures:
            with self.subTest(data=data):
                path.write_bytes(data)
                with self.assertRaises(CORE.CoreError):
                    CORE.line_endings_candidate(path, self.source)
                self.assertEqual(data, path.read_bytes())

    def test_default_checkout_is_lf_for_all_autocrlf_modes(self):
        self.policy()
        (self.target / "nested").mkdir()
        fixtures = {
            "nested/note-雪.md": b"alpha\nbeta\n",
            "program.py": b"print(1)\nprint(2)\n",
            "config.json": b'{\n  "value": 1\n}\n',
            "configure": b"#!/bin/sh\necho hello\n",
            "payload.bin": b"\x00binary\r\n\xff\x00",
            "run.bat": b"@echo off\r\necho test\r\n",
            "run.CmD": b"@echo off\r\necho test\r\n",
        }
        for name, data in fixtures.items():
            (self.target / name).write_bytes(data)
        self.git("add", "--all")
        for mode in ("true", "input", "false"):
            with self.subTest(autocrlf=mode):
                self.git("config", "core.autocrlf", mode)
                for name, data in fixtures.items():
                    path = self.target / name
                    path.unlink()
                    self.git("checkout-index", "--", name)
                    self.assertEqual(data, path.read_bytes(), name)
                self.assertEqual("pass", self.check("line-endings.tracked")["status"])
        self.assertEqual(b"@echo off\necho test\n", self.git("show", ":run.bat"))

    def test_root_nested_and_binary_exceptions_are_honored(self):
        self.policy(b"*.txt text eol=crlf\n*.fixture -text\n*.lfs filter=lfs -text\n")
        nested = self.target / "nested"; nested.mkdir()
        (nested / ".gitattributes").write_bytes(b"*.md text eol=crlf\n")
        fixtures = {"a.txt": b"a\r\nb\r\n", "nested/b.md": b"a\r\nb\r\n",
                    "raw.fixture": b"exact\r\nbytes\n", "raw.lfs": b"version\r\n"}
        for name, data in fixtures.items():
            (self.target / name).write_bytes(data)
        self.git("add", "--all")
        for name, data in fixtures.items():
            (self.target / name).unlink()
            self.git("checkout-index", "--", name)
            self.assertEqual(data, (self.target / name).read_bytes())
        self.assertEqual("pass", self.check("line-endings.tracked")["status"])

    def test_existing_crlf_is_diagnosed_without_converting_or_staging(self):
        file = self.target / "legacy.txt"
        file.write_bytes(b"old\r\nlines\r\n")
        self.git("add", "legacy.txt")
        self.policy()
        index = self.git("rev-parse", "--git-path", "index").decode().strip()
        index_path = Path(index) if Path(index).is_absolute() else self.target / index
        before = index_path.read_bytes()
        result = self.check("line-endings.tracked")
        self.assertEqual("fail", result["status"])
        self.assertIn("legacy.txt", result["detail"])
        self.assertIn("i/crlf", result["detail"])
        self.assertEqual(before, index_path.read_bytes())
        self.assertEqual(b"old\r\nlines\r\n", file.read_bytes())
        # Only an explicit caller action normalizes the index; it does not rewrite the worktree.
        self.git("add", "--renormalize", "--", "legacy.txt")
        self.assertEqual("fail", self.check("line-endings.tracked")["status"])
        file.write_bytes(b"old\nlines\n")
        self.assertEqual("pass", self.check("line-endings.tracked")["status"])

    def test_mixed_tracked_text_is_not_hidden_by_git_clean_diff(self):
        self.policy()
        file = self.target / "note.md"; file.write_bytes(b"one\ntwo\n")
        self.git("add", "--all")
        file.write_bytes(b"one\r\ntwo\n")
        self.assertEqual(b"", self.git("diff", "--", "note.md"))
        result = self.check("line-endings.tracked")
        self.assertEqual("fail", result["status"])
        self.assertIn("w/mixed", result["detail"])

    def test_effective_runtime_attributes_catch_later_nested_and_info_overrides(self):
        self.policy()
        self.assertEqual("pass", self.check("line-endings.runtime-attributes")["status"])
        for name, rule in ((".gitattributes", b".agents/tools/*.sh text eol=crlf\n"),
                           (".agents/tools/.gitattributes", b"*.sh -text\n"),
                           (".git/info/attributes", b".agents/tools/*.py text eol=crlf\n")):
            with self.subTest(name=name):
                path = self.target / name; path.parent.mkdir(parents=True, exist_ok=True)
                before = path.read_bytes() if path.exists() else None
                path.write_bytes((before or b"") + rule)
                self.assertEqual("fail", self.check("line-endings.runtime-attributes")["status"])
                if before is None:
                    path.unlink()
                else:
                    path.write_bytes(before)

    def test_plan_reports_eol_conflicts_without_mutation(self):
        for name in (".gitattributes", ".editorconfig"):
            with self.subTest(name=name):
                path = self.target / name; path.mkdir()
                before = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))
                data = CORE.build_plan(self.target, "light", self.manifest)
                item = next(c for c in data["checks"] if c["path"] == name)
                self.assertEqual("attention", item["status"])
                self.assertEqual(before, sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*")))
                path.rmdir()

    def test_symlinked_policy_is_never_followed(self):
        outside = self.root / "outside"; outside.write_bytes(b"untouched\n")
        link = self.target / ".gitattributes"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest("symlink capability unavailable: {0}".format(exc))
        with self.assertRaises(CORE.CoreError):
            CORE.line_endings_candidate(link, self.source)
        self.assertEqual(b"untouched\n", outside.read_bytes())

    def run_installer(self, *args):
        # Resolve PATH explicitly: native Windows CreateProcess may otherwise
        # select System32's WSL bash before Git Bash. MSYS accepts D:/ paths.
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "Git Bash/POSIX bash is required for installer tests")
        return subprocess.run(
            [bash, (CORE.SKILL_DIR / "agent-scaffold.sh").as_posix(), *args],
            cwd=self.target, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_installer_preserves_existing_editor_settings_and_staged_user_work(self):
        editor = self.target / ".editorconfig"
        original = b"root=true\r\n[*]\r\nindent_size=8\r\nend_of_line=crlf\r\n"
        editor.write_bytes(original)
        (self.target / "staged.txt").write_bytes(b"user work\n")
        self.git("add", "staged.txt")
        before = self.git("ls-files", "--stage", "-z")
        config = (self.target / ".git/config").read_bytes()
        for mode in ("apply", "upgrade", "apply"):
            result = self.run_installer(mode, "--profile", "light")
            self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(original, editor.read_bytes())
            self.assertEqual(before, self.git("ls-files", "--stage", "-z"))
            self.assertEqual(config, (self.target / ".git/config").read_bytes())
            self.assertEqual(1, (self.target / ".gitattributes").read_bytes().count(CORE.EOL_START))
        self.assertEqual("pass", self.check("line-endings.tracked")["status"])

    def test_installer_blocks_malformed_policy_before_any_harness_write(self):
        path = self.target / ".gitattributes"; original = CORE.EOL_START + b"\n"
        path.write_bytes(original)
        for mode in ("apply", "upgrade"):
            result = self.run_installer(mode)
            self.assertEqual(2, result.returncode, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(original, path.read_bytes())
            self.assertFalse((self.target / "AGENTS.md").exists())
            self.assertFalse((self.target / ".agents").exists())
            self.assertFalse((self.target / ".editorconfig").exists())

    def test_diagnostics_handle_tabs_and_newlines(self):
        if os.name == "nt":
            self.skipTest("these filename bytes are POSIX-only")
        self.policy()
        raw_path = os.fsencode(self.target) + b"/unusual\tname\n.md"
        with open(raw_path, "wb") as stream:
            stream.write(b"one\ntwo\n")
        self.git("add", "--all")
        with open(raw_path, "wb") as stream:
            stream.write(b"one\r\ntwo\n")
        result = self.check("line-endings.tracked")
        self.assertEqual("fail", result["status"])
        json.dumps(result, ensure_ascii=False).encode("utf-8")

    def test_non_utf8_git_output_names_have_portable_diagnostics(self):
        self.policy()
        file = self.target / "ordinary.md"
        file.write_bytes(b"one\ntwo\n")
        self.git("add", "--all")
        file.write_bytes(b"one\r\ntwo\n")
        run = CORE.subprocess.run

        def non_utf8_output(*args, **kwargs):
            completed = run(*args, **kwargs)
            if "--eol" in args[0]:
                # Keep real Git byte-state evidence; only replace the filename
                # in its output. APFS/Windows cannot create this raw name.
                marker = b"\tordinary.md\0"
                self.assertIn(marker, completed.stdout)
                completed.stdout = completed.stdout.replace(marker, b"\tnon-utf8-\xff.md\0")
            return completed

        with mock.patch.object(CORE.subprocess, "run", side_effect=non_utf8_output):
            result = self.check("line-endings.tracked")
        self.assertEqual("fail", result["status"])
        self.assertIn(r"non-utf8-\xff.md", result["detail"])
        self.assertIn("w/mixed", result["detail"])
        json.dumps(result, ensure_ascii=False).encode("utf-8")

    def test_git_errors_are_failures_not_empty_success(self):
        with mock.patch.object(CORE.subprocess, "run", side_effect=OSError("no git")):
            result = CORE.line_endings_checks(self.target, "light", self.manifest)
        self.assertEqual("line-endings.git", result[-1]["id"])
        self.assertEqual("fail", result[-1]["status"])


if __name__ == "__main__":
    unittest.main()
