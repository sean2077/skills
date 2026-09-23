# Agent Scaffold Diagnostics

## Structured output

`plan`, `doctor`, and `verify` accept `--json` and write one JSON document to
stdout. Diagnostic detail stays inside the document, so callers do not need to
scrape colored logs.

```bash
bash <skill-dir>/agent-scaffold.sh plan --profile default --json
bash <skill-dir>/agent-scaffold.sh doctor --profile default --json
bash <skill-dir>/agent-scaffold.sh verify --profile default --json
```

The top-level shape is stable within schema version 1:

```json
{
  "schema_version": 1,
  "scope": "harness-assets",
  "project_guidance": "not-assessed",
  "mode": "verify",
  "target": "/path/to/repo",
  "profile": "default",
  "apply_mode": null,
  "ok": true,
  "checks": [
    {
      "id": "runtime.worktree",
      "status": "pass",
      "path": ".agents/tools/worktree.sh",
      "fix": null
    }
  ]
}
```

`plan.apply_mode` is `apply` unless an installed current runtime asset differs
from the bundled source, in which case it is `upgrade`. Every check always has
`id`, `status`, `path`, and `fix`; failed checks may also include `detail`.

Schema-version 1 uses these status values:

| Mode | Statuses |
|---|---|
| `plan` | `create`, `merge`, `adopt`, `refresh`, `present`, `skip`, `attention` |
| `doctor`, `verify` | `pass`, `fail` |

- Check IDs and status meanings are stable within the schema version; consume checks by `id`
  because array order is not an API.
- `path` is repo-relative for target assets and may be absolute for repository/environment checks.
- `fix` is either `null` or one actionable remediation; `detail` carries diagnostics, not identity.
- `ok` is false when any check is `attention` or `fail`.
- A rendered `plan` exits 0 even when `ok` is false, so automation must inspect `ok`. `doctor` and
  `verify` exit 1 when `ok` is false. CLI/manifest errors and mutation preflight failures exit 2.

`scope` and `project_guidance` explicitly bound every report: the installer checks only
harness assets and does not judge semantic project guidance. These additive fields do not
change `ok` or exit-code meanings. The full skill also performs the Agent-owned
[project-convention work](project-conventions.md); no new automatic policy gate is implied.

## Line-ending checks

- `contract.line-endings`: the prepended managed `.gitattributes` defaults match the asset.
- `seed.editorconfig`: a regular project-owned editor file exists; its settings are not interpreted.
- `line-endings.runtime-attributes`: Git resolves scaffold runtime paths to `text eol=lf`.
- `line-endings.tracked`: tracked text/index/worktree bytes follow effective Git EOL rules.
- `line-endings.git`: emitted as a failure if Git EOL diagnostics cannot be obtained.

The existing `contract.gitattributes` line-presence check remains, but is no longer the only
EOL evidence. `plan` previews defaults and editor seeding, and reports malformed markers or
non-regular file conflicts before writes. `doctor` remains a prerequisite/capability check.
`verify` may report old files needing migration even after a successful install: neither mode
stages or converts files. Use the [line-ending guide](line-endings.md), not a reset/clean command.

## Troubleshooting order

1. Run `doctor` when installation stops before mutation or real links cannot be
   created.
2. Run `plan` when authored contracts or host config may need adoption.
3. Run `verify` after installation and use each failed check's `fix` field.
4. For Windows symlink failures, follow [platform support](platform-support.md).
5. For hook mismatches, inspect only the exact current scaffold-owned commands described
   in [host integration](host-integration.md).

Human-readable output and JSON are rendered from the same checks; a difference
between them is a defect in the scaffold, not a separate interpretation layer.

## Profile selection

An explicit `--profile` wins. Otherwise the installer reads the profile marker in its managed AGENTS block. An unmarked block is recognized only when it exactly matches a known default/light rendering; an ambiguous block requires an explicit choice before any project write. A fresh installation uses `default`. This keeps routine plan, verify, and upgrade calls aligned with the installed policy without another settings file.
