#!/usr/bin/env python3
"""Run the stdlib-only resident-route and published-payload preflight.

The full StrictYAML and Agent Skills checks remain in ``validate_skills.py``.
This gate deliberately accepts only the one-line ``name``/``description``
subset published by this repository, so it can also run on the Python 3.8 floor.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Dict, List, Tuple

MAX_DESCRIPTION_CHARS = 320
_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(?P<body>.*?)(?:\r?\n)---(?:\r?\n|\Z)", re.DOTALL
)
_WHITESPACE_RE = re.compile(r"\s+")


def _decode_scalar(raw: str, path: Path, field: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError(f"{path}: {field} must be a non-empty scalar")
    if value[0] in "|>":
        raise ValueError(f"{path}: {field} must stay on one physical line")
    if value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            raise ValueError(f"{path}: unterminated single-quoted {field}")
        return value[1:-1].replace("''", "'")
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid double-quoted {field}: {exc.msg}") from exc
        if not isinstance(decoded, str):
            raise ValueError(f"{path}: {field} must decode to a string")
        return decoded
    return value


def _metadata(path: Path) -> Tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{path}: cannot read UTF-8 text: {exc}") from exc
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(f"{path}: missing or malformed YAML frontmatter delimiters")

    fields: Dict[str, str] = {}
    active = ""
    for line_number, line in enumerate(match.group("body").splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace():
            if active in {"name", "description"}:
                raise ValueError(
                    f"{path}:{line_number}: {active} must stay on one physical line"
                )
            continue
        key, separator, raw = line.partition(":")
        active = key.strip() if separator else ""
        if active not in {"name", "description"}:
            continue
        if active in fields:
            raise ValueError(f"{path}:{line_number}: duplicate {active} field")
        fields[active] = _decode_scalar(raw, path, active)

    missing = sorted({"name", "description"} - fields.keys())
    if missing:
        raise ValueError(f"{path}: missing frontmatter field(s): {', '.join(missing)}")
    return fields["name"], fields["description"]


def _catalog_dirs(skills_dir: Path) -> Tuple[List[Path], List[str]]:
    directories: List[Path] = []
    errors: List[str] = []
    try:
        mode = skills_dir.lstat().st_mode
    except OSError as exc:
        return directories, [f"{skills_dir}: cannot inspect published skills directory: {exc}"]
    if stat.S_ISLNK(mode):
        return directories, [f"{skills_dir}: published skills directory must not be a symlink"]
    if not stat.S_ISDIR(mode):
        return directories, [f"{skills_dir}: published skills directory does not exist"]

    for entry in sorted(skills_dir.iterdir()):
        try:
            mode = entry.lstat().st_mode
        except OSError as exc:
            errors.append(f"{entry}: cannot inspect catalog entry: {exc}")
            continue
        if stat.S_ISLNK(mode):
            errors.append(f"{entry}: published skill roots must not be symlinks")
        elif stat.S_ISDIR(mode):
            directories.append(entry)
        else:
            errors.append(f"{entry}: every entry directly under skills/ must be a directory")
    return directories, errors


def _payload_errors(skill_dir: Path) -> List[str]:
    errors: List[str] = []

    def record_walk_error(exc: OSError) -> None:
        errors.append(f"{skill_dir}: cannot walk published payload: {exc}")

    for current, directory_names, file_names in os.walk(
        skill_dir, topdown=True, onerror=record_walk_error, followlinks=False
    ):
        current_path = Path(current)
        for name in sorted(directory_names + file_names):
            entry = current_path / name
            try:
                mode = entry.lstat().st_mode
            except OSError as exc:
                errors.append(f"{entry}: cannot inspect payload entry: {exc}")
                continue
            if stat.S_ISLNK(mode):
                errors.append(f"{entry}: published skill payloads must not contain symlinks")
            elif not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                errors.append(
                    f"{entry}: published skill payloads may contain only regular files "
                    "and directories"
                )
    return errors


def validate_catalog(repo_root: Path) -> Tuple[List[str], int, int]:
    skill_dirs, errors = _catalog_dirs(repo_root / "skills")
    descriptions: Dict[str, str] = {}
    total_chars = 0
    longest = 0

    for skill_dir in skill_dirs:
        source = skill_dir / "SKILL.md"
        try:
            name, description = _metadata(source)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if name != skill_dir.name:
                errors.append(
                    f"{source}: frontmatter name {name!r} does not match "
                    f"directory {skill_dir.name!r}"
                )
            if description != description.strip():
                errors.append(f"{source}: description has leading or trailing whitespace")
            if len(description) > MAX_DESCRIPTION_CHARS:
                errors.append(
                    f"{source}: description is {len(description)} characters; "
                    f"maximum is {MAX_DESCRIPTION_CHARS}"
                )
            fingerprint = _WHITESPACE_RE.sub(" ", description.strip().casefold())
            previous = descriptions.get(fingerprint)
            if previous is not None:
                errors.append(
                    f"{source}: description duplicates the normalized route for {previous}"
                )
            else:
                descriptions[fingerprint] = skill_dir.name
            total_chars += len(description)
            longest = max(longest, len(description))
        errors.extend(_payload_errors(skill_dir))

    return sorted(set(errors)), total_chars, longest


def main() -> int:
    configured = os.environ.get("SKILLS_REPO")
    repo_root = (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parents[1]
    )
    errors, total_chars, longest = validate_catalog(repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Catalog health failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    count = len([path for path in (repo_root / "skills").iterdir() if path.is_dir()])
    print(
        f"Catalog health OK: {count} skills, {total_chars} resident description "
        f"characters, longest {longest}/{MAX_DESCRIPTION_CHARS}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
