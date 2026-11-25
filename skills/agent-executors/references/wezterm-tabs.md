# WezTerm executor tabs

Use the WezTerm CLI from the running fork. Creating a tab and typing into it are separate operations; verify each one.

## Resolve the GUI and window

The executor tab must be created in the **same window** as the planner's tab. First select the correct GUI/mux instance, then use `spawn --pane-id` to derive the window from the planner pane; do not use `--new-window`. Pane/window numbers alone do not identify an instance.

- Keep inherited `WEZTERM_PANE` and `WEZTERM_UNIX_SOCKET` together when available. The socket selects the instance; the pane selects its window/domain.
- Claude Code's Bash tool may sanitize `WEZTERM_*` from the tool environment even when the parent shell has them. On Linux, recover both values from the same ancestor; do not combine a pane from one process with another instance's socket:

  ```bash
  planner_pane=${WEZTERM_PANE:-}
  planner_socket=${WEZTERM_UNIX_SOCKET:-}
  ancestor_pid=$PPID
  while [ -z "$planner_pane" ] || [ -z "$planner_socket" ]; do
    case "$ancestor_pid" in ''|*[!0-9]*|0|1) break ;; esac
    candidate_pane=$(tr '\0' '\n' 2>/dev/null < "/proc/$ancestor_pid/environ" | sed -n 's/^WEZTERM_PANE=//p')
    candidate_socket=$(tr '\0' '\n' 2>/dev/null < "/proc/$ancestor_pid/environ" | sed -n 's/^WEZTERM_UNIX_SOCKET=//p')
    if [ -n "$candidate_pane" ] && [ -n "$candidate_socket" ]; then
      planner_pane=$candidate_pane
      planner_socket=$candidate_socket
      break
    fi
    ancestor_pid=$(ps -o ppid= -p "$ancestor_pid" | tr -d '[:space:]')
  done
  ```

  If the pair cannot be recovered, resolve the visible instance through the host's supported selector before acting; ask for the window only if it remains ambiguous. Do not set an empty socket or infer the instance from matching numeric pane IDs.
- More than one GUI instance may be running, for example a normal instance and a `quake.lua` dropdown. Confirm `list-clients` and `list` against the resolved instance. Keep its selector on **every** spawn, list, get-text, send-text, title, and close call, including calls in fresh tool shells.
- The examples below assume `planner_socket` is known. Prefix them with `WEZTERM_UNIX_SOCKET="$planner_socket"`; if another supported selector identifies the verified instance, preserve that selector instead. Do not add `--prefer-mux`, which takes precedence over the socket selector.

Instance selection, `--pane-id`, and tab activation were checked on 2026-11-25 against the official [CLI targeting rules](https://wezterm.org/cli/cli/index.html#targeting-the-correct-instance), [spawn reference](https://wezterm.org/cli/cli/spawn.html), and [activate-tab reference](https://wezterm.org/cli/cli/activate-tab.html). A GUI/mux connection still needs host access.

## Verify placement

Keep the returned pane id as `executor_pane`. After spawning, compare `window_id` for `planner_pane` and `executor_pane` within the selected instance:

```bash
WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli list --format json
```

If the ids differ, close only the new executor pane through that same instance and resolve the target before retrying. Do not send the task until the placement is confirmed.

## Commands

| Need | Command |
|---|---|
| List windows, tabs and panes | `wezterm cli list --format json` |
| New tab | `wezterm cli spawn --pane-id "$planner_pane" --cwd "$checkout" -- <program>` |
| Split | `wezterm cli split-pane ...` |
| Title | `wezterm cli set-tab-title --pane-id <pane> "<title>"` |
| Read screen | `wezterm cli get-text --pane-id <pane>` |
| Type | `wezterm cli send-text [--no-paste] --pane-id <pane> "text"` |
| Select executor tab | `wezterm cli activate-tab --tab-id <tab-id>` (use the executor's `tab_id` from `list`) |
| Close | `wezterm cli kill-pane --pane-id <pane>` |

The command table omits the instance prefix for readability; it is still required. `--new-window` is not used for executors.

## Spawn a native session

Use the [executor launch command](../SKILL.md#start-an-executor) to start Claude in a native WezTerm tab. The planner pane determines the window within the selected instance. The new process inherits its own `WEZTERM_PANE`; when the host's SessionStart registration is configured, its session name becomes addressable. Keep the returned id as `executor_pane` and verify messaging registration separately from tab creation.

Codex can pass `NO_COLOR=1` through `wezterm cli spawn`, disabling color in Claude Code. For a Codex launch that should display color, place `env -u NO_COLOR` immediately before `claude`. This clears the variable in the executor process and preserves `TERM` and `COLORTERM` set by WezTerm. Use the same prefix when resuming an executor in a new tab or invoking `claude` inside a shell wrapper.

`--dangerously-skip-permissions` activates YOLO for this executor. `--allow-dangerously-skip-permissions` alone only makes the mode available and does not activate it. Keep the explicit permission flag when using a shell wrapper or resuming a persisted executor, unless a narrower mode was requested. See the [permission default](../SKILL.md#permission-default) and the official [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference).

If the tab must stay open after Claude exits, wrap the command with the user's login shell (`zsh -ic '...; exec zsh'`); otherwise the tab closes with the session.

## Deliver the first task

`send-text` sends paste content. With bracketed paste, the text is not submitted; send Enter separately:

```bash
WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli send-text --pane-id "$executor_pane" "You are the executor. ..."
WEZTERM_UNIX_SOCKET="$planner_socket" wezterm cli send-text --no-paste --pane-id "$executor_pane" $'\r'
```

Read `get-text` before typing: verify the effective permission mode and that the input is the normal prompt, not a startup dialog. Resolve prompts already covered by the user's authorization without asking again. If a trust, login, or hook decision needs new authorization, report that specific blocker. After sending, read back to confirm the task was submitted and is not split across a dialog.

YOLO reduces routine tool approvals; it does not guarantee a prompt-free startup or remove explicit permission rules, managed restrictions, OS access limits, or missing credentials. If the selected mode is rejected or a permission prompt persists, report the exact cause before handing off work. Do not silently fall back to an approval-waiting session or alter shared policy to force the launch. See [Claude Code permissions](https://code.claude.com/docs/en/permissions).

## Failure modes

- Wrong GUI instance: the tab exists in `wezterm cli list` but the user cannot see it. Resolve the socket and window, then retry in the visible instance.
- Unregistered session: built-in messaging cannot find the name. Check the SessionStart hook and that the process inherited `WEZTERM_PANE`.
- Closed tab: the process ends; do not pretend it is still running. Resume only if the session was persisted.
- Version skew: keep the CLI and GUI from the same build; the host's installation and update flow owns upgrades.
