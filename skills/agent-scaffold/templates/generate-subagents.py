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
    return p[len(ROOT) + 1:].replace(os.sep, "/")


def is_generated_projection(path, text):
    """Recognize only this file's canonical, position-bound ownership marker."""
    name, ext = os.path.splitext(os.path.basename(path))
    marker = DO_NOT_EDIT.replace("%s", name)
    if ext == ".toml":
        return text.startswith("# %s\n" % marker)
    if ext == ".md":
        pattern = r"\A---\n[\s\S]*?\n---\n\n<!-- %s -->\n" % re.escape(marker)
        return re.match(pattern, text) is not None
    return False


def normalize_instructions(instructions):
    return instructions if instructions.endswith("\n") else instructions + "\n"


def validate_source(name, meta, instructions):
    if meta.get("name") != name:
        raise SystemExit(
            "subagent '%s': metadata.name='%s' must match directory name" % (name, meta.get("name"))
        )
    if not str(meta.get("description") or "").strip():
        raise SystemExit("subagent '%s': metadata.json needs a non-empty description" % name)
    return normalize_instructions(instructions)


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
        instructions = validate_source(name, meta, read_text(instr_path))
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

# Parse the losslessly representable Claude subset (simple frontmatter + body).
# Unsupported fields/structures fail closed instead of disappearing on projection.
def parse_claude_agent(text):
    m = re.match(r"^---\n([\s\S]*?)\n---\n?([\s\S]*)$", text)
    if not m:
        return None
    fm, raw_body = m.group(1), m.group(2)
    meta = {}
    allowed = {"name", "description", "tools", "model"}
    for line in fm.split("\n"):
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            raise ValueError("unsupported Claude frontmatter comment")
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            raise ValueError("unsupported Claude YAML structure")
        key, raw = kv.group(1), kv.group(2).strip()
        if key not in allowed:
            raise ValueError("unsupported Claude field '%s'" % key)
        if key in meta:
            raise ValueError("duplicate Claude field '%s'" % key)
        if re.search(r"\s#", raw) or raw.startswith(("[", "{", "|", ">", "&", "*", "!")):
            raise ValueError("unsupported Claude value for field '%s'" % key)
        if raw.startswith('"'):
            if not raw.endswith('"'):
                raise ValueError("unsupported Claude value for field '%s'" % key)
            try:
                value = json.loads(raw)
            except ValueError:
                raise ValueError("unsupported Claude value for field '%s'" % key)
            if not isinstance(value, str):
                raise ValueError("unsupported Claude value for field '%s'" % key)
        elif raw.startswith("'"):
            if not raw.endswith("'"):
                raise ValueError("unsupported Claude value for field '%s'" % key)
            value = raw[1:-1].replace("''", "'")
        else:
            value = raw
        meta[key] = value
    tools = [s.strip() for s in meta["tools"].split(",")] if meta.get("tools") else []
    tools = [s for s in tools if s]
    return {
        "name": meta.get("name"),
        "description": meta.get("description") or "",
        "tools": tools,
        "model": meta.get("model"),
        "body": re.sub(r"^\n+", "", raw_body),
    }


# Parse the losslessly representable Codex subset. Both TOML multiline string
# forms are accepted; other session-config fields fail closed before adoption.
def parse_codex_agent(text):
    multiline = re.search(
        r"(?m)^developer_instructions\s*=\s*(?P<quote>'''|\"\"\")\n"
        r"(?P<body>[\s\S]*?)(?P=quote)\s*(?:#.*)?$",
        text,
    )
    instructions = None
    scanned = text
    if multiline:
        instructions = multiline.group("body")
        if multiline.group("quote") == '"""' and "\\" in instructions:
            raise ValueError("unsupported Codex escape in basic multiline developer_instructions")
        scanned = text[: multiline.start()] + 'developer_instructions = ""' + text[multiline.end() :]

    allowed = {
        "name",
        "description",
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "nickname_candidates",
        "developer_instructions",
    }
    values = {}
    for line in scanned.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            raise ValueError("unsupported Codex comment outside developer_instructions")
        table = re.match(r"^\[\[?\s*([^\]]+?)\s*\]\]?\s*(?:#.*)?$", stripped)
        if table:
            raise ValueError("unsupported Codex field '%s'" % table.group(1))
        kv = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(.*?)\s*$", stripped)
        if not kv:
            raise ValueError("unsupported Codex TOML structure")
        key, raw = kv.group(1), kv.group(2)
        if key not in allowed:
            raise ValueError("unsupported Codex field '%s'" % key)
        if key in values:
            raise ValueError("duplicate Codex field '%s'" % key)
        values[key] = raw

    def scalar(key):
        raw = values.get(key)
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except ValueError:
            if len(raw) >= 2 and raw.startswith("'") and raw.endswith("'"):
                value = raw[1:-1].replace("''", "'")
            else:
                raise ValueError("unsupported Codex value for field '%s'" % key)
        if not isinstance(value, str):
            raise ValueError("unsupported Codex value for field '%s'" % key)
        return value

    nicks = None
    if "nickname_candidates" in values:
        try:
            nicks = json.loads(values["nickname_candidates"])
        except ValueError:
            raise ValueError("unsupported Codex value for field 'nickname_candidates'")
        if not isinstance(nicks, list) or not nicks or any(not isinstance(n, str) for n in nicks):
            raise ValueError("unsupported Codex value for field 'nickname_candidates'")
    if "developer_instructions" not in values:
        raise ValueError("missing required Codex field 'developer_instructions'")
    if instructions is None:
        instructions = scalar("developer_instructions")
    return {
        "name": scalar("name"),
        "description": scalar("description") or "",
        "model": scalar("model"),
        "model_reasoning_effort": scalar("model_reasoning_effort"),
        "sandbox_mode": scalar("sandbox_mode"),
        "nickname_candidates": nicks,
        "instructions": instructions,
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
            path = os.path.join(d, f)
            text = read_text(path)
            if is_generated_projection(path, text):
                continue  # a generated projection, not hand-authored
            try:
                parsed = parse_claude_agent(text) if kind == "claude" else parse_codex_agent(text)
            except ValueError as error:
                raise SystemExit("%s: %s" % (rel(path), error))
            if parsed is None:
                label = "Claude" if kind == "claude" else "Codex"
                raise SystemExit("cannot parse %s as a %s agent" % (rel(path), label))
            e = by_name.get(name) or {"name": name}
            e[kind] = parsed
            by_name[name] = e

    consider(CLAUDE_DIR, ".md", "claude")
    consider(CODEX_DIR, ".toml", "codex")
    return by_name


# Write each adoptable host agent back as a .agents/subagents/<name>/ source.
def import_hand_authored():
    # Validate existing sources and every host candidate before the first write.
    projections(load_subagents())
    adoptable = collect_adoptable()
    prepared = []
    for name, e in adoptable.items():
        cc = e.get("claude")
        cx = e.get("codex")
        if not cc and not cx:
            continue
        for kind, parsed, ext in (("Claude", cc, ".md"), ("Codex", cx, ".toml")):
            if not parsed:
                continue
            path = os.path.join(CLAUDE_DIR if kind == "Claude" else CODEX_DIR, name + ext)
            declared = parsed.get("name")
            if not declared:
                raise SystemExit("%s is missing required %s field 'name'" % (rel(path), kind))
            if declared != name:
                raise SystemExit(
                    "%s declares name '%s'; rename it to %s%s before --import"
                    % (rel(path), declared, name, ext)
                )
            if not str(parsed.get("description") or "").strip():
                raise SystemExit("subagent '%s': metadata.json needs a non-empty description" % name)
        if cc and cx:
            if cc["description"] != cx["description"]:
                raise SystemExit(
                    "subagent '%s': .claude/agents/%s.md and .codex/agents/%s.toml have different "
                    "descriptions; resolve the conflict before --import" % (name, name, name)
                )
            claude_instructions = normalize_instructions(cc.get("body") or "")
            codex_instructions = normalize_instructions(cx.get("instructions") or "")
            if claude_instructions != codex_instructions:
                raise SystemExit(
                    "subagent '%s': .claude/agents/%s.md and .codex/agents/%s.toml have different "
                    "instructions; resolve the conflict before --import" % (name, name, name)
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
        instructions = validate_source(
            name,
            meta,
            cc["body"] if (cc and cc.get("body") and cc["body"].strip()) else (cx["instructions"] if cx else ""),
        )
        candidate = {"name": name, "meta": meta, "instructions": instructions}
        render_claude(candidate)
        render_codex(candidate)
        frm = " + ".join(x for x in [cc and ".claude/agents", cx and ".codex/agents"] if x)
        prepared.append((name, meta, instructions, frm))

    imported = 0
    for name, meta, instructions, frm in prepared:
        d = os.path.join(SOURCE_DIR, name)
        os.makedirs(d, exist_ok=True)
        write_text(os.path.join(d, "metadata.json"), json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        write_text(os.path.join(d, "instructions.md"), instructions)
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
            hand = not is_generated_projection(p, read_text(p))
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
        if is_generated_projection(p, read_text(p)):
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
