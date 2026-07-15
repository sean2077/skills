#!/usr/bin/env python
"""Create and verify agent-scaffold's real symlink projections.

This installed helper is intentionally the only code path that creates Claude
projections.  It never copies when symlinks are unavailable: capability errors
exit 2 before the requested mutation starts.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ContractError(RuntimeError):
    """A host preflight or projection contract failed."""


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def effective_symlink_config(repo: Path) -> tuple[str, str]:
    value = git(repo, "config", "--bool", "--get", "core.symlinks")
    origin = git(repo, "config", "--show-origin", "--get", "core.symlinks")
    return value.stdout.strip().lower(), origin.stdout.strip()


def doctor(repo: Path) -> None:
    repo = repo.resolve()
    if os.environ.get("AGENT_SCAFFOLD_TEST_DENY_SYMLINKS") == "1":
        raise ContractError("symlink capability denied by the test fixture")

    if os.name == "nt":
        value, origin = effective_symlink_config(repo)
        if value != "true":
            source = f" ({origin})" if origin else ""
            raise ContractError(
                "effective git core.symlinks is not true"
                f"{source}; remove a local false override and enable it before installing"
            )

    probe_root = Path(tempfile.mkdtemp(prefix=".agent-scaffold-symlink-", dir=repo.parent))
    file_link = probe_root / "file-link"
    dir_link = probe_root / "dir-link"
    try:
        (probe_root / "target.txt").write_text("ok\n", encoding="utf-8")
        (probe_root / "target-dir").mkdir()
        os.symlink("target.txt", file_link)
        os.symlink("target-dir", dir_link, target_is_directory=True)
        if not file_link.is_symlink() or os.readlink(file_link) != "target.txt":
            raise ContractError("file symlink probe did not produce a real relative symlink")
        if not dir_link.is_symlink() or os.readlink(dir_link) != "target-dir":
            raise ContractError("directory symlink probe did not produce a real relative symlink")
    except OSError as exc:
        hint = ""
        if os.name == "nt":
            hint = (
                "; enable Windows Developer Mode (or run with symlink privilege), "
                "ensure effective core.symlinks=true, then restart Git Bash"
            )
        raise ContractError(f"cannot create real symlinks: {exc}{hint}") from exc
    finally:
        for link in (file_link, dir_link):
            try:
                link.unlink()
            except FileNotFoundError:
                pass
        shutil.rmtree(probe_root, ignore_errors=True)


def within_repo(repo: Path, relative: str) -> Path:
    candidate = repo / relative
    try:
        candidate.absolute().relative_to(repo.absolute())
    except ValueError as exc:
        raise ContractError(f"projection escapes the repository: {relative}") from exc
    return candidate


def trees_identical(left: Path, right: Path) -> bool:
    if left.is_file() and right.is_file():
        return filecmp.cmp(left, right, shallow=False)
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    if any(not filecmp.cmp(left / name, right / name, shallow=False) for name in comparison.common_files):
        return False
    return all(trees_identical(left / name, right / name) for name in comparison.common_dirs)


def safe_migration(link: Path, resolved_target: Path, target: str) -> bool:
    if link.is_file() and not link.is_symlink():
        try:
            if link.read_text(encoding="utf-8").strip() == target:
                return True
        except (OSError, UnicodeError):
            pass
    return trees_identical(link, resolved_target)


def managed_skill_target(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith("../../.agents/skills/")


def validate_destination(
    link: Path,
    resolved_target: Path,
    target: str,
    *,
    replace_managed_link: bool,
) -> str:
    if link.is_symlink():
        current = os.readlink(link)
        if current == target:
            if not link.exists():
                raise ContractError(f"projection is dangling: {link} -> {current}")
            return "present"
        if replace_managed_link and managed_skill_target(current):
            return "replace-link"
        raise ContractError(f"projection conflict: {link} is a symlink to {current!r}, expected {target!r}")
    if not link.exists():
        return "create"
    if safe_migration(link, resolved_target, target):
        return "migrate-copy"
    raise ContractError(
        f"projection conflict: {link} exists and differs from the authoritative source; "
        "move or merge it manually"
    )


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def create_relative_link(link: Path, resolved_target: Path, target: str, action: str) -> bool:
    if action == "present":
        return False
    link.parent.mkdir(parents=True, exist_ok=True)
    temp_link = link.with_name(f".{link.name}.agent-scaffold-link")
    if temp_link.exists() or temp_link.is_symlink():
        remove_existing(temp_link)
    try:
        os.symlink(target, temp_link, target_is_directory=resolved_target.is_dir())
        if not temp_link.is_symlink() or os.readlink(temp_link) != target:
            raise ContractError(f"failed to materialize a real symlink for {link}")
        if link.exists() or link.is_symlink():
            remove_existing(link)
        os.replace(temp_link, link)
    finally:
        if temp_link.exists() or temp_link.is_symlink():
            remove_existing(temp_link)
    if not link.is_symlink() or os.readlink(link) != target or not link.exists():
        raise ContractError(f"projection verification failed after creating {link} -> {target}")
    return True


def ensure_contract(repo: Path) -> None:
    doctor(repo)
    link = within_repo(repo, "CLAUDE.md")
    resolved_target = within_repo(repo, "AGENTS.md")
    if not resolved_target.is_file():
        raise ContractError("cannot link CLAUDE.md: AGENTS.md does not exist")
    action = validate_destination(
        link,
        resolved_target,
        "AGENTS.md",
        replace_managed_link=False,
    )
    changed = create_relative_link(link, resolved_target, "AGENTS.md", action)
    print("CLAUDE.md -> AGENTS.md: " + ("linked" if changed else "already correct"))


def skill_sources(repo: Path) -> list[Path]:
    source = within_repo(repo, ".agents/skills")
    if not source.is_dir():
        raise ContractError("missing authoritative skill directory: .agents/skills")
    return sorted(path for path in source.iterdir() if path.is_dir() and not path.name.startswith("_"))


def sync_skills(repo: Path) -> None:
    doctor(repo)
    sources = skill_sources(repo)
    vendor = within_repo(repo, ".claude/skills")
    planned: list[tuple[Path, Path, str, str]] = []

    for source in sources:
        target = f"../../.agents/skills/{source.name}"
        link = vendor / source.name
        action = validate_destination(
            link,
            source,
            target,
            replace_managed_link=True,
        )
        planned.append((link, source, target, action))

    stale: list[Path] = []
    if vendor.is_dir():
        source_names = {source.name for source in sources}
        for link in vendor.iterdir():
            if not link.is_symlink():
                continue
            target = os.readlink(link)
            if managed_skill_target(target) and (link.name.startswith("_") or link.name not in source_names):
                stale.append(link)

    made = 0
    migrated = 0
    for link in stale:
        link.unlink()
    for link, source, target, action in planned:
        if create_relative_link(link, source, target, action):
            made += 1
            if action == "migrate-copy":
                migrated += 1

    print(
        f"relink: {len(sources)} skills · {made} link(s) (re)created · "
        f"{len(stale)} stale pruned · {migrated} legacy copy/copies migrated"
    )


def tracked_mode(repo: Path, relative: str) -> str | None:
    result = git(repo, "ls-files", "--stage", "--", relative)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split(None, 1)[0]


def verify_link(repo: Path, relative: str, target: str, failures: list[str]) -> None:
    link = within_repo(repo, relative)
    if not link.is_symlink():
        failures.append(f"{relative} is not a real symlink")
        return
    current = os.readlink(link)
    if current != target:
        failures.append(f"{relative} points to {current!r}, expected {target!r}")
    if not link.exists():
        failures.append(f"{relative} is dangling")
    mode = tracked_mode(repo, relative)
    if mode is not None and mode != "120000":
        failures.append(f"tracked {relative} has git mode {mode}, expected 120000")


def verify(repo: Path) -> int:
    doctor(repo)
    failures: list[str] = []
    verify_link(repo, "CLAUDE.md", "AGENTS.md", failures)

    sources = skill_sources(repo)
    source_names = {source.name for source in sources}
    for source in sources:
        verify_link(
            repo,
            f".claude/skills/{source.name}",
            f"../../.agents/skills/{source.name}",
            failures,
        )

    vendor = within_repo(repo, ".claude/skills")
    if vendor.is_dir():
        for link in vendor.iterdir():
            if not link.is_symlink():
                continue
            target = os.readlink(link)
            if managed_skill_target(target) and (link.name.startswith("_") or link.name not in source_names):
                failures.append(f"stale managed skill projection: .claude/skills/{link.name}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"OK: real symlink contract verified ({len(sources)} project skill(s))")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("doctor", "ensure-contract", "sync-skills", "verify"))
    result.add_argument("--repo", required=True, type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        raise ContractError(f"not a git repository root: {repo}")
    if args.command == "doctor":
        doctor(repo)
        value, origin = effective_symlink_config(repo)
        config = f"; effective core.symlinks={value or 'unset'}"
        if origin:
            config += f" ({origin})"
        print(f"OK: file and directory symlink probes passed{config}")
        return 0
    if args.command == "ensure-contract":
        ensure_contract(repo)
        return 0
    if args.command == "sync-skills":
        sync_skills(repo)
        return 0
    return verify(repo)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"symlink-manager: {exc}", file=sys.stderr)
        raise SystemExit(2)
