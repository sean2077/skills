# Agent Scaffold Subagents

Read this only when changing subagent source, import, projection, or drift behavior.

## Contents

- [Subagent generator](#subagent-generator)
- [Project-owned source shape](#project-owned-source-shape)
- [Project-owned drift integration](#project-owned-drift-integration)
- [Optional example](#optional-example)
- [Adopting hand-authored subagents](#adopting-hand-authored-subagents)
- [Drift troubleshooting](#drift-troubleshooting)

## Subagent generator

| Capability | Needs | Without it |
|---|---|---|
| full harness, real-link manager, hooks, and subagent projection | git + Bash 3.2+ + Python 3.8+ + real file/directory links | preflight exits 2 before target mutation |
| optional projection drift automation | a project-owned CI job or hook manager | run the generator's `--check` command manually |

`generate-subagents.py`, `symlink-manager.py`, and `hook-paths.py` use only the Python standard
library — no Node or `package.json`. Resolve Python by executing a 3.8+ probe on `PYTHON_BIN`,
`python`, `python3`, then Windows `py -3`; an unusable or older candidate falls through to the
next one. Before the first target write, the installer reuses the symlink manager and generator in
read-only preflight modes so deterministic contract, skill-projection, and subagent-import conflicts
leave the repository unchanged. Node and package-manager integration are not required or selected.

## Project-owned source shape

Each subagent uses one portable source directory:

```text
.agents/subagents/<name>/
├── metadata.json
└── instructions.md
```

`metadata.json` supports the shared identity and host-specific projection fields:

```json
{
  "name": "<lowercase-kebab-case>",
  "description": "<what it does and when to dispatch it>",
  "claude": {
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "<optional>"
  },
  "codex": {
    "model": "<optional>",
    "model_reasoning_effort": "high",
    "sandbox_mode": "read-only",
    "nickname_candidates": ["Reviewer", "Auditor"]
  }
}
```

The directory, metadata name, and generated filenames must agree. Names use lowercase ASCII
letter groups separated by single hyphens and exclude Windows-reserved device names. Optional
projected scalar values must be non-empty strings; Claude tools are trimmed, comma-free strings;
Codex nicknames are unique and use its supported ASCII set. Unsupported fields fail closed rather
than disappearing during projection.

## Project-owned drift integration

The stable command is:

```bash
python .agents/tools/generate-subagents.py --check
```

Choose the integration that matches the project. For example:

```sh
# .husky/pre-commit (if the project already uses Husky)
python .agents/tools/generate-subagents.py --check
```

```yaml
# .pre-commit-config.yaml
- id: agent-subagents-check
  name: agent subagent projection drift
  entry: python .agents/tools/generate-subagents.py --check
  language: system
  pass_filenames: false
```

```json
{
  "scripts": {
    "gen:subagents": "python .agents/tools/generate-subagents.py",
    "check:agents": "python .agents/tools/generate-subagents.py --check"
  }
}
```

The scaffold does not create, rewrite, or validate those files or keys; they remain project-owned.

## Optional example

Create an example only when the project actually wants a reusable reviewer. This reference is not
installed automatically:

```json
{
  "name": "code-reviewer",
  "description": "Read-only reviewer for correctness, security, conventions, and test coverage before merge.",
  "claude": { "tools": ["Read", "Grep", "Glob", "Bash"] },
  "codex": {
    "model_reasoning_effort": "high",
    "sandbox_mode": "read-only",
    "nickname_candidates": ["Reviewer", "Auditor"]
  }
}
```

Example `instructions.md`:

```markdown
Review the requested change set without editing files or running mutating commands.

Report only high-confidence correctness, security, convention, and test-coverage findings. Read
enough surrounding context to validate each finding, then order results by severity with concrete
file and line references.
```

After authoring the two source files, run the generator and commit both host projections.

## Adopting hand-authored subagents

Read [subagent import](subagent-import.md) for the accepted Claude/TOML subsets, portable identity,
ownership conflicts, and fail-before-write inventory rules.

## Drift troubleshooting

- If `generate-subagents.py --check` fails, run
  `python .agents/tools/generate-subagents.py` and commit the regenerated
  `.claude/agents/*` and `.codex/agents/*` projections with their SSOT source.
- If a banner-less host projection has no source, import it; do not delete it as stale output.
- If a same-name source and host file disagree, resolve the ownership conflict before generation.
