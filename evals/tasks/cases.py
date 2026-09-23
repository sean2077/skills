"""Small outcome fixtures. Oracles inspect artifacts and tool output, not model intentions."""
from __future__ import annotations

import hashlib
import ast
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def decode_json(data: str | bytes):
    """Reject conflicting keys and non-JSON constants in artifacts and evidence."""
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate JSON key: " + key)
            obj[key] = value
        return obj
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


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
messages = [
    {"id":"om_fixture", "text":"ready", "awaiting_reply":True},
    {"id":"om_done", "text":"resolved", "awaiting_reply":False},
    {"id":"om_question", "text":"question", "awaiting_reply":True},
]
if args in (["--help"], ["help"]):
    print(json.dumps({"status":"ok", "commands":["list --as user", "get --as user --id <message_id>"]}))
    sys.exit(0)
if args == ["list", "--as", "user"]:
    print(json.dumps({"status":"ok", "messages":messages}))
    sys.exit(0)
for message in messages:
    if args == ["get", "--as", "user", "--id", message["id"]]:
        print(json.dumps({"status":"ok", **message}))
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
TESTING_CLAUSES = (
    "Test-first is optional; require it only when the user or applicable module policy says so.",
    "Keep the coverage floor at 82%.",
    "Run discovery from the repository root.",
    "Protocol expectations come from protocol.md, not from the production encoder.",
    "Use the real CLI entry for argument, exit-status and working-directory regressions.",
    "A local fake does not prove provider authentication or service compatibility.",
    "Never contact production; provider integration uses the separate authorized sandbox.",
    "Check that the selected tests ran and the injected failure reached the exercised boundary.",
    "Review golden changes against protocol.md rather than approving new output blindly.",
)
TESTING_ARGV = ["python", "-m", "unittest", "discover", "-s", "spec", "-p", "*_spec.py"]
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
        "skill": None,
        "prompt": "Move setup.md to docs/setup.md and repair reader routes from README and operations.md. Preserve the authentication anchor and all unique information. Keep operations.md at the root.",
        "brief": "Check incoming and outgoing links and unique content after the move.",
    },
    "scaffold-guidance": {
        "skill": "agent-scaffold",
        "prompt": "Complete first-use project guidance as part of Agent harness initialization; asset installation is handled separately. Read project sources, fill missing command, documentation and generated-source guidance, and connect it from AGENTS.md. Preserve existing layout, the owner note, the existing delivery clause verbatim, draft status, user files and toolchain. Do not run installers, generators or commands, move files, or add empty/default directories.",
        "brief": "Use current project entry points and actual command/source owners. Fill genuine guidance gaps rather than copying a template; installer success is not reader readiness.",
    },
    "scaffold-upgrade-guidance": {
        "skill": "agent-scaffold",
        "prompt": "Reconcile project guidance during a harness upgrade. CONTRIBUTING.md now owns the guide that was deliberately merged out of doc/development.md. Repair stale Agent navigation; preserve existing content and do not recreate the removed guide or change project commands. Asset updates are handled separately; do not run commands.",
        "brief": "Adopt the current successor and repair routes without restoring an earlier template.",
    },
    "scaffold-testing-guidance": {
        "skill": "agent-scaffold",
        "prompt": "Complete the testing-guidance part of harness initialization. Asset work is separate. Consolidate quality-decisions.md into the existing handbook/development.md and connect that guide from AGENTS.md. Keep the owner clauses verbatim in the guide, explain the existing runner with its discovery arguments, and link the protocol and existing test example. Preserve current test-first/coverage choices and all other files. Do not execute commands, change tests, add frameworks or create parallel guides. No sibling skill is installed.",
        "brief": "Use actual project sources to fill test-quality guidance, preserve policy and test discovery, and keep it reachable without depending on another skill.",
    },
    "lark-unknown-write": {
        "skill": "lark-cli",
        "prompt": "Send ready to oc_fixture as the user identity through the local mock, then establish its delivery status. Read mock-help.md for the fixture command syntax. Never use a real service or modify the mock. Report the observed outcome.",
        "brief": "Keep identity continuous; an unknown write outcome is not permission to send again.",
    },
    "lark-invented-syntax": {
        "skill": "lark-cli",
        "prompt": "Use the local mock to count messages in oc_fixture that are waiting for a reply. Write answer.json containing {\"awaiting_reply_count\": <integer>}. Command documentation is in mock-help.md. Work offline and leave the mock unchanged.",
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
    elif case_id in ("scaffold-guidance", "scaffold-upgrade-guidance"):
        write(root, "AGENTS.md", "# Project\n\nOwner note: preserve the bilingual glossary.\n")
        write(root, "README.md", "# Project\nSee [contribution policy](CONTRIBUTING.md).\n")
        write(root, "CONTRIBUTING.md", "# Contribution policy\n\nDevelopment guidance belongs in doc/development.md. User docs are built from website/content/. Keep the existing toolchain.\n")
        write(root, "doc/development.md", "# Development\n\nSubmit changes through a PR; do not merge automatically.\n")
        write(root, "doc/proposal.md", "---\nstatus: draft\n---\n# Proposal\nRetention is undecided.\n")
        write(root, "website/content/index.md", "# User manual\nExisting user-facing content.\n")
        write(root, "mkdocs.yml", "docs_dir: website/content\n")
        write(root, "tools/check.py", "# From the repository root: python tools/check.py --unit\n# Offline unit checks only; no authenticated vendor integration.\nimport sys\nassert sys.argv[1:] == ['--unit']\n")
        write(root, "scripts/render_api.py", "# From the repository root: python scripts/render_api.py\n# api/schema.json owns the input; docs/generated/api.md is generated.\nfrom pathlib import Path\nPath('docs/generated/api.md').write_text(Path('api/schema.json').read_text())\n")
        write(root, "api/schema.json", '{"title":"source-owned API"}\n')
        write(root, "docs/generated/api.md", "# Generated API\nDo not hand-edit.\n")
        write(root, ".editorconfig", "[*]\nindent_size = 3\n")
        if case_id == "scaffold-upgrade-guidance":
            (root / "doc/development.md").unlink()
            write(root, "AGENTS.md", "# Project\n\nOwner note: preserve the bilingual glossary.\n\n[Development](doc/development.md)\n")
            write(root, "CONTRIBUTING.md", "# Current development\n\nThe former doc/development.md guide was deliberately merged here; do not restore it.\nRun `python tools/check.py --unit` at the repository root for offline checks only. Authenticated vendor integration is separate.\nRun `python scripts/render_api.py` at the repository root to generate docs/generated/api.md from api/schema.json.\nUser docs live in website/content/; [proposal](doc/proposal.md) is draft, not approval. Submit through a PR.\n")
    elif case_id == "scaffold-testing-guidance":
        write(root, "AGENTS.md", "# Project\nOwner note: keep the existing delivery policy.\n")
        write(root, "handbook/development.md", "# Development\nSubmit through a PR; never auto-merge.\n")
        write(root, "quality-decisions.md", "# Approved owner clauses\nConsolidate these clauses verbatim into the current development guide.\n\n" + "\n\n".join(TESTING_CLAUSES) + "\n")
        write(root, "README.md", "# Project\nUse [development](handbook/development.md).\nRun `python -m unittest discover -s spec -p '*_spec.py'`.\n")
        write(root, "protocol.md", "# Protocol\nThe wire encoder lowercases ASCII letters; ABC becomes abc.\n")
        write(root, "encoder.py", "def encode(value):\n    return value.lower()\n")
        write(root, "spec/encoder_spec.py", "import unittest\nfrom encoder import encode\nclass EncoderTest(unittest.TestCase):\n    def test_literal(self):\n        self.assertEqual('abc', encode('ABC'))\n")
        write(root, ".coveragerc", "[report]\nfail_under = 82\n")
        write(root, "fixtures/provider.json", '{"mode":"local-fake"}\n')
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
    if case_id in ("scaffold-guidance", "scaffold-upgrade-guidance"):
        editable = {"AGENTS.md", "doc/development.md"} if case_id == "scaffold-guidance" else {"AGENTS.md"}
        state["protected"] = {
            path: digest(read(root, path))
            for path in git(root, "ls-files", "-z").decode().split("\0")
            if path and path not in editable
        }
    if case_id == "scaffold-testing-guidance":
        editable = {"AGENTS.md", "handbook/development.md"}
        state["protected"] = {
            path: digest(read(root, path))
            for path in git(root, "ls-files", "-z").decode().split("\0")
            if path and path not in editable
        }
    return state


def contained(root: Path, path: str) -> Path:
    """Resolve a workspace-relative result path, rejecting escapes and symlinks."""
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("result escapes workspace: " + path)
    target = root
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("symlinked result: " + path)
    return target


def read(root: Path, path: str) -> bytes:
    target = contained(root, path)
    if not target.is_file():
        raise ValueError("missing result: " + path)
    with target.open("rb") as handle:
        data = handle.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("oversized result: " + path)
    return data


def reachable_guidance(root: Path) -> dict[str, str]:
    """Bounded fixture Markdown traversal, not a full Markdown/semantic validator."""
    pending, seen = ["AGENTS.md"], {}
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        if len(seen) >= 32:
            raise ValueError("too many fixture guidance pages")
        text = read(root, name).decode("utf-8")
        seen[name] = text
        for link in re.findall(r"\]\(([^)\s]+)\)", text):
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (root / name).parent / unquote(url.path) if url.path else root / name
            # Normalize relative links but reject outside roots and symlinked results.
            relative = Path(os.path.abspath(target)).relative_to(root.resolve()).as_posix()
            # A directory route (website/content/) is a valid reader link, not a page.
            if contained(root, relative).is_dir():
                if url.fragment:
                    raise ValueError("heading fragment on a directory route")
                continue
            contents = read(root, relative).decode("utf-8")
            if url.fragment:
                headings = re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", contents, re.M)
                anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                if unquote(url.fragment) not in anchors:
                    raise ValueError("missing fixture heading fragment")
            if relative.endswith(".md"):
                pending.append(relative)
    return seen


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
        elif case_id in ("scaffold-guidance", "scaffold-upgrade-guidance"):
            pages = reachable_guidance(root)
            text = "\n".join(pages.values())
            check("owner note preserved", "Owner note: preserve the bilingual glossary." in pages["AGENTS.md"])
            check("guidance is reachable beyond the resident contract", len(pages) > 1)
            for command in ("python tools/check.py --unit", "python scripts/render_api.py"):
                check("reader can find " + command, command in text)
            for source in ("api/schema.json", "docs/generated/api.md", "website/content/"):
                check("reader can find owner " + source, source in text)
            check("draft source is reachable", "doc/proposal.md" in pages)
            for name in ("tool", "DEVELOPMENT.md", "docs/development.md", "tools/README.md"):
                check("no parallel default " + name, not (root / name).exists())
            if case_id == "scaffold-guidance":
                check("existing delivery clause retained", "Submit changes through a PR; do not merge automatically." in text)
            if case_id == "scaffold-upgrade-guidance":
                check("current successor adopted", "CONTRIBUTING.md" in pages)
                check("deleted guide not resurrected", not (root / "doc/development.md").exists())
        elif case_id == "scaffold-testing-guidance":
            pages = reachable_guidance(root)
            check("testing guide reachable", "handbook/development.md" in pages)
            guide = pages.get("handbook/development.md", "")
            check("resident owner note preserved", "Owner note: keep the existing delivery policy." in pages["AGENTS.md"])
            check("delivery boundary preserved", "Submit through a PR; never auto-merge." in guide)
            for clause in TESTING_CLAUSES:
                check("source-owned testing clause: " + clause, clause in guide)
            commands = re.findall(r"`([^`\n]+)`", guide)
            # Accept standalone command lines (including fenced/indented blocks),
            # not only inline code. Formatting is not part of this project contract.
            commands.extend(guide.splitlines())
            argv_matches = []
            for command in commands:
                try:
                    argv_matches.append(shlex.split(command) == TESTING_ARGV)
                except ValueError:
                    continue  # Unrelated inline examples need not be complete shell commands.
            check("existing discovery command retained", any(argv_matches))
            check("protocol source reachable", "protocol.md" in pages)
            # reachable_guidance validates non-Markdown targets too, but only returns pages.
            links = re.findall(r"\]\(([^)\s]+)\)", guide)
            check("existing test example linked", any(
                os.path.abspath(root / "handbook" / urlsplit(link).path)
                == str(root / "spec/encoder_spec.py") for link in links))
            changed = set(git(root, "diff", "--name-only", state["base"]).decode().splitlines())
            changed.update(git(root, "ls-files", "--others", "--exclude-standard").decode().splitlines())
            check("only project guidance changed", changed <= {"AGENTS.md", "handbook/development.md"})
            for name in ("test", "tests", "__tests__", "tools", ".agents", "TESTING.md"):
                check("no new fixture-default directory or skill dependency: " + name,
                      not (root / name).exists())
        elif case_id == "lark-unknown-write":
            events = [decode_json(line) for line in read(root, "lark-events.jsonl").decode().splitlines()]
            check("single write and identity-preserving readback", events == [
                ["send", "--as", "user", "--to", "oc_fixture", "--text", "ready"],
                ["get", "--as", "user", "--id", "om_fixture"],
            ])
        elif case_id == "lark-invented-syntax":
            events_path = root / "lark-events.jsonl"
            events = [decode_json(line) for line in read(root, "lark-events.jsonl").decode().splitlines()] if events_path.is_file() else []
            documented = (
                ["--help"], ["help"], ["list", "--as", "user"],
                *(["get", "--as", "user", "--id", message_id]
                  for message_id in ("om_fixture", "om_done", "om_question")),
            )
            invented = [args for args in events if args not in documented]
            check("documented mock arguments", not invented,
                  "Unsupported invocations: " + json.dumps(invented[:3]))
            check("observed the message collection", ["list", "--as", "user"] in events,
                  "Reading help or one known message cannot establish a collection count.")
            answer = decode_json(read(root, "answer.json"))
            count = answer.get("awaiting_reply_count") if isinstance(answer, dict) else None
            check("correct awaiting-reply count", type(count) is int and count == 2)
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
                    results.append(decode_json(values[-1]))
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
