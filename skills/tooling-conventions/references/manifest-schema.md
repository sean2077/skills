# Tool Surface Manifest Schema

Read this when a growing repository needs a machine-readable tool-surface inventory.

Adapt this lean schema to the project instead of copying unused columns. Keep one row per
command surface and reconcile it with `scripts/manifest-check.sh`. A human-readable README
view is optional and derived. Use a tab-separated file such as `tools/tools-manifest.tsv`;
tabs preserve paths and notes containing spaces or commas.

Adopt this once a repo's script or contributor count makes drift likely; smaller repos can apply the skill's §1–§4 by judgment without a manifest.

## Core columns (every row)

| column | meaning |
|---|---|
| `path` | path relative to the tools root (e.g. `deploy.sh`, `provision/recover_sn.sh`, or `provision/` for a package dir) |
| `surface` | `public` \| `installed` \| `helper` \| `break-glass` \| `paused` \| `legacy` \| `package` \| `native` \| `template` \| `vendor` |
| `domain` | logical area (`build`, `release`, `provision`, `deploy`, `logs`, …) |
| `audience` | who runs it: `dev` \| `ci` \| `operator` \| `release` \| `end-user` \| `runtime` |
| `entry_for` | the independent operator job this entry owns. **Blank ⇒ it is not an independent entry ⇒ it should be a `helper`, not `public`.** |
| `hazard` | `none` \| `low` \| `med` \| `high`, with a short parenthetical (e.g. `med(auto-rollback)`) |
| `verify` | how success is proven (a command or smoke), or `-`; public/installed command rows name `--help=0` + unknown-arg `=2` evidence or a project `cli-contract` test |
| `notes` | freeform: usage boundary, gotchas, why it isn't sunk into a helper |

Keep `path` normalized and relative to the checker scan root: use `/` separators, no
absolute/drive paths, `.`/`..` segments, or duplicate separators. End `package` and
`native` directory rows with `/`; use file syntax for every other surface.

## Optional columns (only where meaningful)

| column | applies to | meaning |
|---|---|---|
| `installed_path` | `installed` | the on-target path — this is the external contract that must not silently change |
| `called_by` | `helper` / `installed` | the entries that call it |
| `trigger` | `break-glass` | when you'd reach for it |
| `activation_gate` | `paused` | what unblocks enabling it |
| `replacement` | `legacy` | what supersedes it |
| `source` / `version` / `checksum` | `vendor` | provenance of the third-party binary |
| `audit_level` | any | `enforce` (default) \| `warn` — lets known debt warn instead of fail |

Keep the column set small. Add a column only when the audit or a reviewer actually consults it; a 25-column manifest nobody reads is the same failure as 30 unread rules.

## Minimal example

```tsv
path	surface	domain	audience	entry_for	hazard	verify	notes
build.sh	public	build	dev	build the project	none	cli-contract test (--help=0; unknown=2)	domain headline
release.sh	public	release	release	cut + publish a release	med(tags/pushes)	cli-contract + dry-run	headline; calls release/changelog.py
release/changelog.py	helper	release	release		none	in-memory compile	called_by release.sh
deploy.sh	public	deploy	operator	deploy a build to a target	high(rollback)	cli-contract + smoke + health check	goes through the upgrade path only
recover.sh	break-glass	provision	operator	sole identity-recovery path	high	manual	trigger: device shows wrong-machine
provision/	package	provision	dev		none	-	python provisioning package (modules not registered individually)
vendor/jq-linux-arm64	vendor	vendor	runtime		none	checksum	source=stedolan/jq version=1.7 checksum=sha256:…
```

Use `cli-contract test (--help=0; unknown=2)` (or the actual project test command with
equivalent wording) in `verify` when that evidence exists. The generic checker validates this
declaration but deliberately does not execute arbitrary project commands: a broken help parser
must not turn a static inventory audit into a deployment or device mutation.

When the optional checker sees `entry_for`, it rejects blank independent entries and nonblank
helpers. When it sees `verify`, it requires the declaration above for public/installed command
files. Omitting an unused column omits its corresponding semantic check; adapt the schema rather
than adding empty ceremony.

## Which scripts get a row

- **Yes:** every `public` / `installed` / `break-glass` / `paused` / `legacy` command entry (a `.sh` script, by suffix, or an executable `.py` CLI).
- **Directory row:** a `package` / `native` dir gets one row; its internal non-executable modules do not.
- **Optional:** `helper` rows are useful for traceability (`called_by`) but the reconciliation check treats unregistered files under an ignored dir (e.g. `internal/`, `vendor/`, `tests/`) as intentionally-unlisted helpers. Register a helper when you want it tracked; otherwise keep it under an ignored dir.
