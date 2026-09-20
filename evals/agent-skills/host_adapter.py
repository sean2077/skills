#!/usr/bin/env python3
"""Bridge skill-eval requests to a read-only Claude Code routing probe."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


CONTRACT = "agent-skill-eval/v1"
MAX_BUDGET_USD = os.environ.get("SKILL_EVAL_MAX_BUDGET_USD", "0.10")
WORKFLOWS = (
    "analysis",
    "code-review",
    "research",
    "implementation",
    "delivery",
    "interview",
    "clarification",
    "documentation",
    "documentation-organization",
    "domain-modeling",
    "tdd",
    "prototype",
    "commit",
    "release",
    "tooling-governance",
    "harness-management",
    "lark",
    "iteration",
    "coordination",
    "general-writing",
    "spec-review",
    "evidence-review",
    "implementation-planning",
    "unspecified",
)
ROUTE_ALIASES = {
    "agent-harness": "agent-scaffold",
    "best-practices-research": "best-practice-research",
    "bounded-iteration": "ralph",
    "conventional-commits": "conventional-commit",
    "docs-organizer": "project-docs-organizer",
    "documentation-organizer": "project-docs-organizer",
    "lark": "lark-cli",
    "semver": "semver-release",
    "test-driven-development": "tdd",
    "tooling-governance": "tooling-conventions",
    "work-coordination": "work-protocol",
}
WORKFLOW_ALIASES = {
    "agent-harness": "harness-management",
    "ai-slop-cleaner": "implementation",
    "analyze": "analysis",
    "autopilot": "delivery",
    "best-practice-research": "research",
    "bounded-iteration": "iteration",
    "causal-investigation": "analysis",
    "conventional-commit": "commit",
    "deep-interview": "interview",
    "docs-organization": "documentation-organization",
    "experiment": "prototype",
    "explanation": "analysis",
    "git-commit": "commit",
    "lark-cli": "lark",
    "project-docs-organizer": "documentation-organization",
    "requirements": "interview",
    "requirements-writing": "documentation",
    "review": "code-review",
    "semver-release": "release",
    "spec-writing": "documentation",
    "specification": "documentation",
    "test-driven-development": "tdd",
    "test-first": "tdd",
    "tooling": "tooling-governance",
    "tooling-conventions": "tooling-governance",
    "work-coordination": "coordination",
}
# Observation names only; never inject desired values or case oracle metadata.
# Keep the vocabulary candidate-local rather than taxing every probe with every key.
BOUNDARY_OBSERVATIONS = {
    "analyze": ("invent_hypotheses",),
    "autopilot": ("repeat_valid_checks",),
    "code-review": ("repeat_valid_checks",),
    "deep-interview": ("approval_accepted", "implementation_authorized", "reapproval_required"),
    "domain-modeling": ("topology_redesign",),
    "tdd": ("separate_behavior_card",),
    "tooling-conventions": ("preserve_external_consumers",),
    "lark-cli": (
        "routine_preflight", "identity_switch", "identity_check_before_write", "blind_write",
        "blind_retry", "claim_success", "reauth_for_acl", "send_authorized",
    ),
    "semver-release": (
        "migration_interview", "preserve_existing_workflow", "compare_options",
        "infrastructure_mutation", "create_unrequested_publisher", "claim_complete",
    ),
    "ai-slop-cleaner": (
        "behavior_change", "fixed_smell_passes", "ritual_no_test_approval", "claim_verified",
    ),
    "prototype": ("production_promotion", "claim_real_integration"),
    "best-practice-research": ("primary_sources", "local_fit", "repeat_source_sweep"),
    "conventional-commit": ("git_preflight", "preserve_unrelated_index"),
}
OBSERVATION_GUIDANCE = {
    "analyze": (
        "When selected, report workflow, mode, and mutation. Include result only when a "
        "next probe is actually requested."
    ),
    "autopilot": (
        "When selected, report workflow, control_plane, persistent_state, test_first, and "
        "external_side_effects when material. Report preserve_decisions, nested_controller, "
        "remote_readback, recheck_revision, and claim_independent_approval as booleans when material."
    ),
    "code-review": (
        "When selected, report workflow and mutation. Report verify_feedback, recheck_revision, "
        "invent_requirements, and claim_independent_approval as booleans when material."
    ),
    "tdd": (
        "When selected, report workflow, test_first, and preserve_parent_contract when a "
        "delivery owner is active."
    ),
    "deep-interview": (
        "When selected, report workflow, mode, question_batch_policy, first_turn_question_count "
        "when the request states a first-turn count, approval_required, persistent_state, and "
        "external_research when material."
    ),
    "domain-modeling": (
        "When selected, report workflow, mutation, modeling_mode, topology_decision, and "
        "preserve_single_owner when material."
    ),
    "project-docs-organizer": (
        "When selected, report workflow. Report decision_artifact only when the task requires a "
        "particular record. Report preserve_decisions and additional_approval_required as "
        "booleans when material."
    ),
    "spec-writing": (
        "When selected, report workflow. Use snake_case keys for material choices, including "
        "preserve_meaning, preserve_decisions, separate_decision_history, observable_acceptance, "
        "separate_current_target, label_open_questions, self_contained_human_document, "
        "route_detail_to_contract, compare_options, recommendation, decision_status, "
        "include_exact_detail, and identify_intended_authority."
    ),
    "tooling-conventions": (
        "When selected, report workflow. Report decision_artifact only when the task requires a "
        "particular record."
    ),
    "conventional-commit": (
        "When selected, report workflow and mutation."
    ),
}


def emit(value: dict[str, Any]) -> None:
    json.dump(value, sys.stdout, ensure_ascii=True, separators=(",", ":"))


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected a numeric measurement")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("expected a finite nonnegative measurement")
    return result


def parse_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite JSON number")
    return result


def parse_json(text: str) -> dict[str, Any]:
    # Both --output-format json and the decision prompt promise one object.
    # Picking a plausible object out of noisy/contradictory output masks failure.
    value = json.loads(text, object_pairs_hook=unique_object,
                       parse_constant=reject_constant, parse_float=parse_float)
    if not isinstance(value, dict):
        raise ValueError("expected exactly one JSON object")
    return value


def load_candidate(
    skill_path: str | None, repository_root: Path
) -> tuple[str, str]:
    if not skill_path:
        return "none", ""
    path = Path(skill_path)
    if not path.is_absolute():
        path = repository_root / path
    path = path.resolve(strict=True)
    path.relative_to(repository_root)
    if path.is_dir():
        path = (path / "SKILL.md").resolve(strict=True)
    path.relative_to(repository_root)
    if not path.is_file():
        raise ValueError("candidate must be a regular file")
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("name:"):
            return line.partition(":")[2].strip().strip("'\""), text
    return path.parent.name, text


def catalog_routes(repository_root: Path) -> tuple[str, ...]:
    skills_dir = repository_root / "skills"
    routes = tuple(
        sorted(
            path.name
            for path in skills_dir.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )
    )
    if not routes:
        raise ValueError("catalog route inventory is empty")
    return routes


def slug(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.strip().casefold()).strip("-")


def behavior_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().casefold()).strip("_")


def normalize_route(value: Any, routes: Iterable[str]) -> str:
    allowed = set(routes)
    normalized = ROUTE_ALIASES.get(slug(value), slug(value))
    return normalized if normalized in allowed else "none"


def normalize_workflow(value: Any) -> str:
    normalized = WORKFLOW_ALIASES.get(slug(value), slug(value))
    return normalized if normalized in WORKFLOWS else "unspecified"


def normalize_behavior_keys(behavior: dict[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for key, value in behavior.items():
        normalized = behavior_key(key)
        if not normalized or normalized in canonical:
            raise ValueError("empty or colliding behavior key")
        canonical[normalized] = value
    return canonical


def make_prompt(
    request: dict[str, Any], skill_text: str, candidate: str, routes: Iterable[str]
) -> str:
    mode = request["mode"]
    user_prompt = request["case"]["prompt"]
    skill_section = skill_text or "(No candidate skill is loaded in baseline mode.)"
    route_vocabulary = ", ".join(("none", *routes))
    workflow_vocabulary = ", ".join(WORKFLOWS)
    observation_guide = OBSERVATION_GUIDANCE.get(
        candidate,
        "Report only request-visible behavior needed to explain the routing decision; "
        "do not invent state.",
    )
    observations = BOUNDARY_OBSERVATIONS.get(candidate, ())
    if observations:
        observation_guide += (
            " When material, report these as booleans, deriving values from the task and "
            "instructions rather than this vocabulary: " + ", ".join(observations) + "."
        )
    return f"""You are a read-only routing evaluator for the agent-skill-eval/v1 protocol.
Do not edit files, run commands, call tools, browse, or perform the user's requested work.
Return exactly one JSON object, with no Markdown:
{{"selected": true|false, "behavior": {{"route": "...", "workflow": "...", ...}}}}

Evaluation mode: {mode}
Candidate skill name: {candidate}
Candidate skill instructions:
---
{skill_section}
---
User request:
---
{user_prompt}
---

Use one exact route value from: {route_vocabulary}.
Use one exact workflow value from: {workflow_vocabulary}.
Use snake_case behavior keys. Always include route and workflow; include other properties only
when the request and candidate instructions support them. {observation_guide}

In baseline mode, selected must be false and route must be none. In treatment mode, selected is
true only when the candidate is the right route. When treatment is false, name the nearest catalog
route or none. Classify from the user request and candidate instructions only. Do not infer hidden
facts, inspect case metadata, or synthesize an expected answer.
"""


def count(value: Any) -> float:
    result = finite_number(value)
    if not result.is_integer():
        raise ValueError("expected an integral usage count")
    return result


def metrics(host: dict[str, Any], elapsed: float) -> dict[str, float]:
    usage = host.get("usage")
    models = host.get("modelUsage")
    if usage is not None and not isinstance(usage, dict):
        raise ValueError("invalid usage object")
    if models is not None and not isinstance(models, dict):
        raise ValueError("invalid model usage object")
    # modelUsage covers the whole call, including the response that crosses a
    # budget; usage can omit that response. Never add these overlapping records.
    if usage:
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            if key in usage:
                count(usage[key])
    if models:
        input_tokens = output_tokens = tool_calls = 0.0
        for record in models.values():
            if not isinstance(record, dict) or not {"inputTokens", "outputTokens"} <= record.keys():
                raise ValueError("missing complete model usage")
            input_tokens += sum(count(record.get(key, 0)) for key in (
                "inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
            output_tokens += count(record["outputTokens"])
            tool_calls += count(record.get("webSearchRequests", 0))
    elif usage and "input_tokens" in usage and "output_tokens" in usage:
        input_tokens = sum(count(usage.get(key, 0)) for key in (
            "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        output_tokens = count(usage["output_tokens"])
        tool_calls = 0.0
    else:
        raise ValueError("missing complete host usage")
    if usage:
        server_tools = usage.get("server_tool_use", {})
        if not isinstance(server_tools, dict):
            raise ValueError("invalid server tool usage")
        # The probe disables local tools. These are overlapping server-tool
        # reports, not extra invocations to add to per-model web search counts.
        tool_calls = max(tool_calls, sum(count(value) for value in server_tools.values()))
    return {
        "input_tokens": finite_number(input_tokens),
        "output_tokens": finite_number(output_tokens),
        "tool_calls": finite_number(tool_calls),
        "wall_time_seconds": finite_number(elapsed),
        "interventions": 0.0,
    }


def canonicalize_behavior(
    request: dict[str, Any],
    behavior: dict[str, Any],
    candidate: str,
    selected: bool,
    routes: Iterable[str],
) -> dict[str, Any]:
    canonical = normalize_behavior_keys(behavior)
    if request["mode"] == "baseline":
        canonical["route"] = "none"
    elif selected:
        canonical["route"] = normalize_route(candidate, routes)
    else:
        canonical["route"] = normalize_route(canonical.get("route"), routes)
    canonical["workflow"] = normalize_workflow(canonical.get("workflow"))
    return canonical


def main() -> int:
    request: dict[str, Any] = {}
    started = time.monotonic()
    observed: dict[str, float] | None = None
    exit_code: int | None = None
    stage = "request"
    try:
        request = parse_json(sys.stdin.read())
        repository_root = Path(request["repository_root"]).resolve(strict=True)
        routes = catalog_routes(repository_root)
        candidate, skill_text = load_candidate(request.get("skill_path"), repository_root)
        claude = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
        if not claude:
            raise FileNotFoundError("Claude Code executable not found")
        stage = "host"
        completed = subprocess.run(
            [
                claude, "-p", make_prompt(request, skill_text, candidate, routes),
                "--output-format", "json", "--no-session-persistence",
                "--disable-slash-commands", "--tools", "",
                "--permission-mode", "dontAsk", "--setting-sources", "user",
                "--max-budget-usd", MAX_BUDGET_USD,
            ],
            cwd=str(repository_root), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", timeout=240, check=False,
        )
        exit_code = completed.returncode
        host = parse_json(completed.stdout)
        stage = "usage"
        observed = metrics(host, 0.0)
        stage = "host-status"
        if exit_code != 0 or host.get("is_error"):
            raise ValueError("host returned an error")
        stage = "decision"
        decision = parse_json(host.get("result", ""))
        if not isinstance(decision.get("behavior"), dict):
            raise ValueError("host result did not contain a behavior object")
        selected = decision.get("selected")
        if not isinstance(selected, bool):
            raise ValueError("host result did not contain a boolean selected value")
        behavior = canonicalize_behavior(request, decision["behavior"], candidate, selected, routes)
        observed["wall_time_seconds"] = time.monotonic() - started
        emit({
            "schema_version": 1, "contract": CONTRACT,
            "run_id": request["run_id"], "mode": request["mode"],
            "selected": selected, "status": "completed", "metrics": observed,
            "metadata": {"behavior": behavior, "host_model": host.get("model"),
                         "usage_available": True},
        })
        return 0
    except Exception as exc:
        # The v1 envelope requires numeric metrics even for a failed run. Keep
        # known usage; explicitly mark unobserved zero placeholders as unavailable.
        measured = observed or {"input_tokens": 0.0, "output_tokens": 0.0,
                                "tool_calls": 0.0, "interventions": 0.0}
        measured["wall_time_seconds"] = time.monotonic() - started
        emit({
            "schema_version": 1, "contract": CONTRACT,
            "run_id": request.get("run_id", "unknown"),
            "mode": request.get("mode", "baseline"),
            "selected": False, "status": "failed", "metrics": measured,
            "metadata": {
                "behavior": {"route": "none", "workflow": "adapter-failed"},
                "error_type": type(exc).__name__, "error_stage": stage,
                "host_exit_code": exit_code, "usage_available": observed is not None,
            },
        })
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
