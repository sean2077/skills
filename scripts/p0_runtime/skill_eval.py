from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from .common import (
    HarnessError,
    SCHEMA_VERSION,
    canonical_json,
    changed_paths,
    copy_tree_no_links,
    digest_json,
    discover_git_context,
    ensure_relative_path,
    match_any,
    read_json,
    repository_snapshot,
    run_git,
    safe_child,
    snapshot_digest,
    tree_snapshot,
    utc_now,
    validate_identifier,
    write_json_atomic,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DATA = 3
EXIT_ADAPTER = 20
EXIT_VERIFIER = 21
EXIT_GATE = 30
CONTRACT = "agent-skill-eval/v1"
CASE_KINDS = {"positive", "negative", "confusable"}
METRIC_KEYS = ("input_tokens", "output_tokens", "tool_calls", "wall_time_seconds", "interventions")
FULL_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class ProtocolFailure(HarnessError):
    pass


def _need_dict(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise HarnessError("%s must be an object" % label, code=EXIT_DATA)
    return dict(value)


def _need_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise HarnessError("%s must be an array" % label, code=EXIT_DATA)
    return list(value)


def _need_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise HarnessError("%s must be a boolean" % label, code=EXIT_DATA)
    return value


def _need_string(value: Any, label: str, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise HarnessError("%s must be a%s string" % (label, " non-empty" if nonempty else ""), code=EXIT_DATA)
    return value


def _need_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HarnessError("%s must be a number" % label, code=EXIT_DATA)
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise HarnessError("%s must be finite and non-negative" % label, code=EXIT_DATA)
    return result


def _validate_command(spec: Any, label: str) -> Dict[str, Any]:
    obj = _need_dict(spec, label)
    command = _need_list(obj.get("command"), "%s.command" % label)
    if not command or not all(isinstance(item, str) and item for item in command):
        raise HarnessError("%s.command must contain non-empty strings" % label, code=EXIT_DATA)
    timeout = _need_number(obj.get("timeout_seconds", 60), "%s.timeout_seconds" % label)
    if timeout <= 0 or timeout > 3600:
        raise HarnessError("%s.timeout_seconds must be in (0, 3600]" % label, code=EXIT_DATA)
    max_output = obj.get("max_output_bytes", 1024 * 1024)
    if isinstance(max_output, bool) or not isinstance(max_output, int) or max_output < 1024 or max_output > 64 * 1024 * 1024:
        raise HarnessError("%s.max_output_bytes must be 1024..67108864" % label, code=EXIT_DATA)
    env = obj.get("env", {})
    env_obj = _need_dict(env, "%s.env" % label)
    clean_env: Dict[str, str] = {}
    for key, value in env_obj.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise HarnessError("%s.env contains a non-portable key" % label, code=EXIT_DATA)
        if any(secret in key.upper() for secret in ("TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL")):
            raise HarnessError("%s.env may not inject secret-like variables: %s" % (label, key), code=EXIT_DATA)
        if not isinstance(value, str) or "\x00" in value:
            raise HarnessError("%s.env.%s must be a string" % (label, key), code=EXIT_DATA)
        clean_env[key] = value
    return {
        "command": command,
        "timeout_seconds": timeout,
        "max_output_bytes": max_output,
        "env": clean_env,
    }


def validate_manifest(raw: Any, repo_root: Path) -> Dict[str, Any]:
    data = _need_dict(raw, "manifest")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise HarnessError("unsupported manifest schema_version", code=EXIT_DATA)
    suite_id = validate_identifier(_need_string(data.get("suite_id"), "suite_id"), "suite_id")
    fixture_rel = ensure_relative_path(_need_string(data.get("fixture"), "fixture"), "fixture")
    fixture = safe_child(repo_root, fixture_rel, "fixture", must_exist=True)
    if fixture.is_symlink() or not fixture.is_dir():
        raise HarnessError("fixture must be a real directory, not a symlink", code=EXIT_DATA)
    skill_rel = ensure_relative_path(_need_string(data.get("skill_path"), "skill_path"), "skill_path")
    skill_path = safe_child(repo_root, skill_rel, "skill_path", must_exist=True)
    if skill_path.is_symlink() or not skill_path.is_dir():
        raise HarnessError("skill_path must be a real directory, not a symlink", code=EXIT_DATA)
    adapter = _validate_command(data.get("adapter"), "adapter")
    verifier = _validate_command(data.get("verifier"), "verifier")
    cases_raw = _need_list(data.get("cases"), "cases")
    if not cases_raw:
        raise HarnessError("cases must not be empty", code=EXIT_DATA)
    seen = set()
    cases: List[Dict[str, Any]] = []
    for index, item in enumerate(cases_raw):
        case = _need_dict(item, "cases[%d]" % index)
        case_id = validate_identifier(_need_string(case.get("id"), "case.id"), "case id")
        if case_id in seen:
            raise HarnessError("duplicate case id: %s" % case_id, code=EXIT_DATA)
        seen.add(case_id)
        kind = _need_string(case.get("kind"), "case.kind")
        if kind not in CASE_KINDS:
            raise HarnessError("case.kind must be positive, negative, or confusable", code=EXIT_DATA)
        prompt = _need_string(case.get("prompt"), "case.prompt")
        expected_selected = case.get("expected_selected", kind == "positive")
        expected_selected = _need_bool(expected_selected, "case.expected_selected")
        if kind in ("negative", "confusable") and expected_selected:
            raise HarnessError("negative/confusable cases cannot expect selection", code=EXIT_DATA)
        metadata = case.get("metadata", {})
        metadata = _need_dict(metadata, "case.metadata")
        forbidden = _secret_like_paths(metadata)
        if forbidden:
            raise HarnessError("case.metadata contains secret-like keys: %s" % ", ".join(forbidden[:8]), code=EXIT_DATA)
        if len(canonical_json(metadata)) > 256 * 1024:
            raise HarnessError("case.metadata exceeds 256 KiB", code=EXIT_DATA)
        cases.append(
            {
                "id": case_id,
                "kind": kind,
                "prompt": prompt,
                "expected_selected": expected_selected,
                "metadata": metadata,
            }
        )
    scope = _need_dict(data.get("scope", {}), "scope")
    allow = _need_list(scope.get("allow", ["**"]), "scope.allow")
    deny = _need_list(scope.get("deny", []), "scope.deny")
    for label, values in (("scope.allow", allow), ("scope.deny", deny)):
        if not all(isinstance(value, str) for value in values):
            raise HarnessError("%s must contain strings" % label, code=EXIT_DATA)
        for value in values:
            ensure_relative_path(value, label=label, allow_glob=True, allow_git=(label == "scope.deny"))
    budgets = _validate_budgets(data.get("budgets", {}))
    revision = data.get("repository_revision")
    if revision is not None:
        revision = _need_string(revision, "repository_revision")
    return {
        "schema_version": SCHEMA_VERSION,
        "suite_id": suite_id,
        "fixture": fixture_rel,
        "skill_path": skill_rel,
        "adapter": adapter,
        "verifier": verifier,
        "cases": cases,
        "scope": {"allow": allow, "deny": deny},
        "budgets": budgets,
        "repository_revision": revision,
    }


def _validate_budgets(raw: Any) -> Dict[str, Any]:
    budgets = _need_dict(raw, "budgets")
    absolute_raw = _need_dict(budgets.get("absolute", {}), "budgets.absolute")
    relative_raw = _need_dict(budgets.get("relative", {}), "budgets.relative")
    absolute: Dict[str, float] = {}
    for key, value in absolute_raw.items():
        if key not in METRIC_KEYS:
            raise HarnessError("unsupported absolute metric: %s" % key, code=EXIT_DATA)
        absolute[key] = _need_number(value, "budgets.absolute.%s" % key)
    relative: Dict[str, Dict[str, float]] = {}
    for key, value in relative_raw.items():
        if key not in METRIC_KEYS:
            raise HarnessError("unsupported relative metric: %s" % key, code=EXIT_DATA)
        rule = _need_dict(value, "budgets.relative.%s" % key)
        ratio = _need_number(rule.get("max_ratio", 1.0), "budgets.relative.%s.max_ratio" % key)
        additive = _need_number(rule.get("max_additive", 0.0), "budgets.relative.%s.max_additive" % key)
        relative[key] = {"max_ratio": ratio, "max_additive": additive}
    return {"absolute": absolute, "relative": relative}


def _resolve_revision(repo_root: Path, requested: Optional[str]) -> str:
    revision = requested or "HEAD"
    result = run_git(["rev-parse", "--verify", "%s^{commit}" % revision], repo_root)
    full = result.stdout.strip()
    if not full or any(ch not in "0123456789abcdef" for ch in full.lower()):
        raise HarnessError("could not resolve repository revision", code=EXIT_DATA)
    return full


@contextmanager
def _materialized_revision(source_root: Path, revision: str) -> Iterator[Path]:
    """Yield a clean detached worktree at exactly ``revision``.

    Evaluation commands are allowed to read repository-owned adapters and skill
    payloads, but baseline/treatment must not accidentally consume dirty files
    from the caller's working tree. A detached worktree gives both modes one
    immutable, content-addressed repository view while preserving standalone
    operation with only Git and the Python standard library.
    """

    temp_root = Path(tempfile.mkdtemp(prefix="skill-eval-revision-"))
    checkout = temp_root / "repository"
    registered = False
    try:
        run_git(
            ["worktree", "add", "--detach", str(checkout), revision],
            source_root,
            timeout=120.0,
        )
        registered = True
        yield checkout.resolve(strict=True)
    finally:
        if registered:
            try:
                result = run_git(
                    ["worktree", "remove", "--force", str(checkout)],
                    source_root,
                    check=False,
                    timeout=120.0,
                )
                if result.returncode != 0:
                    shutil.rmtree(str(checkout), ignore_errors=True)
            except HarnessError:
                shutil.rmtree(str(checkout), ignore_errors=True)
            try:
                run_git(["worktree", "prune"], source_root, check=False, timeout=30.0)
            except HarnessError:
                pass
        shutil.rmtree(str(temp_root), ignore_errors=True)


def _expand_command(command: Sequence[str], repo_root: Path, workspace: Path, mode: str, case_id: str) -> List[str]:
    replacements = {
        "{python}": sys.executable,
        "{repo}": str(repo_root),
        "{workspace}": str(workspace),
        "{mode}": mode,
        "{case_id}": case_id,
    }
    expanded: List[str] = []
    for item in command:
        value = item
        for marker, replacement in replacements.items():
            value = value.replace(marker, replacement)
        if "{" in value or "}" in value:
            raise HarnessError("unsupported command placeholder: %s" % item, code=EXIT_DATA)
        if "\x00" in value:
            raise HarnessError("command argument contains NUL", code=EXIT_DATA)
        expanded.append(value)
    executable = expanded[0]
    if executable.startswith(".") or "/" in executable or "\\" in executable:
        path = Path(executable)
        if not path.is_absolute():
            path = repo_root / path
        path = path.resolve(strict=False)
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            # sys.executable and explicitly absolute system tools are allowed only via placeholders.
            if os.path.normcase(str(path)) != os.path.normcase(str(Path(sys.executable).resolve())):
                raise HarnessError("command executable escapes repository: %s" % executable, code=EXIT_DATA)
        expanded[0] = str(path)
    allowed_roots = (repo_root.resolve(), workspace.resolve())
    for index, value in enumerate(expanded[1:], 1):
        if ".." in PurePosixPath(value.replace("\\", "/")).parts:
            raise HarnessError("command argument contains parent traversal: %s" % value, code=EXIT_DATA)
        candidate = Path(value)
        if not candidate.is_absolute():
            continue
        resolved = candidate.resolve(strict=False)
        if os.path.normcase(str(resolved)) == os.path.normcase(str(Path(sys.executable).resolve())):
            continue
        allowed = False
        for root in allowed_roots:
            try:
                resolved.relative_to(root)
                allowed = True
                break
            except ValueError:
                pass
        if not allowed:
            raise HarnessError("absolute command argument escapes repository/workspace: %s" % value, code=EXIT_DATA)
        expanded[index] = str(resolved)
    return expanded


def _minimal_env(extra: Mapping[str, str]) -> Dict[str, str]:
    allowed = (
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TMP",
        "TEMP",
        "HOME",
        "USERPROFILE",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
    )
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if os.name != "nt" and not any(key in env for key in ("LC_ALL", "LC_CTYPE", "LANG")):
        # C.UTF-8 is not guaranteed on macOS. Python's UTF-8 mode supplies the
        # encoding contract; plain C is the most portable fallback locale.
        env["LC_ALL"] = "C"
    env.update(extra)
    return env


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP alone does not terminate descendants. Use
        # the Windows-native tree kill, then fall back to the direct process.
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def run_protocol_process(
    spec: Mapping[str, Any],
    request: Mapping[str, Any],
    repo_root: Path,
    workspace: Path,
    mode: str,
    case_id: str,
    label: str,
    failure_code: int,
) -> Tuple[Dict[str, Any], float]:
    command = _expand_command(spec["command"], repo_root, workspace, mode, case_id)
    timeout = float(spec["timeout_seconds"])
    max_output = int(spec["max_output_bytes"])
    with tempfile.TemporaryDirectory(prefix="skill-eval-protocol-") as temp:
        temp_path = Path(temp)
        stdin_path = temp_path / "stdin.json"
        stdout_path = temp_path / "stdout.json"
        stderr_path = temp_path / "stderr.txt"
        stdin_path.write_bytes(canonical_json(request) + b"\n")
        started = time.monotonic()
        creationflags = 0
        popen_kwargs: Dict[str, Any] = {}
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True
        with stdin_path.open("rb") as stdin_handle, stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(workspace),
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    env=_minimal_env(spec.get("env", {})),
                    shell=False,
                    creationflags=creationflags,
                    **popen_kwargs,
                )
            except OSError as exc:
                raise ProtocolFailure("%s failed to start: %s" % (label, exc), code=failure_code) from exc
            reason: Optional[str] = None
            while process.poll() is None:
                elapsed = time.monotonic() - started
                try:
                    output_size = stdout_path.stat().st_size + stderr_path.stat().st_size
                except OSError:
                    output_size = 0
                if output_size > max_output:
                    reason = "%s output exceeded %d bytes" % (label, max_output)
                    _terminate_process(process)
                    break
                if elapsed > timeout:
                    reason = "%s timed out after %.3f seconds" % (label, timeout)
                    _terminate_process(process)
                    break
                time.sleep(0.02)
            returncode = process.poll()
        elapsed = time.monotonic() - started
        stdout = stdout_path.read_bytes()
        stderr = stderr_path.read_bytes()
        if len(stdout) + len(stderr) > max_output:
            raise ProtocolFailure("%s output exceeded %d bytes" % (label, max_output), code=failure_code)
        if reason:
            raise ProtocolFailure(reason, code=failure_code)
        if returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace")[:4096]
            raise ProtocolFailure(
                "%s exited with %s: %s" % (label, returncode, stderr_text.strip()),
                code=failure_code,
                details={"returncode": returncode},
            )
        try:
            text = stdout.decode("utf-8")
            parsed = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ProtocolFailure("%s returned invalid JSON" % label, code=failure_code) from exc
        if not isinstance(parsed, dict):
            raise ProtocolFailure("%s response must be an object" % label, code=failure_code)
        return dict(parsed), elapsed


def _secret_like_paths(value: Any, prefix: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = "%s.%s" % (prefix, key) if prefix else str(key)
            lowered = str(key).lower()
            if any(word in lowered for word in ("token", "secret", "password", "credential", "api_key")):
                found.append(label)
            found.extend(_secret_like_paths(item, label))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_secret_like_paths(item, "%s[%d]" % (prefix, index)))
    return found


def _validate_metrics(raw: Any, measured_wall: float) -> Dict[str, float]:
    obj = _need_dict(raw, "adapter.metrics")
    missing = [key for key in METRIC_KEYS if key not in obj]
    if missing:
        raise ProtocolFailure("adapter.metrics must report every metric: %s" % ", ".join(missing), code=EXIT_ADAPTER)
    result: Dict[str, float] = {}
    for key in METRIC_KEYS:
        result[key] = _need_number(obj.get(key), "adapter.metrics.%s" % key)
    # A model cannot under-report elapsed wall time.
    result["wall_time_seconds"] = max(result["wall_time_seconds"], measured_wall)
    return result


def _validate_adapter_response(raw: Mapping[str, Any], request: Mapping[str, Any], measured_wall: float) -> Dict[str, Any]:
    if raw.get("schema_version") != SCHEMA_VERSION or raw.get("contract") != CONTRACT:
        raise ProtocolFailure("adapter response contract mismatch", code=EXIT_ADAPTER)
    if raw.get("run_id") != request.get("run_id") or raw.get("mode") != request.get("mode"):
        raise ProtocolFailure("adapter response identity mismatch", code=EXIT_ADAPTER)
    selected = _need_bool(raw.get("selected"), "adapter.selected")
    status = _need_string(raw.get("status"), "adapter.status")
    if status not in ("completed", "failed"):
        raise ProtocolFailure("adapter.status must be completed or failed", code=EXIT_ADAPTER)
    metrics = _validate_metrics(raw.get("metrics"), measured_wall)
    metadata = _need_dict(raw.get("metadata", {}), "adapter.metadata")
    forbidden = _secret_like_paths(metadata)
    if forbidden:
        raise ProtocolFailure("adapter.metadata contains secret-like keys: %s" % ", ".join(forbidden[:8]), code=EXIT_ADAPTER)
    if len(canonical_json(metadata)) > 256 * 1024:
        raise ProtocolFailure("adapter.metadata exceeds 256 KiB", code=EXIT_ADAPTER)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "run_id": request["run_id"],
        "mode": request["mode"],
        "selected": selected,
        "status": status,
        "metrics": metrics,
        "metadata": metadata,
    }


def _validate_verifier_response(raw: Mapping[str, Any], request: Mapping[str, Any]) -> Dict[str, Any]:
    if raw.get("schema_version") != SCHEMA_VERSION or raw.get("contract") != CONTRACT:
        raise ProtocolFailure("verifier response contract mismatch", code=EXIT_VERIFIER)
    if raw.get("run_id") != request.get("run_id"):
        raise ProtocolFailure("verifier response identity mismatch", code=EXIT_VERIFIER)
    passed = _need_bool(raw.get("passed"), "verifier.passed")
    checks_raw = _need_list(raw.get("checks"), "verifier.checks")
    if not checks_raw:
        raise ProtocolFailure("verifier must return at least one named deterministic check", code=EXIT_VERIFIER)
    checks: List[Dict[str, Any]] = []
    for index, item in enumerate(checks_raw):
        check = _need_dict(item, "verifier.checks[%d]" % index)
        name = _need_string(check.get("name"), "verifier check name")
        ok = _need_bool(check.get("passed"), "verifier check passed")
        message = _need_string(check.get("message", ""), "verifier check message", nonempty=False)
        checks.append({"name": name, "passed": ok, "message": message})
    aggregate = all(check["passed"] for check in checks)
    if passed is not aggregate:
        raise ProtocolFailure("verifier.passed must equal the aggregate of named checks", code=EXIT_VERIFIER)
    return {"passed": passed, "checks": checks}


def _validate_links(root: Path) -> List[str]:
    violations: List[str] = []
    root_real = root.resolve(strict=True)
    for current, dirs, files in os.walk(str(root), topdown=True, followlinks=False):
        current_path = Path(current)
        for name in list(dirs) + list(files):
            item = current_path / name
            if not item.is_symlink():
                continue
            rel = item.relative_to(root).as_posix()
            try:
                resolved = item.resolve(strict=True)
                resolved.relative_to(root_real)
            except (FileNotFoundError, ValueError, OSError):
                violations.append(rel)
    return sorted(violations)


def _scope_gate(paths: Sequence[str], scope: Mapping[str, Sequence[str]]) -> Dict[str, Any]:
    allow = list(scope.get("allow", []))
    deny = list(scope.get("deny", []))
    violations = []
    for raw_path in paths:
        path = raw_path.rstrip("/")
        if not path:
            continue
        allowed = bool(allow) and match_any(path, allow)
        denied = bool(deny) and match_any(path, deny)
        if not allowed or denied:
            violations.append(path)
    return {"passed": not violations, "violations": sorted(set(violations))}


def _budget_gate(baseline: Mapping[str, float], treatment: Mapping[str, float], budgets: Mapping[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    for key, maximum in budgets.get("absolute", {}).items():
        actual = float(treatment[key])
        checks.append(
            {
                "metric": key,
                "kind": "absolute",
                "passed": actual <= float(maximum),
                "actual": actual,
                "limit": float(maximum),
            }
        )
    for key, rule in budgets.get("relative", {}).items():
        base = float(baseline[key])
        actual = float(treatment[key])
        limit = base * float(rule["max_ratio"]) + float(rule["max_additive"])
        checks.append(
            {
                "metric": key,
                "kind": "relative",
                "passed": actual <= limit,
                "baseline": base,
                "actual": actual,
                "limit": limit,
            }
        )
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _run_one(
    manifest: Mapping[str, Any],
    manifest_digest: str,
    case: Mapping[str, Any],
    mode: str,
    repo_root: Path,
    revision: str,
    fixture_snapshot: Mapping[str, Any],
    run_root: Path,
) -> Dict[str, Any]:
    workspace = run_root / mode
    copy_tree_no_links(repo_root / manifest["fixture"], workspace)
    before = tree_snapshot(workspace)
    if before != fixture_snapshot:
        raise HarnessError("fixture copy digest mismatch", code=EXIT_DATA)
    repository_before = repository_snapshot(repo_root, (run_root,))
    repository_digest = snapshot_digest(repository_before)
    case_digest = digest_json(case)
    run_id = digest_json(
        {
            "contract": CONTRACT,
            "suite": manifest["suite_id"],
            "manifest": manifest_digest,
            "case": case_digest,
            "revision": revision,
            "mode": mode,
        }
    )[:32]
    request = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "run_id": run_id,
        "mode": mode,
        "suite_id": manifest["suite_id"],
        "case": case,
        "case_digest": case_digest,
        "manifest_digest": manifest_digest,
        "fixture_digest": snapshot_digest(fixture_snapshot),
        "repository_revision": revision,
        "repository_root": str(repo_root),
        "workspace": str(workspace),
        "skill_path": str((repo_root / manifest["skill_path"]).resolve(strict=True)) if mode == "treatment" else None,
    }
    raw_adapter, measured = run_protocol_process(
        manifest["adapter"], request, repo_root, workspace, mode, case["id"], "adapter", EXIT_ADAPTER
    )
    adapter = _validate_adapter_response(raw_adapter, request, measured)
    repository_after_adapter = repository_snapshot(repo_root, (run_root,))
    repository_changes = changed_paths(repository_before, repository_after_adapter)
    if repository_changes:
        raise ProtocolFailure(
            "adapter modified the repository outside the isolated fixture",
            code=EXIT_ADAPTER,
            details={"changed_paths": repository_changes[:64]},
        )
    after_adapter = tree_snapshot(workspace)
    paths = [path for path in changed_paths(before, after_adapter) if not path.endswith("/")]
    link_violations = _validate_links(workspace)
    verifier_request = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "run_id": run_id,
        "mode": mode,
        "suite_id": manifest["suite_id"],
        "case": case,
        "workspace": str(workspace),
        "adapter": adapter,
        "changed_paths": paths,
        "fixture_digest": request["fixture_digest"],
        "repository_revision": revision,
        "repository_root": str(repo_root),
        "skill_path": request["skill_path"],
        "repository_snapshot_digest": repository_digest,
    }
    raw_verifier, _ = run_protocol_process(
        manifest["verifier"], verifier_request, repo_root, workspace, mode, case["id"], "verifier", EXIT_VERIFIER
    )
    after_verifier = tree_snapshot(workspace)
    if after_verifier != after_adapter:
        raise ProtocolFailure("deterministic verifier modified the workspace", code=EXIT_VERIFIER)
    repository_after_verifier = repository_snapshot(repo_root, (run_root,))
    repository_changes = changed_paths(repository_before, repository_after_verifier)
    if repository_changes:
        raise ProtocolFailure(
            "deterministic verifier modified the repository outside the isolated fixture",
            code=EXIT_VERIFIER,
            details={"changed_paths": repository_changes[:64]},
        )
    verifier = _validate_verifier_response(raw_verifier, verifier_request)
    expected_selected = False if mode == "baseline" else bool(case["expected_selected"])
    trigger_passed = adapter["selected"] is expected_selected
    scope = _scope_gate(paths, manifest["scope"])
    if link_violations:
        scope["passed"] = False
        scope["symlink_violations"] = link_violations
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "run_id": run_id,
        "mode": mode,
        "suite_id": manifest["suite_id"],
        "case_id": case["id"],
        "case_kind": case["kind"],
        "case_digest": case_digest,
        "manifest_digest": manifest_digest,
        "fixture_digest": request["fixture_digest"],
        "repository_revision": revision,
        "repository_snapshot_digest": repository_digest,
        "adapter_contract_digest": digest_json(manifest["adapter"]),
        "verifier_contract_digest": digest_json(manifest["verifier"]),
        "scope_contract_digest": digest_json(manifest["scope"]),
        "scope_contract": manifest["scope"],
        "adapter": adapter,
        "verifier": verifier,
        "trigger": {
            "expected_selected": expected_selected,
            "actual_selected": adapter["selected"],
            "passed": trigger_passed,
        },
        "scope": scope,
        "changed_paths": paths,
        "workspace_digest": snapshot_digest(after_adapter),
    }


COMPARABILITY_FIELDS = (
    "schema_version",
    "contract",
    "suite_id",
    "case_id",
    "case_kind",
    "case_digest",
    "manifest_digest",
    "fixture_digest",
    "repository_revision",
    "repository_snapshot_digest",
    "adapter_contract_digest",
    "verifier_contract_digest",
    "scope_contract_digest",
)


def compare_pair(baseline: Mapping[str, Any], treatment: Mapping[str, Any], budgets: Mapping[str, Any]) -> Dict[str, Any]:
    baseline = _need_dict(baseline, "baseline")
    treatment = _need_dict(treatment, "treatment")
    budget_contract = _validate_budgets(budgets)
    mismatches = []
    for field in COMPARABILITY_FIELDS:
        if field not in baseline or field not in treatment or baseline.get(field) != treatment.get(field):
            mismatches.append(field)
    if baseline.get("mode") != "baseline" or treatment.get("mode") != "treatment":
        mismatches.append("mode")
    if mismatches:
        raise HarnessError(
            "baseline/treatment are incomparable: %s" % ", ".join(sorted(set(mismatches))),
            code=EXIT_DATA,
        )
    baseline_adapter = _need_dict(baseline.get("adapter"), "baseline.adapter")
    treatment_adapter = _need_dict(treatment.get("adapter"), "treatment.adapter")
    baseline_metrics = _need_dict(baseline_adapter.get("metrics"), "baseline.metrics")
    treatment_metrics = _need_dict(treatment_adapter.get("metrics"), "treatment.metrics")
    normalized_baseline: Dict[str, float] = {}
    normalized_treatment: Dict[str, float] = {}
    for key in METRIC_KEYS:
        normalized_baseline[key] = _need_number(baseline_metrics.get(key), "baseline.metrics.%s" % key)
        normalized_treatment[key] = _need_number(treatment_metrics.get(key), "treatment.metrics.%s" % key)
    treatment_trigger = _need_dict(treatment.get("trigger"), "treatment.trigger")
    treatment_verifier = _need_dict(treatment.get("verifier"), "treatment.verifier")
    treatment_scope = _need_dict(treatment.get("scope"), "treatment.scope")
    trigger_passed = _need_bool(treatment_trigger.get("passed"), "treatment.trigger.passed")
    verifier_passed = _need_bool(treatment_verifier.get("passed"), "treatment.verifier.passed")
    scope_passed = _need_bool(treatment_scope.get("passed"), "treatment.scope.passed")
    status = _need_string(treatment_adapter.get("status"), "treatment.adapter.status")
    budget = _budget_gate(normalized_baseline, normalized_treatment, budget_contract)
    correctness_checks = {
        "adapter_completed": status == "completed",
        "trigger": trigger_passed,
        "deterministic_verifier": verifier_passed,
        "scope": scope_passed,
    }
    correctness_passed = all(correctness_checks.values())
    # Correctness is deliberately evaluated before cost and cannot be offset by cheaper execution.
    passed = correctness_passed and budget["passed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "suite_id": treatment["suite_id"],
        "case_id": treatment["case_id"],
        "case_kind": treatment["case_kind"],
        "passed": passed,
        "correctness": {"passed": correctness_passed, "checks": correctness_checks},
        "budget": budget,
        "budget_contract": budget_contract,
        "baseline_run_id": _need_string(baseline.get("run_id"), "baseline.run_id"),
        "treatment_run_id": _need_string(treatment.get("run_id"), "treatment.run_id"),
    }


@contextmanager
def _validated_materialized_suite(
    manifest_path: Path,
) -> Iterator[Tuple[Path, Path, Dict[str, Any], str]]:
    """Validate one control manifest against its detached repository revision."""

    context = discover_git_context(manifest_path.parent)
    source_root = context.worktree_root
    try:
        resolved_manifest = manifest_path.resolve(strict=True)
        manifest_rel = resolved_manifest.relative_to(source_root)
    except ValueError as exc:
        raise HarnessError("manifest must be inside the repository", code=EXIT_DATA) from exc
    raw_manifest = read_json(resolved_manifest)
    source_manifest = _need_dict(raw_manifest, "manifest")
    requested_revision = source_manifest.get("repository_revision")
    if requested_revision is not None:
        requested_revision = _need_string(requested_revision, "repository_revision")
    revision = _resolve_revision(source_root, requested_revision)
    source_head = _resolve_revision(source_root, "HEAD")

    with _materialized_revision(source_root, revision) as repo_root:
        # The common default is HEAD. Fail rather than silently evaluating a
        # committed fixture with an uncommitted control manifest. A manifest
        # explicitly targeting an older revision remains a valid control file,
        # but all paths it names are still resolved in that detached revision.
        if revision == source_head:
            pinned_manifest = repo_root / manifest_rel
            if not pinned_manifest.is_file() or pinned_manifest.read_bytes() != resolved_manifest.read_bytes():
                raise HarnessError(
                    "manifest differs from pinned HEAD; commit suite changes before evaluation",
                    code=EXIT_DATA,
                )

        manifest = validate_manifest(raw_manifest, repo_root)
        yield repo_root, manifest_rel, manifest, revision


def run_suite(manifest_path: Path, output_path: Path, keep_runs: bool = False, case_filter: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    with _validated_materialized_suite(manifest_path) as materialized:
        repo_root, manifest_rel, manifest, revision = materialized
        manifest_digest = digest_json(manifest)
        fixture_snapshot = tree_snapshot(repo_root / manifest["fixture"])
        selected = set(case_filter or [])
        unknown = selected - {case["id"] for case in manifest["cases"]}
        if unknown:
            raise HarnessError("unknown case ids: %s" % ", ".join(sorted(unknown)), code=EXIT_USAGE)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        runs_parent = Path(tempfile.mkdtemp(prefix="skill-eval-%s-runs-" % manifest["suite_id"]))
        case_results: List[Dict[str, Any]] = []
        try:
            for case in manifest["cases"]:
                if selected and case["id"] not in selected:
                    continue
                case_root = runs_parent / case["id"]
                case_root.mkdir(parents=True, exist_ok=False)
                baseline = _run_one(
                    manifest, manifest_digest, case, "baseline", repo_root, revision, fixture_snapshot, case_root
                )
                treatment = _run_one(
                    manifest, manifest_digest, case, "treatment", repo_root, revision, fixture_snapshot, case_root
                )
                comparison = compare_pair(baseline, treatment, manifest["budgets"])
                case_results.append(
                    {"case": case, "baseline": baseline, "treatment": treatment, "comparison": comparison}
                )
            result = {
                "schema_version": SCHEMA_VERSION,
                "contract": CONTRACT,
                "created_at": utc_now(),
                "suite_id": manifest["suite_id"],
                "manifest_path": manifest_rel.as_posix(),
                "manifest_digest": manifest_digest,
                "fixture_digest": snapshot_digest(fixture_snapshot),
                "repository_revision": revision,
                "revision_materialized": True,
                "passed": bool(case_results) and all(item["comparison"]["passed"] for item in case_results),
                "summary": {
                    "total": len(case_results),
                    "passed": sum(1 for item in case_results if item["comparison"]["passed"]),
                    "failed": sum(1 for item in case_results if not item["comparison"]["passed"]),
                },
                "cases": case_results,
            }
            if keep_runs:
                result["runs_path"] = str(runs_parent)
            write_json_atomic(output_path, result, mode=0o644)
            return result
        finally:
            if not keep_runs:
                shutil.rmtree(str(runs_parent), ignore_errors=True)


def _need_digest(value: Any, label: str) -> str:
    digest = _need_string(value, label)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise HarnessError("%s must be a lowercase SHA-256 digest" % label, code=EXIT_DATA)
    return digest


def _validate_result_case(raw: Any, label: str) -> Dict[str, Any]:
    case = _need_dict(raw, label)
    case_id = validate_identifier(_need_string(case.get("id"), "%s.id" % label), "case id")
    kind = _need_string(case.get("kind"), "%s.kind" % label)
    if kind not in CASE_KINDS:
        raise HarnessError("%s.kind is invalid" % label, code=EXIT_DATA)
    prompt = _need_string(case.get("prompt"), "%s.prompt" % label)
    expected_selected = _need_bool(case.get("expected_selected"), "%s.expected_selected" % label)
    if kind in ("negative", "confusable") and expected_selected:
        raise HarnessError("%s cannot expect selection" % label, code=EXIT_DATA)
    metadata = _need_dict(case.get("metadata"), "%s.metadata" % label)
    forbidden = _secret_like_paths(metadata)
    if forbidden:
        raise HarnessError("%s.metadata contains secret-like keys: %s" % (label, ", ".join(forbidden[:8])), code=EXIT_DATA)
    if len(canonical_json(metadata)) > 256 * 1024:
        raise HarnessError("%s.metadata exceeds 256 KiB" % label, code=EXIT_DATA)
    normalized = {
        "id": case_id,
        "kind": kind,
        "prompt": prompt,
        "expected_selected": expected_selected,
        "metadata": metadata,
    }
    if case != normalized:
        raise HarnessError("%s contains unknown or non-normalized fields" % label, code=EXIT_DATA)
    return normalized


def _validate_stored_run(
    raw: Any,
    case: Mapping[str, Any],
    mode: str,
    suite_id: str,
    manifest_digest: str,
    fixture_digest: str,
    revision: str,
) -> Dict[str, Any]:
    run = _need_dict(raw, "%s run" % mode)
    expected_run_keys = {
        "schema_version",
        "contract",
        "run_id",
        "mode",
        "suite_id",
        "case_id",
        "case_kind",
        "case_digest",
        "manifest_digest",
        "fixture_digest",
        "repository_revision",
        "repository_snapshot_digest",
        "adapter_contract_digest",
        "verifier_contract_digest",
        "scope_contract_digest",
        "scope_contract",
        "adapter",
        "verifier",
        "trigger",
        "scope",
        "changed_paths",
        "workspace_digest",
    }
    if set(run) != expected_run_keys:
        raise HarnessError("%s run fields do not match the result contract" % mode, code=EXIT_DATA)
    if run.get("schema_version") != SCHEMA_VERSION or run.get("contract") != CONTRACT:
        raise HarnessError("%s run contract mismatch" % mode, code=EXIT_DATA)
    case_digest = digest_json(case)
    expected_fields = {
        "mode": mode,
        "suite_id": suite_id,
        "case_id": case["id"],
        "case_kind": case["kind"],
        "case_digest": case_digest,
        "manifest_digest": manifest_digest,
        "fixture_digest": fixture_digest,
        "repository_revision": revision,
    }
    for field, expected in expected_fields.items():
        if run.get(field) != expected:
            raise HarnessError("%s run has inconsistent %s" % (mode, field), code=EXIT_DATA)
    expected_run_id = digest_json(
        {
            "contract": CONTRACT,
            "suite": suite_id,
            "manifest": manifest_digest,
            "case": case_digest,
            "revision": revision,
            "mode": mode,
        }
    )[:32]
    if run.get("run_id") != expected_run_id:
        raise HarnessError("%s run_id is inconsistent" % mode, code=EXIT_DATA)
    _need_digest(run.get("repository_snapshot_digest"), "%s.repository_snapshot_digest" % mode)
    _need_digest(run.get("adapter_contract_digest"), "%s.adapter_contract_digest" % mode)
    _need_digest(run.get("verifier_contract_digest"), "%s.verifier_contract_digest" % mode)
    _need_digest(run.get("workspace_digest"), "%s.workspace_digest" % mode)

    scope_contract = _need_dict(run.get("scope_contract"), "%s.scope_contract" % mode)
    allow = _need_list(scope_contract.get("allow"), "%s.scope_contract.allow" % mode)
    deny = _need_list(scope_contract.get("deny"), "%s.scope_contract.deny" % mode)
    for label, values in (("allow", allow), ("deny", deny)):
        if not all(isinstance(value, str) for value in values):
            raise HarnessError("%s.scope_contract.%s must contain strings" % (mode, label), code=EXIT_DATA)
        for value in values:
            ensure_relative_path(value, "%s.scope_contract.%s" % (mode, label), allow_glob=True, allow_git=label == "deny")
    normalized_scope_contract = {"allow": allow, "deny": deny}
    if scope_contract != normalized_scope_contract:
        raise HarnessError("%s.scope_contract contains unknown fields" % mode, code=EXIT_DATA)
    if run.get("scope_contract_digest") != digest_json(normalized_scope_contract):
        raise HarnessError("%s.scope_contract digest mismatch" % mode, code=EXIT_DATA)

    adapter_raw = _need_dict(run.get("adapter"), "%s.adapter" % mode)
    adapter = _validate_adapter_response(adapter_raw, {"run_id": expected_run_id, "mode": mode}, 0.0)
    if adapter_raw != adapter:
        raise HarnessError("%s adapter result is non-normalized" % mode, code=EXIT_DATA)
    verifier_raw = _need_dict(run.get("verifier"), "%s.verifier" % mode)
    verifier_envelope = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "run_id": expected_run_id,
        **verifier_raw,
    }
    verifier = _validate_verifier_response(verifier_envelope, {"run_id": expected_run_id})
    if verifier_raw != verifier:
        raise HarnessError("%s verifier result is non-normalized" % mode, code=EXIT_DATA)

    expected_selected = False if mode == "baseline" else bool(case["expected_selected"])
    expected_trigger = {
        "expected_selected": expected_selected,
        "actual_selected": adapter["selected"],
        "passed": adapter["selected"] is expected_selected,
    }
    if run.get("trigger") != expected_trigger:
        raise HarnessError("%s trigger result is inconsistent" % mode, code=EXIT_DATA)

    changed_raw = _need_list(run.get("changed_paths"), "%s.changed_paths" % mode)
    changed = [ensure_relative_path(value, "%s.changed_path" % mode) for value in changed_raw]
    if changed != sorted(set(changed)):
        raise HarnessError("%s.changed_paths must be sorted and unique" % mode, code=EXIT_DATA)
    expected_scope = _scope_gate(changed, normalized_scope_contract)
    stored_scope = _need_dict(run.get("scope"), "%s.scope" % mode)
    if "symlink_violations" in stored_scope:
        links_raw = _need_list(stored_scope.get("symlink_violations"), "%s.scope.symlink_violations" % mode)
        links = [ensure_relative_path(value, "%s symlink violation" % mode) for value in links_raw]
        if links != sorted(set(links)):
            raise HarnessError("%s symlink violations must be sorted and unique" % mode, code=EXIT_DATA)
        expected_scope["passed"] = False
        expected_scope["symlink_violations"] = links
    if stored_scope != expected_scope:
        raise HarnessError("%s scope result is inconsistent" % mode, code=EXIT_DATA)
    return run


def validate_result(raw: Any) -> Dict[str, Any]:
    result = _need_dict(raw, "result")
    expected_result_keys = {
        "schema_version",
        "contract",
        "created_at",
        "suite_id",
        "manifest_path",
        "manifest_digest",
        "fixture_digest",
        "repository_revision",
        "revision_materialized",
        "passed",
        "summary",
        "cases",
    }
    if set(result) - {"runs_path"} != expected_result_keys:
        raise HarnessError("result fields do not match the result contract", code=EXIT_DATA)
    if "runs_path" in result:
        _need_string(result["runs_path"], "result.runs_path")
    if result.get("schema_version") != SCHEMA_VERSION or result.get("contract") != CONTRACT:
        raise HarnessError("unsupported result contract", code=EXIT_DATA)
    suite_id = validate_identifier(_need_string(result.get("suite_id"), "result.suite_id"), "suite_id")
    manifest_digest = _need_digest(result.get("manifest_digest"), "result.manifest_digest")
    fixture_digest = _need_digest(result.get("fixture_digest"), "result.fixture_digest")
    revision = _need_string(result.get("repository_revision"), "result.repository_revision")
    if not FULL_REVISION_RE.fullmatch(revision):
        raise HarnessError("result.repository_revision must be a full commit SHA", code=EXIT_DATA)
    if result.get("revision_materialized") is not True:
        raise HarnessError("result must record a materialized revision", code=EXIT_DATA)
    ensure_relative_path(_need_string(result.get("manifest_path"), "result.manifest_path"), "result.manifest_path")
    _need_string(result.get("created_at"), "result.created_at")
    cases = _need_list(result.get("cases"), "result.cases")
    if not cases:
        raise HarnessError("result has no cases", code=EXIT_DATA)
    recomputed_passes: List[bool] = []
    seen_cases = set()
    for index, item in enumerate(cases):
        case_result = _need_dict(item, "result.cases[%d]" % index)
        if set(case_result) != {"case", "baseline", "treatment", "comparison"}:
            raise HarnessError("result case fields do not match the result contract", code=EXIT_DATA)
        case = _validate_result_case(case_result.get("case"), "result.cases[%d].case" % index)
        if case["id"] in seen_cases:
            raise HarnessError("result contains duplicate case id: %s" % case["id"], code=EXIT_DATA)
        seen_cases.add(case["id"])
        baseline = _validate_stored_run(
            case_result.get("baseline"), case, "baseline", suite_id, manifest_digest, fixture_digest, revision
        )
        treatment = _validate_stored_run(
            case_result.get("treatment"), case, "treatment", suite_id, manifest_digest, fixture_digest, revision
        )
        if baseline.get("scope_contract") != treatment.get("scope_contract"):
            raise HarnessError("baseline/treatment scope contracts differ", code=EXIT_DATA)
        stored = _need_dict(case_result.get("comparison"), "comparison")
        budget_contract = _validate_budgets(stored.get("budget_contract", {}))
        recomputed = compare_pair(baseline, treatment, budget_contract)
        if stored != recomputed:
            raise HarnessError("stored comparison differs from deterministic recomputation", code=EXIT_DATA)
        recomputed_passes.append(bool(recomputed["passed"]))
    expected_passed = all(recomputed_passes)
    if _need_bool(result.get("passed"), "result.passed") != expected_passed:
        raise HarnessError("result summary is inconsistent", code=EXIT_DATA)
    summary = _need_dict(result.get("summary"), "result.summary")
    expected_summary = {
        "total": len(cases),
        "passed": sum(1 for passed in recomputed_passes if passed),
        "failed": sum(1 for passed in recomputed_passes if not passed),
    }
    for key in expected_summary:
        if isinstance(summary.get(key), bool) or not isinstance(summary.get(key), int):
            raise HarnessError("result summary counts must be integers", code=EXIT_DATA)
    if set(summary) != set(expected_summary) or any(summary.get(key) != value for key, value in expected_summary.items()):
        raise HarnessError("result counts are inconsistent", code=EXIT_DATA)
    return result


def _emit(value: Mapping[str, Any], pretty: bool = False) -> None:
    json.dump(value, sys.stdout, sort_keys=True, ensure_ascii=False, indent=2 if pretty else None, allow_nan=False)
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-eval",
        description="Run deterministic baseline/treatment evaluations for Agent Skills.",
    )
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate an evaluation manifest without executing it")
    validate.add_argument("manifest", type=Path)
    run = sub.add_parser("run", help="run a suite through the configured offline/host adapter")
    run.add_argument("manifest", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--case", action="append", default=[], help="run only this case id; repeatable")
    run.add_argument("--keep-runs", action="store_true", help="retain isolated fixture copies for debugging")
    compare = sub.add_parser("compare", help="strictly compare one baseline and one treatment result")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("treatment", type=Path)
    compare.add_argument("--budgets", type=Path, help="JSON object containing absolute/relative budget rules")
    validate_result_parser = sub.add_parser(
        "validate-result",
        help="recompute every stored comparison and validate a complete suite result",
    )
    validate_result_parser.add_argument("result", type=Path)
    doctor = sub.add_parser("doctor", help="check repository, Python, and Git prerequisites")
    doctor.add_argument("--repo", type=Path, default=Path.cwd())
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            with _validated_materialized_suite(args.manifest) as materialized:
                _repo_root, _manifest_rel, manifest, revision = materialized
                _emit(
                    {
                        "ok": True,
                        "suite_id": manifest["suite_id"],
                        "cases": len(manifest["cases"]),
                        "repository_revision": revision,
                        "revision_materialized": True,
                    },
                    args.pretty,
                )
            return EXIT_OK
        if args.command == "run":
            result = run_suite(args.manifest, args.output, keep_runs=args.keep_runs, case_filter=args.case)
            _emit({"ok": result["passed"], "result": str(args.output), "summary": result["summary"]}, args.pretty)
            return EXIT_OK if result["passed"] else EXIT_GATE
        if args.command == "compare":
            baseline = _need_dict(read_json(args.baseline), "baseline")
            treatment = _need_dict(read_json(args.treatment), "treatment")
            budgets = _validate_budgets(read_json(args.budgets) if args.budgets else {})
            result = compare_pair(baseline, treatment, budgets)
            _emit(result, args.pretty)
            return EXIT_OK if result["passed"] else EXIT_GATE
        if args.command == "validate-result":
            result = validate_result(read_json(args.result))
            _emit(
                {
                    "ok": True,
                    "suite_id": result["suite_id"],
                    "repository_revision": result["repository_revision"],
                    "summary": result["summary"],
                },
                args.pretty,
            )
            return EXIT_OK
        if args.command == "doctor":
            context = discover_git_context(args.repo)
            checks = {
                "git_repository": True,
                "worktree_root": str(context.worktree_root),
                "git_common_dir": str(context.common_dir),
                "python": sys.version.split()[0],
                "contract": CONTRACT,
            }
            _emit({"ok": True, "checks": checks}, args.pretty)
            return EXIT_OK
        parser.error("unknown command")
    except HarnessError as exc:
        _emit({"ok": False, "error": str(exc), "code": exc.code, "details": exc.details}, getattr(args, "pretty", False))
        return exc.code
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
