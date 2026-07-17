#!/usr/bin/env python3
"""Unit tests for agent-scaffold's deterministic internal core."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
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


class ManagedAssetsTests(unittest.TestCase):
    def test_manifest_is_complete_and_profile_filtered(self):
        manifest = CORE.load_manifest()
        default_ids = {item["id"] for item in CORE.active_assets(manifest, "default")}
        light_ids = {item["id"] for item in CORE.active_assets(manifest, "light")}
        self.assertIn("runtime.worktree", default_ids)
        self.assertIn("runtime.trunk-guard", default_ids)
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
        self.assertFalse(any("trunk_edit_guard" in command for command in commands))
        self.assertTrue(any("authority_doc_budget" in command for command in commands))


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


if __name__ == "__main__":
    unittest.main()
