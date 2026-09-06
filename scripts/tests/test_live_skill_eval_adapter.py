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
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "result": json.dumps(
                    {
                        "selected": True,
                        "behavior": {"route": "analyze", "workflow": "analysis"},
                    }
                )
            }
            stdin = io.StringIO(json.dumps(request))
            stdout = io.StringIO()
            completed = types.SimpleNamespace(stdout=json.dumps(host), returncode=0)
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

    def test_selection_contract_honors_explicit_positive_override(self) -> None:
        self.assertEqual(
            [],
            self.verifier.selection_mismatches(
                "treatment", "positive", False, False
            ),
        )
        self.assertTrue(
            self.verifier.selection_mismatches(
                "treatment", "positive", True, False
            )
        )


    def run_host(self, host, *, returncode=0, raw_stdout=None):
        request = {
            "repository_root": str(ROOT), "run_id": "host-contract",
            "mode": "baseline", "case": {"prompt": "Explain the flow."},
        }
        output = io.StringIO()
        completed = types.SimpleNamespace(
            stdout=json.dumps(host) if raw_stdout is None else raw_stdout,
            returncode=returncode,
        )
        with contextlib.redirect_stdout(output), mock.patch(
            "sys.stdin", io.StringIO(json.dumps(request))
        ), mock.patch.object(self.adapter.shutil, "which", return_value="/fake/claude"), mock.patch.object(
            self.adapter.subprocess, "run", return_value=completed
        ):
            self.assertEqual(0, self.adapter.main())
        return json.loads(output.getvalue())

    @staticmethod
    def successful_host():
        return {
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "duration_api_ms": 1,
            "result": json.dumps({
                "selected": False, "behavior": {"route": "none", "workflow": "analysis"}
            }),
        }

    def test_nonzero_host_exit_cannot_become_a_success(self):
        payload = self.run_host(self.successful_host(), returncode=7)
        self.assertEqual("failed", payload["status"])
        self.assertEqual(7, payload["metadata"]["host_exit_code"])
        self.assertTrue(payload["metadata"]["usage_available"])
        self.assertEqual(10, payload["metrics"]["input_tokens"])

    def test_cached_input_is_counted_without_double_counting_model_totals(self):
        host = self.successful_host()
        host["usage"].update(cache_read_input_tokens=200, cache_creation_input_tokens=30)
        host["modelUsage"] = {"model": {
            "inputTokens": 10, "outputTokens": 5,
            "cacheReadInputTokens": 200, "cacheCreationInputTokens": 30,
        }}
        result = self.run_host(host)
        self.assertEqual("completed", result["status"])
        self.assertEqual(240, result["metrics"]["input_tokens"])
        self.assertEqual(5, result["metrics"]["output_tokens"])

    def test_model_usage_fallback_includes_each_models_cache(self):
        host = self.successful_host()
        del host["usage"]
        host["modelUsage"] = {
            "a": {"inputTokens": 3, "outputTokens": 2, "cacheReadInputTokens": 7},
            "b": {"inputTokens": 4, "outputTokens": 5, "cacheCreationInputTokens": 9},
        }
        result = self.run_host(host)
        self.assertEqual("completed", result["status"])
        self.assertEqual(23, result["metrics"]["input_tokens"])
        self.assertEqual(7, result["metrics"]["output_tokens"])


    def test_whole_call_model_usage_precedes_partial_top_level_usage(self):
        host = self.successful_host()
        host["modelUsage"] = {"model": {
            "inputTokens": 20, "outputTokens": 8, "cacheReadInputTokens": 100,
        }}
        result = self.run_host(host, returncode=1)
        self.assertEqual("failed", result["status"])
        self.assertEqual(120, result["metrics"]["input_tokens"])
        self.assertEqual(8, result["metrics"]["output_tokens"])

    def test_missing_or_invalid_usage_is_not_a_zero_cost_success(self):
        invalid = [None, {}, {"input_tokens": 1}, {"input_tokens": True, "output_tokens": 1},
                   {"input_tokens": -1, "output_tokens": 1},
                   {"input_tokens": 1.5, "output_tokens": 1},
                   {"input_tokens": "10", "output_tokens": 1},
                   {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": -1}]
        for usage in invalid:
            with self.subTest(usage=usage):
                host = self.successful_host()
                host["usage"] = usage
                result = self.run_host(host)
                self.assertEqual("failed", result["status"])
                self.assertFalse(result["metadata"]["usage_available"])

    def test_elapsed_time_is_measured_not_copied_from_api_duration(self):
        with mock.patch.object(self.adapter.time, "monotonic", side_effect=[100.0, 102.5]):
            result = self.run_host(self.successful_host())
        self.assertEqual(2.5, result["metrics"]["wall_time_seconds"])

    def test_json_parser_requires_one_unambiguous_finite_object(self):
        for text in ('{}{}', 'log {"selected": true}', '[{}]',
                     '{"selected":false,"selected":true}', '{"x":NaN}',
                     '{"x":Infinity}', '{"x":1e999}'):
            with self.subTest(text=text), self.assertRaises((ValueError, TypeError)):
                self.adapter.parse_json(text)
        self.assertEqual({"ok": True}, self.adapter.parse_json('  {"ok":true}\n'))

    def test_behavior_key_collisions_are_not_silently_overwritten(self):
        with self.assertRaises(ValueError):
            self.adapter.normalize_behavior_keys({"persistent-state": True, "persistent_state": False})

    def test_candidate_symlink_cannot_escape_the_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            outer = Path(temporary)
            root = outer / "repo"
            skill = root / "candidate"
            skill.mkdir(parents=True)
            secret = outer / "outside.md"
            secret.write_text("outside candidate", encoding="utf-8")
            try:
                (skill / "SKILL.md").symlink_to(secret)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            with self.assertRaises(ValueError):
                self.adapter.load_candidate("candidate", root)

    def test_behavior_comparison_does_not_coerce_booleans_to_numbers(self):
        for expected, actual in ((True, 1), (False, 0), (1, True),
                                 ({"a": True}, {"a": 1}), ([False], [0]),
                                 ([{"a": True}], [{"a": 1}])):
            with self.subTest(expected=expected, actual=actual):
                self.assertTrue(self.verifier.subset_mismatches(expected, actual))
        for expected, actual in ((1, 1.0), (None, None), ([1], [1, 2]),
                                 ({"a": True}, {"a": True, "extra": 3})):
            with self.subTest(expected=expected, actual=actual):
                self.assertEqual([], self.verifier.subset_mismatches(expected, actual))

    def test_non_object_request_still_emits_failed_envelope(self):
        for raw in ("[]", "null", '"text"'):
            with self.subTest(raw=raw):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), mock.patch("sys.stdin", io.StringIO(raw)):
                    self.assertEqual(0, self.adapter.main())
                self.assertEqual("failed", json.loads(output.getvalue())["status"])

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
