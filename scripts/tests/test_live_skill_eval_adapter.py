from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "evals" / "agent-skills" / "host_adapter.py"
VERIFIER_PATH = ROOT / "evals" / "agent-skills" / "verifier.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveSkillEvalAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = load_module("agent_skill_eval_host_adapter", ADAPTER_PATH)
        cls.verifier = load_module("agent_skill_eval_verifier", VERIFIER_PATH)

    def test_catalog_routes_are_derived_from_skill_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("zeta", "alpha"):
                skill = root / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: fixture\n---\n", encoding="utf-8"
                )
            (root / "skills" / "not-a-skill").mkdir()
            self.assertEqual(("alpha", "zeta"), self.adapter.catalog_routes(root))

    def test_baseline_normalization_preserves_host_workflow(self) -> None:
        routes = ("analyze", "autopilot", "tdd")
        for workflow in ("analysis", "delivery", "interview", "tdd"):
            with self.subTest(workflow=workflow):
                actual = self.adapter.canonicalize_behavior(
                    {"mode": "baseline"},
                    {"route": "autopilot", "workflow": workflow},
                    "none",
                    False,
                    routes,
                )
                self.assertEqual("none", actual["route"])
                self.assertEqual(workflow, actual["workflow"])

    def test_selected_treatment_binds_candidate_and_normalizes_keys(self) -> None:
        actual = self.adapter.canonicalize_behavior(
            {"mode": "treatment"},
            {
                "route": "none",
                "workflow": "docs-organization",
                "decision-depth": "compact",
            },
            "project-docs-organizer",
            True,
            ("project-docs-organizer", "spec-writing"),
        )
        self.assertEqual(
            {
                "route": "project-docs-organizer",
                "workflow": "documentation-organization",
                "decision_depth": "compact",
            },
            actual,
        )

    def test_rejected_treatment_preserves_nearest_valid_route(self) -> None:
        actual = self.adapter.canonicalize_behavior(
            {"mode": "treatment"},
            {"route": "docs-organizer", "workflow": "docs-organization"},
            "tooling-conventions",
            False,
            ("project-docs-organizer", "tooling-conventions"),
        )
        self.assertEqual("project-docs-organizer", actual["route"])
        self.assertEqual("documentation-organization", actual["workflow"])

    def test_prompt_uses_catalog_vocabulary_without_case_metadata(self) -> None:
        request = {
            "mode": "treatment",
            "case": {
                "prompt": "Move one established documentation page.",
                "metadata": {"expected_behavior": "DO_NOT_LEAK_THIS_SENTINEL"},
            },
        }
        prompt = self.adapter.make_prompt(
            request,
            "candidate instructions",
            "project-docs-organizer",
            ("project-docs-organizer", "spec-writing"),
        )
        self.assertIn("project-docs-organizer, spec-writing", prompt)
        self.assertIn("decision_depth=compact or full", prompt)
        self.assertNotIn("DO_NOT_LEAK_THIS_SENTINEL", prompt)

    def test_baseline_host_selection_is_not_silently_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "skills" / "analyze"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: analyze\ndescription: fixture\n---\n", encoding="utf-8"
            )
            request = {
                "repository_root": str(root),
                "run_id": "baseline-selection",
                "mode": "baseline",
                "case": {"prompt": "Explain the flow."},
            }
            host = {
                "result": json.dumps(
                    {
                        "selected": True,
                        "behavior": {"route": "analyze", "workflow": "analysis"},
                    }
                )
            }
            stdin = io.StringIO(json.dumps(request))
            stdout = io.StringIO()
            completed = types.SimpleNamespace(stdout=json.dumps(host))
            with contextlib.redirect_stdout(stdout), mock.patch(
                "sys.stdin", stdin
            ), mock.patch.object(
                self.adapter.shutil, "which", return_value="/fake/claude"
            ), mock.patch.object(
                self.adapter.subprocess, "run", return_value=completed
            ):
                self.assertEqual(0, self.adapter.main())
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["selected"])
            self.assertEqual("none", payload["metadata"]["behavior"]["route"])

    def test_invalid_request_emits_a_failed_adapter_envelope(self) -> None:
        stdin = io.StringIO("{")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), mock.patch("sys.stdin", stdin):
            self.assertEqual(0, self.adapter.main())
        payload = json.loads(stdout.getvalue())
        self.assertEqual("failed", payload["status"])
        self.assertEqual("unknown", payload["run_id"])
        self.assertEqual("JSONDecodeError", payload["metadata"]["error_type"])

    def test_failed_adapter_status_is_rejected_before_behavior(self) -> None:
        self.assertEqual([], self.verifier.status_mismatches("completed"))
        self.assertTrue(self.verifier.status_mismatches("failed"))

    def test_selection_contract_is_independent_of_behavior_subset(self) -> None:
        self.assertEqual(
            [], self.verifier.selection_mismatches("baseline", "positive", False)
        )
        self.assertEqual(
            [], self.verifier.selection_mismatches("treatment", "positive", True)
        )
        self.assertEqual(
            [], self.verifier.selection_mismatches("treatment", "negative", False)
        )
        self.assertTrue(
            self.verifier.selection_mismatches("treatment", "confusable", True)
        )

    def test_all_live_suites_share_route_workflow_and_key_vocabulary(self) -> None:
        routes = set(self.adapter.catalog_routes(ROOT))
        suite_paths = sorted((ROOT / "evals" / "agent-skills").glob("*/suite.json"))
        self.assertTrue(suite_paths)
        for suite_path in suite_paths:
            suite = json.loads(suite_path.read_text(encoding="utf-8"))
            candidate = Path(suite["skill_path"]).name
            with self.subTest(suite=suite["suite_id"]):
                self.assertIn(candidate, routes)
                for case in suite["cases"]:
                    kind = case["kind"]
                    expected = case["metadata"]["expected_behavior"]
                    for mode in ("baseline", "treatment"):
                        behavior = expected[mode]
                        self.assertEqual(
                            list(behavior),
                            [self.adapter.behavior_key(key) for key in behavior],
                            msg=f"{suite_path}:{case['id']} has a non-snake_case key",
                        )
                        self.assertIn(behavior["route"], routes | {"none"})
                        self.assertIn(behavior["workflow"], self.adapter.WORKFLOWS)
                    self.assertEqual("none", expected["baseline"]["route"])
                    if kind == "positive":
                        self.assertEqual(candidate, expected["treatment"]["route"])
                    else:
                        self.assertNotEqual(candidate, expected["treatment"]["route"])


if __name__ == "__main__":
    unittest.main()
