# WezTerm executor tabs

Use the WezTerm CLI from the running fork. Creating a tab and typing into it are separate operations; verify each one.

## Resolve the GUI and window

The executor tab must be created in the **same window** as the planner's tab. `spawn --pane-id` derives the window from the planner pane; do not use `--new-window`.

- If `WEZTERM_PANE` is set, use it.
- Claude Code's Bash tool may sanitize `WEZTERM_*` from the tool environment even when the parent shell has them. On Linux, walk up the process tree and read `/proc/<pid>/environ`:

  ```bash
  pane=${WEZTERM_PANE:-}
  pid=$PPID
  while [ -z "$pane" ] && [ "$pid" -gt 1 ]; do
    pane=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n 's/^WEZTERM_PANE=//p')
    pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
  done
  ```

  If the pane still cannot be resolved, stop and ask for the window; do not guess.
- More than one GUI instance may be running, for example a normal instance and a `quake.lua` dropdown. The CLI default may target a different instance than the one the user sees. Confirm with `wezterm cli list-clients` and `wezterm cli list`.
- A quake-style instance can hide a newly created window; the same-window rule avoids this failure entirely.

## Verify placement

After spawning, compare `window_id` for the planner pane and the new pane:

```bash
wezterm cli list --format json
```

If the ids differ, close the new tab and retry with `--pane-id <planner pane>`. Do not send the task until the placement is confirmed.

## Commands

| Need | Command |
|---|---|
| List windows, tabs and panes | `wezterm cli list --format json` |
| New tab | `wezterm cli spawn --pane-id <planner-pane> --cwd <dir> -- <program>` |
| Split | `wezterm cli split-pane ...` |
| Title | `wezterm cli set-tab-title --pane-id <pane> "<title>"` |
| Read screen | `wezterm cli get-text --pane-id <pane>` |
| Type | `wezterm cli send-text [--no-paste] --pane-id <pane> "text"` |
| Focus | `wezterm cli activate-tab --pane-id <pane>` or `activate-window --window-id <id>` |
| Close | `wezterm cli kill-pane --pane-id <pane>` |

`--new-window` is not used for executors.

## Spawn a native session

Spawn `claude` directly, not through `screen` or a detached shell:

```bash
wezterm cli spawn --pane-id "$pane" --cwd "$checkout" -- \
  claude --settings "$HOME/.claude/deepseek.json" --effort max -n "exec-<task>"
```

The pane determines the window, so the new tab lands beside the planner. Do not pass `--new-window`.

The new process inherits `WEZTERM_PANE`, so the host's SessionStart hook registers it and the session name becomes addressable. Keep the returned pane id.

If the tab must stay open after Claude exits, wrap the command with the user's login shell (`zsh -ic '...; exec zsh'`); otherwise the tab closes with the session. Direct spawn is preferred: the transcript is persisted and `claude --resume` can recover it.

## Deliver the first task

`send-text` sends paste content. With bracketed paste, the text is not submitted; send Enter separately:

```bash
wezterm cli send-text --pane-id "$pane" "You are the executor. ..."
wezterm cli send-text --no-paste --pane-id "$pane" $'\r'
```

Poll `get-text` until the TUI is ready before typing. After sending, read it back to confirm the prompt appears and the task is not split across a dialog. If the session asks a startup question (trust, permissions, hooks), resolve it with the user or the host configuration; do not assume the prompt was accepted.

## Failure modes

- Wrong GUI instance: the tab exists in `wezterm cli list` but the user cannot see it. Resolve the socket and window, then retry in the visible instance.
- Unregistered session: built-in messaging cannot find the name. Check the SessionStart hook and that the process inherited `WEZTERM_PANE`.
- Closed tab: the process ends; resume from the transcript with `claude --resume` instead of pretending it is still running.
- Version skew: keep the CLI and GUI from the same build; the host's installation and update flow owns upgrades.