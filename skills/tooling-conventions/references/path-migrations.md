# Tool Path Migrations

Read this when moving, renaming, or deleting a committed command path.

## Move / rename / delete checklist

A move is a contract change — sync every mechanical reference surface in the **same commit**:

- [ ] project manual / agent docs that name the path
- [ ] sibling skills that invoke it
- [ ] service/unit files bound to it (change the unit/install contract first, or leave a shim)
- [ ] build files, install scripts, image/packaging scripts, and any other callers
- [ ] the manifest row + its human-readable view
- [ ] decide on a deprecation shim (external/QA: keep ≥1 release; internal: drop)
- [ ] re-check the moved script's own `REPO_ROOT`/`HERE` derivation and sibling-file references (a relocated script often needs one extra `..`)

External state (a wiki, an issue tracker, agent memory) is not a commit-blocking file surface, but list any that affect the current workflow in the change summary.
