---
name: agent-executors
description: "Use when this session plans and reviews while execution belongs in a separate, user-visible claude-ds session; spawn and coordinate interactive WezTerm executor tabs, hand off task files, and use built-in cross-session messaging. Not for invisible subagents, background jobs, or screen/tmux sessions."
---

# Agent executors

Use when this session owns planning and review, and the work should run in a separate Claude Code session on the cheaper executor profile (`claude-ds` by default). The executor must be a normal interactive session in a WezTerm tab so the user can watch it and type into it. Do not substitute a subagent, a hidden background process, or a `screen`/`tmux` session.

## Roles

- **Planner/reviewer** (this session): clarify scope, write task files, make decisions, verify independently. Do not implement, upload, or mutate devices.
- **Executor**: a normal Claude Code session started with the executor profile. It reads the task file, implements, tests, uploads, and reports.

## Permission default

Default new executors to **YOLO** (`--dangerously-skip-permissions`, Claude Code's `bypassPermissions` mode) so routine tool approvals do not interrupt this efficiency-first workflow. Do not ask for a separate YOLO confirmation on every launch.

Honor an explicit user or environment requirement for a narrower mode: omit the bypass flag and pass the required `--permission-mode` explicitly (for example, `default`). Apply the choice to the executor process, without editing shared profile settings. YOLO does not expand the task's authorization or override enforced host policies.

## Start an executor

1. Confirm the checkout and task identifier. Write the task file first: goal, confirmed facts, acceptance criteria, boundaries, and the planner session name.
2. Resolve **this session's WezTerm pane**; the executor tab must live in the same window as the planner. Never use `--new-window`. [WezTerm tabs](references/wezterm-tabs.md) covers resolving the pane when the host strips `WEZTERM_*`, multiple GUI instances, and placement verification.
3. Spawn a tab with the executor profile and the default YOLO mode. For Codex launches, use the `env` prefix below unless the user requests monochrome output. In other cases, start with `claude` after `--`.

   ```bash
   wezterm cli spawn --pane-id "$planner_pane" --cwd "$checkout" -- \
     env -u NO_COLOR claude --settings "$HOME/.claude/deepseek.json" --dangerously-skip-permissions \
       --effort max -n "exec-<task>"
   ```

   `--pane-id` derives the window from this session, so the new tab lands beside it. The command returns the new pane id.
4. Verify placement: compare `window_id` in `wezterm cli list --format json`. If it differs, close the tab and retry; do not hand a task to a misplaced executor.
5. Set a readable tab title and keep the mapping (pane id, session name, task file, permission mode):

   ```bash
   wezterm cli set-tab-title --pane-id <pane> "T<N> <short topic>"
   ```

6. Confirm with `get-text` that the TUI is ready and the intended permission mode is active before sending the task. Resolve [startup dialogs](references/wezterm-tabs.md#deliver-the-first-task) first. Then point the executor at the task file and planner name. Send text and Enter separately, and verify with `get-text`:

   ```bash
   wezterm cli send-text --pane-id <pane> "You are the executor. Read <task file> fully first. Reply to <planner name> with one line at the end of each stage; write results to <result file>. Stay within the task boundaries."
   wezterm cli send-text --no-paste --pane-id <pane> $'\r'
   ```

7. Report the tab mapping to the user. [Coordination](references/coordination.md) covers task/decision/result files, messaging, and review.

## Coordinate

- Prefer built-in cross-session messaging (`SendMessage`) by session name. The executor receives messages between tool calls, not as an interrupt. Fall back to the `agent-messaging` skill only when the session is not registered or the host cannot reach it.
- Put decisions in a file and send one short pointer; do not paste whole documents into the terminal.
- Review independently: read the diff, CI, upload read-back, and the executor's evidence. A result summary is not evidence.
- Keep one planner per executor and one executor per branch or uploaded revision. Do not silently respawn after a stall; report it and decide with the user.

## Boundaries

- Closing the tab ends that executor process. Do not press `Ctrl-C` in an executor tab unless you intend to interrupt its current action.
- The user may type in the tab. Treat their input as authoritative, reconcile it with the task file, and keep the planner as the coordinator.
- Do not use `screen` or `tmux` for executors: they hide the tab from the user and do not register for built-in messaging.
- Executor profile selection (`claude-ds`, model, effort) belongs to the host; this skill establishes visibility, coordination, and the per-executor permission default.
