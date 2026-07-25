"""Per-skill catalog contracts, discovered by filename.

One module per `skills/<name>/` directory. A module opts in by exposing
`SKILL` (the catalog directory name) and `validate(*, readme_text)`. Adding or
retiring a skill contract means adding or deleting exactly one file here — the
generic catalog rules in `validate_skills.py` never need to change.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable, Iterator

PACKAGE = Path(__file__).resolve().parent


def discover() -> Iterator[tuple[str, Callable[..., None]]]:
    """Yield (skill name, validate) for every contract module, sorted by skill."""
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
    """Run every discovered contract and return the skill names that ran."""
    ran = []
    for skill, validate in discover():
        validate(readme_text=readme_text)
        ran.append(skill)
    return ran
