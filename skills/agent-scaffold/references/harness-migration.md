# Agent Scaffold Harness Migration

Read this only for retrofit, adoption, or migration from a legacy installed harness layout.

## Migrating the legacy runtime home

Older installs placed shared runtime files under `tools/agent/`. The current harness keeps the
complete agent-owned runtime under `.agents/tools/` so adopting the harness does not create a new
top-level `tools/` directory in projects that do not already have one.

Run `plan` first. When it reports the legacy runtime, apply with `upgrade`, not `retrofit`:

```bash
bash <skill-dir>/harness-init.sh plan
bash <skill-dir>/harness-init.sh upgrade [profile flags]
```

`init` and `retrofit` create only the current layout. They also reject a partial legacy install
whose runtime has already moved but whose exact managed hook, package/Husky, banner, LF, or
documentation identities still use the old path; `plan` routes that state to `upgrade` as well.

The migration is intentionally a hard cut with no compatibility wrappers:

- known runtime files move from `tools/agent/` to the matching path under `.agents/tools/`;
- active-profile files are then refreshed from the current templates; optional dormant worktree
  files remain dormant under the new runtime home until a later default-profile upgrade refreshes
  them;
- exact managed hook commands, default package scripts, the Husky drift line, generated ownership
  banners, LF attributes, the managed AGENTS block, `.agents/subagents/README.md`, and installer
  messages converge to the new path;
- if both old and new copies of a known file exist with different content, preflight exits 2 before
  any target mutation; resolve the two owners and rerun;
- unknown files below `tools/agent/` are never deleted or moved. The installer removes only known
  managed files and uses non-recursive empty-directory removal for `tools/agent/hooks/`,
  `tools/agent/`, and `tools/`;
- custom CI, documentation, or command strings are user-owned and are not rewritten by broad text
  replacement. Update any reported stale callers before relying on the new commands.

### Retiring the managed formatter hook

The scaffold no longer installs or wires `format_on_edit.sh`; formatter choice, scope, working
directory, ignore rules, and failure policy belong to the target project. `upgrade` removes the
retired `.agents/tools/hooks/format_on_edit.sh` / `tools/agent/hooks/format_on_edit.sh` runtime and
their exact managed hook entries while preserving basename lookalikes and unrelated user hooks.
Move any desired formatter behavior to a project-owned path outside `.agents/tools/` and wire it
using [the host-integration recipe](host-integration.md#project-owned-formatting-hooks).

`--no-format-hook` remains accepted for one compatibility cycle as a deprecated no-op so existing
automation can migrate without an immediate command-line break. New commands should omit it.

`verify` rejects known legacy runtime files, legacy managed hook wiring, the legacy default
package/Husky drift commands, and legacy harness-added LF rules. It does not reject an unrelated
user-owned `tools/agent/` directory whose known managed filenames are absent.

## Retrofitting an in-flight project

`init` and `retrofit` share one code path; what makes `retrofit` safe on a project already
mid-development is that it **adopts** existing assets into the SSOT instead of ignoring or
clobbering them. Preview any of it with `plan` (read-only).

### plan — preview before you write

`bash <skill-dir>/harness-init.sh plan` reports, per concern, whether the run would **create**,
**merge**, **migrate**, or leave something for you (**needs you**), and writes nothing. Use it to
see — before touching the repo — what an existing `CLAUDE.md`, hook config, or hand-authored
subagent will turn into.

### Adopting a real CLAUDE.md

Many live projects already carry a hand-written `CLAUDE.md`. Retrofit treats `AGENTS.md` as the
SSOT and `CLAUDE.md` as its symlink, so:

- **real `CLAUDE.md`, no `AGENTS.md`** → the prose is copied into `AGENTS.md`, the harness block is
  appended (or refreshed if the prose already carried the markers), and the real `CLAUDE.md` is
  replaced with the `CLAUDE.md → AGENTS.md` symlink. Nothing is lost — the content moves, it is not
  deleted.
- **real `CLAUDE.md` *and* real `AGENTS.md`** → ambiguous (two authored files); the installer keeps
  both and exits with a conflict after telling you to merge `CLAUDE.md` into `AGENTS.md` by hand.
- **already the correct symlink** → left as-is; a different symlink target is preserved as a conflict.

Subagent adoption is a separate source/projection concern. When retrofit finds hand-authored host
agents, load [`subagents.md`](subagents.md#adopting-hand-authored-subagents) rather
than expanding that import contract here.
