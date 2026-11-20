# Planner–executor coordination

## Choose the lightest medium

Default to a direct cross-session message. Write a file only when the content must survive a context loss, be re-read later, or be shared by more than two sessions.

- **Message directly:** one-line progress, a clarification, an approval or rejection, a parameter change, a short result such as "done, SMR 1643", or a question.
- **Write a file:** the task brief and boundaries, a decision that changes acceptance or scope, evidence that needs re-reading, a handoff, or content several executors share.

A useful check: if the other session lost its context or restarted, would this sentence still be needed? If not, say it in the message.

## Task brief

Write the task brief before spawning when the work is more than a one-shot exchange. It states the goal, confirmed facts, acceptance, boundaries, and where the executor should stop and report. Use an absolute path.

If a handoff directory helps, keep one per campaign and add files only as needed. `T<N>-TASK.md`, `T<N>-RESULT.md`, and `T<N>-DECISION-*.md` are a familiar layout, not a required one.

## Messaging

- Use the host's built-in cross-session messaging by session name. Messages arrive between tool calls; they do not interrupt a running tool.
- Send one line per stage only when there is something to report; do not turn every action into a status message.
- The executor must know the planner's session name. If the name is not available, have it list peers or report through the user.
- Fall back to the `agent-messaging` skill only when built-in delivery cannot reach the session. It documents the Claude Code inbox sender and the Codex routes.

## Review

Read the actual diff, CI status, uploaded revision, and evidence; do not rely on the summary. Send a short approval or a precise correction directly. Write a decision file only when the correction changes acceptance, scope, or needs to be referenced later.

## Boundaries

- One planner per executor; one executor per branch or uploaded revision. Two writers on the same artifact produce duplicated or conflicting work.
- Do not let the executor merge, publish, or mutate devices beyond its brief; those are separate authorizations.
- If the executor stalls or the tab is closed, report the state to the user. Do not silently spawn a replacement over the same work.
- Keep the user's tab input authoritative. If the user changes direction in the tab, tell the executor and, only if the change is durable, update the brief.