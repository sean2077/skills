#!/usr/bin/env python3
"""Normalize a captured Claude stream, never an assistant-written success summary."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from runner import ROOT, save, validate_driver


def parse_stream(path: Path, version: str, model: str, configuration: str,
                 cache: str, elapsed: float, exit_code: int) -> dict:
    with path.open("rb") as handle:
        data = handle.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("stream exceeds 8 MiB; preserve raw evidence and use a smaller task")
    spec = importlib.util.spec_from_file_location("routing_usage", ROOT / "evals/agent-skills/host_adapter.py")
    usage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(usage)
    events = [usage.parse_json(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    results = [e for e in events if e.get("type") == "result"]
    if len(results) != 1 or events[-1].get("type") != "result":
        raise ValueError("missing, duplicated, or truncated final CLI result")
    models, tools, trace, completed_ids = set(), {}, [], set()
    for event in events:
        if event.get("type") not in ("assistant", "user"):
            continue
        message = event.get("message", {})
        if event["type"] == "assistant" and message.get("model"):
            models.add(message["model"])
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if event["type"] == "assistant" and block.get("type") == "tool_use":
                key = block["id"]
                if key in tools:
                    raise ValueError("duplicate tool-use identity")
                tools[key] = block
            elif event["type"] == "user" and block.get("type") == "tool_result":
                key = block["tool_use_id"]
                if key not in tools or key in completed_ids:
                    raise ValueError("unmatched or duplicate tool result")
                completed_ids.add(key)
                call = tools[key]
                result = block.get("content", "")
                if isinstance(result, list):
                    result = "\n".join(x.get("text", "") for x in result if isinstance(x, dict))
                if not isinstance(result, str):
                    raise ValueError("unsupported tool-result content")
                trace.append({"tool": call.get("name", ""),
                              "command": call.get("input", {}).get("command", ""), "output": result})
    reported = results[0].get("modelUsage", {})
    models.update(reported)
    if models != {model}:
        raise ValueError("recorded models differ from the requested fixed model")
    # Missing/invalid accounting is unknown, not a fabricated zero-cost run.
    try:
        metrics = usage.metrics(results[0], elapsed)
    except (ValueError, TypeError, KeyError):
        metrics = {"input_tokens": None, "output_tokens": None, "wall_time_seconds": elapsed}
    metrics["tool_calls"] = len(tools)
    status = "completed" if (exit_code == 0 and results[0].get("is_error") is False
                              and tools.keys() == completed_ids) else "failed"
    value = {"status": status, "host": {"name": "claude", "version": version.strip(),
             "model": model, "configuration": configuration, "cache": cache},
             "metrics": metrics, "trace": trace}
    return validate_driver(value, elapsed, model)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--version-file", type=Path, required=True)
    parser.add_argument("--model", required=True); parser.add_argument("--configuration", required=True)
    parser.add_argument("--cache-condition", required=True)
    parser.add_argument("--elapsed-seconds", type=float, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    try:
        result = parse_stream(args.stream, args.version_file.read_text(encoding="utf-8"), args.model,
                              args.configuration, args.cache_condition, args.elapsed_seconds, args.exit_code)
        save(args.output, result)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
