#!/usr/bin/env python3
"""Read-only deterministic verifier for the offline example."""
import json
import pathlib
import sys

request = json.load(sys.stdin)
source = (pathlib.Path(request["workspace"]) / "src" / "calc.py").read_text(encoding="utf-8")
positive = request["case"]["kind"] == "positive"
expected = "return left + right" if positive and request["mode"] == "treatment" else "return left - right"
passed = expected in source
json.dump(
    {
        "schema_version": 1,
        "contract": "agent-skill-eval/v1",
        "run_id": request["run_id"],
        "passed": passed,
        "checks": [
            {
                "name": "fixture-content",
                "passed": passed,
                "message": "expected deterministic fixture state",
            }
        ],
    },
    sys.stdout,
)
