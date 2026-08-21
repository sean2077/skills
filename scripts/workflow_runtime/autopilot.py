WORKFLOW = "autopilot"
SCHEMA = "agent-workflow/autopilot/2"
TERMINAL_STATUSES = {"done", "blocked", "aborted"}
PHASES = {"clarify", "plan", "implement", "verify", "deliver", "done", "blocked", "aborted"}


def validate_workflow_state(state: Dict[str, Any]) -> None:
    status = require_str(state.get("status"), "status")
    phase = require_str(state.get("phase"), "phase")
    if status not in {"active", *TERMINAL_STATUSES} or phase not in PHASES:
        raise WorkflowError(6, "corrupt_state", "autopilot status or phase is invalid")
    if status == "active" and phase in {"done", "blocked", "aborted"}:
        raise WorkflowError(6, "corrupt_state", "active autopilot has a terminal phase")
    if status in TERMINAL_STATUSES and phase != status:
        raise WorkflowError(6, "corrupt_state", "terminal autopilot phase must match status")
    goal = require_str(state.get("goal"), "goal")
    if len(goal) > 2000:
        raise WorkflowError(6, "corrupt_state", "goal exceeds its bounded length")
    plan_path = state.get("plan_path")
    if plan_path is not None and (not isinstance(plan_path, str) or not plan_path or len(plan_path) > 512):
        raise WorkflowError(6, "corrupt_state", "plan_path must be null or bounded text")
    if phase in {"implement", "verify", "deliver", "done", "blocked"} and plan_path is None:
        raise WorkflowError(6, "corrupt_state", "this autopilot phase requires a recorded plan")
    failures = require_int(state.get("verify_failures"), "verify_failures", minimum=0)
    if failures > 2:
        raise WorkflowError(6, "corrupt_state", "verify_failures exceeds the bounded retry policy")
    rows = require_list(state.get("verification"), "verification")
    if len(rows) > 2:
        raise WorkflowError(6, "corrupt_state", "verification history exceeds two attempts")
    for index, row_value in enumerate(rows):
        row = require_dict(row_value, "verification[%d]" % index)
        require_int(row.get("exit_code"), "verification[%d].exit_code" % index, minimum=0)
        summary = require_str(row.get("summary"), "verification[%d].summary" % index)
        if len(summary) > 2000:
            raise WorkflowError(6, "corrupt_state", "verification summary exceeds its limit")
        require_timestamp(row.get("recorded_at"), "verification[%d].recorded_at" % index)
    observed_failures = sum(1 for row in rows if row["exit_code"] != 0)
    successes = [index for index, row in enumerate(rows) if row["exit_code"] == 0]
    if failures != observed_failures or len(successes) > 1 or (successes and successes[0] != len(rows) - 1):
        raise WorkflowError(6, "corrupt_state", "verification counters or success ordering are inconsistent")
    if phase in {"deliver", "done"} and (not rows or rows[-1]["exit_code"] != 0):
        raise WorkflowError(6, "corrupt_state", "deliver and done require a successful final verification")
    if phase == "blocked" and (failures != 2 or len(rows) != 2 or any(row["exit_code"] == 0 for row in rows)):
        raise WorkflowError(6, "corrupt_state", "blocked requires exactly two failed verification attempts")
    terminal_reason = state.get("terminal_reason")
    if terminal_reason is not None and (not isinstance(terminal_reason, str) or not terminal_reason or len(terminal_reason) > 1000):
        raise WorkflowError(6, "corrupt_state", "terminal_reason must be null or bounded text")
    if status == "active" and terminal_reason is not None:
        raise WorkflowError(6, "corrupt_state", "active autopilot cannot have a terminal reason")
    if status in TERMINAL_STATUSES and terminal_reason is None:
        raise WorkflowError(6, "corrupt_state", "terminal autopilot requires a reason")


def state_status(state: Dict[str, Any]) -> str:
    return state["status"]


def state_stage(state: Dict[str, Any]) -> str:
    return state["phase"]


def is_terminal(state: Dict[str, Any]) -> bool:
    return state["status"] in TERMINAL_STATUSES


def next_action(state: Dict[str, Any]) -> str:
    phase = state["phase"]
    return {
        "clarify": "confirm scope and acceptance evidence, then advance to plan",
        "plan": "write the plan file and record it",
        "implement": "implement the next bounded slice, then advance to verify",
        "verify": "run the real verifier and record its observed result",
        "deliver": "report evidence and limitations, then finish",
        "done": "stop; delivery is complete",
        "blocked": "stop; report the repeated verification failure",
        "aborted": "stop; the run was aborted",
    }[phase]


def compact_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "phase": state["phase"],
        "plan_path": state["plan_path"],
        "verify_attempts": len(state["verification"]),
        "verify_failures": state["verify_failures"],
        "terminal_reason": state["terminal_reason"],
    }


def history_rows(state: Dict[str, Any], *, full: bool) -> List[Dict[str, Any]]:
    if full:
        return list(state["verification"])
    return [
        {
            "attempt": index + 1,
            "exit_code": row["exit_code"],
            "summary": row["summary"][:240],
            "recorded_at": row["recorded_at"],
        }
        for index, row in enumerate(state["verification"])
    ]


def command_start(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = validate_id(args.id) if args.id else "default"
    goal = bounded_text(args.goal, "goal", 2000)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=True)
    with command_lock(lock):
        if path.exists():
            existing = load_state(path, backup, WORKFLOW, SCHEMA, run_id, session)
            raise WorkflowError(
                5,
                "already_exists",
                "autopilot run already exists",
                revision=existing["revision"],
                stage=existing["phase"],
            )
        stamp = now()
        state: Dict[str, Any] = {
            "schema": SCHEMA,
            "workflow": WORKFLOW,
            "id": run_id,
            "session": session,
            "revision": 1,
            "status": "active",
            "phase": "clarify",
            "goal": goal,
            "plan_path": None,
            "verify_failures": 0,
            "verification": [],
            "terminal_reason": None,
            "binding": new_binding(context),
            "recoveries": [],
            "created_at": stamp,
            "updated_at": stamp,
        }
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_advance(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    allowed = {"clarify": "plan", "implement": "verify"}
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "autopilot run is terminal", status=state["status"])
        expected = allowed.get(state["phase"])
        if expected != args.to:
            raise WorkflowError(
                5,
                "invalid_transition",
                "requested phase transition is not allowed",
                current=state["phase"],
                requested=args.to,
                expected=expected,
            )
        state["phase"] = args.to
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_plan(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "autopilot run is terminal", status=state["status"])
        if state["phase"] != "plan" or state["status"] != "active":
            raise WorkflowError(5, "invalid_transition", "plan can be recorded only in the plan phase", stage=state["phase"])
        relative, _, _ = resolve_artifact_path(state, args.path, label="plan path")
        state["plan_path"] = relative
        state["phase"] = "implement"
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_verify(args: argparse.Namespace) -> int:
    if args.exit_code < 0 or args.exit_code > 255:
        raise WorkflowError(2, "invalid_exit_code", "exit code must be between 0 and 255")
    summary = bounded_text(args.summary, "summary", 2000)
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "autopilot run is terminal", status=state["status"])
        if state["phase"] != "verify" or state["status"] != "active":
            raise WorkflowError(5, "invalid_transition", "verification can be recorded only in verify", stage=state["phase"])
        state["verification"].append(
            {"exit_code": args.exit_code, "summary": summary, "recorded_at": now()}
        )
        if args.exit_code == 0:
            state["phase"] = "deliver"
        else:
            state["verify_failures"] += 1
            if state["verify_failures"] >= 2:
                state["status"] = "blocked"
                state["phase"] = "blocked"
                state["terminal_reason"] = "verification failed twice"
            else:
                state["phase"] = "implement"
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_finish(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "autopilot run is terminal", status=state["status"])
        if state["phase"] != "deliver" or state["status"] != "active":
            raise WorkflowError(5, "invalid_transition", "finish is valid only from deliver", stage=state["phase"])
        state["status"] = "done"
        state["phase"] = "done"
        state["terminal_reason"] = "verified delivery completed"
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_abort(args: argparse.Namespace) -> int:
    reason = bounded_text(args.reason, "reason", 1000)
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "autopilot run is already terminal", status=state["status"])
        state["status"] = "aborted"
        state["phase"] = "aborted"
        state["terminal_reason"] = reason
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def parser() -> JsonArgumentParser:
    root = JsonArgumentParser(description="Deterministic interruption-safe autopilot state")
    sub = root.add_subparsers(dest="command", required=True)

    command = sub.add_parser("start")
    command.add_argument("--id")
    common_args(command, selector=False)
    command.add_argument("--goal", required=True)
    command.set_defaults(func=command_start)

    command = sub.add_parser("advance")
    mutation_args(command)
    command.add_argument("--to", choices=["plan", "verify"], required=True)
    command.set_defaults(func=command_advance)

    command = sub.add_parser("plan")
    mutation_args(command)
    command.add_argument("--path", required=True)
    command.set_defaults(func=command_plan)

    command = sub.add_parser("verify")
    mutation_args(command)
    command.add_argument("--exit-code", type=int, required=True)
    command.add_argument("--summary", required=True)
    command.set_defaults(func=command_verify)

    command = sub.add_parser("finish")
    mutation_args(command)
    command.set_defaults(func=command_finish)

    command = sub.add_parser("abort")
    mutation_args(command)
    command.add_argument("--reason", required=True)
    command.set_defaults(func=command_abort)

    add_common_commands(sub)
    return root


if __name__ == "__main__":
    raise SystemExit(run_main(parser))
