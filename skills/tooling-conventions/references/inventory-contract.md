# Structural Tool Inventory Contract

Read this when recurring command drift justifies a machine-readable inventory. Smaller projects
can use the classification workflow without creating an inventory solely for this skill.

## Bundled checker versus project root

The checker is a distributable skill asset, not a command copied into the target project:

```bash
bash <skill-dir>/scripts/inventory-check.sh [--] [path/to/inventory.tsv]
```

`tools/tools-inventory.tsv` is only the no-argument default. An explicit inventory path always
wins. The scan root is `TOOLS_DIR` when set; otherwise it is the inventory's directory. Projects
may therefore govern `tools/`, `scripts/`, `bin/`, or another existing root. When the inventory
lives outside that root, set `TOOLS_DIR` explicitly.

`INVENTORY_CHECK_SKIP` defines the full reverse-scan exclusion regex. When unset, reverse scan
excludes nothing: no directory or filename carries universal semantic meaning. A project-provided
value is a full project-owned policy, not an additive skill taxonomy.

Python syntax checks resolve a Python 3.8+ interpreter lazily, only when the inventory contains a
`.py` row. Set `PYTHON_BIN` to an explicit executable, or let the checker try `python`, `python3`,
then the Windows `py -3` launcher. If none is compatible, the unavailable-interpreter preflight
exits `2`; it is never downgraded by `audit_level=warn`.

## TSV shape

Only `path` is required. `audit_level` is optional with values `enforce` (default) or `warn`.
All other project-owned columns are opaque to the bundled checker: their names, values, and
cross-field rules belong to Project Tool Policy and its wrapper or tests.

```tsv
path	owner	lifecycle	audit_level
build.sh	developer-experience	active	enforce
release/publish.py	release	active	enforce
generated/	build-system	generated	warn
```

- `path` is relative to the scan root, uses `/`, and contains no absolute prefix, drive prefix,
  `.`, `..`, backslash, or duplicate separator.
- Directory rows end in `/`; file rows do not. A directory row validates that directory only—it
  never covers nested `.sh` commands or executable `.py` CLIs in the reverse inventory.
- Every `.sh` file outside the project-owned skip regex is a command candidate by suffix. A
  tracked Python file is a command candidate when Git mode is `100755`; outside Git, executable
  permission is the fallback.
- Row findings such as missing paths or syntax errors honor `audit_level=warn`. Invalid schema,
  invalid paths, duplicates, reverse drift, and unavailable syntax-check interpreters remain
  blocking preflight failures.

## Checker ownership

The Structural Checker Core validates only:

- normalized, unique paths and file/directory existence;
- reverse drift between command candidates and file rows;
- Bash syntax and in-memory Python compilation without bytecode residue;
- row-level enforce/warn behavior and safe preflight handling.

It does not interpret visibility, audience, lifecycle, hazard, provenance, `--help` applicability,
or any other semantic field. A project that needs those gates owns a Policy Adapter—for example,
a project test that validates its chosen columns and then calls the bundled structural checker.

## CLI contract

- no arguments: inspect `tools/tools-inventory.tsv` relative to the current directory;
- one inventory path, or `--` plus a path: inspect that explicit inventory;
- `-h` / `--help`: print usage and exit `0`;
- structural findings: exit `1`;
- invalid invocation or unavailable inventory/scan root/temp directory/syntax interpreter:
  exit `2`.

The checker prints the effective inventory and scan root so an explicit `TOOLS_DIR` override is
auditable.
