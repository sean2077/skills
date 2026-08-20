#!/usr/bin/env python3
"""Deterministic state runtime bundled with this independently installable skill."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


class WorkflowError(Exception):
    def __init__(self, code: int, kind: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.kind = kind
        self.message = message
        self.details = details


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise WorkflowError(2, "usage", message)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def emit(payload: Dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=stream)


def git(args: List[str]) -> str:
    cp = subprocess.run(
        ["git", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if cp.returncode != 0:
        raise WorkflowError(
            6,
            "not_a_git_worktree",
            "run the workflow from a non-bare Git worktree",
            command=["git", *args],
            stderr=cp.stderr.strip(),
        )
    return cp.stdout.strip()


def repository_context() -> Dict[str, str]:
    worktree = Path(git(["rev-parse", "--show-toplevel"])).resolve()
    cp = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if cp.returncode == 0:
        common = Path(cp.stdout.strip()).resolve()
    else:
        raw = Path(git(["rev-parse", "--git-common-dir"]))
        common = (Path.cwd() / raw).resolve() if not raw.is_absolute() else raw.resolve()
    branch_cp = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    branch = branch_cp.stdout.strip()
    if branch_cp.returncode != 0:
        branch = "DETACHED:" + git(["rev-parse", "--short=12", "HEAD"])
    repository_root = common.parent.resolve() if common.name == ".git" else worktree
    return {
        "worktree": str(worktree),
        "branch": branch,
        "repository_root": str(repository_root),
    }


def validate_id(value: str) -> str:
    if not ID_RE.fullmatch(value):
        raise WorkflowError(
            2,
            "invalid_id",
            "id must be 1-64 lowercase letters, digits, dot, underscore, or hyphen",
            value=value,
        )
    return value


def state_paths(workflow: str, run_id: str, *, create: bool = True) -> Tuple[Path, Path, Path]:
    context = repository_context()
    base = Path(context["repository_root"]) / ".agent-workflows"
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        raise WorkflowError(6, "unsafe_state_root", "workflow state base must not be a symlink", path=str(base))
    if create:
        base.mkdir(parents=True, exist_ok=True)
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        raise WorkflowError(6, "unsafe_state_root", "workflow state base must not be a symlink", path=str(base))
    root = base / workflow
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise WorkflowError(6, "unsafe_state_root", "workflow state directory must not be a symlink", path=str(root))
    if create:
        root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise WorkflowError(6, "unsafe_state_root", "workflow state directory must not be a symlink", path=str(root))
    path = root / f"{run_id}.json"
    if path.is_symlink():
        raise WorkflowError(6, "unsafe_state_file", "workflow state file must not be a symlink", path=str(path))
    return path, path.with_suffix(".json.bak"), path.with_suffix(".json.lock")


@contextlib.contextmanager
def command_lock(lock_path: Path) -> Iterator[None]:
    owner = {"pid": os.getpid(), "created_at": now(), "cwd": str(Path.cwd().resolve())}
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(str(lock_path), flags, 0o600)
    except FileExistsError as exc:
        details: Dict[str, Any] = {"path": str(lock_path)}
        try:
            details["owner"] = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            details["owner"] = "unreadable"
        raise WorkflowError(5, "locked", "another workflow mutation may be active", **details) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(owner, fh, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write(path: Path, payload: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        try:
            os.fchmod(fd, 0o600)
        except AttributeError:
            pass
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(temp_path), str(path))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def save_state(path: Path, backup: Path, state: Dict[str, Any]) -> None:
    if path.exists():
        atomic_write(backup, path.read_bytes())
    state["updated_at"] = now()
    payload = (json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    atomic_write(path, payload)


def load_state(path: Path, workflow: str, run_id: str) -> Dict[str, Any]:
    if not path.exists():
        raise WorkflowError(3, "not_found", "workflow run does not exist", workflow=workflow, id=run_id)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowError(6, "corrupt_state", "workflow state is unreadable", path=str(path), error=str(exc)) from exc
    required = {
        "schema", "workflow", "id", "revision", "status", "phase", "idea", "type", "depth", "threshold",
        "dimensions", "scores", "component_scores", "topology", "rounds", "spec_path", "terminal_reason",
        "binding", "created_at", "updated_at",
    }
    if not isinstance(state, dict):
        raise WorkflowError(6, "corrupt_state", "workflow state must be a JSON object", path=str(path))
    missing = sorted(required - set(state))
    if missing:
        raise WorkflowError(6, "corrupt_state", "workflow state is missing required fields", path=str(path), missing=missing)
    if state.get("schema") != f"agent-workflow/{workflow}/1" or state.get("workflow") != workflow or state.get("id") != run_id:
        raise WorkflowError(6, "corrupt_state", "workflow schema or identity does not match its state path", path=str(path))
    if isinstance(state.get("revision"), bool) or not isinstance(state.get("revision"), int) or state["revision"] < 1:
        raise WorkflowError(6, "corrupt_state", "state revision must be a positive integer", path=str(path))
    if state.get("status") not in {"active", "completed", "aborted"} or state.get("phase") not in {"topology", "interview", "complete", "aborted"}:
        raise WorkflowError(6, "corrupt_state", "workflow state has an invalid status or phase", path=str(path))
    if not isinstance(state["idea"], str) or not state["idea"].strip() or state["type"] not in {"greenfield", "brownfield"} or state["depth"] not in DEPTHS:
        raise WorkflowError(6, "corrupt_state", "workflow idea, type, or depth is invalid", path=str(path))
    threshold = state["threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)) or not 0.0 < float(threshold) < 1.0:
        raise WorkflowError(6, "corrupt_state", "workflow threshold must be finite and between 0 and 1", path=str(path))
    expected_dimensions = dimensions(state["type"])
    if state["dimensions"] != expected_dimensions:
        raise WorkflowError(6, "corrupt_state", "workflow dimensions do not match its type", path=str(path), expected=expected_dimensions)
    if not isinstance(state["scores"], dict) or set(state["scores"]) != set(expected_dimensions) or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
        for value in state["scores"].values()
    ):
        raise WorkflowError(6, "corrupt_state", "workflow dimension scores are invalid", path=str(path))
    component_scores = state["component_scores"]
    if not isinstance(component_scores, dict):
        raise WorkflowError(6, "corrupt_state", "component_scores must be an object", path=str(path))
    topology_state = state["topology"]
    if topology_state is None:
        if component_scores:
            raise WorkflowError(6, "corrupt_state", "component_scores must be empty before topology is locked", path=str(path))
    else:
        if not isinstance(topology_state, dict) or not isinstance(topology_state.get("components"), list):
            raise WorkflowError(6, "corrupt_state", "topology must contain a component list", path=str(path))
        active_ids = set()
        for component in topology_state["components"]:
            if not isinstance(component, dict) or not isinstance(component.get("id"), str) or component.get("status") not in {"active", "deferred"}:
                raise WorkflowError(6, "corrupt_state", "topology contains an invalid component", path=str(path))
            if component["status"] == "active":
                active_ids.add(component["id"])
        if set(component_scores) != active_ids:
            raise WorkflowError(6, "corrupt_state", "component_scores must cover active components exactly", path=str(path), expected=sorted(active_ids))
        for component_id, scores in component_scores.items():
            if not isinstance(scores, dict) or set(scores) != set(expected_dimensions) or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
                for value in scores.values()
            ):
                raise WorkflowError(6, "corrupt_state", "component scores are invalid", path=str(path), component=component_id)
    if not isinstance(state["rounds"], list) or any(not isinstance(row, dict) for row in state["rounds"]):
        raise WorkflowError(6, "corrupt_state", "rounds must be a list of objects", path=str(path))
    if state["spec_path"] is not None and not isinstance(state["spec_path"], str):
        raise WorkflowError(6, "corrupt_state", "spec_path must be a string or null", path=str(path))
    if state["terminal_reason"] is not None and not isinstance(state["terminal_reason"], str):
        raise WorkflowError(6, "corrupt_state", "terminal_reason must be a string or null", path=str(path))
    binding = state["binding"]
    if not isinstance(binding, dict) or not isinstance(binding.get("worktree"), str) or not isinstance(binding.get("branch"), str):
        raise WorkflowError(6, "corrupt_state", "binding must contain worktree and branch strings", path=str(path))
    if not isinstance(state["created_at"], str) or not isinstance(state["updated_at"], str):
        raise WorkflowError(6, "corrupt_state", "created_at and updated_at must be strings", path=str(path))
    return state


def binding_report(state: Dict[str, Any]) -> Dict[str, Any]:
    current = repository_context()
    recorded = state.get("binding", {})
    ok = recorded.get("worktree") == current["worktree"] and recorded.get("branch") == current["branch"]
    return {"ok": ok, "recorded": recorded, "current": {"worktree": current["worktree"], "branch": current["branch"]}}


def require_mutable(
    path: Path,
    workflow: str,
    run_id: str,
    expected_revision: int,
    *,
    allow_mismatch: bool = False,
) -> Dict[str, Any]:
    state = load_state(path, workflow, run_id)
    if state["revision"] != expected_revision:
        raise WorkflowError(
            5,
            "revision_conflict",
            "state changed since it was read",
            expected=expected_revision,
            actual=state["revision"],
        )
    report = binding_report(state)
    if not allow_mismatch and not report["ok"]:
        raise WorkflowError(5, "binding_mismatch", "run is owned by another worktree or branch", **report)
    return state


def bump(state: Dict[str, Any]) -> None:
    state["revision"] += 1


def load_json_file(value: str) -> Dict[str, Any]:
    path = Path(value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(2, "invalid_input", "input must be a readable JSON object", path=str(path), error=str(exc)) from exc
    if not isinstance(payload, dict):
        raise WorkflowError(2, "invalid_input", "input JSON must be an object", path=str(path))
    return payload


def new_binding() -> Dict[str, str]:
    context = repository_context()
    return {"worktree": context["worktree"], "branch": context["branch"]}


def status_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "state": state, "binding": binding_report(state)}


WORKFLOW = "deep-interview"
SCHEMA = "agent-workflow/deep-interview/1"
TOPOLOGY_SCHEMA = "agent-interview-topology/1"
ROUND_SCHEMA = "agent-interview-round/1"
DEPTHS = {"quick": 0.30, "standard": 0.20, "deep": 0.10}
BASE_DIMENSIONS = ["problem", "users", "scope", "behavior", "acceptance", "constraints", "risks"]


def dimensions(kind: str) -> List[str]:
    return BASE_DIMENSIONS + (["context"] if kind == "brownfield" else [])


def metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    topology_state = state.get("topology")
    active_ids: List[str] = []
    if isinstance(topology_state, dict):
        active_ids = sorted(
            component["id"]
            for component in topology_state.get("components", [])
            if component.get("status") == "active"
        )
    if active_ids:
        component_scores = state["component_scores"]
        dimension_scores = {
            name: min(float(component_scores[component_id][name]) for component_id in active_ids)
            for name in state["dimensions"]
        }
    else:
        dimension_scores = {name: float(state["scores"][name]) for name in state["dimensions"]}
    values = [dimension_scores[name] for name in state["dimensions"]]
    mean = sum(values) / len(values)
    ambiguity = round(0.6 * (1.0 - mean) + 0.4 * (1.0 - min(values)), 4)
    gate = ambiguity <= state["threshold"] and min(values) >= 0.5
    if gate:
        next_target = None
    elif active_ids:
        candidates = [
            (float(state["component_scores"][component_id][dimension]), component_id, dimension)
            for component_id in active_ids
            for dimension in state["dimensions"]
        ]
        weakest = min(score for score, _, _ in candidates)
        tied = [(component_id, dimension) for score, component_id, dimension in candidates if abs(score - weakest) < 1e-9]
        last_seen: Dict[Tuple[str, str], int] = {}
        for index, row in enumerate(state["rounds"]):
            target = row.get("target")
            if isinstance(target, dict) and isinstance(target.get("component"), str) and isinstance(target.get("dimension"), str):
                last_seen[(target["component"], target["dimension"])] = index
        component_order = {component_id: index for index, component_id in enumerate(active_ids)}
        dimension_order = {dimension: index for index, dimension in enumerate(state["dimensions"])}
        component_id, dimension = min(
            tied,
            key=lambda pair: (last_seen.get(pair, -1), component_order[pair[0]], dimension_order[pair[1]]),
        )
        next_target = {"component": component_id, "dimension": dimension}
    elif state["dimensions"]:
        weakest = min(values)
        next_target = min(
            (name for name in state["dimensions"] if abs(dimension_scores[name] - weakest) < 1e-9),
            key=state["dimensions"].index,
        )
    else:
        next_target = None
    return {"ambiguity": ambiguity, "dimension_scores": dimension_scores, "gate_passed": gate, "next_target": next_target}


def enrich(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = status_payload(state)
    payload["metrics"] = metrics(state)
    return payload


def start(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    threshold = args.threshold if args.threshold is not None else DEPTHS[args.depth]
    if not 0.0 < threshold < 1.0:
        raise WorkflowError(2, "invalid_threshold", "threshold must be between 0 and 1", threshold=threshold)
    idea = args.idea.strip()
    if not idea:
        raise WorkflowError(2, "invalid_idea", "idea must not be empty")
    with command_lock(lock):
        if path.exists():
            old = load_state(path, WORKFLOW, run_id)
            raise WorkflowError(5, "already_exists", "interview already exists", revision=old["revision"], phase=old.get("phase"))
        stamp = now()
        dims = dimensions(args.type)
        state: Dict[str, Any] = {
            "schema": SCHEMA, "workflow": WORKFLOW, "id": run_id, "revision": 1,
            "status": "active", "phase": "topology", "idea": idea, "type": args.type,
            "depth": args.depth, "threshold": threshold, "dimensions": dims,
            "scores": {name: 0.0 for name in dims}, "component_scores": {}, "topology": None, "rounds": [],
            "spec_path": None, "terminal_reason": None, "binding": new_binding(),
            "created_at": stamp, "updated_at": stamp,
        }
        save_state(path, backup, state)
    emit(enrich(state)); return 0


def status(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, _, _ = state_paths(WORKFLOW, run_id, create=False)
    state = load_state(path, WORKFLOW, run_id); payload = enrich(state); emit(payload)
    return 0 if payload["binding"]["ok"] else 5


def validate_topology(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("schema") != TOPOLOGY_SCHEMA:
        raise WorkflowError(2, "invalid_topology", "topology schema must be agent-interview-topology/1")
    components = payload.get("components")
    deferrals = payload.get("deferrals", [])
    if not isinstance(components, list) or not 1 <= len(components) <= 6:
        raise WorkflowError(2, "invalid_topology", "topology must contain 1-6 components")
    if not isinstance(deferrals, list):
        raise WorkflowError(2, "invalid_topology", "deferrals must be a list")
    seen = set(); deferred = set(); cleaned = []
    for item in components:
        if not isinstance(item, dict): raise WorkflowError(2, "invalid_topology", "each component must be an object")
        cid = item.get("id"); status_value = item.get("status")
        if not isinstance(cid, str) or not ID_RE.fullmatch(cid): raise WorkflowError(2, "invalid_topology", "component id is invalid", id=cid)
        if cid in seen: raise WorkflowError(2, "invalid_topology", "component ids must be unique", id=cid)
        seen.add(cid)
        if status_value not in {"active", "deferred"}: raise WorkflowError(2, "invalid_topology", "component status must be active or deferred", id=cid)
        if status_value == "deferred": deferred.add(cid)
        for field in ("name", "description"):
            if not isinstance(item.get(field), str) or not item[field].strip(): raise WorkflowError(2, "invalid_topology", f"component {field} must not be empty", id=cid)
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(v, str) and v.strip() for v in evidence): raise WorkflowError(2, "invalid_topology", "component evidence must be a list of non-empty strings", id=cid)
        cleaned.append(item)
    if not (seen - deferred): raise WorkflowError(2, "invalid_topology", "topology needs at least one active component")
    reasons: Dict[str, str] = {}
    for item in deferrals:
        if not isinstance(item, dict) or not isinstance(item.get("component_id"), str) or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise WorkflowError(2, "invalid_topology", "each deferral needs component_id and non-empty reason")
        cid = item["component_id"]
        if cid not in deferred or cid in reasons: raise WorkflowError(2, "invalid_topology", "deferral must target one deferred component exactly once", component_id=cid)
        reasons[cid] = item["reason"].strip()
    if set(reasons) != deferred: raise WorkflowError(2, "invalid_topology", "every deferred component needs exactly one reason", missing=sorted(deferred - set(reasons)))
    return {"schema": TOPOLOGY_SCHEMA, "components": cleaned, "deferrals": deferrals}


def topology(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, backup, lock = state_paths(WORKFLOW, run_id)
    payload = validate_topology(load_json_file(args.input))
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active" or state.get("phase") != "topology": raise WorkflowError(4, "invalid_transition", "topology can be locked only once in topology phase", phase=state.get("phase"))
        state["topology"] = payload
        state["component_scores"] = {
            component["id"]: {dimension: 0.0 for dimension in state["dimensions"]}
            for component in payload["components"]
            if component["status"] == "active"
        }
        state["phase"] = "interview"; bump(state); save_state(path, backup, state)
    emit(enrich(state)); return 0


def score(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, backup, lock = state_paths(WORKFLOW, run_id)
    payload = load_json_file(args.input)
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active" or state.get("phase") != "interview": raise WorkflowError(4, "invalid_transition", "scores can be submitted only in interview phase", phase=state.get("phase"))
        current_metrics = metrics(state)
        if current_metrics["gate_passed"]: raise WorkflowError(4, "gate_already_passed", "complete the interview instead of adding another round")
        if payload.get("schema") != ROUND_SCHEMA: raise WorkflowError(2, "invalid_round", "round schema must be agent-interview-round/1")
        expected_round = len(state["rounds"]) + 1
        if payload.get("round") != expected_round: raise WorkflowError(2, "invalid_round", "round number must be contiguous", expected=expected_round, actual=payload.get("round"))
        if payload.get("target") != current_metrics["next_target"]: raise WorkflowError(2, "invalid_target", "round target must match runtime next_target", expected=current_metrics["next_target"], actual=payload.get("target"))
        for field in ("question", "answer"):
            if not isinstance(payload.get(field), str) or not payload[field].strip(): raise WorkflowError(2, "invalid_round", f"{field} must not be empty")
        component_scores = payload.get("component_scores"); evidence = payload.get("evidence")
        active_ids = sorted(state["component_scores"])
        if not isinstance(component_scores, dict) or set(component_scores) != set(active_ids): raise WorkflowError(2, "invalid_scores", "component_scores must contain every active component exactly", expected=active_ids)
        cleaned_component_scores: Dict[str, Dict[str, float]] = {}
        for component_id in active_ids:
            scores = component_scores[component_id]
            if not isinstance(scores, dict) or set(scores) != set(state["dimensions"]): raise WorkflowError(2, "invalid_scores", "each active component must contain every required dimension exactly", component=component_id, expected=state["dimensions"])
            cleaned_component_scores[component_id] = {}
            for name in state["dimensions"]:
                value = scores[name]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0: raise WorkflowError(2, "invalid_scores", "each score must be finite and between 0 and 1", component=component_id, dimension=name, value=value)
                cleaned_component_scores[component_id][name] = float(value)
        if not isinstance(evidence, dict): raise WorkflowError(2, "invalid_evidence", "evidence must be an object")
        changed: List[Tuple[str, str]] = []
        for component_id in active_ids:
            for name in state["dimensions"]:
                if abs(cleaned_component_scores[component_id][name] - float(state["component_scores"][component_id][name])) > 1e-9:
                    changed.append((component_id, name))
        missing_evidence = []
        for component_id, name in changed:
            component_evidence = evidence.get(component_id)
            items = component_evidence.get(name) if isinstance(component_evidence, dict) else evidence.get(name)
            if not isinstance(items, list) or not items or not all(isinstance(v, str) and v.strip() for v in items):
                missing_evidence.append({"component": component_id, "dimension": name})
        if missing_evidence:
            raise WorkflowError(2, "invalid_evidence", "every changed component score needs at least one non-empty evidence item", dimensions=missing_evidence)
        dimension_scores = {
            name: min(cleaned_component_scores[component_id][name] for component_id in active_ids)
            for name in state["dimensions"]
        }
        row = {"round": expected_round, "target": payload["target"], "question": payload["question"].strip(), "answer": payload["answer"].strip(), "component_scores": cleaned_component_scores, "scores": dimension_scores, "evidence": evidence, "recorded_at": now()}
        state["rounds"].append(row); state["component_scores"] = cleaned_component_scores; state["scores"] = dimension_scores; bump(state); save_state(path, backup, state)
    emit(enrich(state)); return 0


def complete(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, backup, lock = state_paths(WORKFLOW, run_id); spec_path = args.spec_path.strip()
    if not spec_path: raise WorkflowError(2, "invalid_spec_path", "spec path must not be empty")
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        report = metrics(state)
        if state.get("status") != "active" or state.get("phase") != "interview" or not report["gate_passed"]: raise WorkflowError(4, "gate_not_passed", "interview cannot complete before the mechanical gate passes", metrics=report)
        state["phase"] = "complete"; state["status"] = "completed"; state["spec_path"] = spec_path; state["terminal_reason"] = "pending approval spec recorded"; bump(state); save_state(path, backup, state)
    emit(enrich(state)); return 0


def abort(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, backup, lock = state_paths(WORKFLOW, run_id); reason = args.reason.strip()
    if not reason: raise WorkflowError(2, "invalid_reason", "abort reason must not be empty")
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active": raise WorkflowError(4, "terminal", "interview is already terminal", status=state.get("status"))
        state["phase"] = "aborted"; state["status"] = "aborted"; state["terminal_reason"] = reason; bump(state); save_state(path, backup, state)
    emit(enrich(state)); return 0


def rebind(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id); path, backup, lock = state_paths(WORKFLOW, run_id)
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision, allow_mismatch=True)
        if state.get("status") != "active": raise WorkflowError(4, "terminal", "terminal interviews cannot be rebound", status=state.get("status"))
        state["binding"] = new_binding(); bump(state); save_state(path, backup, state)
    emit(enrich(state)); return 0


def parser() -> JsonArgumentParser:
    p = JsonArgumentParser(description="Deterministic deep-interview scoring state"); sub = p.add_subparsers(dest="command", required=True)
    s=sub.add_parser("start"); s.add_argument("--id",required=True); s.add_argument("--idea",required=True); s.add_argument("--depth",choices=sorted(DEPTHS),default="standard"); s.add_argument("--threshold",type=float); s.add_argument("--type",choices=["greenfield","brownfield"],default="greenfield"); s.set_defaults(func=start)
    s=sub.add_parser("status"); s.add_argument("--id",required=True); s.set_defaults(func=status)
    s=sub.add_parser("topology"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--input",required=True); s.set_defaults(func=topology)
    s=sub.add_parser("score"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--input",required=True); s.set_defaults(func=score)
    s=sub.add_parser("complete"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--spec-path",required=True); s.set_defaults(func=complete)
    s=sub.add_parser("abort"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--reason",required=True); s.set_defaults(func=abort)
    s=sub.add_parser("rebind"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.set_defaults(func=rebind)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    try: args=parser().parse_args(argv); return int(args.func(args))
    except WorkflowError as exc: emit({"ok":False,"error":exc.kind,"message":exc.message,"details":exc.details},stream=sys.stderr); return exc.code

if __name__ == "__main__": raise SystemExit(main())
