#!/usr/bin/env python
# Generate Claude Code (.claude/agents/*.md) and Codex (.codex/agents/*.toml)
# subagent files from the authoritative source in .agents/subagents/.
#
#   python tools/agent/generate-subagents.py           # write projections
#   python tools/agent/generate-subagents.py --check   # exit 1 on drift (CI / pre-commit)
#   python tools/agent/generate-subagents.py --import  # adopt hand-authored host agents into sources
#
# Source per subagent: .agents/subagents/<name>/{metadata.json, instructions.md}.
# Generated files are marked "do not edit by hand" — edit the source and re-run.
#
# Standard-library Python 3 only (no pip installs). The bash harness already assumes
# python, so subagents work anywhere the rest of the harness does — no Node / package.json.
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SOURCE_DIR = os.path.join(ROOT, ".agents", "subagents")
CLAUDE_DIR = os.path.join(ROOT, ".claude", "agents")
CODEX_DIR = os.path.join(ROOT, ".codex", "agents")
DO_NOT_EDIT = (
    "Generated from .agents/subagents/%s; do not edit by hand. "
    "Run: python tools/agent/generate-subagents.py"
)
# Marker that identifies a generated projection. Use the full "Generated from
# .agents/subagents/" lead-in, NOT a loose "do not edit by hand": the latter can
# occur in a genuinely hand-authored agent's prose, which would misclassify it as
# generated -> wrongly skipped by --import and wrongly pruned as a stale orphan.
BANNER = "Generated from .agents/subagents/"


def is_dir(p):
    return os.path.isdir(p)


def read_text(p):
    with open(p, "r", encoding="utf-8") as f:
        # Normalize CRLF/CR -> LF: Windows/Git-Bash-authored agent files must still
        # match the LF-based frontmatter regexes (--import), and projections must not
        # false-drift on line endings alone (--check / write_if_changed).
        return f.read().replace("\r\n", "\n").replace("\r", "\n")


def write_text(p, content):
    # newline="\n": never let text mode translate to CRLF on Windows. The repo is
    # LF-only (.gitattributes + CI CRLF check) and read_text() normalizes CRLF->LF
    # before --check compares, so a CRLF write would be a silent false-green.
    # tmp + os.replace makes the write atomic (no half-file on a crash mid-write).
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp, p)


def rel(p):
    return p[len(ROOT) + 1:]


# JSON string encoding doubles as a valid YAML double-quoted scalar / TOML basic
# string for our text; ensure_ascii=False keeps raw Unicode (matches the prior Node port).
def jstr(s):
    return json.dumps(str(s), ensure_ascii=False)


def load_subagents():
    if not is_dir(SOURCE_DIR):
        return []
    out = []
    for name in sorted(os.listdir(SOURCE_DIR)):
        if name.startswith("_"):
            continue
        d = os.path.join(SOURCE_DIR, name)
        if not is_dir(d):
            continue
        meta_path = os.path.join(d, "metadata.json")
        instr_path = os.path.join(d, "instructions.md")
        if not os.path.exists(meta_path) or not os.path.exists(instr_path):
            raise SystemExit("subagent '%s' is missing metadata.json or instructions.md" % name)
        try:
            meta = json.loads(read_text(meta_path))
        except ValueError as e:
            raise SystemExit("subagent '%s': metadata.json is not valid JSON: %s" % (name, e))
        if meta.get("name") != name:
            raise SystemExit(
                "subagent '%s': metadata.name='%s' must match directory name" % (name, meta.get("name"))
            )
        if not str(meta.get("description") or "").strip():
            raise SystemExit("subagent '%s': metadata.json needs a non-empty description" % name)
        instructions = read_text(instr_path)
        if not instructions.endswith("\n"):
            instructions += "\n"
        out.append({"name": name, "meta": meta, "instructions": instructions})
    return out


# YAML single-line scalar: quote only when raw would be ambiguous.
_YAML_NEEDS_QUOTE = re.compile(r"""^[\s>|@`"'%#&*!?{}\[\],]|:\s|\s#|^$""")


def yaml_scalar(s):
    one_line = re.sub(r"\s*\n\s*", " ", str(s)).strip()
    return jstr(one_line) if _YAML_NEEDS_QUOTE.search(one_line) else one_line


def render_claude(sa):
    name, meta, instructions = sa["name"], sa["meta"], sa["instructions"]
    fm = ["name: %s" % name, "description: %s" % yaml_scalar(meta.get("description"))]
    claude = meta.get("claude") or {}
    tools = claude.get("tools")
    if isinstance(tools, list) and tools:
        fm.append("tools: %s" % ", ".join(tools))
    if claude.get("model"):
        fm.append("model: %s" % claude["model"])
    banner = DO_NOT_EDIT.replace("%s", name)
    return "---\n%s\n---\n\n<!-- %s -->\n\n%s" % ("\n".join(fm), banner, instructions)


def toml_multiline(s):
    if "'''" in s:
        raise SystemExit("instructions cannot contain ''' (TOML multiline literal delimiter)")
    return "'''\n%s'''" % s


def render_codex(sa):
    name, meta, instructions = sa["name"], sa["meta"], sa["instructions"]
    c = meta.get("codex") or {}
    lines = [
        "# %s" % DO_NOT_EDIT.replace("%s", name),
        "name = %s" % jstr(name),
        "description = %s" % jstr(meta.get("description")),
    ]
    if c.get("model"):
        lines.append("model = %s" % jstr(c["model"]))
    if c.get("model_reasoning_effort"):
        lines.append("model_reasoning_effort = %s" % jstr(c["model_reasoning_effort"]))
    if c.get("sandbox_mode"):
        lines.append("sandbox_mode = %s" % jstr(c["sandbox_mode"]))
    nicks = c.get("nickname_candidates")
    if isinstance(nicks, list) and nicks:
        lines.append("nickname_candidates = [%s]" % ", ".join(jstr(n) for n in nicks))
    lines.append("developer_instructions = %s" % toml_multiline(instructions))
    return "\n".join(lines) + "\n"


def projections(subagents):
    out = []
    for sa in subagents:
        out.append({"path": os.path.join(CLAUDE_DIR, sa["name"] + ".md"), "content": render_claude(sa)})
        out.append({"path": os.path.join(CODEX_DIR, sa["name"] + ".toml"), "content": render_codex(sa)})
    return out


# Generated files with no matching source (would be stale).
def orphans(subagents):
    expect = set()
    for sa in subagents:
        expect.add(os.path.join(CLAUDE_DIR, sa["name"] + ".md"))
        expect.add(os.path.join(CODEX_DIR, sa["name"] + ".toml"))
    found = []
    for d, ext in ((CLAUDE_DIR, ".md"), (CODEX_DIR, ".toml")):
        if not is_dir(d):
            continue
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if f.endswith(ext) and p not in expect:
                found.append(p)
    return found


# --- Adoption (--import): turn hand-authored host agent files into SSOT sources ---

# Parse a Claude Code agent markdown (YAML frontmatter + body). Returns None when it
# has no frontmatter. Only the keys this generator emits are understood
# (name / description / tools / model); anything else is ignored.
def parse_claude_agent(text):
    m = re.match(r"^---\n([\s\S]*?)\n---\n?([\s\S]*)$", text)
    if not m:
        return None
    fm, raw_body = m.group(1), m.group(2)
    meta = {}
    for line in fm.split("\n"):
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        v = kv.group(2).strip()
        if v.startswith('"') and v.endswith('"'):
            try:
                v = json.loads(v)
            except Exception:
                v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        meta[kv.group(1)] = v
    tools = [s.strip() for s in meta["tools"].split(",")] if meta.get("tools") else []
    tools = [s for s in tools if s]
    return {
        "name": meta.get("name"),
        "description": meta.get("description") or "",
        "tools": tools,
        "model": meta.get("model"),
        "body": re.sub(r"^\n+", "", raw_body),
    }


# Parse a Codex agent TOML (only the keys this generator emits).
def parse_codex_agent(text):
    def scalar(key):
        m = re.search(r"^" + key + r"\s*=\s*(.+)$", text, re.MULTILINE)
        if not m:
            return None
        raw = m.group(1).strip()
        try:
            return json.loads(raw)
        except Exception:
            return re.sub(r"""^["']|["']$""", "", raw)

    nicks = None
    nm = re.search(r"^nickname_candidates\s*=\s*\[(.*)\]\s*$", text, re.MULTILINE)
    if nm:
        try:
            nicks = json.loads("[" + nm.group(1) + "]")
        except Exception:
            nicks = None
    di = re.search(r"developer_instructions\s*=\s*'''\n([\s\S]*?)'''", text)
    return {
        "name": scalar("name"),
        "description": scalar("description") or "",
        "model": scalar("model"),
        "model_reasoning_effort": scalar("model_reasoning_effort"),
        "sandbox_mode": scalar("sandbox_mode"),
        "nickname_candidates": nicks,
        "instructions": di.group(1) if di else "",
    }


# Collect hand-authored host agent files (no SSOT source yet, no generated banner),
# keyed by subagent name, merging the Claude (.md) and Codex (.toml) sides.
def collect_adoptable():
    by_name = {}

    def consider(d, ext, kind):
        if not is_dir(d):
            return
        for f in sorted(os.listdir(d)):
            if not f.endswith(ext):
                continue
            name = f[: -len(ext)]
            if is_dir(os.path.join(SOURCE_DIR, name)):
                continue  # already an SSOT source
            text = read_text(os.path.join(d, f))
            if BANNER in text:
                continue  # a generated projection, not hand-authored
            e = by_name.get(name) or {"name": name}
            e[kind] = parse_claude_agent(text) if kind == "claude" else parse_codex_agent(text)
            by_name[name] = e

    consider(CLAUDE_DIR, ".md", "claude")
    consider(CODEX_DIR, ".toml", "codex")
    return by_name


# Write each adoptable host agent back as a .agents/subagents/<name>/ source.
def import_hand_authored():
    imported = 0
    for name, e in collect_adoptable().items():
        cc = e.get("claude")
        cx = e.get("codex")
        if not cc and not cx:
            continue
        if cc and cx and cc["description"] and cx["description"] and cc["description"] != cx["description"]:
            print(
                "warn: %s has different descriptions in .claude vs .codex -- keeping the Claude one" % name,
                file=sys.stderr,
            )
        meta = {"name": name, "description": (cc and cc["description"]) or (cx and cx["description"]) or ""}
        claude = {}
        if cc and cc.get("tools"):
            claude["tools"] = cc["tools"]
        if cc and cc.get("model"):
            claude["model"] = cc["model"]
        if claude:
            meta["claude"] = claude
        codex = {}
        if cx:
            if cx.get("model"):
                codex["model"] = cx["model"]
            if cx.get("model_reasoning_effort"):
                codex["model_reasoning_effort"] = cx["model_reasoning_effort"]
            if cx.get("sandbox_mode"):
                codex["sandbox_mode"] = cx["sandbox_mode"]
            if cx.get("nickname_candidates"):
                codex["nickname_candidates"] = cx["nickname_candidates"]
        if codex:
            meta["codex"] = codex
        instructions = cc["body"] if (cc and cc.get("body") and cc["body"].strip()) else (cx["instructions"] if cx else "")
        if not instructions.endswith("\n"):
            instructions += "\n"
        d = os.path.join(SOURCE_DIR, name)
        os.makedirs(d, exist_ok=True)
        write_text(os.path.join(d, "metadata.json"), json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        write_text(os.path.join(d, "instructions.md"), instructions)
        frm = " + ".join(x for x in [cc and ".claude/agents", cx and ".codex/agents"] if x)
        print("adopted %s -> %s (from %s)" % (name, rel(d), frm))
        imported += 1
    print(
        "--import: adopted %d hand-authored subagent(s) into %s" % (imported, rel(SOURCE_DIR))
        if imported
        else "--import: no hand-authored subagents to adopt"
    )
    return imported


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(
            "\n".join(
                [
                    "generate-subagents.py -- project .agents/subagents/ into Claude Code + Codex agent files.",
                    "",
                    "Usage:",
                    "  python generate-subagents.py           write .claude/agents/*.md + .codex/agents/*.toml",
                    "  python generate-subagents.py --check   exit 1 on drift (CI / pre-commit); writes nothing",
                    "  python generate-subagents.py --import  adopt hand-authored .claude/agents + .codex/agents into .agents/subagents/, then project",
                    "  python generate-subagents.py -h|--help show this help",
                    "",
                    "Source per subagent: .agents/subagents/<name>/{metadata.json, instructions.md}.",
                ]
            )
        )
        return 0

    check = "--check" in argv
    if "--import" in argv and not check:
        import_hand_authored()
    subagents = load_subagents()
    wanted = projections(subagents)
    stale = orphans(subagents)

    if check:
        drift = []
        for w in wanted:
            if not os.path.exists(w["path"]) or read_text(w["path"]) != w["content"]:
                drift.append(rel(w["path"]))
        for p in stale:
            hand = BANNER not in read_text(p)
            note = "hand-authored; run --import to adopt" if hand else "no source"
            drift.append("%s (orphan -- %s)" % (rel(p), note))
        if drift:
            print("generate-subagents --check: DRIFT in %d file(s):" % len(drift), file=sys.stderr)
            for d in drift:
                print("  - %s" % d, file=sys.stderr)
            print("Run: python tools/agent/generate-subagents.py", file=sys.stderr)
            return 1
        print(
            "generate-subagents --check: %d file(s) in sync (%d subagent(s))" % (len(wanted), len(subagents))
        )
        return 0

    for d in (CLAUDE_DIR, CODEX_DIR):
        os.makedirs(d, exist_ok=True)
    wrote = 0
    for w in wanted:
        if not os.path.exists(w["path"]) or read_text(w["path"]) != w["content"]:
            write_text(w["path"], w["content"])
            wrote += 1
    pruned = 0
    for p in stale:
        if BANNER in read_text(p):
            os.remove(p)
            pruned += 1
            print("pruned orphan %s" % rel(p))
        else:
            print(
                "kept %s -- hand-authored (no generated banner). Run --import to adopt it, or delete it by hand."
                % rel(p),
                file=sys.stderr,
            )
    print(
        "generate-subagents: %d subagent(s); %d file(s) written; %d unchanged; %d pruned"
        % (len(subagents), wrote, len(wanted) - wrote, pruned)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
