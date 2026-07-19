#!/usr/bin/env python
"""Focused tests for the semver-release read-only planner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNER = REPO_ROOT / "skills" / "semver-release" / "scripts" / "release-plan.py"


class ReleasePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        self.env = os.environ.copy()
        self.env.update(
            {
                "GIT_AUTHOR_NAME": "Release Fixture",
                "GIT_AUTHOR_EMAIL": "release-fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Release Fixture",
                "GIT_COMMITTER_EMAIL": "release-fixture@example.invalid",
            }
        )
        self.git("init", "-q")
        self.git("checkout", "-q", "-b", "main")
        self.commit("chore: initialize fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
            check=check,
        )

    def commit(self, subject: str, body: Optional[str] = None) -> None:
        tracked = self.repo / "tracked.txt"
        previous = tracked.read_text(encoding="utf-8") if tracked.exists() else ""
        tracked.write_text(previous + subject + "\n", encoding="utf-8")
        self.git("add", "--", "tracked.txt")
        command = ["commit", "-q", "-m", subject]
        if body is not None:
            command.extend(["-m", body])
        self.git(*command)

    def tag(self, name: str) -> None:
        self.git("tag", "-a", name, "-m", name)

    def git_path(self, name: str) -> Path:
        path = Path(self.git("rev-parse", "--git-path", name).stdout.strip())
        return path if path.is_absolute() else self.repo / path

    def plan_repo(self, repo: Path, target: Optional[str] = None) -> tuple[int, dict[str, object]]:
        command = [sys.executable, str(PLANNER), "--repo", str(repo), "--json"]
        if target is not None:
            command.extend(["--target", target])
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
            check=False,
        )
        self.assertTrue(completed.stdout, completed.stderr)
        return completed.returncode, json.loads(completed.stdout)

    def plan(self, target: Optional[str] = None) -> tuple[int, dict[str, object]]:
        return self.plan_repo(self.repo, target)

    def attention_ids(self, report: dict[str, object]) -> set[str]:
        return {item["id"] for item in report["attention"]}  # type: ignore[index,union-attr]

    def planner_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PLANNER), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
            check=False,
        )

    def test_infers_patch_without_mutating_repository(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix(api): handle missing value")
        self.git("config", "core.abbrev", "12")
        before = (
            self.git("rev-parse", "HEAD").stdout,
            self.git("status", "--porcelain").stdout,
            self.git("tag", "--list").stdout,
        )

        status, report = self.plan()

        after = (
            self.git("rev-parse", "HEAD").stdout,
            self.git("status", "--porcelain").stdout,
            self.git("tag", "--list").stdout,
        )
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["inferred_bump"], "patch")
        self.assertEqual(report["selected_tag"], "v1.2.4")
        self.assertEqual(
            report["commits"][0]["short_hash"],  # type: ignore[index]
            self.git("rev-parse", "--short", "HEAD").stdout.strip(),
        )
        self.assertEqual(before, after)

    def test_breaking_footer_infers_major(self) -> None:
        self.tag("v1.2.3")
        self.commit("refactor(api): replace transport", "BREAKING-CHANGE: remove v1 transport")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["inferred_bump"], "major")
        self.assertEqual(report["selected_tag"], "v2.0.0")

    def test_exact_target_is_retained_with_mismatch_warning(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: repair state")

        status, report = self.plan("v1.5.0")

        self.assertEqual(status, 0)
        self.assertEqual(report["selected_tag"], "v1.5.0")
        self.assertTrue(any("differs from inferred" in item for item in report["warnings"]))

    def test_prerelease_requires_target_and_stable_uses_previous_stable_notes_base(self) -> None:
        self.tag("v1.1.0")
        self.commit("feat: add preview capability")
        self.tag("v1.2.0-beta.1")
        self.commit("fix: stabilize preview")

        status, report = self.plan()
        promoted_status, promoted = self.plan("v1.2.0")

        self.assertEqual(status, 1)
        self.assertIn("target-tag", self.attention_ids(report))
        self.assertEqual(promoted_status, 0)
        self.assertEqual(promoted["selected_tag"], "v1.2.0")
        self.assertEqual(promoted["release_notes_base"]["tag"], "v1.1.0")  # type: ignore[index]

    def test_dirty_tree_requires_attention(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: repair state")
        (self.repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

        status, report = self.plan()

        self.assertEqual(status, 1)
        self.assertIn("clean-worktree", self.attention_ids(report))

    def test_clean_attached_merge_still_requires_attention(self) -> None:
        self.tag("v1.2.3")
        self.git("checkout", "-q", "-b", "topic")
        self.git("commit", "-q", "--allow-empty", "-m", "fix: topic history")
        self.git("checkout", "-q", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "fix: main history")
        self.git("merge", "-q", "--no-commit", "--no-ff", "topic")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

        status, report = self.plan()

        self.assertEqual(status, 1)
        self.assertNotIn("clean-worktree", self.attention_ids(report))
        self.assertIn("operation-state", self.attention_ids(report))
        operation_check = next(
            item for item in report["checks"] if item["id"] == "operation-state"  # type: ignore[union-attr]
        )
        self.assertEqual(operation_check["operations"], ["merge"])

    def test_stale_rebase_head_without_active_rebase_is_ignored(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: prepare release")
        self.git_path("REBASE_HEAD").write_text(
            self.git("rev-parse", "HEAD").stdout,
            encoding="utf-8",
        )
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertNotIn("operation-state", self.attention_ids(report))
        operation_check = next(
            item for item in report["checks"] if item["id"] == "operation-state"  # type: ignore[union-attr]
        )
        self.assertEqual(operation_check["status"], "ok")

    def test_nonconventional_merge_does_not_mask_child_inference(self) -> None:
        self.tag("v1.2.3")
        self.git("checkout", "-q", "-b", "topic")
        self.git("commit", "-q", "--allow-empty", "-m", "feat: add topic capability")
        self.git("checkout", "-q", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "fix: repair main behavior")
        self.git("merge", "-q", "--no-ff", "-m", "Merge topic", "topic")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["inferred_bump"], "minor")
        self.assertEqual(report["selected_tag"], "v1.3.0")
        merge = next(  # type: ignore[union-attr]
            item for item in report["commits"] if item["subject"] == "Merge topic"
        )
        self.assertEqual(merge["kind"], "merge")
        self.assertNotIn("unclassified-commits", self.attention_ids(report))

    def test_active_rebase_directory_requires_attention(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: prepare release")
        stopped = self.git("rebase", "--exec", "git false", "HEAD~1", check=False)
        self.assertNotEqual(stopped.returncode, 0)
        self.assertTrue(
            self.git_path("rebase-merge").is_dir() or self.git_path("rebase-apply").is_dir()
        )
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

        status, report = self.plan()

        self.assertEqual(status, 1)
        self.assertIn("operation-state", self.attention_ids(report))
        operation_check = next(
            item for item in report["checks"] if item["id"] == "operation-state"  # type: ignore[union-attr]
        )
        self.assertEqual(operation_check["operations"], ["rebase/am"])

    def test_equal_precedence_tags_on_different_commits_are_ambiguous(self) -> None:
        self.tag("v1.2.3+one")
        self.commit("fix: second release point")
        self.tag("v1.2.3+two")

        status, report = self.plan("v1.2.4")

        self.assertEqual(status, 1)
        self.assertIn("reachable-semver-base", self.attention_ids(report))

    def test_invalid_historical_tag_is_ignored_before_ranking(self) -> None:
        self.tag("v01.2.3")
        self.commit("feat: first valid release content")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["selected_tag"], "v0.1.0")
        self.assertEqual(report["ignored_invalid_tags"], ["v01.2.3"])

    def test_first_release_defaults_to_v0_1_0(self) -> None:
        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["base"], None)
        self.assertEqual(report["selected_tag"], "v0.1.0")

    def test_no_commits_after_base_blocks_explicit_target(self) -> None:
        self.tag("v1.2.3")

        status, report = self.plan("v1.2.4")

        self.assertEqual(status, 1)
        self.assertIn("release-commits", self.attention_ids(report))
        self.assertEqual(report["selected_tag"], "v1.2.4")

    def test_unclassified_commit_requires_an_explicit_target(self) -> None:
        self.tag("v1.2.3")
        self.commit("maintenance without conventional type")

        status, report = self.plan()
        explicit_status, explicit = self.plan("v1.2.4")

        self.assertEqual(status, 1)
        self.assertIn("unclassified-commits", self.attention_ids(report))
        self.assertEqual(explicit_status, 0)
        self.assertTrue(any("Unclassified commit" in item for item in explicit["warnings"]))  # type: ignore[union-attr]

    def test_equal_precedence_build_tags_on_one_commit_share_the_base(self) -> None:
        self.tag("v1.2.3+one")
        self.tag("v1.2.3+two")
        self.commit("fix: repair state")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["selected_tag"], "v1.2.4")
        self.assertEqual(report["base"]["tags"], ["v1.2.3+one", "v1.2.3+two"])  # type: ignore[index]

    def test_known_prerelease_order_selects_the_stable_base(self) -> None:
        for tag in (
            "v1.0.0-alpha",
            "v1.0.0-alpha.1",
            "v1.0.0-alpha.beta",
            "v1.0.0-beta",
            "v1.0.0-beta.2",
            "v1.0.0-beta.11",
            "v1.0.0-rc.1",
            "v1.0.0",
        ):
            self.tag(tag)
        self.commit("fix: repair stable release")

        status, report = self.plan()

        self.assertEqual(status, 0)
        self.assertEqual(report["base"]["tag"], "v1.0.0")  # type: ignore[index]
        self.assertEqual(report["selected_tag"], "v1.0.1")

    def test_numbered_prerelease_can_advance_explicitly(self) -> None:
        self.tag("v1.2.3")
        self.commit("feat: preview capability")
        self.tag("v1.3.0-beta.1")
        self.commit("fix: stabilize preview")

        status, report = self.plan("v1.3.0-beta.2")

        self.assertEqual(status, 0)
        self.assertEqual(report["selected_tag"], "v1.3.0-beta.2")

    def test_invalid_existing_and_non_new_targets_require_attention(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: repair state")

        for target in ("1.2.4", "v1.2.3", "v1.2.2"):
            with self.subTest(target=target):
                status, report = self.plan(target)
                self.assertEqual(status, 1)
                self.assertIn("target-tag", self.attention_ids(report))

    def test_detached_head_requires_attention(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: repair state")
        self.git("checkout", "-q", "--detach")

        status, report = self.plan()

        self.assertEqual(status, 1)
        self.assertIn("attached-head", self.attention_ids(report))

    def test_real_shallow_boundary_blocks_base_selection(self) -> None:
        self.tag("v1.2.3")
        self.commit("fix: repair state")
        with tempfile.TemporaryDirectory() as clone_parent:
            shallow = Path(clone_parent) / "shallow"
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", "--no-local", str(self.repo), str(shallow)],
                env=self.env,
                check=True,
            )

            status, report = self.plan_repo(shallow)

        self.assertEqual(status, 1)
        self.assertIn("complete-head-history", self.attention_ids(report))

    def test_help_does_not_mask_invalid_planner_arguments(self) -> None:
        for args in (("--help", "--not-a-real-option"), ("--repo", str(self.repo), "--help")):
            with self.subTest(args=args):
                completed = self.planner_cli(*args)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("cannot be combined", completed.stderr)

    def test_pure_planner_help_succeeds(self) -> None:
        completed = self.planner_cli("--help")

        self.assertEqual(completed.returncode, 0)
        self.assertIn("read-only semantic-release plan", completed.stdout)


if __name__ == "__main__":
    unittest.main()
