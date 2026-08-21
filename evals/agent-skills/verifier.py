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


def main():
    request = json.load(sys.stdin)
    mode = request["mode"]
    metadata = request["case"].get("metadata", {})
    expected_by_mode = metadata.get("expected_behavior", {})
    expected = expected_by_mode.get(mode)
    behavior = request["adapter"].get("metadata", {}).get("behavior")

    if not isinstance(expected, dict):
        mismatches = [f"case.metadata.expected_behavior.{mode}: expected object"]
    elif not isinstance(behavior, dict):
        mismatches = ["adapter.metadata.behavior: expected object"]
    else:
        mismatches = subset_mismatches(expected, behavior)

    passed = not mismatches
    json.dump(
        {
            "schema_version": 1,
            "contract": "agent-skill-eval/v1",
            "run_id": request["run_id"],
            "passed": passed,
            "checks": [
                {
                    "name": "expected-behavior-subset",
                    "passed": passed,
                    "message": "behavior matched" if passed else "; ".join(mismatches[:16]),
                }
            ],
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
