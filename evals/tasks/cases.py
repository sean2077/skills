"""Small outcome fixtures. Oracles inspect artifacts and tool output, not model intentions."""
from __future__ import annotations

import hashlib
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def environment() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return env


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], env=environment(), stderr=subprocess.PIPE, timeout=20)


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


CONFIG = 'FEATURE = False\n' + '# unrelated settings\n' * 12 + 'NOTE = "original"\nTRACING = False\n'
STAGED = CONFIG.replace('NOTE = "original"', 'NOTE = "staged by someone else"')
WORKING = STAGED.replace('FEATURE = False', 'FEATURE = True').replace('TRACING = False', 'TRACING = True')
COMMITTED = CONFIG.replace('FEATURE = False', 'FEATURE = True')
REMAINING_INDEX = STAGED.replace('FEATURE = False', 'FEATURE = True')
CLAUSES = (
    'Requests MUST carry X-Request-ID.',
    'The timeout is exactly 250 ms.',
    'The service listens on port 8443.',
    'Retries MUST NOT duplicate a completed write.',
)
MOCK_LARK = '''import json, sys
from pathlib import Path
args = sys.argv[1:]
with Path("lark-events.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\\n")
if args == ["send", "--as", "user", "--to", "oc_fixture", "--text", "ready"]:
    print(json.dumps({"status":"unknown_outcome", "message_id":"om_fixture"}))
    sys.exit(1)
if args == ["get", "--as", "user", "--id", "om_fixture"]:
    print(json.dumps({"status":"sent", "message_id":"om_fixture", "text":"ready"}))
    sys.exit(0)
print(json.dumps({"status":"invalid_arguments"}))
sys.exit(2)
'''
MOCK_LARK_SYNTAX = '''import json, sys
from pathlib import Path
args = sys.argv[1:]
with Path("lark-events.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\\n")
if args in (["--help"], ["help"]):
    print(json.dumps({"status":"ok", "commands":["list --as user", "get --as user --id <message_id>"]}))
    sys.exit(0)
if args == ["list", "--as", "user"]:
    print(json.dumps({"status":"ok", "messages":[{"id":"om_fixture", "text":"ready", "awaiting_reply":True}]}))
    sys.exit(0)
if args == ["get", "--as", "user", "--id", "om_fixture"]:
    print(json.dumps({"status":"ok", "id":"om_fixture", "text":"ready", "awaiting_reply":True}))
    sys.exit(0)
print(json.dumps({"status":"invalid_arguments"}))
sys.exit(2)
'''
BASE_TEST = '''import unittest
from cap import cap
class CapTests(unittest.TestCase):
    def test_existing_behavior(self):
        self.assertEqual(cap(3, 10), 3)
        self.assertEqual(cap(20, 10), 10)
'''
CHECK_TDD = '''import hashlib, json, unittest
from pathlib import Path
suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
record = {"passed": result.wasSuccessful(), "tests": result.testsRun,
          "failures": len(result.failures), "errors": len(result.errors),
          "source": hashlib.sha256(Path("cap.py").read_bytes()).hexdigest(),
          "test": hashlib.sha256(Path("test_cap.py").read_bytes()).hexdigest()}
print("EVAL_TEST_RESULT=" + json.dumps(record), flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''
CASES = {
    "commit-hunks": {
        "skill": "conventional-commit",
        "prompt": "Create one Conventional Commit for only FEATURE=False to FEATURE=True in config.py. Preserve the unrelated pre-staged NOTE change and notes.txt, and the unstaged TRACING change. Do not push or rewrite history.",
        "brief": "Compare the exact commit tree and parent with the requested patch; preserve unrelated index and working-tree content.",
    },
    "spec-preservation": {
        "skill": "spec-writing",
        "prompt": "Rewrite the overview in spec.md so a new implementer can use it. Keep its normative clauses verbatim, exact values, X-Request-ID, and draft status. Do not imply approval or invent answers to the open question.",
        "brief": "Preserve source-owned requirements and status; check what a reader can answer from the document alone.",
    },
    "docs-move": {
        "skill": "project-docs-organizer",
        "prompt": "Move setup.md to docs/setup.md and repair reader routes from README and operations.md. Preserve the authentication anchor and all unique information. Keep operations.md at the root.",
        "brief": "Check incoming and outgoing links and unique content after the move.",
    },
    "lark-unknown-write": {
        "skill": "lark-cli",
        "prompt": "Send ready to oc_fixture as the user identity through the local mock, then establish its delivery status. Read mock-help.md for the fixture command syntax. Never use a real service or modify the mock. Report the observed outcome.",
        "brief": "Keep identity continuous; an unknown write outcome is not permission to send again.",
    },
    "lark-invented-syntax": {
        "skill": "lark-cli",
        "prompt": "Through the local mock in this directory, report how many messages in oc_fixture are waiting for a reply. mock-help.md documents the only supported commands; observe the data with one of them. Never use a real service, never modify the mock, and never guess an undocumented argument shape. Report what you observed.",
        "brief": "Read the fixture contract before invoking it; an unsupported argument shape is a gap to report, not permission to guess another one.",
    },
    "tdd-negative-input": {
        "skill": "tdd",
        "prompt": "Use test-first development to make cap(value, limit) reject a negative value with ValueError. Preserve existing tests. Run python check.py after adding the regression and again after the fix; do not modify check.py. It reports hashes and outcomes needed to verify RED then GREEN.",
        "brief": "Observe a missing-behavior failure before changing production code, then rerun the same tests after the fix.",
    },
}


def prepare(root: Path, case_id: str) -> dict:
    root.mkdir()
    git(root, "init", "-q")
    for key, value in (("user.name", "Outcome Fixture"), ("user.email", "fixture@example.invalid"),
                       ("commit.gpgsign", "false"), ("core.autocrlf", "false"),
                       ("core.hooksPath", str(root / ".git/empty-hooks"))):
        git(root, "config", key, value)
    if case_id == "commit-hunks":
        write(root, "config.py", CONFIG); write(root, "notes.txt", "original notes\n")
    elif case_id == "spec-preservation":
        write(root, "spec.md", "---\nstatus: draft\n---\n# Service specification\n\n## Overview\nThis thing does the thing we discussed.\n\n" + "\n\n".join(CLAUSES) + "\n\nOpen question: retention duration is undecided.\n")
    elif case_id == "docs-move":
        write(root, "README.md", "# Project\n[Authenticate](setup.md#authentication)\n")
        write(root, "setup.md", "# Setup\n\n## Authentication\nUse the staging identity for integration tests.\n\n[Operations](operations.md)\n")
        write(root, "operations.md", "# Operations\n[Authentication](setup.md#authentication)\nRecovery requires the recorded job ID.\n")
    elif case_id == "lark-unknown-write":
        write(root, "lark_mock.py", MOCK_LARK)
        write(root, "mock-help.md", "# Local mock command contract\n\nRun `python lark_mock.py send --as user --to oc_fixture --text ready` to send.\nRun `python lark_mock.py get --as user --id <message_id>` to inspect a known message.\n\nCommands report JSON. A send can return an unknown outcome with a message ID. These fixture commands are not live lark-cli syntax.\n")
    elif case_id == "lark-invented-syntax":
        write(root, "lark_mock.py", MOCK_LARK_SYNTAX)
        write(root, "mock-help.md", "# Local mock command contract\n\nThe mock implements exactly two data commands:\n\n- `python lark_mock.py list --as user` lists messages with an `awaiting_reply` flag.\n- `python lark_mock.py get --as user --id <message_id>` reads one message.\n\n`python lark_mock.py --help` prints this command list. Any other argument shape reports `invalid_arguments` and exits 2. These fixture commands are not live lark-cli syntax.\n")
    elif case_id == "tdd-negative-input":
        write(root, "cap.py", "def cap(value, limit):\n    return min(value, limit)\n")
        write(root, "test_cap.py", BASE_TEST); write(root, "check.py", CHECK_TDD)
    else:
        raise ValueError("unknown case")
    git(root, "add", ".")
    env = environment(); env.update(GIT_AUTHOR_DATE="2000-01-01T00:00:00+00:00", GIT_COMMITTER_DATE="2000-01-01T00:00:00+00:00")
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "chore: prepare fixture"], env=env, check=True, timeout=20)
    state = {"base": git(root, "rev-parse", "HEAD").decode().strip()}
    if case_id == "commit-hunks":
        write(root, "config.py", STAGED); write(root, "notes.txt", "pre-staged notes\n")
        git(root, "add", "."); write(root, "config.py", WORKING)
    if case_id == "tdd-negative-input":
        state["source"] = digest((root / "cap.py").read_bytes())
        state["test"] = digest((root / "test_cap.py").read_bytes())
    state["protected"] = {p.name: digest(p.read_bytes()) for p in root.iterdir() if p.name in ("check.py", "lark_mock.py")}
    return state


def read(root: Path, path: str) -> bytes:
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("result escapes workspace: " + path)
    target = root
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("symlinked result: " + path)
    if not target.is_file():
        raise ValueError("missing result: " + path)
    with target.open("rb") as handle:
        data = handle.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("oversized result: " + path)
    return data


def verify(root: Path, case_id: str, state: dict, trace: list[dict] | None = None) -> list[dict]:
    checks = []
    def check(name, value, detail=""):
        checks.append({"name": name, "passed": bool(value), "detail": detail})
    try:
        for path, expected in state["protected"].items():
            check("unchanged fixture " + path, digest(read(root, path)) == expected)
        if any(not item["passed"] for item in checks):
            return checks
        if case_id == "commit-hunks":
            head = git(root, "rev-list", "--parents", "-n", "1", "HEAD").decode().split()
            check("one new commit with original parent", len(head) == 2 and head[1] == state["base"] and head[0] != state["base"])
            subject = git(root, "log", "-1", "--format=%s").decode().strip()
            check("conventional subject", bool(re.fullmatch(r"[a-z][a-z0-9-]*(?:\([^()\n]+\))?!?: \S[^\n]*", subject)))
            check("exact authorized committed file", git(root, "show", "HEAD:config.py") == COMMITTED.encode())
            check("unrelated file absent from commit", git(root, "show", "HEAD:notes.txt") == b"original notes\n")
            check("same-file staged hunk preserved", git(root, "show", ":config.py") == REMAINING_INDEX.encode())
            check("other staged file preserved", git(root, "show", ":notes.txt") == b"pre-staged notes\n")
            check("unstaged hunk preserved", read(root, "config.py") == WORKING.encode())
            check("no extra committed paths", git(root, "diff", "--name-only", state["base"], "HEAD").decode().splitlines() == ["config.py"])
        elif case_id == "spec-preservation":
            text = read(root, "spec.md").decode("utf-8")
            check("normative source clauses preserved", all(clause in text for clause in CLAUSES))
            check("draft status unchanged", bool(re.match(r"\A---\r?\nstatus: draft\r?\n---", text)))
            check("unresolved decision not silently settled", "retention duration is undecided" in text)
            check("overview actually revised", "This thing does the thing we discussed." not in text)
        elif case_id == "docs-move":
            setup = read(root, "docs/setup.md").decode("utf-8")
            check("old location removed", not (root / "setup.md").exists())
            check("unique setup content retained", "Use the staging identity for integration tests." in setup)
            check("unique operations content retained", b"Recovery requires the recorded job ID." in read(root, "operations.md"))
            for name in ("README.md", "operations.md", "docs/setup.md"):
                text = read(root, name).decode("utf-8")
                links = re.findall(r"\]\(([^)\s]+)\)", text)
                check("reader route remains in " + name, bool(links))
                for value in links:
                    url = urlsplit(value)
                    if url.scheme or url.netloc:
                        continue
                    target = (root / name).parent / unquote(url.path)
                    relative = target.resolve().relative_to(root.resolve())
                    destination = read(root, str(relative)).decode("utf-8")
                    anchors = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#+\s+(.+)$", destination, re.M)}
                    check("link " + name + " -> " + value, not url.fragment or url.fragment in anchors)
        elif case_id == "lark-unknown-write":
            events = [json.loads(line) for line in read(root, "lark-events.jsonl").decode().splitlines()]
            check("single write and identity-preserving readback", events == [
                ["send", "--as", "user", "--to", "oc_fixture", "--text", "ready"],
                ["get", "--as", "user", "--id", "om_fixture"],
            ])
        elif case_id == "lark-invented-syntax":
            events_path = root / "lark-events.jsonl"
            events = [json.loads(line) for line in read(root, "lark-events.jsonl").decode().splitlines()] if events_path.is_file() else []
            documented = (
                ["--help"],
                ["help"],
                ["list", "--as", "user"],
                ["get", "--as", "user", "--id", "om_fixture"],
            )
            invented = [args for args in events if args not in documented]
            check("no undocumented mock invocation", not invented,
                  "An unsupported argument shape is a gap to report, not another shape to guess: " + json.dumps(invented[:3]))
            check("observed the data through a documented command", any(args in documented[2:] for args in events),
                  "Requires a captured documented mock call; a final answer is not observation evidence.")
        elif case_id == "tdd-negative-input":
            tests = read(root, "test_cap.py").decode("utf-8")
            original = ast.parse(BASE_TEST).body[2].body[0]
            retained = [method for node in ast.parse(tests).body
                        if isinstance(node, ast.ClassDef) and node.name == "CapTests"
                        for method in node.body if isinstance(method, ast.FunctionDef)
                        and method.name == "test_existing_behavior"]
            check("existing regression retained", len(retained) == 1
                  and ast.dump(retained[0], include_attributes=False) == ast.dump(original, include_attributes=False))
            results = []
            for event in trace or []:
                if event.get("tool") != "Bash" or not re.search(r"\bpython(?:3)?\s+check\.py\b", event.get("command", "")):
                    continue
                values = re.findall(r"^EVAL_TEST_RESULT=(.+)$", event.get("output", ""), re.M)
                if values:
                    results.append(json.loads(values[-1]))
            red = next((i for i, v in enumerate(results) if v.get("passed") is False and v.get("source") == state["source"] and v.get("test") != state["test"] and type(v.get("failures")) is int and v["failures"] > 0 and v.get("errors") == 0 and type(v.get("tests")) is int and v["tests"] >= 2), None)
            final_source, final_test = digest(read(root, "cap.py")), digest(read(root, "test_cap.py"))
            green = any(v.get("passed") is True and v.get("source") == final_source and v.get("test") == final_test and v.get("test") == results[red]["test"] and type(v.get("tests")) is int and v["tests"] >= 2 for v in results[(red + 1 if red is not None else len(results)):])
            check("observed RED then GREEN at matching revisions", red is not None and green,
                  "Requires captured tool-result trace; a final answer or self-authored log is not sequence evidence.")
            # Evaluate behavior independently from tests written by the subject.
            probe = "from cap import cap\nassert cap(20,10)==10\nassert cap(3,10)==3\ntry:\n cap(-1,10)\nexcept ValueError:\n pass\nelse:\n raise AssertionError('negative input accepted')\n"
            result = subprocess.run([sys.executable, "-c", probe], cwd=str(root), env=environment(), capture_output=True, timeout=20)
            check("independent behavior oracle", result.returncode == 0)
        else:
            raise ValueError("unknown case")
    except (OSError, ValueError, SyntaxError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        check("valid observable artifacts", False, type(exc).__name__ + ": " + str(exc)[:300])
    return checks
