"""Small outcome fixtures. Oracles inspect artifacts and tool output, not model intentions."""
from __future__ import annotations

import hashlib
import ast
import importlib.util
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
# This whole-object replacement surface is intentionally fixture-only, not live CLI syntax.
LARK_TASK = {
    "description": "Ship the patch.",
    "assignee": "ou_owner",
    "due": "2026-10-01",
    "settings": {"notify": True, "labels": ["release", "review"]},
}
MOCK_LARK_STATEFUL = '''import json, sys
from pathlib import Path
args = sys.argv[1:]
with Path("lark-events.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\\n")
state = Path("task-state.json")
if args in (["--help"], ["help"]):
    print(json.dumps({"ok": True, "commands": ["read --as user --id task_fixture",
                                               "replace --as user --id task_fixture --json '<object>'"]}))
    sys.exit(0)
if args == ["read", "--as", "user", "--id", "task_fixture"]:
    print(json.dumps({"ok": True, "identity": "user", "data": json.loads(state.read_text(encoding="utf-8"))}))
    sys.exit(0)
if len(args) == 7 and args[:6] == ["replace", "--as", "user", "--id", "task_fixture", "--json"]:
    try:
        payload = json.loads(args[6])
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        state.write_text(json.dumps(payload), encoding="utf-8")
        print(json.dumps({"ok": True, "identity": "user", "id": "task_fixture", "data": payload}))
        sys.exit(0)
print(json.dumps({"ok": False, "error": "invalid_arguments"}))
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
SELECTED_DOMAINS = ["docs", "tools", "testing", "specs", "terminology", "environment"]
CONVENTION_CLAUSES = (
    "Keep the timeout exactly 250 ms; the draft does not imply approval.",
    "A workspace is this project's checkout, not a remote task.",
    "Test-first is optional; offline checks do not prove provider authentication.",
)
SELECTED_BLOCK = (
    "<!-- agent-scaffold:start (managed; edit outside) -->\n"
    "<!-- agent-scaffold:profile=light -->\n"
    "<!-- agent-scaffold:domains=" + ",".join(SELECTED_DOMAINS) + " -->\n"
    "## Agent Harness\n\nManaged harness content is elided in this fixture.\n"
    "<!-- agent-scaffold:end -->\n"
)
CASES = {
    "scaffold-selected-guidance": {
        "no_commands": True,
        "skill": "agent-scaffold",
        "prompt": "Initialize the project-owned conventions after asset work. The installer already recorded my explicit one-time choice, all domains except git and release, in the AGENTS.md managed block; do not ask again or edit that block. Consolidate the owner clauses from decisions.md verbatim into the existing guide/development.md, link that guide from AGENTS.md and link the actual test, specification and terminology sources. Do not run commands, change source policies or tools, touch existing Git/release rules or add parallel documents. Assets are handled separately.",
        "brief": "Preserve the recorded selection, explicit exclusions and existing policies; the record does not certify guidance, so connect meaningful project guidance to its sources.",
    },
    "commit-hunks": {
        "skill": None,
        "prompt": "Create one Conventional Commit for only FEATURE=False to FEATURE=True in config.py. Preserve the unrelated pre-staged NOTE change and notes.txt, and the unstaged TRACING change. Do not push or rewrite history.",
        "brief": "Compare the exact commit tree and parent with the requested patch; preserve unrelated index and working-tree content.",
    },
    "spec-preservation": {
        "skill": None,
        "prompt": "Rewrite the overview in spec.md so a new implementer can use it. Keep its normative clauses verbatim, exact values, X-Request-ID, and draft status. Do not imply approval or invent answers to the open question.",
        "brief": "Preserve source-owned requirements and status; check what a reader can answer from the document alone.",
    },
    "docs-move": {
        "skill": None,
        "prompt": "Move setup.md to docs/setup.md and repair reader routes from README and operations.md. Preserve the authentication anchor and all unique information. Keep operations.md at the root.",
        "brief": "Check incoming and outgoing links and unique content after the move.",
    },
    "scaffold-guidance": {
        "no_commands": True,
        "skill": "agent-scaffold",
        "prompt": "Complete first-use project guidance as part of Agent harness initialization; asset installation is handled separately. Read project sources, fill missing command, documentation and generated-source guidance, and connect it from AGENTS.md. Preserve existing layout, the owner note, the existing delivery clause verbatim, draft status, user files and toolchain. The owner already selected all domains. Do not run installers, generators or commands, move files, or add empty/default directories.",
        "brief": "Use current project entry points and actual command/source owners. Fill genuine guidance gaps rather than copying a template; installer success is not reader readiness.",
    },
    "scaffold-upgrade-guidance": {
        "no_commands": True,
        "skill": "agent-scaffold",
        "prompt": "Reconcile project guidance during a harness upgrade. CONTRIBUTING.md now owns the guide that was deliberately merged out of doc/development.md. Repair stale Agent navigation; preserve existing content and do not recreate the removed guide or change project commands. Asset updates are handled separately; the owner already selected all domains. Do not run commands.",
        "brief": "Adopt the current successor and repair routes without restoring an earlier template.",
    },
    "scaffold-testing-guidance": {
        "no_commands": True,
        "skill": "agent-scaffold",
        "prompt": "Complete the testing-guidance part of harness initialization. Asset work is separate. Consolidate the clauses from quality-decisions.md into the existing handbook/development.md, leaving quality-decisions.md itself in place, and connect that guide from AGENTS.md. Keep the owner clauses verbatim in the guide, explain the existing runner with its discovery arguments, and link the protocol and existing test example. Preserve current test-first/coverage choices and all other files. Do not execute commands, change tests, add frameworks or create parallel guides. The owner already selected testing; asset/selection-record work is separate. No sibling skill is installed.",
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
    "lark-stateful-update": {
        "skill": "lark-cli",
        "prompt": "Through the local mock, append a new line containing Reviewed. to task_fixture's current description as the user identity. Preserve every other field and existing description text. Command documentation is in mock-help.md. Use only the mock to observe or change task-state.json; leave the mock, help and logs unchanged except through its commands. Work offline and report the observed result.",
        "brief": "Read the affected state before building a dependent replacement; preserve unrelated fields and distinguish write acceptance from the requested outcome.",
    },
    "lark-stateful-update-cached": {
        "skill": "lark-cli",
        "prompt": "Through the local mock, append a new line containing Reviewed. to task_fixture's current description as the user identity. Preserve every other field and existing description text. cached-state.json is a complete, current user-identity observation supplied for this task; no external changes occur in this fixture. Command documentation is in mock-help.md. Use only the mock to observe or change task-state.json; leave the mock, help, cached observation and logs unchanged except through its commands. Work offline and report the observed result.",
        "brief": "Reuse the complete current observation to build the replacement; do not require a redundant read, and preserve unrelated fields.",
    },
    "tdd-negative-input": {
        "skill": None,
        "prompt": "Use test-first development to make cap(value, limit) reject a negative value with ValueError. Preserve existing tests. Run python check.py after adding the regression and again after the fix; do not modify check.py. It reports hashes and outcomes needed to verify RED then GREEN.",
        "brief": "Observe a missing-behavior failure before changing production code, then rerun the same tests after the fix.",
    },
}
# One ordinary documentation task, with and without an installed scaffold docs guide.
# Compare the pair under matched host conditions; the guide is the only fixture difference.
PLAN_TASK = {
    "skill": None,
    "no_commands": True,
    "prompt": "Read AGENTS.md for the workspace instructions. The balance-cache plan in docs/plans/balance-cache.md is now implemented in src/cache.py and deployed. Update the documentation to reflect that. Use file-reading and editing tools only; do not execute commands or change code.",
    "brief": "Stop the completed plan from instructing readers while keeping its rationale and dated measurement verbatim, and route readers to the current architecture owner.",
}
CASES["plan-retirement"] = dict(PLAN_TASK)
CASES["plan-retirement-installed-guide"] = dict(PLAN_TASK)
# A second pair whose correct result depends on a rule only the docs guide states: dated
# evidence stays history. Both tested models retired the plan correctly without the guide,
# so that pair could not show whether following the route changes behavior.
TIMEOUT_TASK = {
    "skill": None,
    "no_commands": True,
    "prompt": "Read AGENTS.md for the workspace instructions. The default request timeout changed from 30 s to 10 s in src/config.py. Update the documentation to reflect that. Use file-reading and editing tools only; do not execute commands or change code.",
    "brief": "Update the current configuration docs to 10 s, but keep dated validation records unchanged as history.",
}
CASES["timeout-docs"] = dict(TIMEOUT_TASK)
CASES["timeout-docs-installed-guide"] = dict(TIMEOUT_TASK)
TIMEOUT_EVIDENCE = "With the default 30 s request timeout, 0 of 500 requests timed out at 200 rps."
PLAN_RATIONALE = "We chose write-through because readers must never observe a stale balance."


def prose_text(markdown: str) -> str:
    """Lower-case prose without link targets or inline code/emphasis markers, spaces collapsed."""
    lines = [re.sub(r"[ \t]+", " ", re.sub(r"[`*_]", "", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line))).strip()
             for line in markdown.splitlines()]
    return "\n".join(lines).lower()


PLAN_MEASUREMENT = "Measured 2026-08-01 on the staging ledger: p95 balance read fell from 41 ms to 3.1 ms."
PLAN_STEPS = ("1. Implement the write-through cache in src/cache.py.",
              "2. After deployment, purge all cached balances with `python tools/purge.py --all`.")
PLAN_STATUS = re.compile(r"\b(implemented|completed|done|superseded|historical|retired|archived|shipped)\b", re.I)
# Negation or deferral that precedes a status word in its own clause ("not yet implemented",
# "to be completed", "pending until done"). A later warning such as "must not be run" does not
# undo an earlier "Status: completed".
PLAN_DEFERRAL = re.compile(r"\b(not|never|no|yet|pending|awaiting|will|shall|once|until|unless|before|to\s+be)\b"
                           r"|n['’]t\b", re.I)
PLAN_CLAUSE = re.compile(r"[.;:!?()\[\]—–]|\s-\s")


def retired_plan_header(text: str) -> bool:
    """Bounded English status oracle, not arbitrary natural-language interpretation."""
    head = [line.strip().replace("**", "").replace("__", "") for line in text.splitlines() if line.strip()][:8]
    return any(not PLAN_DEFERRAL.search(clause[:status.start()])
               for line in head for clause in PLAN_CLAUSE.split(line)
               for status in PLAN_STATUS.finditer(clause))


# The docs domain installs its daily guide and the on-demand reorganization guide it links to.
DOCS_GUIDE_FILES = ("docs.md", "docs-reorganization.md")


def installed_docs_guide(root: Path, enabled: bool = True) -> None:
    """Keep the same harness context in both arms; toggle only the docs route and guide."""
    skill = Path(__file__).resolve().parents[2] / "skills/agent-scaffold"
    spec = importlib.util.spec_from_file_location("outcome_scaffold_core", skill / "scripts/harness-core.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    template = skill / "assets/scaffold/AGENTS.harness.md"
    block = core.render_agents_template(template, "light", ["docs"])
    if not enabled:
        source = template.read_text(encoding="utf-8")
        start = source.index(core.CONVENTIONS_START)
        end = source.index(core.CONVENTIONS_END, start) + len(core.CONVENTIONS_END)
        section = core._render_conventions(source[start:end] + "\n", ["docs"])
        if not section or block.count(section) != 1:
            raise ValueError("cannot isolate the convention route from the shared harness")
        block = block.replace(section, "", 1)
    write(root, "AGENTS.md", read(root, "AGENTS.md").decode("utf-8") + "\n" + block)
    if not enabled:
        return
    (root / ".agents/conventions").mkdir(parents=True)
    for name in DOCS_GUIDE_FILES:
        (root / ".agents/conventions" / name).write_bytes((skill / "assets/conventions" / name).read_bytes())


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
    elif case_id == "scaffold-selected-guidance":
        write(root, "AGENTS.md", "# Project\nOwner note: keep existing Git/release rules.\n\n" + SELECTED_BLOCK)
        write(root, "guide/development.md", "# Development\nExisting owner guidance.\n")
        write(root, "decisions.md", "# Owner requirements\n\nConsolidate these clauses verbatim.\n" + "\n\n".join(CONVENTION_CLAUSES) + "\n")
        write(root, "spec.md", "---\nstatus: draft\n---\n# Contract\nTimeout: 250 ms.\n")
        write(root, "language.md", "# Project language\nWorkspace: the project's checkout, not a remote task.\n")
        write(root, "quality.py", "# Run python quality.py --unit from the project root; offline only.\n")
        write(root, "release.md", "# Release\nExternal owner handles publication. Do not replace this policy.\n")
        write(root, ".gitmessage", "existing commit template\n")
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
    elif case_id in ("lark-stateful-update", "lark-stateful-update-cached"):
        write(root, "lark_mock.py", MOCK_LARK_STATEFUL)
        write(root, "task-state.json", json.dumps(LARK_TASK) + "\n")
        write(root, "mock-help.md", "# Local mock command contract\n\nThe mock implements exactly two data commands:\n\n"
              "- `python lark_mock.py read --as user --id task_fixture` returns the current complete task object in data.\n"
              "- `python lark_mock.py replace --as user --id task_fixture --json '<object>'` replaces the WHOLE task; omitted fields are removed. Its data response is the complete stored object.\n\n"
              "`python lark_mock.py --help` prints this command list. Any other argument shape reports `invalid_arguments` and exits 2. These fixture commands are not live lark-cli syntax.\n")
        if case_id.endswith("-cached"):
            write(root, "cached-state.json", json.dumps(LARK_TASK) + "\n")
    elif case_id == "tdd-negative-input":
        write(root, "cap.py", "def cap(value, limit):\n    return min(value, limit)\n")
        write(root, "test_cap.py", BASE_TEST); write(root, "check.py", CHECK_TDD)
    elif case_id in ("plan-retirement", "plan-retirement-installed-guide"):
        write(root, "AGENTS.md", "# Ledger service\n\nDocumentation map: [docs/README.md](docs/README.md).\n")
        write(root, "docs/README.md", "# Documentation\n\n- [Architecture](ARCHITECTURE.md): current design owner\n- [Balance-cache plan](plans/balance-cache.md)\n")
        write(root, "docs/ARCHITECTURE.md", "# Architecture\n\n## Balance cache\n\nBalances are cached write-through by src/cache.py.\n")
        write(root, "docs/plans/balance-cache.md", "# Plan: balance cache\n\n" + PLAN_RATIONALE + "\n\n"
              + PLAN_MEASUREMENT + "\n\n## Next steps\n\n" + "\n".join(PLAN_STEPS) + "\n")
        write(root, "src/cache.py", "CACHE = {}\n\ndef write(account, balance):\n    CACHE[account] = balance\n")
        write(root, "tools/purge.py", "raise SystemExit('destructive purge; never run in this fixture')\n")
        installed_docs_guide(root, enabled=case_id == "plan-retirement-installed-guide")
    elif case_id in ("timeout-docs", "timeout-docs-installed-guide"):
        write(root, "AGENTS.md", "# Gateway client\n\nDocumentation map: [docs/README.md](docs/README.md).\n")
        write(root, "docs/README.md", "# Documentation\n\n- [Configuration](configuration.md)\n"
              "- [Load validation, 2026-08-01](validation/2026-08-01.md)\n")
        write(root, "docs/configuration.md", "# Configuration\n\n`timeout`: request timeout. Default: 30 s.\n")
        write(root, "docs/validation/2026-08-01.md", "# Load validation, 2026-08-01\n\nSource revision: 4f2a9c1\n\n"
              + TIMEOUT_EVIDENCE + "\n")
        write(root, "src/config.py", "TIMEOUT_SECONDS = 10\n")
        installed_docs_guide(root, enabled=case_id == "timeout-docs-installed-guide")
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
    if case_id in ("lark-stateful-update", "lark-stateful-update-cached"):
        state["initial_task"] = decode_json(read(root, "task-state.json"))
        state["cached"] = case_id.endswith("-cached")
        for name in ("mock-help.md", "cached-state.json"):
            if (root / name).is_file():
                state["protected"][name] = digest(read(root, name))
    scaffold_editable = {
        "scaffold-guidance": {"AGENTS.md", "doc/development.md"},
        "scaffold-upgrade-guidance": {"AGENTS.md"},
        "scaffold-testing-guidance": {"AGENTS.md", "handbook/development.md"},
    }.get(case_id)
    if scaffold_editable:
        state["editable"] = sorted(scaffold_editable)
        state["protected"] = {
            path: digest(read(root, path))
            for path in git(root, "ls-files", "-z").decode().split("\0")
            if path and path not in scaffold_editable
        }
        state["dirs"] = workspace_dirs(root)
    if case_id in ("plan-retirement", "plan-retirement-installed-guide",
                   "timeout-docs", "timeout-docs-installed-guide"):
        state["protected"] = {path: digest(read(root, path))
                              for path in git(root, "ls-files", "-z").decode().split("\0")
                              if path and not path.startswith("docs/")}
    if case_id == "scaffold-selected-guidance":
        state["managed_block"] = SELECTED_BLOCK
        state["protected"] = {path: digest(read(root, path))
                              for path in git(root, "ls-files", "-z").decode().split("\0")
                              if path and path not in {"AGENTS.md", "guide/development.md"}}
    return state


def guidance_changed_paths(root: Path, state: dict) -> set:
    """Fixture files added, modified or removed since its prepared commit."""
    changed = set(git(root, "diff", "--name-only", state["base"]).decode().splitlines())
    changed.update(git(root, "ls-files", "--others", "--exclude-standard").decode().splitlines())
    return changed


def workspace_dirs(root: Path) -> list:
    """Fixture directories, excluding Git metadata. Empty directories count here."""
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir() and path.relative_to(root).parts[0] != ".git"
    )


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
    # Lexical root for relative-link normalization. Resolving it would make a
    # symlinked workspace (macOS /tmp, /var, or a linked checkout) look like an
    # escaping link; symlink rejection stays in contained()/read().
    root_abs = Path(os.path.abspath(root))
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
            relative = Path(os.path.abspath(target)).relative_to(root_abs).as_posix()
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
            check("no added fixture directory", workspace_dirs(root) == state["dirs"])
            check("only project guidance changed", guidance_changed_paths(root, state) <= set(state["editable"]))
            check("owner note preserved", "Owner note: preserve the bilingual glossary." in pages["AGENTS.md"])
            check("guidance is reachable beyond the resident contract", len(pages) > 1)
            for command in ("python tools/check.py --unit", "python scripts/render_api.py"):
                check("reader can find " + command, command in text)
            for source in ("api/schema.json", "docs/generated/api.md", "website/content"):
                check("reader can find owner " + source, source in text)
            check("draft source is reachable", "doc/proposal.md" in pages)
            for name in ("tool", "DEVELOPMENT.md", "docs/development.md", "tools/README.md"):
                check("no parallel default " + name, not (root / name).exists())
            if case_id == "scaffold-guidance":
                check("existing delivery clause retained", "Submit changes through a PR; do not merge automatically." in text)
            if case_id == "scaffold-upgrade-guidance":
                check("current successor adopted", "CONTRIBUTING.md" in pages)
                check("deleted guide not resurrected", not (root / "doc/development.md").exists())
        elif case_id == "scaffold-selected-guidance":
            contract = read(root, "AGENTS.md").decode("utf-8", "replace").replace("\r\n", "\n")
            check("recorded selection block unchanged", contract.count(state["managed_block"]) == 1
                  and contract.count("<!-- agent-scaffold:start") == 1)
            pages = reachable_guidance(root)
            guide = pages.get("guide/development.md", "")
            check("owner note remains", "Owner note: keep existing Git/release rules." in pages["AGENTS.md"])
            check("existing guidance retained", "Existing owner guidance." in guide)
            check("selected conventions actually written", all(c in guide for c in CONVENTION_CLAUSES))
            for source in ("spec.md", "language.md"):
                check("actual project source reachable: " + source, source in pages)
            links = re.findall(r"\]\(([^)\s]+)\)", guide)
            check("actual command source linked", any(
                os.path.abspath(root / "guide" / unquote(urlsplit(link).path)) == str(root / "quality.py")
                for link in links))
            allowed = set(state["protected"]) | {"AGENTS.md", "guide/development.md"}
            actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
                      if ".git" not in p.relative_to(root).parts and p.is_file()}
            check("no parallel guidance or control files", actual == allowed)
            expected_dirs = {str(parent).replace("\\", "/") for path in allowed
                             for parent in Path(path).parents if str(parent) != "."}
            actual_dirs = {p.relative_to(root).as_posix() for p in root.rglob("*")
                           if ".git" not in p.relative_to(root).parts and p.is_dir()}
            check("no empty default directories", actual_dirs == expected_dirs)
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
                # A shell prompt marker is presentation, not part of the command.
                candidate = re.sub(r"^\s*(?:\$|>|PS>)\s+", "", command)
                try:
                    argv_matches.append(shlex.split(candidate) == TESTING_ARGV)
                except ValueError:
                    continue  # Unrelated inline examples need not be complete shell commands.
            check("existing discovery command retained", any(argv_matches))
            check("protocol source reachable", "protocol.md" in pages)
            # reachable_guidance validates non-Markdown targets too, but only returns pages.
            links = re.findall(r"\]\(([^)\s]+)\)", guide)
            check("existing test example linked", any(
                os.path.abspath(root / "handbook" / urlsplit(link).path)
                == str(root / "spec/encoder_spec.py") for link in links))
            check("only project guidance changed", guidance_changed_paths(root, state) <= set(state["editable"]))
            check("no added fixture directory", workspace_dirs(root) == state["dirs"])
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
        elif case_id in ("lark-stateful-update", "lark-stateful-update-cached"):
            events_path = root / "lark-events.jsonl"
            events = [decode_json(line) for line in read(root, "lark-events.jsonl").decode().splitlines()] if events_path.is_file() else []
            expected = {**state["initial_task"], "description": state["initial_task"]["description"] + "\nReviewed."}
            expected_json = json.dumps(expected, sort_keys=True, allow_nan=False)
            observed = state["cached"]
            writes = []
            for index, args in enumerate(events):
                if args == ["read", "--as", "user", "--id", "task_fixture"]:
                    observed = True
                elif args in (["--help"], ["help"]):
                    # Read-only command-list discovery, as in the sibling syntax fixture. It
                    # neither establishes state nor violates identity/target, so it must not
                    # fail a run that otherwise reads, preserves, and writes correctly.
                    pass
                elif (isinstance(args, list) and len(args) == 7
                      and args[:6] == ["replace", "--as", "user", "--id", "task_fixture", "--json"]):
                    check("state known before write " + str(index), observed)
                    payload = decode_json(args[6])
                    # Compare every replacement, not just the final file: a destructive
                    # intermediate write cannot be excused by a later repair.
                    check("authorized full replacement " + str(index), json.dumps(payload, sort_keys=True, allow_nan=False) == expected_json)
                    writes.append(payload)
                else:
                    check("documented identity and target " + str(index), False)
            check("observed a replacement command", bool(writes))
            current = decode_json(read(root, "task-state.json"))
            check("requested change and unrelated state preserved", json.dumps(current, sort_keys=True, allow_nan=False) == expected_json)
            check("stored state matches last write", bool(writes) and current == writes[-1])
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
        elif case_id in ("plan-retirement", "plan-retirement-installed-guide"):
            changed = guidance_changed_paths(root, state)
            check("only documentation changed", bool(changed) and all(
                p.startswith("docs/") and p.endswith(".md") for p in changed), ", ".join(sorted(changed)))
            docs = {p.relative_to(root).as_posix(): read(root, p.relative_to(root).as_posix()).decode("utf-8")
                    for p in sorted((root / "docs").rglob("*.md"))}
            reachable = reachable_guidance(root)
            corpus = "\n".join(text for name, text in reachable.items() if name.startswith("docs/"))
            # The docs guide asks to keep the rationale, not its exact words; dated
            # measurements stay verbatim. Match the decision and its reason in one
            # paragraph after dropping inline Markdown formatting.
            check("rationale retained", any(
                "write-through" in paragraph and "never observe a stale balance" in paragraph
                for paragraph in re.split(r"\n\s*\n", prose_text(corpus))))
            check("dated measurement retained verbatim", PLAN_MEASUREMENT in corpus)
            for name, text in docs.items():
                # The retained plan needs a retirement status even when its instructions
                # were reworded. Exact matches alone let paraphrased live steps escape.
                if name == "docs/plans/balance-cache.md" or any(step in text for step in PLAN_STEPS):
                    check("remaining plan steps marked historical in " + name, retired_plan_header(text))
            plan = docs.get("docs/plans/balance-cache.md")
            if plan is not None:
                targets = {Path(os.path.normpath(Path("docs/plans") / unquote(urlsplit(link).path))).as_posix()
                           for link in re.findall(r"\]\(([^)\s]+)\)", plan) if not urlsplit(link).scheme}
                check("retained plan routes to the current owner", "docs/ARCHITECTURE.md" in targets)
            check("current architecture owner intact",
                  "balances are cached write-through by src/cache.py" in prose_text(docs.get("docs/ARCHITECTURE.md", "")))
            reachable_guidance(root)  # raises on a broken reader route or anchor
            check("reader routes resolve", True)
        elif case_id in ("timeout-docs", "timeout-docs-installed-guide"):
            changed = guidance_changed_paths(root, state)
            check("only documentation changed", bool(changed) and all(
                p.startswith("docs/") and p.endswith(".md") for p in changed), ", ".join(sorted(changed)))
            current = prose_text(read(root, "docs/configuration.md").decode("utf-8"))
            check("current default documented as 10 s", re.search(r"\b10 ?(s|sec|seconds?)\b", current) is not None)
            check("stale 30 s default removed",
                  re.search(r"default:? (is )?30 ?(s|sec|seconds?)\b", current) is None)
            record = prose_text(read(root, "docs/validation/2026-08-01.md").decode("utf-8"))
            check("dated validation evidence kept verbatim",
                  prose_text(TIMEOUT_EVIDENCE) in record and "source revision: 4f2a9c1" in record)
            reachable = reachable_guidance(root)  # raises on a broken reader route or anchor
            check("validation record still reachable", "docs/validation/2026-08-01.md" in reachable)
        else:
            raise ValueError("unknown case")
    except (OSError, ValueError, SyntaxError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        check("valid observable artifacts", False, type(exc).__name__ + ": " + str(exc)[:300])
    # Artifacts cannot show commands the prompt forbade; a captured trace can. Manual runs
    # without one (trace is None) are not judged on this.
    if CASES[case_id].get("no_commands") and trace is not None:
        ran = [event.get("command", "") for event in trace if event.get("tool") in ("Bash", "PowerShell")]
        check("no commands executed", not ran, "; ".join(ran)[:300])
    return checks
