# Agent Scaffold Diagnostics

Read this when a target needs machine-readable planning, prerequisite diagnosis,
or installed-contract troubleshooting.

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

## Troubleshooting order

1. Run `doctor` when installation stops before mutation or real links cannot be
   created.
2. Run `plan` when authored contracts or host config may need adoption.
3. Run `verify` after installation and use each failed check's `fix` field.
4. For Windows symlink failures, follow [platform support](platform-support.md).
5. For hook mismatches, inspect only the exact current managed commands described
   in [host integration](host-integration.md).

Human-readable output and JSON are rendered from the same checks; a difference
between them is a defect in the scaffold, not a separate interpretation layer.
