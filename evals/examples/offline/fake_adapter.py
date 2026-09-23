#!/usr/bin/env python3
"""Deterministic CI adapter implementing agent-skill-eval/v1 without a model."""
import json
import pathlib
import sys

request = json.load(sys.stdin)
case = request["case"]
mode = request["mode"]
selected = mode == "treatment" and case["kind"] == "positive"
if selected:
    target = pathlib.Path(request["workspace"]) / "src" / "calc.py"
    target.write_text(
        "def add(left, right):\n    return left + right\n",
        encoding="utf-8",
    )
metrics = {
    "input_tokens": 10 if mode == "baseline" else 14,
    "output_tokens": 2 if mode == "baseline" else 4,
    "tool_calls": 0 if mode == "baseline" else (1 if selected else 0),
    "wall_time_seconds": 0,
    "interventions": 0,
}
json.dump(
    {
        "schema_version": 1,
        "contract": "agent-skill-eval/v1",
        "run_id": request["run_id"],
        "mode": mode,
        "selected": selected,
        "status": "completed",
        "metrics": metrics,
        "metadata": {"fixture_adapter": True},
    },
    sys.stdout,
)
