---
name: agent-executors
description: "Use when this session plans and reviews while execution belongs in a separate, user-visible claude-ds session; spawn and coordinate interactive WezTerm executor tabs, hand off task files, and use built-in cross-session messaging. Not for invisible subagents, background jobs, or screen/tmux sessions."
---

# Agent executors

Use when this session owns planning and review, and the work should run in a separate Claude Code session on the cheaper executor profile (`claude-ds` by default). The executor must be a normal interactive session in a WezTerm tab so the user can watch it and type into it. Do not substitute a subagent, a hidden background process, or a `screen`/`tmux` session.

## Roles

- **Planner/reviewer** (this session): clarify scope, prepare task briefs, make decisions, verify independently. Do not implement, upload, or mutate devices.
- **Executor**: a normal Claude Code session started with the executor profile. It reads the task brief, implements, tests, uploads, and reports.

## Permission default

Default new executors to **YOLO** (`--dangerously-skip-permissions`, Claude Code's `bypassPermissions` mode) so routine tool approvals do not interrupt this efficiency-first workflow. Do not ask for a separate YOLO confirmation on every launch.

Honor an explicit user or environment requirement for a narrower mode: omit the bypass flag and pass the required `--permission-mode` explicitly (for example, `default`). Apply the choice to the executor process, without editing shared profile settings. YOLO does not expand the task's authorization or override enforced host policies.

## Start an executor

1. Confirm the checkout and task identifier. Prepare the goal, confirmed facts, acceptance criteria, boundaries, and planner session name. Use an absolute task-file path for work that needs durable context; a complete short brief can be sent directly for a one-shot exchange.
2. Resolve **this session's WezTerm instance and pane**; the executor tab must live in the same window as the planner. Never use `--new-window`. [WezTerm tabs](references/wezterm-tabs.md) covers recovering the pane/socket pair when the host strips `WEZTERM_*`, preserving the instance selector on every command, and placement verification. The examples below use the recovered `planner_socket`.
3. Spawn a tab with the executor profile and the default YOLO mode. For Codex launches, use the `env` prefix below unless the user requests monochrome output. In other cases, start with `claude` after `--`.

   ```bash
   WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli spawn --pane-id "$planner_pane" --cwd "$checkout" -- \
     env -u NO_COLOR claude --settings "$HOME/.claude/deepseek.json" --dangerously-skip-permissions \
       --effort max -n "exec-<task>"
   ```

   `--pane-id` derives the window within that instance. Keep the returned pane id as `executor_pane`.
4. Verify placement: compare both panes' `window_id` in `wezterm cli list --format json`, targeting the same instance. If it differs, close the new executor pane and resolve the target before retrying; do not hand a task to a misplaced executor.
5. Set a readable tab title and keep the mapping (instance selector, pane id, session name, task brief, permission mode):

   ```bash
   WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli set-tab-title --pane-id "$executor_pane" "T<N> <short topic>"
   ```

6. Confirm with `get-text` that the TUI is ready and the intended permission mode is active before sending the task. Resolve [startup dialogs](references/wezterm-tabs.md#deliver-the-first-task) first. Send the short brief or task-file pointer with the planner name; request a result file only when the evidence needs to persist. Send text and Enter separately, and verify with `get-text`:

   ```bash
   WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli send-text --pane-id "$executor_pane" "You are the executor. Task: <complete brief or absolute task-file path>. Read any referenced task file fully before acting. Report material progress and final evidence to <planner name>. Stay within the task boundaries."
   WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli send-text --no-paste --pane-id "$executor_pane" $'\r'
   ```

7. Report the tab mapping to the user. [Coordination](references/coordination.md) covers task/decision/result files, messaging, and review.

## Coordinate

- Prefer built-in cross-session messaging (`SendMessage`) by session name. The executor receives messages between tool calls, not as an interrupt. Fall back to the `agent-messaging` skill only when the session is not registered or the host cannot reach it.
- Send ordinary decisions directly. Write a file when a decision changes acceptance/scope or must survive context loss, then send a short pointer instead of pasting the whole document.
- Review independently: read the diff, CI, upload read-back, and the executor's evidence. A result summary is not evidence.
- Keep one planner per executor and one executor per branch or uploaded revision. Do not silently respawn after a stall; report it and decide with the user.

## Boundaries

- Closing the tab ends that executor process. Do not press `Ctrl-C` in an executor tab unless you intend to interrupt its current action.
- The user may type in the tab. Treat their input as authoritative, reconcile it with the task file, and keep the planner as the coordinator.
- Do not use `screen` or `tmux` for executors: they hide the tab from the user and do not register for built-in messaging.
- Executor profile selection (`claude-ds`, model, effort) belongs to the host; this skill establishes visibility, coordination, and the per-executor permission default.
