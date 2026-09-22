#!/usr/bin/env python3
"""Prepare one disposable task and inspect its actual output. No workflow controller."""
from __future__ import annotations

import argparse
import json
import math
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from p0_runtime.common import HarnessError
from p0_runtime.skill_eval import run_protocol_process, repository_snapshot, snapshot_digest
from cases import CASES, digest, git, prepare, read, verify

CONTRACT = "skill-task-outcome/1"
METRICS = ("input_tokens", "output_tokens", "tool_calls", "wall_time_seconds")


def load(path: Path) -> dict:
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate JSON key: " + key)
            obj[key] = value
        return obj
    with path.open("rb") as handle:
        data = handle.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("JSON input exceeds 8 MiB")
    obj = json.loads(data, object_pairs_hook=unique,
                     parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def save(path: Path, value: dict) -> None:
    # Every output is write-once, including failed runs, to preserve observed evidence.
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def evaluator_digest() -> str:
    return digest(b"".join((Path(__file__).parent / name).read_bytes()
                           for name in ("cases.py", "runner.py", "import_claude.py")))


def export_skill(skill: str, revision: str, output: Path) -> str:
    records = git(ROOT, "ls-tree", "-rz", revision, "--", "skills/" + skill).split(b"\0")
    payload = []
    for raw in records:
        if not raw:
            continue
        meta, path = raw.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("skill payload must contain regular files only")
        relative = Path(path.decode()).relative_to("skills/" + skill)
        if ".." in relative.parts:
            raise ValueError("unsafe payload path")
        data = git(ROOT, "cat-file", "blob", sha)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if mode == "100755" else 0o644)
        payload.append((relative.as_posix(), mode, sha))
    if not (output / "SKILL.md").is_file():
        raise ValueError("candidate missing from pinned revision")
    return digest(json.dumps(payload, sort_keys=True).encode())


def fixture_digest(root: Path) -> str:
    return digest(json.dumps({"files": repository_snapshot(root),
                              "index": git(root, "ls-files", "--stage").decode(),
                              "head": git(root, "rev-parse", "HEAD").decode()},
                             sort_keys=True).encode())


def prepare_run(case_id: str, output: Path, condition: str, revision: str = "HEAD") -> dict:
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; use a fresh directory")
    # Never initialize experimental repositories inside the catalog checkout.
    try:
        output.resolve().relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("prepare outside the source checkout")
    case = CASES[case_id]
    full = git(ROOT, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    output.mkdir(parents=True)
    state = prepare(output / "workspace", case_id)
    prompt = case["prompt"]
    skill_path, payload_digest = None, None
    if condition == "skill":
        skill_path = output / "guidance"
        payload_digest = export_skill(case["skill"], full, skill_path)
        prompt = "Use the skill at " + str(skill_path / "SKILL.md") + ". Read relevant references as needed.\n\n" + prompt
    elif condition == "brief":
        prompt += "\n\n" + case["brief"]
    metadata = {"contract": CONTRACT, "case": case_id, "condition": condition,
                "evaluator_digest": evaluator_digest(), "skill_revision": full if skill_path else None,
                "skill_digest": payload_digest, "state": state,
                "fixture_digest": fixture_digest(output / "workspace"),
                "platform": platform.system(), "python": sys.version.split()[0],
                "prompt_digest": digest(prompt.encode())}
    (output / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    save(output / "fixture.json", metadata)
    return metadata


def assess(output: Path, driver: dict | None = None) -> dict:
    metadata = load(output / "fixture.json")
    if metadata.get("contract") != CONTRACT or metadata.get("evaluator_digest") != evaluator_digest():
        raise ValueError("fixture/evaluator mismatch; use the matching evaluator or prepare a new run")
    before = snapshot_digest(repository_snapshot(output / "workspace"))
    checks = verify(output / "workspace", metadata["case"], metadata["state"],
                    (driver or {}).get("trace", []))
    if before != snapshot_digest(repository_snapshot(output / "workspace")):
        checks.append({"name": "verification did not mutate artifacts", "passed": False, "detail": ""})
    result = {**metadata, "checks": checks, "passed": bool(checks) and all(x["passed"] for x in checks),
              "execution": "manual" if driver is None else driver["status"],
              "host": (driver or {}).get("host"),
              "metrics": (driver or {}).get("metrics", {key: None for key in METRICS})}
    if driver is not None and driver["status"] != "completed":
        result["passed"] = False
    return result


def validate_driver(value: dict, elapsed: float, model: str) -> dict:
    if value.get("status") not in ("completed", "failed"):
        raise ValueError("driver must report actual execution status")
    host = value.get("host")
    if not isinstance(host, dict) or not all(isinstance(host.get(k), str) and host[k]
                                            for k in ("name", "version", "model", "configuration", "cache")):
        raise ValueError("driver must identify host/version/model/configuration/cache conditions")
    if host["model"] != model:
        raise ValueError("actual model differs from requested fixed model")
    trace = value.get("trace", [])
    if not isinstance(trace, list) or not all(isinstance(e, dict) and all(isinstance(e.get(k), str) for k in ("tool", "command", "output")) for e in trace):
        raise ValueError("trace must contain captured tool records")
    metrics = value.get("metrics", {})
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object")
    clean = {}
    for key in METRICS:
        v = metrics.get(key)
        if v is not None and (type(v) not in (float, int) or not math.isfinite(v) or v < 0
                              or (key != "wall_time_seconds" and int(v) != v)):
            raise ValueError("invalid measured metric: " + key)
        clean[key] = v
    clean["wall_time_seconds"] = max(elapsed, clean["wall_time_seconds"] or 0)
    return {"status": value["status"], "host": host, "metrics": clean, "trace": trace}


def execute(output: Path, command: list[str], model: str, timeout: int) -> dict:
    if not command or any(not isinstance(x, str) or not x for x in command):
        raise ValueError("driver command must be a nonempty argv array")
    metadata = load(output / "fixture.json")
    if metadata.get("evaluator_digest") != evaluator_digest():
        raise ValueError("evaluator changed after preparation")
    if fixture_digest(output / "workspace") != metadata["fixture_digest"]:
        raise ValueError("workspace changed after preparation; prepare a fresh run")
    for name in ("driver.json", "result.json", "started.json"):
        if (output / name).exists():
            raise ValueError("run already attempted; preserve it and prepare a new run")
    prompt = (output / "prompt.txt").read_text(encoding="utf-8")
    if digest(prompt.encode()) != metadata["prompt_digest"]:
        raise ValueError("prepared prompt changed")
    save(output / "started.json", {"driver_command": command, "model": model})
    # Reuse the existing process budget and process-tree termination implementation.
    source_before = snapshot_digest(repository_snapshot(ROOT))
    controls_before = snapshot_digest(repository_snapshot(output, (output / "workspace",)))
    request = {"prompt": prompt, "workspace": str(output / "workspace"), "model": model}
    raw, elapsed = run_protocol_process(
        {"command": command, "timeout_seconds": timeout, "max_output_bytes": 8 * 1024 * 1024, "env": {}},
        request, ROOT, output / "workspace", metadata["condition"], metadata["case"], "task driver", 20)
    if controls_before != snapshot_digest(repository_snapshot(output, (output / "workspace",))):
        raise ValueError("driver changed prepared controls or guidance")
    if source_before != snapshot_digest(repository_snapshot(ROOT)):
        raise ValueError("driver changed the source repository")
    driver = validate_driver(raw, elapsed, model)
    save(output / "driver.json", driver)
    result = assess(output, driver)
    save(output / "result.json", result)
    return result


def compare(left: dict, right: dict) -> dict:
    for data in (left, right):
        if data.get("contract") != CONTRACT or data.get("execution") != "completed" or not data.get("host"):
            raise ValueError("comparison requires two completed measured host runs")
        if (not isinstance(data.get("checks"), list) or not data["checks"]
                or any(not isinstance(c, dict) or type(c.get("passed")) is not bool for c in data["checks"])
                or type(data.get("passed")) is not bool
                or data["passed"] is not all(c["passed"] for c in data["checks"])):
            raise ValueError("inconsistent result checks")
        validate_driver({"status": data["execution"], "host": data["host"],
                         "metrics": data["metrics"], "trace": []}, 0, data["host"]["model"])
    for key in ("case", "fixture_digest", "evaluator_digest", "platform", "python", "host"):
        if left[key] != right[key]:
            raise ValueError("incomparable runs: " + key)
    return {"baseline_passed": left["passed"], "treatment_passed": right["passed"],
            "metric_deltas": {key: None if left["metrics"].get(key) is None or right["metrics"].get(key) is None
                               else right["metrics"][key] - left["metrics"][key] for key in METRICS},
            "note": "One pair is descriptive evidence, not a statistically established efficacy claim."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("case", choices=CASES); prep.add_argument("output", type=Path)
    prep.add_argument("--condition", choices=("none", "brief", "skill"), required=True)
    prep.add_argument("--skill-revision", default="HEAD")
    run = commands.add_parser("run")
    run.add_argument("output", type=Path); run.add_argument("--driver-json", type=Path, required=True)
    run.add_argument("--model", required=True); run.add_argument("--timeout", type=int, default=600, choices=range(1,3601), metavar="1..3600")
    run.add_argument("--allow-execution", action="store_true", help="authorize the trusted local driver in a disposable environment")
    check = commands.add_parser("verify")
    check.add_argument("output", type=Path); check.add_argument("--driver-result", type=Path)
    comp = commands.add_parser("compare")
    comp.add_argument("baseline", type=Path); comp.add_argument("treatment", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            value = prepare_run(args.case, args.output, args.condition, args.skill_revision)
        elif args.action == "run":
            if not args.allow_execution:
                raise ValueError("run needs --allow-execution; the driver is not OS-sandboxed")
            value = execute(args.output.resolve(), load(args.driver_json)["command"], args.model, args.timeout)
        elif args.action == "verify":
            driver = load(args.driver_result) if args.driver_result else None
            if driver is not None:
                driver = validate_driver(driver, 0, driver.get("host", {}).get("model", ""))
            value = assess(args.output.resolve(), driver)
        else:
            value = compare(load(args.baseline), load(args.treatment))
        print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if value.get("passed", True) else 30
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError, HarnessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
