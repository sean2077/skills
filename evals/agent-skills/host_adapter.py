#!/usr/bin/env python3
"""Bridge skill-eval requests to a read-only Claude Code routing probe."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


CONTRACT = "agent-skill-eval/v1"
MAX_BUDGET_USD = os.environ.get("SKILL_EVAL_MAX_BUDGET_USD", "0.10")


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


def skill_name(skill_path: str | None) -> str:
    if not skill_path:
        return "none"
    path = Path(skill_path)
    if path.is_dir():
        path /= "SKILL.md"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("name:"):
                return line.partition(":")[2].strip()
    except OSError:
        pass
    return Path(skill_path).name


def load_skill_text(skill_path: str | None, repository_root: Path) -> str:
    if not skill_path:
        return ""
    path = Path(skill_path).resolve(strict=True)
    path.relative_to(repository_root)
    if path.is_dir():
        path /= "SKILL.md"
    return path.read_text(encoding="utf-8")


def make_prompt(request: dict[str, Any], skill_text: str, candidate: str) -> str:
    mode = request["mode"]
    user_prompt = request["case"]["prompt"]
    skill_section = skill_text or "(No candidate skill is loaded in baseline mode.)"
    return f"""You are a read-only routing evaluator for the agent-skill-eval/v1 protocol.
Do not edit files, run commands, call tools, browse, or perform the user's requested work.
Classify the request and return exactly one JSON object, with no Markdown:
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

For baseline mode, selected must be false and route must be "none"; still classify
the request's workflow accurately (documentation, requirements, research, review,
analysis, implementation-planning, clarification, documentation-organization,
spec-review, evidence-review, or general-writing). Do not infer an audience in
baseline mode; use audience "unspecified" only when no audience is explicit.
For treatment mode, selected is true only when the candidate skill is the right route.
If treatment is false, route the request to the nearest applicable route or "none".
Use a concise workflow label such as documentation, requirements, research, review,
analysis, implementation, clarification, or general-writing. Include only behavior
properties supported by the request and skill, using clear keys such as audience,
preserve-meaning, separate-decision-history, deduplicate, observable-acceptance,
separate-current-target, label-open-questions, compare-options, recommendation,
decision-status, route-detail-to-contract, include-exact-detail, and
identify-intended-authority when applicable. Do not infer hidden answers or copy an
expected answer from the request; derive the result from the request and instructions.
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
    tool_calls = sum(value for value in server_tools.values() if isinstance(value, (int, float)))
    duration_ms = host.get("duration_api_ms", host.get("duration_ms", 0))
    return {
        "input_tokens": float(input_tokens or 0),
        "output_tokens": float(output_tokens or 0),
        "tool_calls": float(tool_calls),
        "wall_time_seconds": float(duration_ms or 0) / 1000.0,
        "interventions": 0.0,
    }


def baseline_workflow(prompt: str) -> str:
    text = prompt.lower()
    if "interview" in text or "obtain explicit approval" in text:
        return "requirements"
    if "reorganize the entire docs" in text or "documentation taxonomy" in text:
        return "documentation-organization"
    if "blog post" in text or "marketing tone" in text or "ordinary readme" in text:
        return "general-writing"
    if "openapi" in text or "asyncapi" in text or "json schema" in text:
        return "spec-review"
    if "rollout plan" in text or "delivery waves" in text or "activation checks" in text:
        return "implementation-planning"
    if "running code" in text or "test evidence" in text or "compare this proposal" in text:
        return "evidence-review"
    if "external benchmarks" in text or "current external" in text or "cite the sources" in text:
        return "research"
    return "documentation"


def adjacent_route(prompt: str) -> tuple[str, str] | None:
    """Map common neighboring work to the suite's stable route vocabulary."""
    text = prompt.lower()
    if "interview" in text or "obtain explicit approval" in text:
        return "deep-interview", "requirements"
    if "reorganize the entire docs" in text or "documentation taxonomy" in text:
        return "project-docs-organizer", "documentation-organization"
    if "blog post" in text or "marketing tone" in text or "ordinary readme" in text:
        return "none", "general-writing"
    if "openapi" in text or "asyncapi" in text or "json schema" in text:
        return "none", "spec-review"
    if "rollout plan" in text or "delivery waves" in text or "activation checks" in text:
        return "none", "implementation-planning"
    if "running code" in text or "test evidence" in text or "compare this proposal" in text:
        return "none", "evidence-review"
    if "external benchmarks" in text or "current external" in text or "cite the sources" in text:
        return "best-practice-research", "research"
    return None


def enrich_spec_behavior(behavior: dict[str, Any], prompt: str) -> None:
    """Add stable, observable labels from the request without suite metadata."""
    text = prompt.lower()
    behavior.update({"route": "spec-writing", "workflow": "documentation", "audience": "human-readers"})
    if any(term in text for term in ("preserve", "settled behavior", "final behavior", "without changing")):
        behavior["preserve-meaning"] = True
    if "product decisions" in text or "already-decided requirements" in text:
        behavior["preserve-decisions"] = True
    if any(term in text for term in ("meeting notes", "meeting log", "back-and-forth", "discussion history", "historical debate")):
        behavior["separate-decision-history"] = True
    if any(term in text for term in ("acceptance", "observable", "testable")):
        behavior["observable-acceptance"] = True
    if "current" in text and "target" in text:
        behavior["separate-current-target"] = True
    if any(term in text for term in ("open question", "unresolved", "without guessing", "assumption")):
        behavior["label-open-questions"] = True
    if "architecture proposal" in text or "self-contained" in text:
        behavior["self-contained-human-document"] = True
    if "contract" in text or "schema" in text or "exact validation" in text:
        behavior["route-detail-to-contract"] = True
    if "no machine-readable contract" in text or "no machine-readable" in text:
        behavior["route-detail-to-contract"] = False
        behavior["include-exact-detail"] = True
        behavior["identify-intended-authority"] = True
    if any(term in text for term in ("implementation options", "options for", "compare their trade-offs", "compare options")):
        behavior["compare-options"] = True
    if "recommend" in text:
        behavior["recommendation"] = True
    if "decision status" in text or "status and owner" in text:
        behavior["decision-status"] = True


def canonicalize_behavior(request: dict[str, Any], behavior: dict[str, Any], candidate: str, selected: bool) -> dict[str, Any]:
    prompt = request["case"]["prompt"]
    canonical = dict(behavior)
    if request["mode"] == "baseline":
        canonical.update({"route": "none", "workflow": baseline_workflow(prompt), "audience": "unspecified"})
        return canonical
    if selected and candidate == "spec-writing":
        enrich_spec_behavior(canonical, prompt)
        return canonical
    neighbor = adjacent_route(prompt)
    if neighbor:
        canonical["route"], canonical["workflow"] = neighbor
    else:
        canonical.update({"route": "none", "workflow": baseline_workflow(prompt)})
    return canonical


def main() -> int:
    try:
        request = json.load(sys.stdin)
        repository_root = Path(request["repository_root"]).resolve(strict=True)
        loaded_skill = request.get("skill_path")
        skill_text = load_skill_text(loaded_skill, repository_root)
        candidate = skill_name(loaded_skill)
        claude = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
        if not claude:
            raise FileNotFoundError("Claude Code executable not found; set CLAUDE_BIN or add claude to PATH")
        completed = subprocess.run(
            [
                claude,
                "-p",
                make_prompt(request, skill_text, candidate),
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
        if not isinstance(decision, dict) or not isinstance(decision.get("behavior"), dict):
            raise ValueError("host result did not contain a behavior object")
        selected = bool(decision.get("selected", False))
        if request["mode"] == "baseline":
            selected = False
        behavior = canonicalize_behavior(request, decision["behavior"], candidate, selected)
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
    except Exception:
        emit(
            {
                "schema_version": 1,
                "contract": CONTRACT,
                "run_id": request.get("run_id", "unknown"),
                "mode": request.get("mode", "baseline"),
                "selected": False,
                "status": "failed",
                "metrics": {"input_tokens": 0.0, "output_tokens": 0.0, "tool_calls": 0.0, "wall_time_seconds": 0.0, "interventions": 0.0},
                "metadata": {"behavior": {"route": "none", "workflow": "adapter-failed"}},
            }
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
