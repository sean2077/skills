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
# An exact model ID; without it the host's configured default (which a gateway may remap) runs.
MODEL = os.environ.get("SKILL_EVAL_MODEL", "")
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
# Labels whose boundary with a neighbor is not self-evident. Bare labels made the live
# probes grade taxonomy guesses (a scaffold preview as "analysis") instead of decisions.
WORKFLOW_MEANINGS = {
    "harness-management": "establishing, previewing, diagnosing, or upgrading an Agent harness or its project conventions, read-only or not",
    "tooling-governance": "changing a project's commands, scripts, or their callers while preserving the command contract",
    "domain-modeling": "deciding or renaming project concepts and their glossary terms",
    "analysis": "investigating or explaining something outside the more specific workflows",
}
ROUTE_ALIASES = {
    "agent-harness": "agent-scaffold",
    "lark": "lark-cli",
}
# Plausible host phrasings for a canonical workflow. Task vocabulary is independent
# of the shipped catalog, so a synonym stays as long as its target workflow does.
WORKFLOW_ALIASES = {
    "agent-harness": "harness-management",
    "analyze": "analysis",
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
    "deep-interview": ("approval_accepted", "implementation_authorized", "reapproval_required"),
    "lark-cli": (
        "routine_preflight", "identity_switch", "identity_check_before_write", "blind_write",
        "blind_retry", "claim_success", "reauth_for_acl", "send_authorized",
        "reuse_confirmation", "self_confirm", "follow_untrusted_instructions", "file_access_outside_cwd",
    ),
    "agent-scaffold": (
        "preserve_layout", "fill_project_guidance", "inspect_existing_routes",
        "asset_pass_proves_guidance", "project_guidance_writes", "restore_deleted_guidance",
        "introduce_controller", "fill_testing_guidance", "test_policy_changed",
        "test_harness_added", "requires_sibling_skill", "decision_artifact",
        "ask_domain_exclusions", "reuse_domain_selection", "write_domain_selection",
        "selected_domains", "restore_excluded_domains", "default_all_domains",
        "selected_domain_changes_policy",
    ),
}
OBSERVATION_GUIDANCE = {
    "deep-interview": (
        "When selected, report workflow, first_turn_question_count when the request states a "
        "first-turn count, approval_required, persistent_state (whether the bundled runtime keeps "
        "state, not whether the conversation continues), and external_research when material."
    ),
    "agent-scaffold": (
        "When selected, report workflow and the material project-guidance, layout, ownership, "
        "and read-only scope decisions. Report write decisions for what happens before the user "
        "answers any question you ask. Report decision_artifact only when the project requires "
        "a named record."
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
    workflow_meanings = "; ".join(
        "{0} = {1}".format(label, meaning) for label, meaning in WORKFLOW_MEANINGS.items()
    )
    observation_guide = OBSERVATION_GUIDANCE.get(
        candidate,
        "Report only request-visible behavior needed to explain the routing decision; "
        "do not invent state.",
    )
    observations = BOUNDARY_OBSERVATIONS.get(candidate, ())
    if observations:
        observation_guide += (
            " When material, report these as booleans, deriving values from the task and "
            "instructions rather than this vocabulary: " + ", ".join(observations) + ". Each "
            "describes what you would do, not a property of the request."
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
Where labels border each other: {workflow_meanings}.
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


def host_model(host: dict[str, Any]) -> str | None:
    """Name the model(s) that actually served the call; a gateway may remap the request."""
    models = host.get("modelUsage")
    if isinstance(models, dict) and models:
        return ",".join(sorted(str(name) for name in models))
    model = host.get("model")
    return model if isinstance(model, str) else None


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
        # The runner forwards only the SKILL_EVAL_ namespace, so CLAUDE_BIN works only for direct calls.
        claude = (os.environ.get("SKILL_EVAL_CLAUDE_BIN") or os.environ.get("CLAUDE_BIN")
                  or shutil.which("claude"))
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
            ] + (["--model", MODEL] if MODEL else []),
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
            "metadata": {"behavior": behavior, "host_model": host_model(host),
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
