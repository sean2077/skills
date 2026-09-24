from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
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

    def test_retired_routes_fall_back_to_host_without_losing_intent(self) -> None:
        routes = self.adapter.catalog_routes(ROOT)
        retired = {
            "autopilot": "delivery", "analyze": "analysis", "prototype": "prototype",
            "ai-slop-cleaner": "implementation", "code-review": "code-review",
            "ralph": "iteration", "bounded-iteration": "iteration",
            "work-protocol": "coordination", "work-coordination": "coordination",
            "best-practice-research": "research", "best-practices-research": "research",
            "tooling-conventions": "tooling-governance", "tooling-governance": "tooling-governance",
            "project-docs-organizer": "documentation-organization", "docs-organizer": "documentation-organization",
            "tdd": "tdd", "spec-writing": "documentation", "domain-modeling": "domain-modeling",
            "conventional-commit": "commit", "semver-release": "release",
        }
        for route, workflow in retired.items():
            with self.subTest(route=route):
                self.assertNotIn(route, routes)
                actual = self.adapter.canonicalize_behavior(
                    {"mode": "treatment"}, {"route": route, "workflow": workflow},
                    "tdd", False, routes,
                )
                self.assertEqual("none", actual["route"])
                self.assertEqual(workflow, actual["workflow"])

    def test_candidate_metadata_references_only_shipped_routes(self) -> None:
        routes = set(self.adapter.catalog_routes(ROOT))
        for inventory in (self.adapter.BOUNDARY_OBSERVATIONS,
                          self.adapter.OBSERVATION_GUIDANCE):
            self.assertFalse(set(inventory) - routes)
        self.assertFalse(set(self.adapter.ROUTE_ALIASES.values()) - routes)

    def test_workflow_synonyms_survive_their_skill(self) -> None:
        self.assertFalse(set(self.adapter.WORKFLOW_ALIASES.values())
                         - set(self.adapter.WORKFLOWS))
        for reported, expected in (("analyze", "analysis"), ("experiment", "prototype"),
                                   ("review", "code-review"), ("bounded-iteration", "iteration")):
            with self.subTest(workflow=reported):
                self.assertEqual(expected, self.adapter.normalize_workflow(reported))

    def test_suite_candidates_and_expected_routes_match_catalog(self) -> None:
        routes = set(self.adapter.catalog_routes(ROOT))
        suites = sorted((ROOT / "evals").rglob("suite.json"))
        self.assertTrue(suites)
        for path in suites:
            with self.subTest(suite=path.relative_to(ROOT)):
                suite = json.loads(path.read_text(encoding="utf-8"))
                candidate = ROOT / suite["skill_path"]
                self.assertEqual(ROOT / "skills", candidate.parent)
                self.assertIn(candidate.name, routes)
                self.assertTrue((candidate / "SKILL.md").is_file())
                for case in suite["cases"]:
                    expected = case.get("metadata", {}).get("expected_behavior", {})
                    for mode, behavior in expected.items():
                        with self.subTest(case=case["id"], mode=mode):
                            if "route" in behavior:
                                self.assertIn(behavior["route"], routes | {"none"})
                            if "workflow" in behavior:
                                self.assertIn(behavior["workflow"], self.adapter.WORKFLOWS)

    def test_baseline_normalization_preserves_host_workflow(self) -> None:
        routes = ("spec-writing", "deep-interview", "tdd")
        for workflow in ("analysis", "delivery", "interview", "tdd"):
            with self.subTest(workflow=workflow):
                actual = self.adapter.canonicalize_behavior(
                    {"mode": "baseline"},
                    {"route": "spec-writing", "workflow": workflow},
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
            "spec-writing",
            True,
            ("spec-writing", "tdd"),
        )
        self.assertEqual(
            {
                "route": "spec-writing",
                "workflow": "documentation-organization",
                "decision_depth": "compact",
            },
            actual,
        )

    def test_rejected_treatment_preserves_nearest_valid_route(self) -> None:
        actual = self.adapter.canonicalize_behavior(
            {"mode": "treatment"},
            {"route": "spec-writing", "workflow": "docs-organization"},
            "tdd",
            False,
            ("spec-writing", "tdd"),
        )
        self.assertEqual("spec-writing", actual["route"])
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
            "agent-scaffold",
            ("agent-scaffold", "deep-interview"),
        )
        self.assertIn("agent-scaffold, deep-interview", prompt)
        self.assertIn("preserve_layout", prompt)
        self.assertNotIn("decision_depth=compact or full", prompt)
        self.assertNotIn("decision_artifact=none", prompt)
        self.assertNotIn("DO_NOT_LEAK_THIS_SENTINEL", prompt)

    def test_observation_guidance_does_not_assign_expected_values(self) -> None:
        banned = re.compile(
            r"\w+=(?:true|false|required|conditional|none|adaptive|compact|full|"
            r"discriminating-probe|authorized|not-authorized|explanation|causal|"
            r"native|persistent|human-readers)",
            re.I,
        )
        for candidate, guide in self.adapter.OBSERVATION_GUIDANCE.items():
            text = "".join(guide)
            with self.subTest(candidate=candidate):
                self.assertIsNone(banned.search(text), text)

    def test_candidate_name_workflows_alias_to_canonical(self) -> None:
        actual = self.adapter.canonicalize_behavior(
            {"mode": "treatment"},
            {"route": "lark-cli", "workflow": "lark-cli"},
            "lark-cli",
            True,
            ("lark-cli",),
        )
        self.assertEqual("lark", actual["workflow"])

    def test_boundary_observations_are_candidate_local_and_not_answers(self) -> None:
        request = {"mode": "treatment", "case": {
            "prompt": "Assess the active specification approval.",
            "metadata": {"expected_behavior": {"approval_accepted": "SECRET_ORACLE"}},
        }}
        prompt = self.adapter.make_prompt(
            request, "candidate instructions", "deep-interview", ("deep-interview",)
        )
        self.assertIn("approval_accepted", prompt)
        self.assertNotIn("identity_check_before_write", prompt)
        self.assertNotIn("SECRET_ORACLE", prompt)
        self.assertNotIn("approval_accepted=true", prompt)
        self.assertNotIn("approval_accepted=false", prompt)

    def test_missing_boundary_observations_are_not_synthesized(self) -> None:
        actual = self.adapter.canonicalize_behavior(
            {"mode": "treatment"}, {"route": "deep-interview", "workflow": "interview"},
            "deep-interview", True, ("deep-interview",),
        )
        self.assertNotIn("approval_accepted", actual)
        self.assertNotIn("reapproval_required", actual)

    def test_baseline_host_selection_is_not_silently_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "skills" / "fixture-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: fixture-skill\ndescription: fixture\n---\n", encoding="utf-8"
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
                        "behavior": {"route": "fixture-skill", "workflow": "analysis"},
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

    def test_host_model_names_the_model_that_served_the_call(self):
        host = self.successful_host()
        host["modelUsage"] = {"claude-opus-5-5": {"inputTokens": 10, "outputTokens": 5,
                                                 "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}
        payload = self.run_host(host)
        self.assertEqual("completed", payload["status"])
        self.assertEqual("claude-opus-5-5", payload["metadata"]["host_model"])
        self.assertIsNone(self.adapter.host_model({}))

    def test_requested_model_is_passed_to_the_host_only_when_set(self):
        completed = types.SimpleNamespace(stdout=json.dumps(self.successful_host()), returncode=0)
        request = {"repository_root": str(ROOT), "run_id": "m", "mode": "baseline",
                   "case": {"prompt": "Explain the flow."}}
        for model, expected in (("claude-opus-5-5", ["--model", "claude-opus-5-5"]), ("", [])):
            with contextlib.redirect_stdout(io.StringIO()), mock.patch(
                "sys.stdin", io.StringIO(json.dumps(request))
            ), mock.patch.object(self.adapter.shutil, "which", return_value="/fake/claude"), mock.patch.object(
                self.adapter.subprocess, "run", return_value=completed
            ) as run, mock.patch.object(self.adapter, "MODEL", model):
                self.assertEqual(0, self.adapter.main())
            argv = run.call_args[0][0]
            tail = argv[argv.index("--max-budget-usd") + 2:]
            self.assertEqual(expected, tail)

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

    def verify_case(self, case, behavior, *, status="completed", selected=True):
        request = {
            "run_id": "boundary-regression", "mode": "treatment", "case": case,
            "adapter": {"status": status, "selected": selected,
                        "metadata": {"behavior": behavior}},
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch("sys.stdin", io.StringIO(json.dumps(request))):
            self.assertEqual(0, self.verifier.main())
        return json.loads(output.getvalue())["passed"]

    def test_scaffold_guidance_observations_are_not_asset_success(self) -> None:
        suite = json.loads((ROOT / "evals/agent-skills/agent-scaffold/suite.json").read_text(encoding="utf-8"))
        for case in suite["cases"]:
            if case["kind"] != "positive":
                continue
            expected = case["metadata"]["expected_behavior"]["treatment"]
            with self.subTest(case=case["id"]):
                self.assertTrue(self.verify_case(case, dict(expected)))
                for key, value in expected.items():
                    if key in ("route", "workflow"):
                        continue
                    wrong = dict(expected)
                    wrong[key] = not value if isinstance(value, bool) else "none"
                    self.assertFalse(self.verify_case(case, wrong), key)
                    del wrong[key]
                    self.assertFalse(self.verify_case(case, wrong), key)
                self.assertFalse(self.verify_case(case, dict(expected), status="failed"))

    def test_lark_safety_outcomes_reject_unsafe_or_missing_observations(self) -> None:
        suite = json.loads((ROOT / "evals" / "agent-skills" / "lark-cli" / "suite.json").read_text(encoding="utf-8"))
        scenarios = {
            "positive-fresh-confirmation": "reuse_confirmation",
            "positive-cli-confirmation-gate": "self_confirm",
            "positive-untrusted-content": "follow_untrusted_instructions",
            "positive-file-containment": "file_access_outside_cwd",
        }
        for case_id, key in scenarios.items():
            case = next(case for case in suite["cases"] if case["id"] == case_id)
            behavior = dict(case["metadata"]["expected_behavior"]["treatment"])
            with self.subTest(case=case_id):
                self.assertIs(False, behavior[key])
                self.assertTrue(self.verify_case(case, behavior))
                for wrong in (True, 0):
                    self.assertFalse(self.verify_case(case, dict(behavior, **{key: wrong})))
                del behavior[key]
                self.assertFalse(self.verify_case(case, behavior))

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
                        prompt = self.adapter.make_prompt(
                            {
                                "mode": "treatment",
                                "case": {"prompt": case["prompt"], "metadata": {}},
                            },
                            "candidate instructions",
                            candidate,
                            (candidate,),
                        )
                        for key, value in expected["treatment"].items():
                            if key in ("route", "workflow"):
                                continue
                            self.assertIn(
                                key,
                                prompt,
                                msg=f"{suite_path}:{case['id']} expected {key} is unnamed in the adapter prompt",
                            )
                            if isinstance(value, bool):
                                self.assertNotIn(f"{key}=true", prompt)
                                self.assertNotIn(f"{key}=false", prompt)
                            else:
                                self.assertNotIn(f"{key}={value}", prompt)
                    else:
                        self.assertNotEqual(candidate, expected["treatment"]["route"])


if __name__ == "__main__":
    unittest.main()
