# Tool Path Migrations

Read this when moving, renaming, or deleting a committed command path.

## Move / rename / delete checklist

A move is a contract change — sync every mechanical reference surface in the **same commit**:

- [ ] project manual / agent docs that name the path
- [ ] sibling skills that invoke it
- [ ] service/unit files bound to it (change the owning unit/install contract first)
- [ ] build files, install scripts, image/packaging scripts, and any other callers
- [ ] the structural inventory row, Project Tool Policy, and any derived human-readable view,
      when the project has adopted them
- [ ] re-check the moved script's own `REPO_ROOT`/`HERE` derivation and sibling-file references (a relocated script often needs one extra `..`)

If an active external consumer cannot move in the same change, stop and report the coordination
boundary. Do not create a generic compatibility shim or indefinite dual path from this skill.

External state (a wiki, an issue tracker, agent memory) is not a commit-blocking file surface, but list any that affect the current workflow in the change summary.
