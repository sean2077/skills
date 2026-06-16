# Surface manifest — lean schema

A machine-readable, one-row-per-command-surface index of a project's tooling, kept in sync with reality by `manifest-check.sh`. This is the **source of truth**; a human-readable `README` view (a rendered table) is optional and derived. Use a **tab-separated** file (e.g. `tools/tools-manifest.tsv`) — tabs survive paths/notes that contain spaces and commas.

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
| `verify` | how success is proven (a command or smoke), or `-` |
| `notes` | freeform: usage boundary, gotchas, why it isn't sunk into a helper |

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
build.sh	public	build	dev	build the project	none	bash -n; --help	domain headline
release.sh	public	release	release	cut + publish a release	med(tags/pushes)	dry-run	headline; calls release/changelog.py
release/changelog.py	helper	release	release		none	py_compile	called_by release.sh
deploy.sh	public	deploy	operator	deploy a build to a target	high(rollback)	smoke + health check	goes through the upgrade path only
recover.sh	break-glass	provision	operator	sole identity-recovery path	high	manual	trigger: device shows wrong-machine
provision/	package	provision	dev		none	-	python provisioning package (modules not registered individually)
vendor/jq-linux-arm64	vendor	vendor	runtime		none	checksum	source=stedolan/jq version=1.7 checksum=sha256:…
```

## Which scripts get a row

- **Yes:** every `public` / `installed` / `break-glass` / `paused` / `legacy` command entry (a `.sh` script, by suffix, or an executable `.py` CLI).
- **Directory row:** a `package` / `native` dir gets one row; its internal non-executable modules do not.
- **Optional:** `helper` rows are useful for traceability (`called_by`) but the reconciliation check treats unregistered files under an ignored dir (e.g. `internal/`, `vendor/`, `tests/`) as intentionally-unlisted helpers. Register a helper when you want it tracked; otherwise keep it under an ignored dir.
