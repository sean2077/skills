#!/usr/bin/env python3
"""Deterministic core for agent-scaffold.sh.

This helper is internal to agent-scaffold. The Bash entry owns orchestration and
target mutation; this module owns manifest resolution, JSON reconciliation, and
machine-readable read-only reports.
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = Path(__file__).with_name("managed-assets.json")
PROFILES = {"default", "light"}
STRATEGIES = {"copy", "seed", "merge-json", "managed-block"}
MANAGED_HOOK_NAMES = ("trunk_edit_guard", "authority_doc_budget")
CHECK_STATUSES = {
    "adopt",
    "attention",
    "create",
    "fail",
    "merge",
    "pass",
    "present",
    "refresh",
    "skip",
}
REPORT_MODES = {"plan", "doctor", "verify"}
REQUIRED_ASSETS = {
    "contract.agents": ("managed-block", "AGENTS.md"),
    "host.claude-hooks": ("merge-json", ".claude/settings.json"),
    "host.codex-hooks": ("merge-json", ".codex/hooks.json"),
    "runtime.symlink-manager": ("copy", ".agents/symlink-manager.py"),
    "runtime.subagent-generator": ("copy", ".agents/tools/generate-subagents.py"),
}
WORKTREE_START = "<!-- agent-scaffold:worktree:start -->"
WORKTREE_END = "<!-- agent-scaffold:worktree:end -->"
WORKTREE_ONLY = "<!-- agent-scaffold:worktree-only -->"
MANAGED_DIRECTORY_BOUNDARIES = (
    ".agents",
    ".agents/skills",
    ".agents/subagents",
    ".agents/tools",
    ".agents/tools/hooks",
    ".claude",
    ".claude/agents",
    ".claude/skills",
    ".codex",
    ".codex/agents",
)


class CoreError(Exception):
    pass


def _reject_constant(value: str) -> None:
    raise ValueError("non-standard constant {0}".format(value))


def _validate_json_value(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number")
    if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("unpaired Unicode surrogate")
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_json_value(key)
            _validate_json_value(item)


def load_json(path: Path, display_name: Optional[str] = None) -> Any:
    name = display_name or str(path)
    try:
        with path.open(encoding="utf-8") as source:
            data = json.load(source, parse_constant=_reject_constant)
        _validate_json_value(data)
        return data
    except json.JSONDecodeError as exc:
        raise CoreError(
            "{0}: invalid JSON ({1}, line {2}, column {3})".format(
                name, exc.msg, exc.lineno, exc.colno
            )
        )
    except (OSError, UnicodeError) as exc:
        raise CoreError("{0}: cannot read UTF-8 JSON ({1})".format(name, exc))
    except (ValueError, RecursionError) as exc:
        raise CoreError("{0}: invalid JSON ({1})".format(name, exc))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".{0}.agent-scaffold-".format(path.name), dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as destination:
            json.dump(value, destination, indent=2, ensure_ascii=False)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def atomic_replace_file(source: Path, target: Path) -> None:
    """Copy source into a unique target-directory sibling, then replace target."""
    if source.is_symlink() or not source.is_file():
        raise CoreError("atomic source must be a regular file: {0}".format(source))
    if os.path.lexists(str(target)) and (target.is_symlink() or not target.is_file()):
        raise CoreError("atomic target must be missing or a regular file: {0}".format(target))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".{0}.agent-scaffold-".format(target.name),
            dir=str(target.parent),
        )
        temporary = Path(temporary_name)
        try:
            with source.open("rb") as input_file, os.fdopen(descriptor, "wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
                output_file.flush()
                os.fsync(output_file.fileno())
            os.chmod(str(temporary), mode)
            os.replace(str(temporary), str(target))
            try:
                parent_descriptor = os.open(str(target.parent), os.O_RDONLY)
            except OSError:
                parent_descriptor = None
            if parent_descriptor is not None:
                try:
                    os.fsync(parent_descriptor)
                except OSError:
                    pass
                finally:
                    os.close(parent_descriptor)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    except CoreError:
        raise
    except OSError as exc:
        raise CoreError("atomic replace failed for {0}: {1}".format(target, exc))


def _safe_relative(value: Any, field: str, asset_id: str) -> str:
    if not isinstance(value, str) or not value:
        raise CoreError("asset {0}: {1} must be a non-empty string".format(asset_id, field))
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CoreError("asset {0}: {1} must stay relative".format(asset_id, field))
    return value.replace("\\", "/")


def _validate_profiles(value: Any, item_id: str) -> List[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(profile not in PROFILES for profile in value)
        or len(set(value)) != len(value)
    ):
        raise CoreError("{0}: invalid profiles".format(item_id))
    return value


def _validate_stable_id(value: Any, kind: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9.-]*", value):
        raise CoreError("{0} id must be stable lowercase dotted text".format(kind))
    return value


def load_manifest(path: Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise CoreError("managed-assets manifest must use schema_version 1")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CoreError("managed-assets manifest must contain a non-empty assets array")
    seen_ids: Set[str] = set()
    seen_targets: Set[str] = set()
    for item in assets:
        if not isinstance(item, dict):
            raise CoreError("managed-assets entries must be JSON objects")
        asset_id = _validate_stable_id(item.get("id"), "managed asset")
        if asset_id in seen_ids:
            raise CoreError("duplicate managed asset id: {0}".format(asset_id))
        seen_ids.add(asset_id)
        source = _safe_relative(item.get("source"), "source", asset_id)
        target = _safe_relative(item.get("target"), "target", asset_id)
        if target in seen_targets:
            raise CoreError("duplicate managed asset target: {0}".format(target))
        seen_targets.add(target)
        strategy = item.get("strategy")
        if strategy not in STRATEGIES:
            raise CoreError("asset {0}: unknown strategy {1}".format(asset_id, strategy))
        _validate_profiles(item.get("profiles"), "asset {0}".format(asset_id))
        if not isinstance(item.get("executable"), bool):
            raise CoreError("asset {0}: executable must be boolean".format(asset_id))
        if not (SKILL_DIR / source).is_file():
            raise CoreError("asset {0}: source is missing: {1}".format(asset_id, source))

    by_id = {item["id"]: item for item in assets}
    for asset_id, (strategy, target) in REQUIRED_ASSETS.items():
        if asset_id not in by_id:
            raise CoreError("missing required managed asset: {0}".format(asset_id))
        item = by_id[asset_id]
        if item["strategy"] != strategy or item["target"] != target:
            raise CoreError(
                "managed asset {0} must use strategy {1} and target {2}".format(
                    asset_id, strategy, target
                )
            )

    line_invariants = data.get("line_invariants")
    if not isinstance(line_invariants, list) or not line_invariants:
        raise CoreError("managed-assets manifest must contain line_invariants")
    for item in line_invariants:
        if not isinstance(item, dict):
            raise CoreError("line_invariants entries must be JSON objects")
        invariant_id = _validate_stable_id(item.get("id"), "line invariant")
        if invariant_id in seen_ids:
            raise CoreError("duplicate manifest id: {0}".format(invariant_id))
        seen_ids.add(invariant_id)
        _safe_relative(item.get("target"), "target", invariant_id)
        _validate_profiles(item.get("profiles"), "line invariant {0}".format(invariant_id))
        lines = item.get("lines")
        if (
            not isinstance(lines, list)
            or not lines
            or any(
                not isinstance(line, str)
                or not line
                or "\n" in line
                or "\r" in line
                or "\t" in line
                for line in lines
            )
            or len(set(lines)) != len(lines)
        ):
            raise CoreError("line invariant {0}: invalid lines".format(invariant_id))
    return data


def active_assets(manifest: Dict[str, Any], profile: str) -> Iterable[Dict[str, Any]]:
    return (item for item in manifest["assets"] if profile in item["profiles"])


def active_line_invariants(
    manifest: Dict[str, Any], profile: str
) -> Iterable[Dict[str, Any]]:
    return (
        item for item in manifest["line_invariants"] if profile in item["profiles"]
    )


def asset_by_id(manifest: Dict[str, Any], asset_id: str) -> Dict[str, Any]:
    for item in manifest["assets"]:
        if item["id"] == asset_id:
            return item
    raise CoreError("unknown managed asset id: {0}".format(asset_id))


def _case_insensitive_paths(root: Path) -> bool:
    text = str(root).rstrip("/\\")
    start = max(text.rfind("/"), text.rfind("\\")) + 1
    probe: Optional[str] = None
    for index in range(start, len(text)):
        character = text[index]
        if character.isascii() and character.isalpha():
            replacement = character.upper() if character.islower() else character.lower()
            probe = text[:index] + replacement + text[index + 1 :]
            break
    if probe is None:
        return False
    try:
        return os.path.samefile(str(root), probe)
    except OSError:
        return False


def managed_hook_pattern(root: Path) -> re.Pattern:
    flags = re.IGNORECASE if _case_insensitive_paths(root) else 0
    names = "|".join(re.escape(name) for name in MANAGED_HOOK_NAMES)
    return re.compile(
        r"(?:^|[/\s\"\x27;&|()<>])\.agents/tools/hooks/(?:"
        + names
        + r")\.sh(?=$|[\s\"\x27;&|()<>])",
        flags,
    )


def validate_hook_config(path: Path, display_name: str) -> Dict[str, Any]:
    data = load_json(path, display_name)
    if not isinstance(data, dict):
        raise CoreError("{0}: top level must be a JSON object".format(display_name))
    hooks = data.get("hooks")
    if hooks is not None and not isinstance(hooks, dict):
        raise CoreError("{0}: hooks must be a JSON object or null".format(display_name))
    for event in ("PreToolUse", "PostToolUse"):
        groups = (hooks or {}).get(event)
        if groups is None:
            continue
        if not isinstance(groups, list):
            raise CoreError("{0}: hooks.{1} must be an array or null".format(display_name, event))
        for group_index, group in enumerate(groups):
            field = "hooks.{0}[{1}]".format(event, group_index)
            if not isinstance(group, dict):
                raise CoreError("{0}: {1} must be a JSON object".format(display_name, field))
            entries = group.get("hooks")
            if entries is None:
                continue
            if not isinstance(entries, list):
                raise CoreError("{0}: {1}.hooks must be an array or null".format(display_name, field))
            for hook_index, hook in enumerate(entries):
                if not isinstance(hook, dict):
                    raise CoreError(
                        "{0}: {1}.hooks[{2}] must be a JSON object".format(
                            display_name, field, hook_index
                        )
                    )
                if "command" in hook and not isinstance(hook["command"], str):
                    raise CoreError(
                        "{0}: {1}.hooks[{2}].command must be a string".format(
                            display_name, field, hook_index
                        )
                    )
    return data


def hook_tuples(data: Dict[str, Any]) -> Set[Tuple[str, Any, str]]:
    found: Set[Tuple[str, Any, str]] = set()
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups or []:
            if not isinstance(group, dict):
                continue
            matcher = group.get("matcher")
            for hook in group.get("hooks") or []:
                if isinstance(hook, dict) and "command" in hook:
                    found.add((event, matcher, str(hook["command"])))
    return found


def prepare_hooks(source: Path, profile: str) -> Dict[str, Any]:
    data = validate_hook_config(source, str(source))
    disabled = [] if profile == "default" else ["trunk_edit_guard"]
    for event, groups in list((data.get("hooks") or {}).items()):
        kept = []
        for original in groups or []:
            group = dict(original)
            group["hooks"] = [
                hook
                for hook in group.get("hooks", [])
                if not any(name in str(hook.get("command", "")) for name in disabled)
            ]
            if group["hooks"] or any(key not in {"matcher", "hooks"} for key in group):
                kept.append(group)
        data["hooks"][event] = kept
    return data


def merge_hooks(existing: Dict[str, Any], addition: Dict[str, Any], target: Path) -> Dict[str, Any]:
    if not isinstance(existing.get("hooks"), dict):
        existing["hooks"] = {}
    owned = managed_hook_pattern(target)

    def is_managed(command: Any) -> bool:
        return bool(owned.search(str(command or "").replace("\\", "/")))

    def union(current: Sequence[Dict[str, Any]], incoming: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        output = list(current or [])
        seen = {hook.get("command") for hook in output}
        for hook in incoming or []:
            if hook.get("command") not in seen:
                output.append(hook)
                seen.add(hook.get("command"))
        return output

    for event in ("PreToolUse", "PostToolUse"):
        if event not in (addition.get("hooks") or {}):
            continue
        cleaned = []
        for original in existing["hooks"].get(event) or []:
            if not isinstance(original, dict):
                cleaned.append(original)
                continue
            group = dict(original)
            group["hooks"] = [
                hook for hook in group.get("hooks") or [] if not is_managed(hook.get("command", ""))
            ]
            if group["hooks"] or any(key not in {"matcher", "hooks"} for key in group):
                cleaned.append(group)
        for incoming in addition["hooks"].get(event) or []:
            index = next(
                (
                    position
                    for position, current in enumerate(cleaned)
                    if isinstance(current, dict) and current.get("matcher") == incoming.get("matcher")
                ),
                -1,
            )
            if index < 0:
                cleaned.append(incoming)
            else:
                cleaned[index]["hooks"] = union(
                    cleaned[index].get("hooks") or [], incoming.get("hooks") or []
                )
        if cleaned:
            existing["hooks"][event] = cleaned
        else:
            existing["hooks"].pop(event, None)
    return existing


def verify_hooks(existing: Dict[str, Any], expected: Dict[str, Any], target: Path) -> bool:
    actual_tuples = hook_tuples(existing)
    expected_tuples = hook_tuples(expected)
    owned = managed_hook_pattern(target)
    managed_actual = {
        item for item in actual_tuples if owned.search(item[2].replace("\\", "/"))
    }
    return expected_tuples <= actual_tuples and managed_actual <= expected_tuples


def marker_state(path: Path) -> str:
    if not path.is_file():
        return "absent"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CoreError("{0}: cannot read UTF-8 text ({1})".format(path, exc))
    starts = text.count("<!-- agent-scaffold:start")
    ends = text.count("<!-- agent-scaffold:end")
    if starts == 0 and ends == 0:
        return "absent"
    start = text.find("<!-- agent-scaffold:start")
    end = text.find("<!-- agent-scaffold:end", start + 1)
    if starts == 1 and ends == 1 and 0 <= start < end:
        return "valid"
    return "invalid"


def render_agents_template(source: Path, profile: str) -> str:
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CoreError("{0}: cannot read UTF-8 text ({1})".format(source, exc))
    output: List[str] = []
    skip = False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines(True):
        if WORKTREE_START in line:
            skip = profile == "light"
            continue
        if WORKTREE_END in line:
            skip = False
            continue
        if profile == "light" and WORKTREE_ONLY in line:
            continue
        if not skip:
            output.append(re.sub(r"[ \t]*" + re.escape(WORKTREE_ONLY), "", line))
    return "".join(output)


def extract_managed_block(text: str) -> Optional[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    start = normalized.find("<!-- agent-scaffold:start")
    if start < 0:
        return None
    end = normalized.find("<!-- agent-scaffold:end", start)
    if end < 0:
        return None
    line_end = normalized.find("\n", end)
    if line_end < 0:
        line_end = len(normalized)
    else:
        line_end += 1
    return normalized[start:line_end]


def managed_block_matches(path: Path, source: Path, profile: str) -> bool:
    if marker_state(path) != "valid":
        return False
    try:
        actual = extract_managed_block(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return False
    expected = extract_managed_block(render_agents_template(source, profile))
    return actual == expected


def is_target_text_placeholder(path: Path, target: str) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        return path.read_text(encoding="utf-8").strip() == target
    except (OSError, UnicodeError):
        return False


def missing_required_lines(path: Path, lines: Sequence[str]) -> List[str]:
    if not path.is_file() or path.is_symlink():
        return list(lines)
    try:
        present = set(path.read_bytes().splitlines())
    except OSError:
        return list(lines)
    return [line for line in lines if line.encode("utf-8") not in present]


def check_record(
    check_id: str,
    status: str,
    path: Optional[str],
    fix: Optional[str],
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    if not re.fullmatch(r"[a-z][a-z0-9.-]*", check_id):
        raise CoreError("invalid stable check id: {0}".format(check_id))
    if status not in CHECK_STATUSES:
        raise CoreError("unknown check status: {0}".format(status))
    record: Dict[str, Any] = {"id": check_id, "status": status, "path": path, "fix": fix}
    if detail:
        record["detail"] = detail
    return record


def report(mode: str, target: Path, profile: str, checks: List[Dict[str, Any]], apply_mode: Optional[str]) -> Dict[str, Any]:
    if mode not in REPORT_MODES:
        raise CoreError("unknown report mode: {0}".format(mode))
    if profile not in PROFILES:
        raise CoreError("unknown report profile: {0}".format(profile))
    if apply_mode not in {None, "apply", "upgrade"}:
        raise CoreError("unknown apply mode: {0}".format(apply_mode))
    failure_states = {"fail", "attention"}
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "target": str(target),
        "profile": profile,
        "apply_mode": apply_mode,
        "ok": not any(item["status"] in failure_states for item in checks),
        "checks": checks,
    }


def render_report(data: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print("[harness] {0}: {1} (profile: {2})".format(data["mode"], data["target"], data["profile"]))
    for item in data["checks"]:
        location = " {0}".format(item["path"]) if item.get("path") else ""
        print("  [{0}] {1}{2}".format(item["status"], item["id"], location))
        if item.get("detail"):
            print("    {0}".format(item["detail"].strip().replace("\n", "\n    ")))
        if item.get("fix") and item["status"] in {"fail", "attention"}:
            print("    fix: {0}".format(item["fix"]))
    if data.get("apply_mode") and data["ok"]:
        print(
            "[harness] to apply: bash <skill-dir>/agent-scaffold.sh {0} --profile {1}".format(
                data["apply_mode"], data["profile"]
            )
        )
    elif data["mode"] == "plan" and not data["ok"]:
        print("[harness] resolve attention items, then rerun plan")


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def is_current_generated_projection(path: Path) -> bool:
    name = path.stem
    marker = (
        "Generated from .agents/subagents/{0}; do not edit by hand. "
        "Run: python .agents/tools/generate-subagents.py"
    ).format(name)
    try:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (OSError, UnicodeError):
        return False
    if path.suffix == ".toml":
        return text.startswith("# {0}\n".format(marker))
    if path.suffix == ".md":
        return re.match(
            r"\A---\n[\s\S]*?\n---\n\n<!-- {0} -->\n".format(re.escape(marker)),
            text,
        ) is not None
    return False


def host_agent_inventory(target: Path) -> List[str]:
    inventory: List[str] = []
    for relative in (Path(".claude/agents"), Path(".codex/agents")):
        root = target / relative
        if root.is_symlink() or not root.is_dir():
            continue
        inventory.extend(path.relative_to(target).as_posix() for path in sorted(root.iterdir()))
    return inventory


def host_agent_candidates(target: Path) -> List[str]:
    candidates: List[str] = []
    for relative, suffix in ((Path(".claude/agents"), ".md"), (Path(".codex/agents"), ".toml")):
        root = target / relative
        if root.is_symlink() or not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.is_file() and path.suffix == suffix and not is_current_generated_projection(path):
                candidates.append(path.relative_to(target).as_posix())
    return candidates


def build_plan(target: Path, profile: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    boundary_conflict = False
    for relative in MANAGED_DIRECTORY_BOUNDARIES:
        directory = target / relative
        if os.path.lexists(str(directory)) and (
            directory.is_symlink() or not directory.is_dir()
        ):
            boundary_conflict = True
            checks.append(
                check_record(
                    "boundary.{0}".format(relative.lstrip(".").replace("/", "-")),
                    "attention",
                    relative,
                    "replace the managed path boundary with a real directory",
                    "managed directory must not be a symlink or non-directory path",
                )
            )
    if boundary_conflict:
        return report("plan", target, profile, checks, "apply")
    contract = asset_by_id(manifest, "contract.agents")
    agents = target / contract["target"]
    contract_source = SKILL_DIR / contract["source"]
    claude = target / "CLAUDE.md"
    if os.path.lexists(str(agents)) and (agents.is_symlink() or not agents.is_file()):
        checks.append(
            check_record(
                "contract.agents",
                "attention",
                contract["target"],
                "replace the conflict with a regular authored AGENTS.md",
            )
        )
    else:
        state = marker_state(agents)
        if state == "invalid":
            raise CoreError(
                "AGENTS.md has malformed agent-scaffold markers "
                "(expected exactly one ordered start/end pair)"
            )
        if not agents.exists() and claude.is_file() and not claude.is_symlink():
            checks.append(
                check_record(
                    "contract.agents",
                    "adopt",
                    contract["target"],
                    None,
                    "adopt prose from CLAUDE.md",
                )
            )
        elif not agents.exists():
            checks.append(check_record("contract.agents", "create", contract["target"], None))
        elif state == "valid" and managed_block_matches(agents, contract_source, profile):
            checks.append(check_record("contract.agents", "present", contract["target"], None))
        elif state == "valid":
            checks.append(check_record("contract.agents", "refresh", contract["target"], None))
        else:
            checks.append(check_record("contract.agents", "merge", contract["target"], None))

    if claude.is_symlink():
        try:
            destination = os.readlink(str(claude))
        except OSError:
            destination = ""
        if destination == contract["target"]:
            checks.append(check_record("contract.claude-link", "present", "CLAUDE.md", None))
        else:
            checks.append(
                check_record(
                    "contract.claude-link",
                    "attention",
                    "CLAUDE.md",
                    "point the symlink at {0}".format(contract["target"]),
                )
            )
    elif os.path.lexists(str(claude)) and not claude.is_file():
        checks.append(
            check_record(
                "contract.claude-link",
                "attention",
                "CLAUDE.md",
                "replace the conflict with an authored file or the managed symlink",
            )
        )
    elif claude.exists() and agents.exists() and is_target_text_placeholder(
        claude, contract["target"]
    ):
        checks.append(
            check_record(
                "contract.claude-link",
                "refresh",
                "CLAUDE.md",
                None,
                "materialize the tracked target-text placeholder as a real symlink",
            )
        )
    elif claude.exists() and agents.exists():
        checks.append(
            check_record(
                "contract.claude-link",
                "attention",
                "CLAUDE.md",
                "merge authored prose into {0}".format(contract["target"]),
            )
        )
    elif claude.exists():
        checks.append(check_record("contract.claude-link", "adopt", "CLAUDE.md", None))
    else:
        checks.append(check_record("contract.claude-link", "create", "CLAUDE.md", None))

    apply_mode = "apply"
    for item in active_assets(manifest, profile):
        if item["strategy"] != "copy":
            continue
        source = SKILL_DIR / item["source"]
        installed = target / item["target"]
        if not os.path.lexists(str(installed)):
            status = "create"
            fix = None
        elif installed.is_symlink() or not installed.is_file():
            status = "attention"
            fix = "replace the conflict with a regular managed file"
        elif _same_file(source, installed):
            status = "present"
            fix = None
        else:
            status = "refresh"
            fix = None
            apply_mode = "upgrade"
        checks.append(check_record(item["id"], status, item["target"], fix))

    for item in active_assets(manifest, profile):
        if item["strategy"] != "merge-json":
            continue
        existing = target / item["target"]
        if not os.path.lexists(str(existing)):
            checks.append(check_record(item["id"], "create", item["target"], None))
        elif existing.is_symlink():
            checks.append(
                check_record(
                    item["id"],
                    "attention",
                    item["target"],
                    "replace the conflict with a regular JSON file",
                    "{0}: symlinked hook configs are unsupported".format(item["target"]),
                )
            )
        elif not existing.is_file():
            checks.append(
                check_record(
                    item["id"],
                    "attention",
                    item["target"],
                    "replace the conflict with a regular JSON file",
                )
            )
        else:
            try:
                validate_hook_config(existing, item["target"])
            except CoreError as exc:
                checks.append(
                    check_record(
                        item["id"],
                        "attention",
                        item["target"],
                        "repair the hook JSON before mutation",
                        str(exc),
                    )
                )
            else:
                checks.append(check_record(item["id"], "merge", item["target"], None))

    for item in active_line_invariants(manifest, profile):
        installed = target / item["target"]
        if os.path.lexists(str(installed)) and (installed.is_symlink() or not installed.is_file()):
            checks.append(
                check_record(
                    item["id"],
                    "attention",
                    item["target"],
                    "replace the conflict with a regular text file",
                )
            )
            continue
        missing = missing_required_lines(installed, item["lines"])
        checks.append(
            check_record(
                item["id"],
                "merge" if missing else "present",
                item["target"],
                None,
                "add: " + ", ".join(missing) if missing else None,
            )
        )

    checks.append(
        check_record(
            "profile.worktree",
            "present" if profile == "default" else "skip",
            None,
            None,
            "worktree governance enabled" if profile == "default" else "worktree governance omitted",
        )
    )

    manager = SKILL_DIR / asset_by_id(manifest, "runtime.symlink-manager")["source"]
    code, output = run_tool(
        [sys.executable, str(manager), "preflight-install", "--repo", str(target)]
    )
    checks.append(
        check_record(
            "contract.symlink-shape",
            "present" if code == 0 else "attention",
            str(target),
            None if code == 0 else "resolve the reported contract or skill-projection conflict",
            output or None,
        )
    )

    generator = SKILL_DIR / asset_by_id(manifest, "runtime.subagent-generator")["source"]
    environment = os.environ.copy()
    environment["AGENT_SCAFFOLD_PREFLIGHT_REPO"] = str(target)
    code, output = run_tool(
        [sys.executable, str(generator), "--preflight-import"], environment=environment
    )
    if code != 0:
        inventory = host_agent_inventory(target)
        detail = output or "subagent import preflight failed"
        if inventory:
            detail += "\nhost inventory: " + ", ".join(inventory)
        checks.append(
            check_record(
                "subagents.import",
                "attention",
                ".agents/subagents",
                "resolve the reported host-agent ownership or parse conflict",
                detail,
            )
        )
    else:
        candidates = host_agent_candidates(target)
        checks.append(
            check_record(
                "subagents.import",
                "adopt" if candidates else "present",
                ".agents/subagents",
                None,
                "adopt " + ", ".join(candidates) if candidates else "no hand-authored host agents",
            )
        )
    return report("plan", target, profile, checks, apply_mode)


def run_tool(
    command: Sequence[str], environment: Optional[Dict[str, str]] = None
) -> Tuple[int, str]:
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
    )
    return completed.returncode, completed.stdout.strip()


def build_doctor(target: Path, profile: str, symlink_manager: Path) -> Dict[str, Any]:
    checks = [
        check_record("prerequisite.git-repository", "pass", str(target), None),
        check_record("prerequisite.python", "pass", sys.executable, None),
    ]
    code, output = run_tool([sys.executable, str(symlink_manager), "doctor", "--repo", str(target)])
    checks.append(
        check_record(
            "prerequisite.real-symlinks",
            "pass" if code == 0 else "fail",
            str(target),
            None if code == 0 else "enable real file and directory symlink support, then rerun doctor",
            output or None,
        )
    )
    return report("doctor", target, profile, checks, None)


def build_verify(
    target: Path,
    profile: str,
    manifest: Dict[str, Any],
    symlink_manager: Path,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    for relative in MANAGED_DIRECTORY_BOUNDARIES:
        directory = target / relative
        if os.path.lexists(str(directory)) and (
            directory.is_symlink() or not directory.is_dir()
        ):
            checks.append(
                check_record(
                    "boundary.{0}".format(relative.lstrip(".").replace("/", "-")),
                    "fail",
                    relative,
                    "replace the managed path boundary with a real directory",
                    "managed directory must not be a symlink or non-directory path",
                )
            )
    if checks:
        return report("verify", target, profile, checks, None)
    for item in active_assets(manifest, profile):
        if item["strategy"] != "copy":
            continue
        installed = target / item["target"]
        source = SKILL_DIR / item["source"]
        if installed.is_symlink() or not installed.is_file():
            checks.append(check_record(item["id"], "fail", item["target"], "run agent-scaffold apply"))
        elif not _same_file(source, installed):
            checks.append(check_record(item["id"], "fail", item["target"], "run agent-scaffold upgrade"))
        else:
            checks.append(check_record(item["id"], "pass", item["target"], None))

    for item in active_assets(manifest, profile):
        if item["strategy"] != "merge-json":
            continue
        existing_path = target / item["target"]
        try:
            existing = validate_hook_config(existing_path, item["target"])
            expected = prepare_hooks(SKILL_DIR / item["source"], profile)
            matches = verify_hooks(existing, expected, target)
        except CoreError:
            matches = False
        checks.append(
            check_record(
                item["id"],
                "pass" if matches else "fail",
                item["target"],
                None if matches else "run agent-scaffold apply after resolving invalid JSON",
            )
        )

    claude = target / "CLAUDE.md"
    contract = asset_by_id(manifest, "contract.agents")
    try:
        claude_ok = claude.is_symlink() and os.readlink(str(claude)) == contract["target"]
    except OSError:
        claude_ok = False
    checks.append(
        check_record(
            "contract.claude-link",
            "pass" if claude_ok else "fail",
            "CLAUDE.md",
            None if claude_ok else "run agent-scaffold apply after resolving authored-file conflicts",
        )
    )

    code, output = run_tool([sys.executable, str(symlink_manager), "verify", "--repo", str(target)])
    checks.append(
        check_record(
            "contract.real-symlinks",
            "pass" if code == 0 else "fail",
            str(target),
            None if code == 0 else "repair real symlink projections",
            output or None,
        )
    )

    agents = target / contract["target"]
    state = marker_state(agents)
    checks.append(
        check_record(
            "contract.agents-markers",
            "pass" if state == "valid" else "fail",
            contract["target"],
            None if state == "valid" else "run agent-scaffold apply after repairing marker conflicts",
        )
    )
    content_ok = managed_block_matches(
        agents, SKILL_DIR / contract["source"], profile
    )
    checks.append(
        check_record(
            "contract.agents-content",
            "pass" if content_ok else "fail",
            contract["target"],
            None if content_ok else "run agent-scaffold apply to refresh the managed block",
        )
    )
    managed = ""
    if state == "valid":
        text = agents.read_text(encoding="utf-8")
        start = text.index("<!-- agent-scaffold:start")
        end = text.index("<!-- agent-scaffold:end", start)
        managed = text[start:end]
    policy_present = "### Worktree-per-change (hard rule)" in managed
    policy_ok = policy_present if profile == "default" else not policy_present
    checks.append(
        check_record(
            "profile.worktree-policy",
            "pass" if policy_ok else "fail",
            contract["target"],
            None if policy_ok else "run agent-scaffold apply with the intended --profile",
        )
    )

    for item in active_line_invariants(manifest, profile):
        missing = missing_required_lines(target / item["target"], item["lines"])
        checks.append(
            check_record(
                item["id"],
                "fail" if missing else "pass",
                item["target"],
                "run agent-scaffold apply" if missing else None,
                "missing: " + ", ".join(missing) if missing else None,
            )
        )

    generator_item = asset_by_id(manifest, "runtime.subagent-generator")
    generator = target / generator_item["target"]
    if generator.is_file() and not generator.is_symlink():
        code, output = run_tool([sys.executable, str(generator), "--check"])
        generator_ok = code == 0
    else:
        generator_ok = False
        output = "generator missing"
    checks.append(
        check_record(
            "subagents.projections",
            "pass" if generator_ok else "fail",
            generator_item["target"],
            None if generator_ok else "run python .agents/tools/generate-subagents.py",
            output or None,
        )
    )
    return report("verify", target, profile, checks, None)


def command_assets(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    if args.assets_command == "validate":
        return 0
    if args.assets_command == "get":
        item = asset_by_id(manifest, args.id)
        value = item[args.field]
        if isinstance(value, bool):
            print("1" if value else "0")
        else:
            print(value)
        return 0
    strategies = set(args.strategy or STRATEGIES)
    for item in active_assets(manifest, args.profile):
        if item["strategy"] not in strategies:
            continue
        print(
            "\t".join(
                [
                    item["id"],
                    item["source"],
                    item["target"],
                    item["strategy"],
                    "1" if item["executable"] else "0",
                ]
            )
        )
    return 0


def command_lines(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    for item in active_line_invariants(manifest, args.profile):
        for line in item["lines"]:
            print("\t".join([item["id"], item["target"], line]))
    return 0


def command_hooks(args: argparse.Namespace) -> int:
    if args.hooks_command == "validate":
        validate_hook_config(Path(args.existing), args.name)
        return 0
    if args.hooks_command == "prepare":
        write_json(Path(args.output), prepare_hooks(Path(args.source), args.profile))
        return 0
    if args.hooks_command == "merge":
        existing_path = Path(args.existing) if args.existing else None
        existing = validate_hook_config(existing_path, str(existing_path)) if existing_path and existing_path.exists() else {}
        addition = validate_hook_config(Path(args.addition), args.addition)
        write_json(Path(args.output), merge_hooks(existing, addition, Path(args.target)))
        return 0
    if args.hooks_command == "verify":
        existing = validate_hook_config(Path(args.existing), args.existing)
        expected = validate_hook_config(Path(args.expected), args.expected)
        return 0 if verify_hooks(existing, expected, Path(args.target)) else 1
    raise CoreError("unknown hooks command")


def command_agents(args: argparse.Namespace) -> int:
    if args.agents_command == "render":
        rendered = render_agents_template(Path(args.source), args.profile)
        sys.stdout.buffer.write(rendered.encode("utf-8"))
        return 0
    state = marker_state(Path(args.file))
    if state == "invalid":
        raise CoreError("AGENTS.md has malformed agent-scaffold markers (expected one ordered pair)")
    return 0


def command_files(args: argparse.Namespace) -> int:
    if args.files_command == "atomic-replace":
        atomic_replace_file(Path(args.source), Path(args.target))
        return 0
    raise CoreError("unknown files command")


def command_preflight(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    manifest = load_manifest(Path(args.manifest))
    data = build_plan(target, args.profile, manifest)
    if not data["ok"]:
        render_report(data, False)
        raise CoreError("preflight has attention items; resolve them before mutation")
    if args.mode == "apply" and data["apply_mode"] == "upgrade":
        raise CoreError(
            "managed runtime drift requires upgrade; run plan, then agent-scaffold.sh upgrade"
        )
    return 0


def command_report(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    manifest = load_manifest(Path(args.manifest))
    manager_item = asset_by_id(manifest, "runtime.symlink-manager")
    manager = SKILL_DIR / manager_item["source"]
    if args.report_command == "plan":
        data = build_plan(target, args.profile, manifest)
    elif args.report_command == "doctor":
        data = build_doctor(target, args.profile, manager)
    elif args.report_command == "verify":
        data = build_verify(target, args.profile, manifest, manager)
    else:
        raise CoreError("unknown report command")
    render_report(data, args.json)
    if args.report_command == "plan":
        return 0
    return 0 if data["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Internal deterministic core for agent-scaffold")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    subparsers = parser.add_subparsers(dest="command", required=True)

    assets = subparsers.add_parser("assets")
    assets_sub = assets.add_subparsers(dest="assets_command", required=True)
    assets_sub.add_parser("validate")
    assets_list = assets_sub.add_parser("list")
    assets_list.add_argument("--profile", choices=sorted(PROFILES), required=True)
    assets_list.add_argument("--strategy", action="append", choices=sorted(STRATEGIES))
    assets_get = assets_sub.add_parser("get")
    assets_get.add_argument("--id", required=True)
    assets_get.add_argument("--field", choices=["source", "target", "strategy", "executable"], required=True)

    lines = subparsers.add_parser("lines")
    lines.add_argument("--profile", choices=sorted(PROFILES), required=True)

    hooks = subparsers.add_parser("hooks")
    hooks_sub = hooks.add_subparsers(dest="hooks_command", required=True)
    hooks_validate = hooks_sub.add_parser("validate")
    hooks_validate.add_argument("--existing", required=True)
    hooks_validate.add_argument("--name", required=True)
    hooks_prepare = hooks_sub.add_parser("prepare")
    hooks_prepare.add_argument("--source", required=True)
    hooks_prepare.add_argument("--output", required=True)
    hooks_prepare.add_argument("--profile", choices=sorted(PROFILES), required=True)
    hooks_merge = hooks_sub.add_parser("merge")
    hooks_merge.add_argument("--existing")
    hooks_merge.add_argument("--addition", required=True)
    hooks_merge.add_argument("--output", required=True)
    hooks_merge.add_argument("--target", required=True)
    hooks_verify = hooks_sub.add_parser("verify")
    hooks_verify.add_argument("--existing", required=True)
    hooks_verify.add_argument("--expected", required=True)
    hooks_verify.add_argument("--target", required=True)

    agents = subparsers.add_parser("agents")
    agents_sub = agents.add_subparsers(dest="agents_command", required=True)
    agents_validate = agents_sub.add_parser("validate-markers")
    agents_validate.add_argument("--file", required=True)
    agents_render = agents_sub.add_parser("render")
    agents_render.add_argument("--source", required=True)
    agents_render.add_argument("--profile", choices=sorted(PROFILES), required=True)

    files = subparsers.add_parser("files")
    files_sub = files.add_subparsers(dest="files_command", required=True)
    files_replace = files_sub.add_parser("atomic-replace")
    files_replace.add_argument("--source", required=True)
    files_replace.add_argument("--target", required=True)

    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--target", required=True)
    preflight.add_argument("--profile", choices=sorted(PROFILES), required=True)
    preflight.add_argument("--mode", choices=("apply", "upgrade"), required=True)

    report_parser = subparsers.add_parser("report")
    report_sub = report_parser.add_subparsers(dest="report_command", required=True)
    for name in ("plan", "doctor", "verify"):
        report_mode = report_sub.add_parser(name)
        report_mode.add_argument("--target", required=True)
        report_mode.add_argument("--profile", choices=sorted(PROFILES), required=True)
        report_mode.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "assets":
            return command_assets(args)
        if args.command == "lines":
            return command_lines(args)
        if args.command == "hooks":
            return command_hooks(args)
        if args.command == "agents":
            return command_agents(args)
        if args.command == "files":
            return command_files(args)
        if args.command == "preflight":
            return command_preflight(args)
        if args.command == "report":
            return command_report(args)
        raise CoreError("unknown command")
    except CoreError as exc:
        print("[harness] ABORT: {0}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
