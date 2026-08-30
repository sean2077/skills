#!/usr/bin/env python3
"""Read-only verifier for live Agent Skill routing and decision suites."""

import json
import sys


def subset_mismatches(expected, actual, path="behavior"):
    mismatches = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        for key, value in expected.items():
            child = f"{path}.{key}"
            if key not in actual:
                mismatches.append(f"{child}: missing")
            else:
                mismatches.extend(subset_mismatches(value, actual[key], child))
        return mismatches
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected array, got {type(actual).__name__}"]
        for index, value in enumerate(expected):
            if value not in actual:
                mismatches.append(f"{path}[{index}]: expected member is absent")
        return mismatches
    if expected != actual:
        mismatches.append(f"{path}: expected {expected!r}, got {actual!r}")
    return mismatches


def status_mismatches(actual):
    if actual != "completed":
        return [f"adapter.status: expected 'completed', got {actual!r}"]
    return []


def expected_selection(mode, kind):
    if mode == "baseline":
        return False
    if mode == "treatment" and kind in {"positive", "negative", "confusable"}:
        return kind == "positive"
    raise ValueError(f"unsupported evaluation mode/kind: {mode!r}/{kind!r}")


def selection_mismatches(mode, kind, actual):
    try:
        expected = expected_selection(mode, kind)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(actual, bool):
        return [f"adapter.selected: expected boolean {expected!r}, got {type(actual).__name__}"]
    if actual != expected:
        return [f"adapter.selected: expected {expected!r}, got {actual!r}"]
    return []


def main():
    request = json.load(sys.stdin)
    mode = request["mode"]
    case = request["case"]
    metadata = case.get("metadata", {})
    expected_by_mode = metadata.get("expected_behavior", {})
    expected = expected_by_mode.get(mode)
    adapter = request["adapter"]
    behavior = adapter.get("metadata", {}).get("behavior")

    status_errors = status_mismatches(adapter.get("status"))
    selection_errors = selection_mismatches(mode, case.get("kind"), adapter.get("selected"))
    if not isinstance(expected, dict):
        behavior_errors = [f"case.metadata.expected_behavior.{mode}: expected object"]
    elif not isinstance(behavior, dict):
        behavior_errors = ["adapter.metadata.behavior: expected object"]
    else:
        behavior_errors = subset_mismatches(expected, behavior)

    status_passed = not status_errors
    selection_passed = not selection_errors
    behavior_passed = not behavior_errors
    passed = status_passed and selection_passed and behavior_passed
    json.dump(
        {
            "schema_version": 1,
            "contract": "agent-skill-eval/v1",
            "run_id": request["run_id"],
            "passed": passed,
            "checks": [
                {
                    "name": "completed-adapter-run",
                    "passed": status_passed,
                    "message": "adapter completed"
                    if status_passed
                    else "; ".join(status_errors[:4]),
                },
                {
                    "name": "expected-selection",
                    "passed": selection_passed,
                    "message": "selection matched"
                    if selection_passed
                    else "; ".join(selection_errors[:4]),
                },
                {
                    "name": "expected-behavior-subset",
                    "passed": behavior_passed,
                    "message": "behavior matched"
                    if behavior_passed
                    else "; ".join(behavior_errors[:16]),
                },
            ],
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
