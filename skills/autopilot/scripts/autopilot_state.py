#!/usr/bin/env python3
"""Deterministic state runtime bundled with this independently installable skill."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
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
        "schema", "workflow", "id", "revision", "status", "phase", "goal", "plan_path",
        "verify_failures", "verification", "terminal_reason", "binding", "created_at", "updated_at",
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
    if state.get("status") not in {"active", *TERMINAL} or state.get("phase") not in {"clarify", "plan", "implement", "verify", "deliver", "done", "blocked", "aborted"}:
        raise WorkflowError(6, "corrupt_state", "workflow state has an invalid status or phase", path=str(path))
    if not isinstance(state["goal"], str) or not state["goal"].strip():
        raise WorkflowError(6, "corrupt_state", "workflow goal must be a non-empty string", path=str(path))
    if state["plan_path"] is not None and not isinstance(state["plan_path"], str):
        raise WorkflowError(6, "corrupt_state", "workflow plan_path must be a string or null", path=str(path))
    if isinstance(state["verify_failures"], bool) or not isinstance(state["verify_failures"], int) or state["verify_failures"] < 0:
        raise WorkflowError(6, "corrupt_state", "verify_failures must be a non-negative integer", path=str(path))
    if not isinstance(state["verification"], list) or any(
        not isinstance(row, dict)
        or isinstance(row.get("exit_code"), bool)
        or not isinstance(row.get("exit_code"), int)
        or not isinstance(row.get("summary"), str)
        or not row["summary"].strip()
        for row in state["verification"]
    ):
        raise WorkflowError(6, "corrupt_state", "verification must contain valid result records", path=str(path))
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


def new_binding() -> Dict[str, str]:
    context = repository_context()
    return {"worktree": context["worktree"], "branch": context["branch"]}


def status_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "state": state, "binding": binding_report(state)}


WORKFLOW = "autopilot"
SCHEMA = "agent-workflow/autopilot/1"
TERMINAL = {"done", "blocked", "aborted"}


def start(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    with command_lock(lock):
        if path.exists():
            state = load_state(path, WORKFLOW, run_id)
            raise WorkflowError(5, "already_exists", "workflow run already exists", revision=state["revision"], phase=state.get("phase"))
        stamp = now()
        state: Dict[str, Any] = {
            "schema": SCHEMA,
            "workflow": WORKFLOW,
            "id": run_id,
            "revision": 1,
            "status": "active",
            "phase": "clarify",
            "goal": args.goal.strip(),
            "plan_path": None,
            "verify_failures": 0,
            "verification": [],
            "terminal_reason": None,
            "binding": new_binding(),
            "created_at": stamp,
            "updated_at": stamp,
        }
        if not state["goal"]:
            raise WorkflowError(2, "invalid_goal", "goal must not be empty")
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def status(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, _, _ = state_paths(WORKFLOW, run_id, create=False)
    state = load_state(path, WORKFLOW, run_id)
    payload = status_payload(state)
    emit(payload)
    return 0 if payload["binding"]["ok"] else 5


def advance(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    allowed = {("clarify", "plan"), ("implement", "verify")}
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        pair = (state.get("phase"), args.to)
        if state.get("status") != "active" or pair not in allowed:
            raise WorkflowError(4, "invalid_transition", "requested phase transition is not allowed", current=state.get("phase"), requested=args.to)
        state["phase"] = args.to
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def record_plan(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    plan_path = args.path.strip()
    if not plan_path:
        raise WorkflowError(2, "invalid_plan_path", "plan path must not be empty")
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active" or state.get("phase") != "plan":
            raise WorkflowError(4, "invalid_transition", "a plan can be recorded only in plan phase", current=state.get("phase"))
        state["plan_path"] = plan_path
        state["phase"] = "implement"
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def verify(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    summary = args.summary.strip()
    if not summary:
        raise WorkflowError(2, "invalid_summary", "verification summary must not be empty")
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active" or state.get("phase") != "verify":
            raise WorkflowError(4, "invalid_transition", "verification can be recorded only in verify phase", current=state.get("phase"))
        record = {"exit_code": args.exit_code, "summary": summary, "recorded_at": now()}
        state["verification"].append(record)
        if args.exit_code == 0:
            state["phase"] = "deliver"
        else:
            state["verify_failures"] += 1
            if state["verify_failures"] == 1:
                state["phase"] = "implement"
            else:
                state["phase"] = "blocked"
                state["status"] = "blocked"
                state["terminal_reason"] = summary
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0 if state["status"] == "active" else 4


def finish(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") != "active" or state.get("phase") != "deliver":
            raise WorkflowError(4, "invalid_transition", "finish is allowed only in deliver phase", current=state.get("phase"))
        state["phase"] = "done"
        state["status"] = "done"
        state["terminal_reason"] = args.summary.strip() or "delivered"
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def abort(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    reason = args.reason.strip()
    if not reason:
        raise WorkflowError(2, "invalid_reason", "abort reason must not be empty")
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision)
        if state.get("status") in TERMINAL:
            raise WorkflowError(4, "terminal", "run is already terminal", status=state.get("status"))
        state["phase"] = "aborted"
        state["status"] = "aborted"
        state["terminal_reason"] = reason
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def rebind(args: argparse.Namespace) -> int:
    run_id = validate_id(args.id)
    path, backup, lock = state_paths(WORKFLOW, run_id)
    with command_lock(lock):
        state = require_mutable(path, WORKFLOW, run_id, args.expected_revision, allow_mismatch=True)
        if state.get("status") in TERMINAL:
            raise WorkflowError(4, "terminal", "terminal runs cannot be rebound", status=state.get("status"))
        state["binding"] = new_binding()
        bump(state)
        save_state(path, backup, state)
    emit(status_payload(state))
    return 0


def parser() -> JsonArgumentParser:
    p = JsonArgumentParser(description="Deterministic autopilot phase state")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("start"); s.add_argument("--id", required=True); s.add_argument("--goal", required=True); s.set_defaults(func=start)
    s = sub.add_parser("status"); s.add_argument("--id", required=True); s.set_defaults(func=status)
    s = sub.add_parser("advance"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.add_argument("--to", choices=["plan", "verify"], required=True); s.set_defaults(func=advance)
    s = sub.add_parser("plan"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.add_argument("--path", required=True); s.set_defaults(func=record_plan)
    s = sub.add_parser("verify"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.add_argument("--exit-code", type=int, required=True); s.add_argument("--summary", required=True); s.set_defaults(func=verify)
    s = sub.add_parser("finish"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.add_argument("--summary", default="delivered"); s.set_defaults(func=finish)
    s = sub.add_parser("abort"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.add_argument("--reason", required=True); s.set_defaults(func=abort)
    s = sub.add_parser("rebind"); s.add_argument("--id", required=True); s.add_argument("--expected-revision", type=int, required=True); s.set_defaults(func=rebind)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parser().parse_args(argv)
        return int(args.func(args))
    except WorkflowError as exc:
        emit({"ok": False, "error": exc.kind, "message": exc.message, "details": exc.details}, stream=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
