# WezTerm executor tabs

Use the WezTerm CLI from the running fork. Creating a tab and typing into it are separate operations; verify each one.

## Resolve the GUI and window

- If `WEZTERM_UNIX_SOCKET` and `WEZTERM_PANE` are set, use them. Resolve the pane's window with `wezterm cli list --format json`.
- Claude Code's Bash tool may sanitize `WEZTERM_*` from the tool environment even when the parent shell has them. On Linux, walk up `/proc/<pid>/environ` from `$PPID` until the socket appears; otherwise require an explicit socket and window id.
- More than one GUI instance may be running, for example a normal instance and a `quake.lua` dropdown. The CLI default may target a different instance than the one the user sees. Confirm with `wezterm cli list-clients` and `wezterm cli list`.
- In a quake-style instance, `--new-window` can create a window outside the user's visible surface. Add tabs to the visible window with `--window-id` instead.

## Commands

| Need | Command |
|---|---|
| List windows, tabs and panes | `wezterm cli list --format json` |
| New tab | `wezterm cli spawn --window-id <id> --cwd <dir> -- <program>` |
| New window | `wezterm cli spawn --new-window ...` (see quake caveat) |
| Split | `wezterm cli split-pane ...` |
| Title | `wezterm cli set-tab-title --pane-id <pane> "<title>"` |
| Read screen | `wezterm cli get-text --pane-id <pane>` |
| Type | `wezterm cli send-text [--no-paste] --pane-id <pane> "text"` |
| Focus | `wezterm cli activate-tab --pane-id <pane>` or `activate-window --window-id <id>` |
| Close | `wezterm cli kill-pane --pane-id <pane>` |

## Spawn a native session

Spawn `claude` directly, not through `screen` or a detached shell:

```bash
wezterm cli spawn --window-id "$window" --cwd "$checkout" -- \
  claude --settings "$HOME/.claude/deepseek.json" --effort max -n "exec-<task>"
```

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