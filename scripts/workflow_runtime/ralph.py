WORKFLOW = "ralph"
SCHEMA = "agent-workflow/ralph/2"
TERMINAL_STATUSES = {"passed", "stalled", "plateaued", "exhausted", "aborted"}
KEEP_POLICIES = {"pass_only", "score_improvement"}
PROFILES = {"standard", "research", "adversarial-qa"}


def normalize_keep_policy(value: str) -> str:
    mapping = {
        "pass": "pass_only",
        "pass-only": "pass_only",
        "pass_only": "pass_only",
        "score-improvement": "score_improvement",
        "score_improvement": "score_improvement",
    }
    return mapping[value]


def validate_workflow_state(state: Dict[str, Any]) -> None:
    status = require_str(state.get("status"), "status")
    if status not in {"active", *TERMINAL_STATUSES}:
        raise WorkflowError(6, "corrupt_state", "ralph status is invalid")
    goal = require_str(state.get("goal"), "goal")
    if len(goal) > 2000:
        raise WorkflowError(6, "corrupt_state", "goal exceeds its bounded length")
    profile = require_str(state.get("profile"), "profile")
    policy = require_str(state.get("keep_policy"), "keep_policy")
    if profile not in PROFILES or policy not in KEEP_POLICIES:
        raise WorkflowError(6, "corrupt_state", "ralph profile or keep policy is invalid")
    max_rounds = require_int(state.get("max_rounds"), "max_rounds", minimum=1)
    if max_rounds > 50:
        raise WorkflowError(6, "corrupt_state", "max_rounds exceeds 50")
    round_value = require_int(state.get("round"), "round", minimum=0)
    if round_value > max_rounds:
        raise WorkflowError(6, "corrupt_state", "round exceeds max_rounds")
    pending = state.get("pending_round")
    if pending is not None and (isinstance(pending, bool) or not isinstance(pending, int) or pending != round_value):
        raise WorkflowError(6, "corrupt_state", "pending_round must match the current round")
    stall_window = require_int(state.get("stall_window"), "stall_window", minimum=2)
    plateau_window = require_int(state.get("plateau_window"), "plateau_window", minimum=2)
    if stall_window > 10 or plateau_window > 10:
        raise WorkflowError(6, "corrupt_state", "ralph windows exceed 10")
    best_score = require_number(state.get("best_score"), "best_score", nullable=True)
    if best_score is not None and not 0.0 <= best_score <= 1.0:
        raise WorkflowError(6, "corrupt_state", "best_score must be between 0 and 1")
    best_round = state.get("best_round")
    if best_round is not None:
        require_int(best_round, "best_round", minimum=1)
        if best_round > round_value:
            raise WorkflowError(6, "corrupt_state", "best_round exceeds the current round")
    require_int(state.get("no_improvement"), "no_improvement", minimum=0)
    history = require_list(state.get("history"), "history")
    if len(history) > max_rounds or len(history) > 50:
        raise WorkflowError(6, "corrupt_state", "ralph history exceeds its round budget")
    seen: List[int] = []
    for index, value in enumerate(history):
        row = require_dict(value, "history[%d]" % index)
        row_round = require_int(row.get("round"), "history[%d].round" % index, minimum=1)
        seen.append(row_round)
        exit_code = require_int(row.get("verifier_exit"), "history[%d].verifier_exit" % index, minimum=0)
        if exit_code > 255:
            raise WorkflowError(6, "corrupt_state", "verifier exit code exceeds 255")
        signature = require_str(row.get("signature"), "history[%d].signature" % index, allow_empty=True)
        note = require_str(row.get("note"), "history[%d].note" % index, allow_empty=True)
        if len(signature) > 500 or len(note) > 2000:
            raise WorkflowError(6, "corrupt_state", "ralph history text exceeds its limit")
        score = require_number(row.get("score"), "history[%d].score" % index, nullable=True)
        if score is not None and not 0.0 <= score <= 1.0:
            raise WorkflowError(6, "corrupt_state", "ralph score must be between 0 and 1")
        if not isinstance(row.get("improved"), bool):
            raise WorkflowError(6, "corrupt_state", "history improved flag must be boolean")
        require_timestamp(row.get("recorded_at"), "history[%d].recorded_at" % index)
    if seen != list(range(1, len(seen) + 1)):
        raise WorkflowError(6, "corrupt_state", "ralph history rounds must be consecutive")
    if round_value != len(history) + (1 if pending is not None else 0):
        raise WorkflowError(6, "corrupt_state", "round, history, and pending_round are inconsistent")
    if pending is not None and status != "active":
        raise WorkflowError(6, "corrupt_state", "only an active ralph run can have a pending round")
    passing_rows = [row for row in history if row["verifier_exit"] == 0]
    if len(passing_rows) > 1 or (passing_rows and history[-1]["verifier_exit"] != 0):
        raise WorkflowError(6, "corrupt_state", "verifier pass ordering is inconsistent")
    if policy == "pass_only":
        if best_score is not None or best_round is not None or state["no_improvement"] != 0:
            raise WorkflowError(6, "corrupt_state", "pass-only state cannot contain score-improvement metrics")
        if any(row["score"] is not None or row["improved"] for row in history):
            raise WorkflowError(6, "corrupt_state", "pass-only history cannot contain scores")
    else:
        if any(row["score"] is None for row in history):
            raise WorkflowError(6, "corrupt_state", "score-improvement history requires a score per round")
        if history:
            expected_best = max(float(row["score"]) for row in history)
            expected_round = next(row["round"] for row in history if float(row["score"]) == expected_best)
            if best_score != expected_best or best_round != expected_round:
                raise WorkflowError(6, "corrupt_state", "best score metadata does not match history")
        elif best_score is not None or best_round is not None:
            raise WorkflowError(6, "corrupt_state", "empty score history cannot have a best score")
    if status in TERMINAL_STATUSES and pending is not None:
        raise WorkflowError(6, "corrupt_state", "terminal ralph run cannot have a pending round")
    if status == "passed" and (not history or history[-1]["verifier_exit"] != 0):
        raise WorkflowError(6, "corrupt_state", "passed ralph run requires a successful final verifier")
    if status == "exhausted" and round_value != max_rounds:
        raise WorkflowError(6, "corrupt_state", "exhausted ralph run must consume its round budget")
    if status == "stalled" and (not history or consecutive_signature(history, history[-1]["signature"]) < stall_window):
        raise WorkflowError(6, "corrupt_state", "stalled ralph run lacks the required repeated signature")
    if status == "plateaued" and state["no_improvement"] < plateau_window:
        raise WorkflowError(6, "corrupt_state", "plateaued ralph run lacks the required non-improvement window")
    terminal_reason = state.get("terminal_reason")
    if terminal_reason is not None and (not isinstance(terminal_reason, str) or not terminal_reason or len(terminal_reason) > 1000):
        raise WorkflowError(6, "corrupt_state", "terminal_reason must be null or bounded text")
    if status == "active" and terminal_reason is not None:
        raise WorkflowError(6, "corrupt_state", "active ralph run cannot have a terminal reason")
    if status in TERMINAL_STATUSES and terminal_reason is None:
        raise WorkflowError(6, "corrupt_state", "terminal ralph run requires a reason")


def state_status(state: Dict[str, Any]) -> str:
    return state["status"]


def state_stage(state: Dict[str, Any]) -> str:
    return "round_pending" if state["pending_round"] is not None else state["status"]


def is_terminal(state: Dict[str, Any]) -> bool:
    return state["status"] in TERMINAL_STATUSES


def next_action(state: Dict[str, Any]) -> str:
    if state["status"] == "active" and state["pending_round"] is None:
        return "open the next round"
    if state["status"] == "active":
        return "make one bounded attempt, run the verifier, then submit check"
    return "stop and report the terminal judgment"


def compact_metrics(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "round": state["round"],
        "max_rounds": state["max_rounds"],
        "pending_round": state["pending_round"],
        "keep_policy": state["keep_policy"],
        "best_score": state["best_score"],
        "best_round": state["best_round"],
        "last_signature": state["history"][-1]["signature"] if state["history"] else "",
        "terminal_reason": state["terminal_reason"],
    }


def history_rows(state: Dict[str, Any], *, full: bool) -> List[Dict[str, Any]]:
    if full:
        return list(state["history"])
    return [
        {
            "round": row["round"],
            "verifier_exit": row["verifier_exit"],
            "signature": row["signature"][:160],
            "score": row["score"],
            "improved": row["improved"],
            "recorded_at": row["recorded_at"],
        }
        for row in state["history"]
    ]


def command_start(args: argparse.Namespace) -> int:
    if not 1 <= args.max_rounds <= 50:
        raise WorkflowError(2, "invalid_bounds", "--max-rounds must be between 1 and 50")
    if not 2 <= args.stall_window <= 10 or not 2 <= args.plateau_window <= 10:
        raise WorkflowError(2, "invalid_bounds", "stall and plateau windows must be between 2 and 10")
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = validate_id(args.id) if args.id else "default"
    goal = bounded_text(args.goal, "goal", 2000)
    keep_policy = normalize_keep_policy(args.keep_policy)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=True)
    with command_lock(lock):
        if path.exists():
            existing = load_state(path, backup, WORKFLOW, SCHEMA, run_id, session)
            raise WorkflowError(
                5,
                "already_exists",
                "ralph run already exists",
                revision=existing["revision"],
                status=existing["status"],
            )
        stamp = now()
        state: Dict[str, Any] = {
            "schema": SCHEMA,
            "workflow": WORKFLOW,
            "id": run_id,
            "session": session,
            "revision": 1,
            "status": "active",
            "goal": goal,
            "profile": args.profile,
            "keep_policy": keep_policy,
            "max_rounds": args.max_rounds,
            "stall_window": args.stall_window,
            "plateau_window": args.plateau_window,
            "round": 0,
            "pending_round": None,
            "history": [],
            "best_score": None,
            "best_round": None,
            "no_improvement": 0,
            "terminal_reason": None,
            "binding": new_binding(context),
            "recoveries": [],
            "created_at": stamp,
            "updated_at": stamp,
        }
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def command_next(args: argparse.Namespace) -> int:
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "ralph run is terminal", status=state["status"], reason=state["terminal_reason"])
        if state["pending_round"] is not None:
            raise WorkflowError(5, "round_pending", "submit the pending round before opening another", round=state["pending_round"])
        if state["round"] >= state["max_rounds"]:
            state["status"] = "exhausted"
            state["terminal_reason"] = "round budget exhausted"
        else:
            state["round"] += 1
            state["pending_round"] = state["round"]
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def consecutive_signature(history: List[Dict[str, Any]], signature: str) -> int:
    count = 0
    for row in reversed(history):
        if row["verifier_exit"] == 0 or row["signature"] != signature:
            break
        count += 1
    return count


def command_check(args: argparse.Namespace) -> int:
    if args.verifier_exit < 0 or args.verifier_exit > 255:
        raise WorkflowError(2, "invalid_exit_code", "verifier exit must be between 0 and 255")
    signature = bounded_text(args.signature, "signature", 500, allow_empty=True)
    note = bounded_text(args.note, "note", 2000, allow_empty=True)
    context = workspace_context(args.root)
    session = normalize_session(args.session)
    run_id = resolve_run_id(args, context, session)
    path, backup, lock = state_paths(context, WORKFLOW, session, run_id, create=False)
    with command_lock(lock):
        state = require_mutable(path, backup, run_id, session, args.expected_revision, context)
        if is_terminal(state):
            raise WorkflowError(4, "terminal", "ralph run is terminal", status=state["status"])
        if state["pending_round"] != args.round:
            raise WorkflowError(
                5,
                "round_mismatch",
                "result must match the single pending round",
                pending=state["pending_round"],
                submitted=args.round,
            )
        if args.verifier_exit != 0 and not signature:
            raise WorkflowError(2, "invalid_signature", "a failing verifier needs a stable non-empty signature")
        if state["keep_policy"] == "score_improvement":
            if args.score is None or not math.isfinite(args.score) or not 0.0 <= args.score <= 1.0:
                raise WorkflowError(2, "invalid_score", "score-improvement runs require --score between 0 and 1")
        elif args.score is not None:
            raise WorkflowError(2, "unexpected_score", "--score is valid only for score-improvement runs")

        improved = False
        if state["keep_policy"] == "score_improvement":
            improved = state["best_score"] is None or args.score > state["best_score"]
        row = {
            "round": args.round,
            "verifier_exit": args.verifier_exit,
            "signature": signature,
            "score": args.score,
            "improved": improved,
            "note": note,
            "recorded_at": now(),
        }
        state["history"].append(row)
        state["pending_round"] = None

        if args.verifier_exit == 0:
            if improved:
                state["best_score"] = args.score
                state["best_round"] = args.round
            state["status"] = "passed"
            state["terminal_reason"] = "verifier passed"
        elif state["keep_policy"] == "pass_only":
            repeated = consecutive_signature(state["history"], signature)
            if repeated >= state["stall_window"]:
                state["status"] = "stalled"
                state["terminal_reason"] = "signature repeated %d rounds: %s" % (repeated, signature)
            elif state["round"] >= state["max_rounds"]:
                state["status"] = "exhausted"
                state["terminal_reason"] = "round budget exhausted"
        else:
            if improved:
                state["best_score"] = args.score
                state["best_round"] = args.round
                state["no_improvement"] = 0
            else:
                state["no_improvement"] += 1
            if state["no_improvement"] >= state["plateau_window"]:
                state["status"] = "plateaued"
                state["terminal_reason"] = "score did not improve for %d rounds" % state["no_improvement"]
            elif state["round"] >= state["max_rounds"]:
                state["status"] = "exhausted"
                state["terminal_reason"] = "round budget exhausted"

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
            raise WorkflowError(4, "terminal", "ralph run is already terminal", status=state["status"])
        state["status"] = "aborted"
        state["terminal_reason"] = reason
        state["pending_round"] = None
        bump(state)
        save_state(path, backup, state)
    emit_state(state, context, full=args.full, changed=True)
    return 0


def parser() -> JsonArgumentParser:
    root = JsonArgumentParser(description="Deterministic bounded verifier loop")
    sub = root.add_subparsers(dest="command", required=True)

    command = sub.add_parser("start")
    command.add_argument("--id")
    common_args(command, selector=False)
    command.add_argument("--goal", required=True)
    command.add_argument("--max-rounds", type=int, default=10)
    command.add_argument("--stall-window", type=int, default=3)
    command.add_argument("--plateau-window", type=int, default=3)
    command.add_argument(
        "--keep-policy",
        choices=["pass", "pass-only", "pass_only", "score-improvement", "score_improvement"],
        default="pass-only",
    )
    command.add_argument("--profile", choices=sorted(PROFILES), default="standard")
    command.set_defaults(func=command_start)

    command = sub.add_parser("next")
    mutation_args(command)
    command.set_defaults(func=command_next)

    command = sub.add_parser("check")
    mutation_args(command)
    command.add_argument("--round", type=int, required=True)
    command.add_argument("--verifier-exit", type=int, required=True)
    command.add_argument("--signature", default="")
    command.add_argument("--score", type=float)
    command.add_argument("--note", default="")
    command.set_defaults(func=command_check)

    command = sub.add_parser("abort")
    mutation_args(command)
    command.add_argument("--reason", required=True)
    command.set_defaults(func=command_abort)

    add_common_commands(sub)
    return root


if __name__ == "__main__":
    raise SystemExit(run_main(parser))
