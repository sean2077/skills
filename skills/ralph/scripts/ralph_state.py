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
        "schema", "workflow", "id", "revision", "status", "goal", "profile", "keep_policy",
        "max_rounds", "stall_window", "plateau_window", "round", "pending_round", "history",
        "best_score", "no_improvement", "terminal_reason", "binding", "created_at", "updated_at",
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
    if state.get("status") not in {"active", *TERMINAL}:
        raise WorkflowError(6, "corrupt_state", "workflow state has an invalid status", path=str(path))
    if not isinstance(state["goal"], str) or not state["goal"].strip():
        raise WorkflowError(6, "corrupt_state", "workflow goal must be a non-empty string", path=str(path))
    if state["profile"] not in {"standard", "research", "adversarial-qa"} or state["keep_policy"] not in {"pass", "score-improvement"}:
        raise WorkflowError(6, "corrupt_state", "workflow profile or keep_policy is invalid", path=str(path))
    for field, minimum in (("max_rounds", 1), ("stall_window", 2), ("plateau_window", 2)):
        if isinstance(state[field], bool) or not isinstance(state[field], int) or state[field] < minimum:
            raise WorkflowError(6, "corrupt_state", f"{field} must be an integer at least {minimum}", path=str(path))
    if isinstance(state["round"], bool) or not isinstance(state["round"], int) or not 0 <= state["round"] <= state["max_rounds"]:
        raise WorkflowError(6, "corrupt_state", "round must be within the configured budget", path=str(path))
    if state["pending_round"] is not None and (isinstance(state["pending_round"], bool) or not isinstance(state["pending_round"], int) or state["pending_round"] < 1):
        raise WorkflowError(6, "corrupt_state", "pending_round must be a positive integer or null", path=str(path))
    if not isinstance(state["history"], list) or any(
        not isinstance(row, dict)
        or isinstance(row.get("round"), bool)
        or not isinstance(row.get("round"), int)
        or isinstance(row.get("verifier_exit"), bool)
        or not isinstance(row.get("verifier_exit"), int)
        or not isinstance(row.get("signature"), str)
        or not isinstance(row.get("improved"), bool)
        for row in state["history"]
    ):
        raise WorkflowError(6, "corrupt_state", "history must contain valid result records", path=str(path))
    if state["best_score"] is not None and (isinstance(state["best_score"], bool) or not isinstance(state["best_score"], (int, float)) or not 0.0 <= float(state["best_score"] ) <= 1.0):
        raise WorkflowError(6, "corrupt_state", "best_score must be between 0 and 1 or null", path=str(path))
    if isinstance(state["no_improvement"], bool) or not isinstance(state["no_improvement"], int) or state["no_improvement"] < 0:
        raise WorkflowError(6, "corrupt_state", "no_improvement must be a non-negative integer", path=str(path))
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


WORKFLOW = "ralph"
SCHEMA = "agent-workflow/ralph/1"
TERMINAL = {"passed", "stalled", "plateaued", "exhausted", "aborted"}


def enriched(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = status_payload(state)
    payload["continue"] = state.get("status") == "active"
    return payload


def start(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,backup,lock=state_paths(WORKFLOW,run_id); goal=args.goal.strip()
    if not goal: raise WorkflowError(2,"invalid_goal","goal must not be empty")
    if args.max_rounds < 1 or args.stall_window < 2 or args.plateau_window < 2: raise WorkflowError(2,"invalid_bounds","max-rounds must be >=1 and windows >=2")
    with command_lock(lock):
        if path.exists():
            old=load_state(path,WORKFLOW,run_id); raise WorkflowError(5,"already_exists","ralph run already exists",revision=old["revision"],status=old.get("status"))
        stamp=now(); state: Dict[str,Any]={"schema":SCHEMA,"workflow":WORKFLOW,"id":run_id,"revision":1,"status":"active","goal":goal,"profile":args.profile,"keep_policy":args.keep_policy,"max_rounds":args.max_rounds,"stall_window":args.stall_window,"plateau_window":args.plateau_window,"round":0,"pending_round":None,"history":[],"best_score":None,"no_improvement":0,"terminal_reason":None,"binding":new_binding(),"created_at":stamp,"updated_at":stamp}; save_state(path,backup,state)
    emit(enriched(state)); return 0


def status(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,_,_=state_paths(WORKFLOW,run_id,create=False); state=load_state(path,WORKFLOW,run_id); payload=enriched(state); emit(payload)
    if not payload["binding"]["ok"]: return 5
    return 4 if state.get("status") in TERMINAL else 0


def next_round(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,backup,lock=state_paths(WORKFLOW,run_id)
    with command_lock(lock):
        state=require_mutable(path,WORKFLOW,run_id,args.expected_revision)
        if state.get("status") in TERMINAL: raise WorkflowError(4,"terminal","ralph run is terminal",status=state.get("status"),reason=state.get("terminal_reason"))
        if state.get("pending_round") is not None: raise WorkflowError(5,"round_pending","submit the pending round before opening another",round=state["pending_round"])
        if state["round"] >= state["max_rounds"]:
            state["status"]="exhausted"; state["terminal_reason"]="round budget exhausted"; bump(state); save_state(path,backup,state); emit(enriched(state)); return 4
        state["round"] += 1; state["pending_round"] = state["round"]; bump(state); save_state(path,backup,state)
    emit(enriched(state)); return 0


def consecutive_signature(history: List[Dict[str,Any]], signature: str) -> int:
    count=0
    for row in reversed(history):
        if row.get("verifier_exit") == 0 or row.get("signature") != signature or row.get("improved"): break
        count += 1
    return count


def check(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,backup,lock=state_paths(WORKFLOW,run_id); signature=args.signature.strip()
    with command_lock(lock):
        state=require_mutable(path,WORKFLOW,run_id,args.expected_revision)
        if state.get("status") in TERMINAL: raise WorkflowError(4,"terminal","ralph run is terminal",status=state.get("status"))
        if state.get("pending_round") != args.round: raise WorkflowError(5,"round_mismatch","result must match the single pending round",pending=state.get("pending_round"),submitted=args.round)
        if args.verifier_exit != 0 and not signature: raise WorkflowError(2,"invalid_signature","a failing verifier needs a stable non-empty signature")
        if state["keep_policy"] == "score-improvement":
            if args.score is None or not 0.0 <= args.score <= 1.0: raise WorkflowError(2,"invalid_score","score-improvement runs require --score between 0 and 1")
        elif args.score is not None: raise WorkflowError(2,"unexpected_score","--score is valid only for score-improvement runs")
        improved = False
        if state["keep_policy"] == "score-improvement":
            previous=state["best_score"]
            improved = previous is None or args.score > previous
        row={"round":args.round,"verifier_exit":args.verifier_exit,"signature":signature,"score":args.score,"improved":improved,"note":args.note.strip(),"recorded_at":now()}; state["history"].append(row); state["pending_round"]=None
        if args.verifier_exit == 0:
            if improved:
                state["best_score"] = args.score
            state["status"]="passed"; state["terminal_reason"]="verifier passed"
        else:
            if state["keep_policy"] == "score-improvement":
                if improved:
                    state["best_score"]=args.score; state["no_improvement"]=0
                else: state["no_improvement"] += 1
            repeated=consecutive_signature(state["history"],signature)
            if repeated >= state["stall_window"]:
                state["status"]="stalled"; state["terminal_reason"]=f"signature repeated {repeated} rounds: {signature}"
            elif state["keep_policy"] == "score-improvement" and state["no_improvement"] >= state["plateau_window"]:
                state["status"]="plateaued"; state["terminal_reason"]=f"score did not improve for {state['no_improvement']} rounds"
            elif state["round"] >= state["max_rounds"]:
                state["status"]="exhausted"; state["terminal_reason"]="round budget exhausted"
        bump(state); save_state(path,backup,state)
    emit(enriched(state)); return 4 if state["status"] in TERMINAL and state["status"] != "passed" else 0


def abort(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,backup,lock=state_paths(WORKFLOW,run_id); reason=args.reason.strip()
    if not reason: raise WorkflowError(2,"invalid_reason","abort reason must not be empty")
    with command_lock(lock):
        state=require_mutable(path,WORKFLOW,run_id,args.expected_revision)
        if state.get("status") in TERMINAL: raise WorkflowError(4,"terminal","ralph run is already terminal",status=state.get("status"))
        state["status"]="aborted"; state["terminal_reason"]=reason; state["pending_round"]=None; bump(state); save_state(path,backup,state)
    emit(enriched(state)); return 0


def rebind(args: argparse.Namespace) -> int:
    run_id=validate_id(args.id); path,backup,lock=state_paths(WORKFLOW,run_id)
    with command_lock(lock):
        state=require_mutable(path,WORKFLOW,run_id,args.expected_revision,allow_mismatch=True)
        if state.get("status") in TERMINAL: raise WorkflowError(4,"terminal","terminal runs cannot be rebound",status=state.get("status"))
        state["binding"]=new_binding(); bump(state); save_state(path,backup,state)
    emit(enriched(state)); return 0


def parser() -> JsonArgumentParser:
    p=JsonArgumentParser(description="Deterministic bounded verifier loop"); sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("start"); s.add_argument("--id",required=True); s.add_argument("--goal",required=True); s.add_argument("--max-rounds",type=int,default=10); s.add_argument("--stall-window",type=int,default=3); s.add_argument("--plateau-window",type=int,default=3); s.add_argument("--keep-policy",choices=["pass","score-improvement"],default="pass"); s.add_argument("--profile",choices=["standard","research","adversarial-qa"],default="standard"); s.set_defaults(func=start)
    s=sub.add_parser("status"); s.add_argument("--id",required=True); s.set_defaults(func=status)
    s=sub.add_parser("next"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.set_defaults(func=next_round)
    s=sub.add_parser("check"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--round",type=int,required=True); s.add_argument("--verifier-exit",type=int,required=True); s.add_argument("--signature",default=""); s.add_argument("--score",type=float); s.add_argument("--note",default=""); s.set_defaults(func=check)
    s=sub.add_parser("abort"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.add_argument("--reason",required=True); s.set_defaults(func=abort)
    s=sub.add_parser("rebind"); s.add_argument("--id",required=True); s.add_argument("--expected-revision",type=int,required=True); s.set_defaults(func=rebind)
    return p


def main(argv: Optional[List[str]]=None) -> int:
    try: args=parser().parse_args(argv); return int(args.func(args))
    except WorkflowError as exc: emit({"ok":False,"error":exc.kind,"message":exc.message,"details":exc.details},stream=sys.stderr); return exc.code

if __name__ == "__main__": raise SystemExit(main())
