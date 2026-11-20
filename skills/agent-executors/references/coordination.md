# Planner–executor coordination

## Files

Keep one handoff directory per campaign. A practical layout:

```text
<handoff>/
  T<N>-TASK.md        # goal, confirmed facts, acceptance, boundaries
  T<N>-RESULT.md      # executor's evidence and result
  T<N>-DECISION-*.md  # planner decisions and corrections
  T<N>-REVIEW-*.md    # planner review findings
```

Write the task file before spawning; the executor reads it instead of relying on a long terminal message. State what is already confirmed, what is excluded, and what would make the executor stop and report. Use absolute paths in messages.

## Messaging

- Use the host's built-in cross-session messaging by session name. Messages arrive between tool calls; they do not interrupt a running tool.
- Send one line per stage: what changed, the result file path, and any blocker. Do not resend only because no reply arrived.
- The executor must know the planner's session name. If the name is not available, have it list peers or report through the task file and the user.
- Fall back to the `agent-messaging` skill only when built-in delivery cannot reach the session. It documents the Claude Code inbox sender and the Codex routes.

## Review loop

1. The executor reports a stage and writes evidence to the result file.
2. The planner reads the actual diff, CI status, uploaded revision, and evidence; it does not rely on the summary.
3. Findings go into a decision file with the exact required change and the reason; send a short pointer.
4. The executor reworks and reports again. Only the planner decides pass or rework.
5. On pass, the planner records the accepted revision and any remaining known limitations.

## Boundaries

- One planner per executor; one executor per branch or uploaded revision. Two writers on the same artifact produce duplicated or conflicting work.
- Do not let the executor merge, publish, or mutate devices beyond its task file; those are separate authorizations.
- If the executor stalls or the tab is closed, report the state to the user. Do not silently spawn a replacement over the same work.
- Keep the user's tab input authoritative. If the user changes direction in the tab, update the task or decision file and tell the executor, rather than running two conflicting instructions.