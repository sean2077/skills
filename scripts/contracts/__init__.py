"""Targeted catalog contracts, discovered by filename.

A module opts in by exposing `SKILL` (the catalog directory name) and
`validate(*, readme_text)`. Use modules for executable or high-risk invariants
that generic catalog validation cannot express; prompt-only skills do not need
one. Adding or retiring a targeted contract touches exactly one file here.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable, Iterator
PACKAGE = Path(__file__).resolve().parent

def discover() -> Iterator[tuple[str, Callable[..., None]]]:
    """Yield (skill name, validate) for every targeted module, sorted by skill."""
    found: list[tuple[str, Callable[..., None]]] = []
    for path in sorted(PACKAGE.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{path.stem}")
        skill = getattr(module, "SKILL", None)
        validate = getattr(module, "validate", None)
        if not isinstance(skill, str) or not callable(validate):
            raise RuntimeError(
                f"contracts/{path.name} must define SKILL: str and validate(*, readme_text)"
            )
        found.append((skill, validate))
    yield from sorted(found, key=lambda item: item[0])

def run_all(*, readme_text: str | None = None) -> list[str]:
    """Run every discovered targeted contract and return the covered skills."""
    ran = []
    for skill, validate in discover():
        validate(readme_text=readme_text)
        ran.append(skill)
    return ran
