WORKFLOW = "deep-interview"
SCHEMA = "agent-workflow/deep-interview/3"
TERMINAL_STATUSES = {"completed", "aborted"}
STATUS_BY_PHASE = {
    "drafting": "active",
    "crystallized": "awaiting_approval",
    "approved": "approved",
    "completed": "completed",
    "aborted": "aborted",
}


def validate_workflow_state(state: Dict[str, Any]) -> None:
    phase = require_str(state.get("phase"), "phase")
    if phase not in STATUS_BY_PHASE or state.get("status") != STATUS_BY_PHASE[phase]:
        raise WorkflowError(6, "corrupt_state", "interview phase/status is invalid")
    idea = require_str(state.get("initial_idea"), "initial_idea")
    if not idea.strip() or len(idea) > 2000:
        raise WorkflowError(6, "corrupt_state", "interview idea is invalid")
    path, digest = state.get("spec_path"), state.get("spec_sha256")
    if path is not None:
        require_str(path, "spec_path")
        if len(path) > 512 or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise WorkflowError(6, "corrupt_state", "spec path/digest is invalid")
    elif digest is not None or phase in {"crystallized", "approved", "completed"}:
        raise WorkflowError(6, "corrupt_state", "spec path/digest is missing")
    approval = state.get("approval")
    if approval is not None:
        approval = require_dict(approval, "approval")
        evidence = require_str(approval.get("evidence"), "approval.evidence")
        if not evidence.strip() or len(evidence) > 1000:
            raise WorkflowError(6, "corrupt_state", "approval evidence is invalid")
        require_timestamp(approval.get("approved_at"), "approval.approved_at")
        if digest is None or approval.get("spec_sha256") != digest:
            raise WorkflowError(6, "corrupt_state", "approval does not bind the crystallized digest")
    if phase in {"approved", "completed"} and approval is None:
        raise WorkflowError(6, "corrupt_state", "approved state lacks approval evidence")
    if phase in {"drafting", "crystallized"} and approval is not None:
        raise WorkflowError(6, "corrupt_state", "unapproved state contains approval evidence")
    if phase == "drafting" and path is not None:
        raise WorkflowError(6, "corrupt_state", "drafting state contains a crystallized spec")
    reason = state.get("terminal_reason")
    if phase in TERMINAL_STATUSES:
        require_str(reason, "terminal_reason")
    elif reason is not None:
        raise WorkflowError(6, "corrupt_state", "active interview has a terminal reason")
    previous = 1
    for raw in require_list(state.get("history"), "history"):
        row = require_dict(raw, "history entry")
        revision = require_int(row.get("revision"), "history.revision", minimum=2)
        if not previous < revision <= state["revision"] or row.get("phase") not in STATUS_BY_PHASE:
            raise WorkflowError(6, "corrupt_state", "history revision/phase is invalid")
        require_timestamp(row.get("at"), "history.at")
        previous = revision


def state_status(state: Dict[str, Any]) -> str:
    return state["status"]


def state_stage(state: Dict[str, Any]) -> str:
    return state["phase"]


def is_terminal(state: Dict[str, Any]) -> bool:
    return state["status"] in TERMINAL_STATUSES


def next_action(state: Dict[str, Any]) -> str:
    return {
        "drafting": "resolve requirements and crystallize the specification when ready",
        "crystallized": "present the exact specification and record explicit approval",
        "approved": "complete with the unchanged approved specification",
        "completed": "stop; the approved specification is complete",
        "aborted": "stop; the interview was aborted",
    }[state["phase"]]


def compact_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"spec_path": state["spec_path"], "spec_sha256": state["spec_sha256"],
            "approved": state["approval"] is not None}


def history_rows(state: Dict[str, Any], *, full: bool) -> List[Dict[str, Any]]:
    return list(state["history"])


def record_change(state: Dict[str, Any]) -> None:
    bump(state)
    state["history"].append({"revision": state["revision"], "phase": state["phase"],
                             "spec_sha256": state["spec_sha256"], "at": now()})


def command_start(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = validate_id(args.id) if args.id else "default"
    idea = bounded_text(args.idea, "idea", 2000)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=True)
    with command_lock(lock):
        if path.exists():
            # Existing runs, including v2 scoring runs, are never overwritten.
            raise WorkflowError(5, "already_exists", "interview run already exists; select another id")
        stamp = now()
        state: Dict[str, Any] = {
            "schema": SCHEMA, "workflow": WORKFLOW, "id": run_id, "session": session,
            "revision": 1, "status": "active", "phase": "drafting", "initial_idea": idea,
            "spec_path": None, "spec_sha256": None, "approval": None, "history": [],
            "terminal_reason": None, "binding": new_binding(context), "recoveries": [],
            "created_at": stamp, "updated_at": stamp,
        }
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_crystallize(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "interview is terminal", status=state["status"])
        if state["phase"] not in {"drafting", "crystallized", "approved"}:
            raise WorkflowError(5, "invalid_transition", "crystallize requires an active interview", stage=state["phase"])
        relative, _, content = resolve_artifact_path(state, args.spec_path, label="spec path", max_bytes=1024 * 1024)
        assert content is not None
        if not content.strip():
            raise WorkflowError(2, "invalid_spec", "specification must contain text")
        state["spec_path"] = relative
        state["spec_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        state["approval"] = None
        state["phase"] = "crystallized"
        state["status"] = STATUS_BY_PHASE[state["phase"]]
        record_change(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def current_spec_content(state: Dict[str, Any]) -> str:
    if not state["spec_path"] or not state["spec_sha256"]:
        raise WorkflowError(6, "corrupt_state", "crystallized interview lacks a spec path or digest")
    _, _, content = resolve_artifact_path(state, state["spec_path"], label="spec path", max_bytes=1024 * 1024)
    assert content is not None
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if digest != state["spec_sha256"]:
        raise WorkflowError(5, "spec_changed", "spec changed after crystallization; validate and crystallize it again")
    return content


def command_approve(args: argparse.Namespace) -> int:
    evidence = bounded_text(args.evidence, "approval evidence", 1000)
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "interview is terminal", status=state["status"])
        if state["phase"] != "crystallized":
            raise WorkflowError(5, "invalid_transition", "approval can be recorded only after crystallization", stage=state["phase"])
        current_spec_content(state)
        state["approval"] = {"evidence": evidence, "approved_at": now(), "spec_sha256": state["spec_sha256"]}
        state["phase"] = "approved"
        state["status"] = STATUS_BY_PHASE[state["phase"]]
        record_change(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_complete(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "interview is terminal", status=state["status"])
        if state["phase"] != "approved" or state["approval"] is None:
            raise WorkflowError(5, "approval_required", "complete requires a separately recorded user approval", stage=state["phase"])
        current_spec_content(state)
        state["phase"] = "completed"
        state["status"] = STATUS_BY_PHASE[state["phase"]]
        state["terminal_reason"] = "approved specification completed"
        record_change(state)
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
            raise WorkflowError(4, "terminal", "interview is already terminal", status=state["status"])
        state["phase"] = "aborted"
        state["status"] = STATUS_BY_PHASE[state["phase"]]
        state["terminal_reason"] = reason
        record_change(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def parser() -> JsonArgumentParser:
    root = JsonArgumentParser(description="Versioned specification approval and recovery")
    sub = root.add_subparsers(dest="command", required=True)
    command = sub.add_parser("start")
    command.add_argument("--id")
    common_args(command, selector=False)
    command.add_argument("--idea", required=True)
    command.set_defaults(func=command_start)

    command = sub.add_parser("crystallize")
    mutation_args(command)
    command.add_argument("--spec-path", required=True)
    command.set_defaults(func=command_crystallize)

    command = sub.add_parser("approve")
    mutation_args(command)
    command.add_argument("--evidence", required=True)
    command.set_defaults(func=command_approve)

    command = sub.add_parser("complete")
    mutation_args(command)
    command.set_defaults(func=command_complete)

    command = sub.add_parser("abort")
    mutation_args(command)
    command.add_argument("--reason", required=True)
    command.set_defaults(func=command_abort)

    add_common_commands(sub)
    return root


if __name__ == "__main__":
    raise SystemExit(run_main(parser))
