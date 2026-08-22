# Compatibility and verification matrix

Audit base: **2026-08-22**, repository `main` at `88a9d9a9d3c9e56945d0d421b8c3ccd3b5a806ca`. Re-run the checks below before carrying these claims into a later commit or release.

“Compatible” is not one binary property. This repository separates four layers so a true statement at one layer is not promoted into an unsupported claim at another.

## Support layers

| Layer | What this repository verifies | What it does not prove |
|---|---|---|
| Agent Skills format | CI is configured to run the repository-pinned official `skills-ref` validator for every published `skills/<name>/`; the catalog validator also checks frontmatter, names, references, and payload structure. | That every client discovers the same paths, loads the same optional fields, or can execute every bundled language. |
| Installer discovery | CI runs `skills@1.5.17` against the catalog root and checks the discovered/installed payload. `1.5.17` is an audited pin, not a claim that it is the current upstream release. | That every target advertised by a newer or older installer is runtime-tested here. |
| Host skill discovery | Codex is wired to project skills in `.agents/skills/`; Claude Code is wired through real directory symlinks in `.claude/skills/`. The scaffold verifies the repository shape and projections. | Cloud-hosted variants, enterprise policy layers, plugins, or other agents unless a separate test says so. |
| Project harness behavior | The bundled scaffold installs and verifies shared hook runtimes, generated subagent projections, authority docs, worktree governance, and host JSON for Claude Code + Codex. | That a host has accepted project trust, that a user has approved a hook, or that organization policy permits the behavior. |

The published catalog currently contains 16 skills. `skill-eval` is intentionally excluded from all four public catalog claims: its source, references, generated runtime, and Claude Code projection live under `.agents/skills/skill-eval` for this repository's trusted project harness only. Its `metadata.internal: true` marker excludes it from normal `skills` CLI discovery unless internal skills are explicitly enabled. It is validated by the repository's private contract and CI, but it is not listed in `.claude-plugin/plugin.json`, README catalog rows, or normal `npx skills` discovery.

## Current host facts that affect this harness

### Codex

- Codex scans `.agents/skills` from the working directory through the repository root and follows symlinked skill directories.
- Project `.codex/` configuration, hooks, and rules require a trusted project layer. The scaffold treats its generated agent projections as part of the same project-owned harness boundary.
- Trusting the project is not sufficient to run scaffold-owned command hooks. In Codex terminology these are **non-managed hooks**, not policy-managed hooks. Review them in `/hooks`; Codex stores trust against the exact hook-definition hash, so an unreviewed or changed definition is skipped until reviewed again. This hook gate is independent: it does not revoke trust from the rest of the project layer.

Official references:
[skills](https://developers.openai.com/codex/build-skills),
[hooks](https://developers.openai.com/codex/hooks), and
[configuration](https://developers.openai.com/codex/config-reference).

### Claude Code

- Project skills live in `.claude/skills/<name>/SKILL.md`; a skill directory may be a symlink and Claude Code follows the target.
- Repository-provided project settings and plugin-like behavior remain subject to workspace trust and the user's policy.
- Checkpoint restore does not rewind symlinked or hard-linked files. A successful `/rewind` can therefore leave edits in `AGENTS.md` or `.agents/skills/*` when they were reached through a harness symlink. Use Git or an explicit reverse edit for the real target.

Official references:
[skills](https://code.claude.com/docs/en/skills),
[settings](https://code.claude.com/docs/en/settings), and
[checkpointing](https://code.claude.com/docs/en/checkpointing).

## Installer semantics used in this repository

The upstream `skills` CLI supports many targets. That target list is useful discovery metadata, not this repository's certification matrix.

- Install selected skills to selected targets with repeated `--skill` and `-a` options.
- Install every skill from this catalog to only Claude Code and Codex with:

  ```bash
  npx skills add sean2077/skills --skill '*' -a claude-code -a codex
  ```

- `--all` is intentionally not used for that example because its current upstream meaning is all discovered skills to all supported agents without prompts.
- `.claude-plugin/plugin.json` is maintained here as catalog discovery/grouping metadata for the tested installer flow. Its presence does not certify native runtime support for an agent.
- At this audit date the upstream CLI release is [`v1.5.23`](https://github.com/vercel-labs/skills/releases/tag/v1.5.23), while repository CI deliberately remains pinned to `1.5.17`. A reproducibility pin and the upstream latest version answer different questions and must not be presented as the same fact.

Official reference: [vercel-labs/skills](https://github.com/vercel-labs/skills).

## Maintenance rule

Reverify this page whenever a host path, trust model, hook schema, installer flag, compatibility claim, or audited pin changes. Prefer a dated, bounded claim over “universal,” “all hosts,” “latest,” or similar wording that silently expires. Follow the [documentation maintenance policy](documentation-maintenance.md) for source and duplication rules.
