#!/usr/bin/env python
"""Shared state and helpers for the catalog validator and its per-skill contracts.

Every module appends to the same `errors`/`warnings` lists, so a contract module
never has to thread a result object through its call chain.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from strictyaml import YAMLValidationError, dirty_load
except ImportError:  # reported as a concise catalog error from validate_skills.main()
    YAMLValidationError = Exception  # type: ignore[assignment,misc]
    dirty_load = None

REPO = Path(os.environ.get("SKILLS_REPO", Path(__file__).resolve().parent.parent))

SKILLS_DIR = REPO / "skills"

README = REPO / "README.md"

MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"

GROUPING_MANIFEST = REPO / ".claude-plugin" / "plugin.json"

VALIDATE_WORKFLOW = REPO / ".github" / "workflows" / "validate.yml"

RELEASE_WORKFLOW = REPO / ".github" / "workflows" / "release.yml"

# Coarse repo-local prose budget, not a host token limit. It scales with the
# catalog so adding a well-scoped skill does not consume another skill's share.
METADATA_PROSE_CHARS_PER_SKILL = 512

ALLOWED_FRONTMATTER_FIELDS = {"name", "description"}

RESIDENT_SKILL_MAX_LINES = 100

RESIDENT_SKILL_MAX_CHARS = 8000

errors: list[str] = []

warnings: list[str] = []

def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse a leading frontmatter block with a real strict YAML parser."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md has no opening `---` frontmatter delimiter")
    closing = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = index
            break
    if closing is None:
        raise ValueError("SKILL.md has no closing `---` frontmatter delimiter")
    if dirty_load is None:
        raise ValueError(
            "StrictYAML is unavailable — run `python -m pip install -r requirements-validation.txt`"
        )
    try:
        parsed = dirty_load("\n".join(lines[1:closing]), allow_flow_style=True).data
    except YAMLValidationError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc.context} {exc.problem}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return parsed

def readme_skill_rows(readme_text: str, skill_name: str) -> str:
    """Return public catalog rows for one skill so domain guards cover that projection."""
    marker = f"[{skill_name}](skills/{skill_name}/)"
    return "\n".join(line for line in readme_text.splitlines() if marker in line)
