#!/usr/bin/env python3
"""Bridge skill-eval requests to a read-only Claude Code routing probe."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
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
    "bounded-iteration": "iteration",
    "causal-investigation": "analysis",
    "docs-organization": "documentation-organization",
    "experiment": "prototype",
    "explanation": "analysis",
    "git-commit": "commit",
    "requirements": "interview",
    "requirements-writing": "documentation",
    "review": "code-review",
    "semver-release": "release",
    "specification": "documentation",
    "test-driven-development": "tdd",
    "test-first": "tdd",
    "tooling": "tooling-governance",
    "work-coordination": "coordination",
}
OBSERVATION_GUIDANCE = {
    "analyze": (
        "When selected, use workflow=analysis, mode=explanation or causal, mutation=none, "
        "and result=discriminating-probe only when that outcome is requested."
    ),
    "autopilot": (
        "When selected, use workflow=delivery. Report control_plane=native or persistent, "
        "persistent_state as a boolean, test_first=conditional or required, and "
        "external_side_effects=authorized or not-authorized when material."
    ),
    "deep-interview": (
        "When selected, use workflow=interview. Report mode=adaptive or persistent, "
        "question_batch_policy=adaptive, question counts when explicit, "
        "structured_answer_template as a boolean, approval_required as a boolean, "
        "persistent_state as a boolean, and external_research=conditional when material."
    ),
    "domain-modeling": (
        "When selected, use workflow=domain-modeling. Report mutation=none or "
        "authorized-scope, modeling_mode=incremental or up-front, "
        "topology_decision=evidence-based, and preserve_single_owner as a boolean when material."
    ),
    "project-docs-organizer": (
        "When selected, use workflow=documentation-organization. Report "
        "decision_depth=compact or full and decision_artifact=inline-delta or "
        "documentation-ia-decision-record."
    ),
    "spec-writing": (
        "When selected, use workflow=documentation. Use snake_case keys for material choices, "
        "including preserve_meaning, preserve_decisions, separate_decision_history, "
        "observable_acceptance, separate_current_target, label_open_questions, "
        "self_contained_human_document, route_detail_to_contract, compare_options, "
        "recommendation, decision_status, include_exact_detail, and identify_intended_authority."
    ),
    "tooling-conventions": (
        "When selected, use workflow=tooling-governance. Report decision_depth=compact or full "
        "and decision_artifact=inline-delta or tool-governance-decision-record."
    ),
}


def emit(value: dict[str, Any]) -> None:
    json.dump(value, sys.stdout, ensure_ascii=True, separators=(",", ":"))


def parse_json(text: str) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return value
    raise ValueError("host did not return a JSON object")


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
        path /= "SKILL.md"
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
        if normalized:
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


def metrics(host: dict[str, Any]) -> dict[str, float]:
    usage = host.get("usage") or {}
    model_usage = host.get("modelUsage") or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if input_tokens is None:
        input_tokens = sum(item.get("inputTokens", 0) for item in model_usage.values())
    if output_tokens is None:
        output_tokens = sum(item.get("outputTokens", 0) for item in model_usage.values())
    server_tools = usage.get("server_tool_use") or {}
    tool_calls = sum(
        value for value in server_tools.values() if isinstance(value, (int, float))
    )
    duration_ms = host.get("duration_api_ms", host.get("duration_ms", 0))
    return {
        "input_tokens": float(input_tokens or 0),
        "output_tokens": float(output_tokens or 0),
        "tool_calls": float(tool_calls),
        "wall_time_seconds": float(duration_ms or 0) / 1000.0,
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
    try:
        request = json.load(sys.stdin)
        repository_root = Path(request["repository_root"]).resolve(strict=True)
        routes = catalog_routes(repository_root)
        candidate, skill_text = load_candidate(
            request.get("skill_path"), repository_root
        )
        claude = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
        if not claude:
            raise FileNotFoundError(
                "Claude Code executable not found; set CLAUDE_BIN or add claude to PATH"
            )
        completed = subprocess.run(
            [
                claude,
                "-p",
                make_prompt(request, skill_text, candidate, routes),
                "--output-format",
                "json",
                "--no-session-persistence",
                "--disable-slash-commands",
                "--tools",
                "",
                "--permission-mode",
                "dontAsk",
                "--setting-sources",
                "user",
                "--max-budget-usd",
                MAX_BUDGET_USD,
            ],
            cwd=str(repository_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=240,
            check=False,
        )
        host = parse_json(completed.stdout)
        if not isinstance(host, dict) or host.get("is_error"):
            raise ValueError("host returned an error")
        decision = parse_json(host.get("result", ""))
        if not isinstance(decision, dict) or not isinstance(
            decision.get("behavior"), dict
        ):
            raise ValueError("host result did not contain a behavior object")
        selected = decision.get("selected")
        if not isinstance(selected, bool):
            raise ValueError("host result did not contain a boolean selected value")
        behavior = canonicalize_behavior(
            request, decision["behavior"], candidate, selected, routes
        )
        emit(
            {
                "schema_version": 1,
                "contract": CONTRACT,
                "run_id": request["run_id"],
                "mode": request["mode"],
                "selected": selected,
                "status": "completed",
                "metrics": metrics(host),
                "metadata": {"behavior": behavior, "host_model": host.get("model")},
            }
        )
        return 0
    except Exception as exc:
        emit(
            {
                "schema_version": 1,
                "contract": CONTRACT,
                "run_id": request.get("run_id", "unknown"),
                "mode": request.get("mode", "baseline"),
                "selected": False,
                "status": "failed",
                "metrics": {
                    "input_tokens": 0.0,
                    "output_tokens": 0.0,
                    "tool_calls": 0.0,
                    "wall_time_seconds": 0.0,
                    "interventions": 0.0,
                },
                "metadata": {
                    "behavior": {"route": "none", "workflow": "adapter-failed"},
                    "error_type": type(exc).__name__,
                },
            }
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
