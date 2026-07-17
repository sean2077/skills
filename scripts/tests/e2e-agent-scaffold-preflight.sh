#!/usr/bin/env bash
# e2e-agent-scaffold-preflight.sh — deterministic agent-scaffold preflight suite.
#
# Exercises generator parsing, ownership, import, metadata, and installer
# preflight conflicts. All writes stay inside a generated temporary directory.
#
# Usage: bash scripts/tests/e2e-agent-scaffold-preflight.sh [-h|--help]
# Exit 0 = all assertions passed, 1 = a failure. Needs git + python.
set -uo pipefail

usage() { sed -n '2,8p' "$0" | sed 's/^# \?//'; exit "${1:-0}"; }
case "${1:-}" in -h | --help) usage 0 ;; esac

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
H="$repo/skills/agent-scaffold/agent-scaffold.sh"
[ -f "$H" ] || { echo "installer not found: $H" >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "git required" >&2; exit 1; }
command -v python >/dev/null 2>&1 || { echo "python required" >&2; exit 1; }

fails=0
ok()  { printf '  \033[1;32mPASS\033[0m %s\n' "$*"; }
bad() { printf '  \033[1;31mFAIL\033[0m %s\n' "$*" >&2; fails=$((fails + 1)); }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
# JSON assertions via python (portable; avoids a jq dependency in CI).
# shellcheck disable=SC2317,SC2329  # run indirectly through check() "$@"; code varies by ShellCheck version
jmatch() { python -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["hooks"][sys.argv[2]][0]["matcher"]==sys.argv[3] else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
jcount() { python -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if len(d["hooks"][sys.argv[2]][0]["hooks"])==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
jcommand_count() { python -c 'import json,re,sys; d=json.load(open(sys.argv[1])); p=re.compile(r"(?:^|[/\s\"\x27;&|()<>]).agents/tools/hooks/"+re.escape(sys.argv[2])+r"\.sh(?=$|[\s\"\x27;&|()<>])"); n=sum(bool(p.search(str(h.get("command", "")).replace("\\", "/"))) for groups in d.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])); sys.exit(0 if n==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329
fixed_text_in_both() { grep -qF "$1" "$2" && grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
fixed_text_absent_in_both() { ! grep -qF "$1" "$2" && ! grep -qF "$1" "$3"; }
# shellcheck disable=SC2317,SC2329
logical_line_count() { python -c 'import pathlib,sys; lines=pathlib.Path(sys.argv[1]).read_bytes().splitlines(); sys.exit(0 if lines.count(sys.argv[2].encode())==int(sys.argv[3]) else 1)' "$@"; }
# shellcheck disable=SC2317,SC2329  # run indirectly through check() "$@"
is_real_dir() { [ -d "$1" ] && [ ! -L "$1" ]; }
# shellcheck disable=SC2317,SC2329
no_fixed_text() { ! grep -qF -- "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
no_exact_line() { ! grep -qxF "$2" "$1"; }
# shellcheck disable=SC2317,SC2329
both_absent() { [ ! -e "$1" ] && [ ! -e "$2" ]; }
# shellcheck disable=SC2317,SC2329
no_partial_harness() {
  local root="$1" path
  for path in AGENTS.md CLAUDE.md .agents .claude .codex tools; do
    [ ! -e "$root/$path" ] && [ ! -L "$root/$path" ] || return 1
  done
}
# shellcheck disable=SC2317,SC2329
no_generated_harness() {
  local root="$1" path
  for path in CLAUDE.md .agents .claude .codex tools; do
    [ ! -e "$root/$path" ] && [ ! -L "$root/$path" ] || return 1
  done
}

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
echo "== generator CLI rejects unknown options before help or writes =="
GOPT="$work/generator-options"; mkdir -p "$GOPT/.agents/tools"
cp "$repo/.agents/tools/generate-subagents.py" "$GOPT/.agents/tools/generate-subagents.py"
generator_before="$(find "$GOPT" -mindepth 1 -print | sort)"
( cd "$GOPT" && python .agents/tools/generate-subagents.py --help --write-anyway ) \
  >"$work/generator-help-unknown.out" 2>&1; rc=$?
check "help does not mask an unknown generator option" test "$rc" = 2
check "generator names the unknown option" grep -qF "unknown option(s): --write-anyway" "$work/generator-help-unknown.out"
( cd "$GOPT" && python .agents/tools/generate-subagents.py --write-anyway ) \
  >"$work/generator-unknown.out" 2>&1; rc=$?
check "unknown generator option exits 2" test "$rc" = 2
generator_after="$(find "$GOPT" -mindepth 1 -print | sort)"
check "unknown generator options write nothing" test "$generator_after" = "$generator_before"

echo "== malformed AGENTS markers: fail before mutation =="
B="$work/bad-agents-markers"; mkdir -p "$B"
git -C "$B" init -q -b main
git -C "$B" config user.email t@t.t; git -C "$B" config user.name tester
git -C "$B" config core.symlinks true
printf '# Project contract\n\n<!-- agent-scaffold:start -->\nKEEP-THIS-USER-TAIL\n' > "$B/AGENTS.md"
git -C "$B" add AGENTS.md && git -C "$B" commit -q -m "malformed contract fixture"
agents_before="$(git hash-object "$B/AGENTS.md")"
( cd "$B" && bash "$H" plan ) >"$work/bad-markers-plan.out" 2>&1; rc=$?
check "plan rejects malformed managed markers"       test "$rc" = 2
check "plan explains the malformed marker conflict"  grep -qF "malformed agent-scaffold markers" "$work/bad-markers-plan.out"
check "plan leaves malformed AGENTS.md byte-identical" test "$(git hash-object "$B/AGENTS.md")" = "$agents_before"
( cd "$B" && AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" upgrade ) >"$work/bad-markers-upgrade.out" 2>&1; rc=$?
check "upgrade rejects malformed markers before doctor" grep -qF "malformed agent-scaffold markers" "$work/bad-markers-upgrade.out"
check "failed upgrade leaves AGENTS.md byte-identical" test "$(git hash-object "$B/AGENTS.md")" = "$agents_before"
check "failed upgrade leaves no partial harness"      no_generated_harness "$B"

echo "== invalid hook configs: fail before capability probe or mutation =="
for fixture in claude-syntax codex-root codex-hooks claude-command codex-constant codex-overflow claude-surrogate; do
  J="$work/invalid-$fixture-hooks"; mkdir -p "$J"
  git -C "$J" init -q -b main
  git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
  git -C "$J" config core.symlinks true
  case "$fixture" in
    claude-syntax)
      rel=.claude/settings.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.claude"; printf '{"hooks":' > "$J/$rel"
      ;;
    codex-root)
      rel=.codex/hooks.json; expected="$rel: top level must be a JSON object"
      mkdir -p "$J/.codex"; printf '[]\n' > "$J/$rel"
      ;;
    codex-hooks)
      rel=.codex/hooks.json; expected="$rel: hooks must be a JSON object or null"
      mkdir -p "$J/.codex"; printf '{"hooks":[]}\n' > "$J/$rel"
      ;;
    claude-command)
      rel=.claude/settings.json
      expected="$rel: hooks.PreToolUse[0].hooks[0].command must be a string"
      mkdir -p "$J/.claude"
      printf '%s\n' '{"hooks":{"PreToolUse":[{"matcher":"Edit|MultiEdit|Write|NotebookEdit","hooks":[{"type":"command","command":[]}]}]}}' > "$J/$rel"
      ;;
    codex-constant)
      rel=.codex/hooks.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.codex"; printf '{"model":NaN}\n' > "$J/$rel"
      ;;
    codex-overflow)
      rel=.codex/hooks.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.codex"; printf '{"model":1e9999}\n' > "$J/$rel"
      ;;
    claude-surrogate)
      rel=.claude/settings.json; expected="$rel: invalid JSON"
      mkdir -p "$J/.claude"; printf '%s\n' '{"label":"\ud800"}' > "$J/$rel"
      ;;
  esac
  git -C "$J" add "$rel" && git -C "$J" commit -q -m "invalid $fixture hook fixture"
  if [ "$fixture" = claude-syntax ]; then
    (
      cd "$J" || exit 1
      bash "$H" plan --profile light --json
    ) >"$work/invalid-hook-plan.json" 2>&1; plan_rc=$?
    check "plan reports invalid hook JSON without failing to render" test "$plan_rc" = 0
    check "plan marks invalid hook JSON as attention" python - "$work/invalid-hook-plan.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
item = next(check for check in data["checks"] if check["id"] == "host.claude-hooks")
raise SystemExit(data["ok"] or item["status"] != "attention" or "invalid JSON" not in item.get("detail", ""))
PY
  fi
  (
    cd "$J" || exit 1
    AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply
  ) >"$work/invalid-$fixture-hooks.out" 2>&1; rc=$?
  check "$fixture invalid hook config exits 2"              test "$rc" = 2
  check "$fixture invalid hook config names the error"      grep -qF "$expected" "$work/invalid-$fixture-hooks.out"
  check "$fixture invalid hook config prints no traceback"  no_fixed_text "$work/invalid-$fixture-hooks.out" "Traceback"
  check "$fixture invalid hook config stops before doctor"  no_fixed_text "$work/invalid-$fixture-hooks.out" "symlink capability denied by the test fixture"
  check "$fixture invalid hook config leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"
done

J="$work/invalid-nested-hooks"; mkdir -p "$J/.claude"
git -C "$J" init -q -b main
git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
git -C "$J" config core.symlinks true
printf '%s\n' '{"hooks":{"PreToolUse":[{"matcher":"x","hooks":"bad"}]}}' > "$J/.claude/settings.json"
git -C "$J" add .claude/settings.json && git -C "$J" commit -q -m "invalid nested hook fixture"
(
  cd "$J" || exit 1
  AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply
) >"$work/invalid-nested-hooks.out" 2>&1; rc=$?
check "nested invalid hook config exits 2"              test "$rc" = 2
check "nested invalid hook config names the field"      grep -qF ".claude/settings.json: hooks.PreToolUse[0].hooks must be an array" "$work/invalid-nested-hooks.out"
check "nested invalid hook config prints no traceback"  no_fixed_text "$work/invalid-nested-hooks.out" "Traceback"
check "nested invalid hook config stops before doctor"  no_fixed_text "$work/invalid-nested-hooks.out" "symlink capability denied by the test fixture"
check "nested invalid hook config leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"

J="$work/valid-unicode-hooks"; mkdir -p "$J/.claude"
git -C "$J" init -q -b main
git -C "$J" config user.email t@t.t; git -C "$J" config user.name tester
git -C "$J" config core.symlinks true
printf '%s\n' '{"label":"\ud83d\ude00","hooks":null}' > "$J/.claude/settings.json"
git -C "$J" add .claude/settings.json && git -C "$J" commit -q -m "valid Unicode hook fixture"
(
  cd "$J" || exit 1
  AGENT_SCAFFOLD_TEST_DENY_SYMLINKS=1 bash "$H" apply
) >"$work/valid-unicode-hooks.out" 2>&1; rc=$?
check "valid Unicode pair reaches capability probe" test "$rc" = 2
check "valid Unicode pair is not rejected as JSON" no_fixed_text "$work/valid-unicode-hooks.out" "invalid JSON"
check "valid Unicode pair preserves hooks:null compatibility" grep -qF "symlink capability denied by the test fixture" "$work/valid-unicode-hooks.out"
check "valid Unicode fixture leaves repo unchanged" test -z "$(git -C "$J" status --porcelain --untracked-files=all)"

echo "== generated ownership requires the canonical marker, not prose =="
P="$work/provenance-phrase"; mkdir -p "$P/.claude/agents" "$P/.codex/agents" "$P/.agents/tools"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
printf -- '---\nname: phrase-claude\ndescription: hand-authored Claude agent\n---\n\nThis prose discusses Generated from .agents/subagents/ without claiming ownership.\nCLAUDE_PROSE_SENTINEL\n' > "$P/.claude/agents/phrase-claude.md"
printf '%s\n' \
  'name = "phrase-codex"' \
  'description = "hand-authored Codex agent"' \
  "developer_instructions = '''" \
  'This prose discusses Generated from .agents/subagents/ without claiming ownership.' \
  'CODEX_PROSE_SENTINEL' \
  "'''" > "$P/.codex/agents/phrase-codex.toml"
( cd "$P" && bash "$H" plan ) >"$work/provenance-plan.out" 2>&1; rc=$?
check "provenance plan exits 0"                    test "$rc" = 0
check "plan lists Claude prose file for adoption" grep -qF ".claude/agents/phrase-claude.md" "$work/provenance-plan.out"
check "plan lists Codex prose file for adoption"  grep -qF ".codex/agents/phrase-codex.toml" "$work/provenance-plan.out"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
( cd "$P" && python .agents/tools/generate-subagents.py --import ) >"$work/provenance-import.out" 2>&1; rc=$?
check "provenance import exits 0"                 test "$rc" = 0
check "Claude prose file is adopted into SSOT"   test -f "$P/.agents/subagents/phrase-claude/metadata.json"
check "Codex prose file is adopted into SSOT"    test -f "$P/.agents/subagents/phrase-codex/metadata.json"
check "Claude SSOT preserves prose"               grep -qF CLAUDE_PROSE_SENTINEL "$P/.agents/subagents/phrase-claude/instructions.md"
check "Codex SSOT preserves prose"                grep -qF CODEX_PROSE_SENTINEL "$P/.agents/subagents/phrase-codex/instructions.md"
check "Claude projection keeps prose"             grep -qF CLAUDE_PROSE_SENTINEL "$P/.claude/agents/phrase-claude.md"
check "Codex projection keeps prose"              grep -qF CODEX_PROSE_SENTINEL "$P/.codex/agents/phrase-codex.toml"
( cd "$P" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "provenance projections are in sync"        test "$rc" = 0
rm -rf "$P/.agents"
python - "$P/.claude/agents/phrase-claude.md" "$P/.codex/agents/phrase-codex.toml" <<'PY'
from pathlib import Path
import sys

for name in sys.argv[1:]:
    path = Path(name)
    data = path.read_bytes()
    assert b"\r" not in data
    path.write_bytes(data.replace(b"\n", b"\r\n"))
PY
( cd "$P" && bash "$H" plan ) >"$work/provenance-crlf-plan.out" 2>&1; rc=$?
check "CRLF provenance plan exits 0"               test "$rc" = 0
check "plan recognizes canonical CRLF projections" no_fixed_text "$work/provenance-crlf-plan.out" "subagent phrase-"

echo "== divergent dual-host instructions fail before adoption =="
D="$work/divergent-hosts"; mkdir -p "$D/.claude/agents" "$D/.codex/agents" "$D/.agents/tools"
printf -- '---\nname: alpha\ndescription: Claude-only control\n---\n\nALPHA_INSTRUCTIONS\n' > "$D/.claude/agents/alpha.md"
printf -- '---\nname: dual\ndescription: shared description\n---\n\nCLAUDE_ONLY_INSTRUCTIONS\n' > "$D/.claude/agents/dual.md"
printf '%s\n' \
  'name = "dual"' \
  'description = "shared description"' \
  "developer_instructions = '''" \
  'CODEX_ONLY_INSTRUCTIONS' \
  "'''" > "$D/.codex/agents/dual.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$D/.agents/tools/generate-subagents.py"
alpha_before="$(git hash-object "$D/.claude/agents/alpha.md")"
claude_before="$(git hash-object "$D/.claude/agents/dual.md")"
codex_before="$(git hash-object "$D/.codex/agents/dual.toml")"
( cd "$D" && python .agents/tools/generate-subagents.py --import ) >"$work/divergent-import.out" 2>&1; rc=$?
check "divergent import exits nonzero"             test "$rc" != 0
check "divergent import explains the conflict"     grep -qF "subagent 'dual': .claude/agents/dual.md and .codex/agents/dual.toml have different instructions" "$work/divergent-import.out"
check "conflict preserves earlier Claude input"    test "$(git hash-object "$D/.claude/agents/alpha.md")" = "$alpha_before"
check "conflict preserves dual Claude input"       test "$(git hash-object "$D/.claude/agents/dual.md")" = "$claude_before"
check "conflict preserves dual Codex input"        test "$(git hash-object "$D/.codex/agents/dual.toml")" = "$codex_before"
check "conflict writes no SSOT sources"            test ! -e "$D/.agents/subagents"

Q="$work/matching-hosts"; mkdir -p "$Q/.claude/agents" "$Q/.codex/agents" "$Q/.agents/tools"
printf -- '---\nname: matching\ndescription: shared description\n---\n\nMATCHING_INSTRUCTIONS' > "$Q/.claude/agents/matching.md"
printf '%s\n' \
  'name = "matching"' \
  'description = "shared description"' \
  "developer_instructions = '''" \
  'MATCHING_INSTRUCTIONS' \
  "'''" > "$Q/.codex/agents/matching.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Q/.agents/tools/generate-subagents.py"
( cd "$Q" && python .agents/tools/generate-subagents.py --import ) >"$work/matching-import.out" 2>&1; rc=$?
check "matching dual-host import exits 0"           test "$rc" = 0
check "matching dual-host import creates SSOT"      grep -qF MATCHING_INSTRUCTIONS "$Q/.agents/subagents/matching/instructions.md"
( cd "$Q" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "matching dual-host projections are in sync" test "$rc" = 0

echo "== hand-authored import is lossless or fails before writing =="
U="$work/unparseable-host"; mkdir -p "$U/.claude/agents" "$U/.codex/agents" "$U/.agents/tools"
printf -- '---\nname: alpha\ndescription: valid earlier candidate\n---\n\nALPHA_BEFORE_PARSE_FAILURE\n' > "$U/.claude/agents/alpha.md"
printf 'BROKEN_CLAUDE_SENTINEL\n' > "$U/.claude/agents/broken.md"
printf '%s\n' \
  'name = "broken"' \
  'description = "valid Codex counterpart"' \
  'developer_instructions = """' \
  'CODEX_COUNTERPART_SENTINEL' \
  '"""' > "$U/.codex/agents/broken.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$U/.agents/tools/generate-subagents.py"
broken_claude_before="$(git hash-object "$U/.claude/agents/broken.md")"
broken_codex_before="$(git hash-object "$U/.codex/agents/broken.toml")"
( cd "$U" && python .agents/tools/generate-subagents.py --import ) >"$work/unparseable-import.out" 2>&1; rc=$?
check "unparseable host import exits nonzero"       test "$rc" != 0
check "unparseable host names the rejected file"    grep -qF "cannot parse .claude/agents/broken.md as a Claude agent" "$work/unparseable-import.out"
check "unparseable Claude input stays byte-identical" test "$(git hash-object "$U/.claude/agents/broken.md")" = "$broken_claude_before"
check "unparseable Codex input stays byte-identical" test "$(git hash-object "$U/.codex/agents/broken.toml")" = "$broken_codex_before"
check "parse failure writes no SSOT sources"        test ! -e "$U/.agents/subagents"

M="$work/missing-import-metadata"; mkdir -p "$M/.claude/agents" "$M/.codex/agents" "$M/.agents/tools"
printf -- '---\nname: alpha\ndescription: valid earlier candidate\n---\n\nALPHA_BEFORE_METADATA_FAILURE\n' > "$M/.claude/agents/alpha.md"
printf -- '---\nname: meta\ndescription:\n---\n\nMATCHING_METADATA_INSTRUCTIONS\n' > "$M/.claude/agents/meta.md"
printf '%s\n' \
  'name = "meta"' \
  'description = ""' \
  'developer_instructions = """' \
  'MATCHING_METADATA_INSTRUCTIONS' \
  '"""' > "$M/.codex/agents/meta.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$M/.agents/tools/generate-subagents.py"
( cd "$M" && python .agents/tools/generate-subagents.py --import ) >"$work/missing-import-metadata.out" 2>&1; rc=$?
check "missing import metadata exits nonzero"       test "$rc" != 0
check "missing import metadata explains the field" grep -qF "subagent 'meta': metadata.json needs a non-empty description" "$work/missing-import-metadata.out"
check "metadata failure writes no SSOT sources"     test ! -e "$M/.agents/subagents"

T="$work/codex-basic-multiline"; mkdir -p "$T/.codex/agents" "$T/.agents/tools"
printf '%s\n' \
  'name = "basic-multiline"' \
  'description = "official basic multiline form"' \
  'developer_instructions = """' \
  'CODEX_BASIC_MULTILINE_SENTINEL' \
  '"""' > "$T/.codex/agents/basic-multiline.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$T/.agents/tools/generate-subagents.py"
( cd "$T" && python .agents/tools/generate-subagents.py --import ) >"$work/basic-multiline-import.out" 2>&1; rc=$?
check "Codex basic multiline import exits 0"        test "$rc" = 0
check "Codex basic multiline prompt is preserved"  grep -qF CODEX_BASIC_MULTILINE_SENTINEL "$T/.agents/subagents/basic-multiline/instructions.md"
( cd "$T" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "Codex basic multiline projection is in sync" test "$rc" = 0

F="$work/unsupported-host-fields"; mkdir -p "$F/.claude/agents" "$F/.agents/tools"
printf -- '---\nname: rich-claude\ndescription: unsupported Claude metadata\nmemory: project\n---\n\nRICH_CLAUDE_SENTINEL\n' > "$F/.claude/agents/rich-claude.md"
cp "$repo/.agents/tools/generate-subagents.py" "$F/.agents/tools/generate-subagents.py"
( cd "$F" && python .agents/tools/generate-subagents.py --import ) >"$work/unsupported-claude-import.out" 2>&1; rc=$?
check "unsupported Claude metadata exits nonzero"   test "$rc" != 0
check "unsupported Claude metadata names the field" grep -qF "unsupported Claude field 'memory'" "$work/unsupported-claude-import.out"
check "unsupported Claude metadata writes no SSOT" test ! -e "$F/.agents/subagents"

F="$work/unsupported-codex-fields"; mkdir -p "$F/.codex/agents" "$F/.agents/tools"
printf '%s\n' \
  'name = "rich-codex"' \
  'description = "unsupported Codex metadata"' \
  'developer_instructions = """' \
  'RICH_CODEX_SENTINEL' \
  '"""' \
  '[mcp_servers.docs]' \
  'command = "docs-server"' > "$F/.codex/agents/rich-codex.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$F/.agents/tools/generate-subagents.py"
( cd "$F" && python .agents/tools/generate-subagents.py --import ) >"$work/unsupported-codex-import.out" 2>&1; rc=$?
check "unsupported Codex metadata exits nonzero"    test "$rc" != 0
check "unsupported Codex metadata names the field" grep -qF "unsupported Codex field 'mcp_servers.docs'" "$work/unsupported-codex-import.out"
check "unsupported Codex metadata writes no SSOT"  test ! -e "$F/.agents/subagents"

N="$work/host-identity-conflict"; mkdir -p "$N/.codex/agents" "$N/.agents/tools"
printf '%s\n' \
  'name = "declared-name"' \
  'description = "name differs from the filename"' \
  "developer_instructions = '''" \
  'NAME_CONFLICT_SENTINEL' \
  "'''" > "$N/.codex/agents/filename-name.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$N/.agents/tools/generate-subagents.py"
( cd "$N" && python .agents/tools/generate-subagents.py --import ) >"$work/identity-conflict-import.out" 2>&1; rc=$?
check "host identity conflict exits nonzero"        test "$rc" != 0
check "host identity conflict explains the mismatch" grep -qF "declares name 'declared-name'; rename it to filename-name.toml before --import" "$work/identity-conflict-import.out"
check "host identity conflict writes no SSOT"       test ! -e "$N/.agents/subagents"

V="$work/description-conflict"; mkdir -p "$V/.claude/agents" "$V/.codex/agents" "$V/.agents/tools"
printf -- '---\nname: description-conflict\ndescription: Claude description\n---\n\nSHARED_DESCRIPTION_INSTRUCTIONS\n' > "$V/.claude/agents/description-conflict.md"
printf '%s\n' \
  'name = "description-conflict"' \
  'description = "Codex description"' \
  "developer_instructions = '''" \
  'SHARED_DESCRIPTION_INSTRUCTIONS' \
  "'''" > "$V/.codex/agents/description-conflict.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$V/.agents/tools/generate-subagents.py"
( cd "$V" && python .agents/tools/generate-subagents.py --import ) >"$work/description-conflict-import.out" 2>&1; rc=$?
check "description conflict exits nonzero"          test "$rc" != 0
check "description conflict explains the mismatch" grep -qF "different descriptions; resolve the conflict before --import" "$work/description-conflict-import.out"
check "description conflict writes no SSOT"        test ! -e "$V/.agents/subagents"

I="$work/inline-multiline-strings"; mkdir -p "$I/.codex/agents" "$I/.agents/tools"
printf '%s\n' \
  'name = "basic-inline"' \
  'description = "inline basic multiline"' \
  'developer_instructions = """INLINE_BASIC_SENTINEL"""' > "$I/.codex/agents/basic-inline.toml"
printf '%s\n' \
  'name = "literal-inline"' \
  'description = "inline literal multiline"' \
  "developer_instructions = '''INLINE_LITERAL_SENTINEL'''" > "$I/.codex/agents/literal-inline.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$I/.agents/tools/generate-subagents.py"
( cd "$I" && python .agents/tools/generate-subagents.py --import ) >"$work/inline-multiline-import.out" 2>&1; rc=$?
check "inline TOML multiline forms import"           test "$rc" = 0
check "inline basic prompt is exact"                 grep -qxF INLINE_BASIC_SENTINEL "$I/.agents/subagents/basic-inline/instructions.md"
check "inline literal prompt is exact"               grep -qxF INLINE_LITERAL_SENTINEL "$I/.agents/subagents/literal-inline/instructions.md"

Y="$work/claude-comment-boundary"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf '%s\n' \
  '---' \
  'name: quoted-hash' \
  'description: "  Review #123\nNext  "' \
  'model: "false"' \
  '---' \
  '' \
  'QUOTED_HASH_SENTINEL' > "$Y/.claude/agents/quoted-hash.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/quoted-hash-import.out" 2>&1; rc=$?
check "quoted hash Claude metadata imports"          test "$rc" = 0
check "quoted hash description stays exact"         grep -qxF 'description: "  Review #123\nNext  "' "$Y/.claude/agents/quoted-hash.md"
check "bool-looking model stays quoted"              grep -qxF 'model: "false"' "$Y/.claude/agents/quoted-hash.md"

Y="$work/claude-leading-body-space"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf '%s\n' \
  '---' \
  'name: leading-body-space' \
  'description: preserve intentional leading body space' \
  '---' \
  '' \
  '' \
  'LEADING_BODY_SENTINEL' > "$Y/.claude/agents/leading-body-space.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/leading-body-space-import.out" 2>&1; rc=$?
check "leading body whitespace imports"              test "$rc" = 0
check "one intentional leading body line remains"    python -c 'import pathlib,sys; raise SystemExit(pathlib.Path(sys.argv[1]).read_bytes() != b"\nLEADING_BODY_SENTINEL\n")' "$Y/.agents/subagents/leading-body-space/instructions.md"

Y="$work/claude-implicit-type"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: implicit-type\ndescription: reject implicit YAML types\nmodel: false\n---\n\nIMPLICIT_TYPE_SENTINEL\n' > "$Y/.claude/agents/implicit-type.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/implicit-type-import.out" 2>&1; rc=$?
check "implicit YAML type exits nonzero"              test "$rc" != 0
check "implicit YAML type explains string boundary"  grep -qF "implicit non-string YAML value for field 'model'" "$work/implicit-type-import.out"
check "implicit YAML type writes no SSOT"             test ! -e "$Y/.agents/subagents"

Y="$work/claude-empty-optional"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: empty-optional\ndescription: reject empty optional YAML values\nmodel:\n---\n\nEMPTY_OPTIONAL_SENTINEL\n' > "$Y/.claude/agents/empty-optional.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/empty-optional-import.out" 2>&1; rc=$?
check "empty optional YAML value exits nonzero"       test "$rc" != 0
check "empty optional YAML value is typed"            grep -qF "implicit non-string YAML value for field 'model'" "$work/empty-optional-import.out"
check "empty optional YAML value writes no SSOT"      test ! -e "$Y/.agents/subagents"

expect_empty_claude_field() {
  local slug="$1" field="$2" field_line="$3" root="$work/$1"
  mkdir -p "$root/.claude/agents" "$root/.agents/tools"
  printf -- '---\nname: %s\ndescription: explicit empty Claude option\n%s\n---\n\nEMPTY_CLAUDE_OPTION_SENTINEL\n' \
    "$slug" "$field_line" > "$root/.claude/agents/$slug.md"
  cp "$repo/.agents/tools/generate-subagents.py" "$root/.agents/tools/generate-subagents.py"
  ( cd "$root" && python .agents/tools/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                         test "$rc" != 0
  check "$slug names the empty field"                grep -qF "Claude field '$field' must not be empty" "$work/$slug.out"
  check "$slug writes no SSOT"                       test ! -e "$root/.agents/subagents"
}

expect_empty_codex_field() {
  local slug="$1" field="$2" field_line root="$work/$1"
  field_line="${3:-$field = \"\"}"
  mkdir -p "$root/.codex/agents" "$root/.agents/tools"
  printf '%s\n' \
    "name = \"$slug\"" \
    'description = "explicit empty Codex option"' \
    "$field_line" \
    "developer_instructions = 'EMPTY_CODEX_OPTION_SENTINEL'" > "$root/.codex/agents/$slug.toml"
  cp "$repo/.agents/tools/generate-subagents.py" "$root/.agents/tools/generate-subagents.py"
  ( cd "$root" && python .agents/tools/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                         test "$rc" != 0
  check "$slug names the empty field"                grep -qF "Codex field '$field' must not be empty" "$work/$slug.out"
  check "$slug writes no SSOT"                       test ! -e "$root/.agents/subagents"
}

expect_empty_claude_field empty-claude-tools tools 'tools: ""'
expect_empty_claude_field empty-claude-tools-commas tools 'tools: ", ,"'
expect_empty_claude_field empty-claude-tools-tail tools 'tools: "Read, "'
expect_empty_claude_field empty-claude-model model 'model: ""'
expect_empty_claude_field empty-claude-model-single model "model: ''"
expect_empty_codex_field empty-codex-model model
expect_empty_codex_field empty-codex-model-literal model "model = ''"
expect_empty_codex_field empty-codex-reasoning model_reasoning_effort
expect_empty_codex_field empty-codex-sandbox sandbox_mode

Y="$work/claude-value-comment"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: value-comment\ndescription: # KEEP_COMMENT\n---\n\nVALUE_COMMENT_SENTINEL\n' > "$Y/.claude/agents/value-comment.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/value-comment-import.out" 2>&1; rc=$?
check "Claude value comment exits nonzero"           test "$rc" != 0
check "Claude value comment writes no SSOT"          test ! -e "$Y/.agents/subagents"

Y="$work/codex-closing-comment"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  'name = "closing-comment"' \
  'description = "closing delimiter comment"' \
  'developer_instructions = """' \
  'CLOSING_COMMENT_SENTINEL' \
  '""" # KEEP_COMMENT' > "$Y/.codex/agents/closing-comment.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/closing-comment-import.out" 2>&1; rc=$?
check "Codex closing comment exits nonzero"          test "$rc" != 0
check "Codex closing comment writes no SSOT"         test ! -e "$Y/.agents/subagents"

expect_internal_multiline_delimiter_rejected() {
  local slug="$1" instruction_line="$2" root="$work/$1"
  mkdir -p "$root/.codex/agents" "$root/.agents/tools"
  printf '%s\n' \
    "name = \"$slug\"" \
    'description = "internal multiline delimiter"' \
    "$instruction_line" > "$root/.codex/agents/$slug.toml"
  cp "$repo/.agents/tools/generate-subagents.py" "$root/.agents/tools/generate-subagents.py"
  ( cd "$root" && python .agents/tools/generate-subagents.py --import ) >"$work/$slug.out" 2>&1; rc=$?
  check "$slug exits nonzero"                        test "$rc" != 0
  check "$slug names the rejected field"            grep -qF "unsupported Codex value for field 'developer_instructions'" "$work/$slug.out"
  check "$slug writes no SSOT"                      test ! -e "$root/.agents/subagents"
}

expect_internal_multiline_delimiter_rejected codex-internal-basic-delimiter \
  'developer_instructions = """abc"""def"""'

Y="$work/codex-literal-quote"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  "name = 'literal-quote'" \
  "description = 'can''t be one TOML literal'" \
  "developer_instructions = 'LITERAL_QUOTE_SENTINEL'" > "$Y/.codex/agents/literal-quote.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/literal-quote-import.out" 2>&1; rc=$?
check "invalid TOML literal exits nonzero"            test "$rc" != 0
check "invalid TOML literal names the field"         grep -qF "unsupported Codex value for field 'description'" "$work/literal-quote-import.out"
check "invalid TOML literal writes no SSOT"           test ! -e "$Y/.agents/subagents"

Y="$work/codex-invalid-basic-escape"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  'name = "invalid-basic-escape"' \
  'description = "a\/b"' \
  "developer_instructions = 'INVALID_BASIC_ESCAPE_SENTINEL'" > "$Y/.codex/agents/invalid-basic-escape.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/invalid-basic-escape.out" 2>&1; rc=$?
check "invalid TOML basic escape exits nonzero"       test "$rc" != 0
check "invalid TOML basic escape names the field"    grep -qF "unsupported Codex value for field 'description'" "$work/invalid-basic-escape.out"
check "invalid TOML basic escape writes no SSOT"     test ! -e "$Y/.agents/subagents"

Y="$work/codex-invalid-unicode-scalar"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  'name = "invalid-unicode-scalar"' \
  'description = "\uD800"' \
  "developer_instructions = 'INVALID_UNICODE_SENTINEL'" > "$Y/.codex/agents/invalid-unicode-scalar.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/invalid-unicode-scalar.out" 2>&1; rc=$?
check "invalid TOML Unicode scalar exits nonzero"    test "$rc" != 0
check "invalid TOML Unicode scalar names the field" grep -qF "unsupported Codex value for field 'description'" "$work/invalid-unicode-scalar.out"
check "invalid TOML Unicode scalar writes no SSOT"  test ! -e "$Y/.agents/subagents"

Y="$work/codex-raw-del"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf 'name = "raw-del"\ndescription = "a\177b"\ndeveloper_instructions = "RAW_DEL_SENTINEL"\n' > "$Y/.codex/agents/raw-del.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/codex-raw-del.out" 2>&1; rc=$?
check "raw TOML DEL exits nonzero"                   test "$rc" != 0
check "raw TOML DEL names the field"                grep -qF "unsupported Codex value for field 'description'" "$work/codex-raw-del.out"
check "raw TOML DEL writes no SSOT"                 test ! -e "$Y/.agents/subagents"

Y="$work/claude-raw-del"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: raw-del\ndescription: "a\177b"\n---\n\nRAW_DEL_SENTINEL\n' > "$Y/.claude/agents/raw-del.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/claude-raw-del.out" 2>&1; rc=$?
check "raw YAML DEL exits nonzero"                   test "$rc" != 0
check "raw YAML DEL names the field"                grep -qF "unsupported Claude value for field 'description'" "$work/claude-raw-del.out"
check "raw YAML DEL writes no SSOT"                 test ! -e "$Y/.agents/subagents"

Y="$work/claude-raw-noncharacter"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
python - "$Y/.claude/agents/raw-noncharacter.md" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(
    '---\nname: raw-noncharacter\ndescription: "a%sb"\n---\n\nRAW_NONCHARACTER_SENTINEL\n'
    % chr(0xFFFE),
    encoding="utf-8",
)
PY
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/claude-raw-noncharacter.out" 2>&1; rc=$?
check "raw YAML noncharacter exits nonzero"          test "$rc" != 0
check "raw YAML noncharacter names the field"       grep -qF "unsupported Claude value for field 'description'" "$work/claude-raw-noncharacter.out"
check "raw YAML noncharacter writes no SSOT"        test ! -e "$Y/.agents/subagents"

Y="$work/codex-raw-tab"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf 'name = "raw-tab"\ndescription = "a\tb"\ndeveloper_instructions = "RAW_TAB_SENTINEL"\n' > "$Y/.codex/agents/raw-tab.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/codex-raw-tab.out" 2>&1; rc=$?
check "raw TOML TAB imports"                         test "$rc" = 0
check "raw TOML TAB stays semantic"                 python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if d["description"] == "a\tb" else 1)' "$Y/.agents/subagents/raw-tab/metadata.json"
( cd "$Y" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "raw TOML TAB projection is in sync"           test "$rc" = 0

Y="$work/source-escaped-del"; mkdir -p "$Y/.agents/subagents/escaped-del" "$Y/.agents/tools"
printf '%s\n' '{"name":"escaped-del","description":"a\u007fb"}' > "$Y/.agents/subagents/escaped-del/metadata.json"
printf 'ESCAPED_DEL_SOURCE\n' > "$Y/.agents/subagents/escaped-del/instructions.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py ) >"$work/source-escaped-del.out" 2>&1; rc=$?
check "escaped DEL source generates"                 test "$rc" = 0
check "escaped DEL projections stay escaped"        python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; sys.exit(0 if all(b"\x7f" not in d and b"\\u007f" in d for d in data) else 1)' "$Y/.claude/agents/escaped-del.md" "$Y/.codex/agents/escaped-del.toml"
( cd "$Y" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "escaped DEL projections are in sync"          test "$rc" = 0

Y="$work/source-yaml-boundary"; mkdir -p "$Y/.agents/subagents/yaml-boundary" "$Y/.agents/tools"
printf '%s\n' '{"name":"yaml-boundary","description":"a\ufffeb\uffff"}' > "$Y/.agents/subagents/yaml-boundary/metadata.json"
printf 'YAML_BOUNDARY_SOURCE\n' > "$Y/.agents/subagents/yaml-boundary/instructions.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py ) >"$work/source-yaml-boundary.out" 2>&1; rc=$?
check "YAML boundary source generates"               test "$rc" = 0
check "YAML boundary projections stay escaped"      python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; raw=(chr(0xfffe).encode(),chr(0xffff).encode()); sys.exit(0 if all(not any(c in d for c in raw) and b"\\ufffe" in d and b"\\uffff" in d for d in data) else 1)' "$Y/.claude/agents/yaml-boundary.md" "$Y/.codex/agents/yaml-boundary.toml"
( cd "$Y" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "YAML boundary projections are in sync"        test "$rc" = 0

Y="$work/host-escaped-del"; mkdir -p "$Y/.claude/agents" "$Y/.codex/agents" "$Y/.agents/tools"
printf -- '---\nname: escaped-del-import\ndescription: "a\\u007fb"\n---\n\nESCAPED_DEL_IMPORT_SENTINEL\n' > "$Y/.claude/agents/escaped-del-import.md"
printf '%s\n' \
  'name = "escaped-del-import"' \
  'description = "a\u007Fb"' \
  "developer_instructions = '''" \
  'ESCAPED_DEL_IMPORT_SENTINEL' \
  "'''" > "$Y/.codex/agents/escaped-del-import.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/host-escaped-del.out" 2>&1; rc=$?
check "escaped DEL host import succeeds"             test "$rc" = 0
check "escaped DEL host import stays semantic"       python -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if d["description"] == "a\x7fb" else 1)' "$Y/.agents/subagents/escaped-del-import/metadata.json"
check "escaped DEL host projections stay escaped"   python -c 'import pathlib,sys; data=[pathlib.Path(p).read_bytes() for p in sys.argv[1:]]; sys.exit(0 if all(b"\x7f" not in d and b"\\u007f" in d for d in data) else 1)' "$Y/.claude/agents/escaped-del-import.md" "$Y/.codex/agents/escaped-del-import.toml"
( cd "$Y" && python .agents/tools/generate-subagents.py --check ) >/dev/null 2>&1; rc=$?
check "escaped DEL host projections are in sync"     test "$rc" = 0

Y="$work/claude-invalid-plain-colon"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: invalid-plain-colon\ndescription: value: changes YAML structure\n---\n\nINVALID_PLAIN_COLON_SENTINEL\n' > "$Y/.claude/agents/invalid-plain-colon.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/invalid-plain-colon.out" 2>&1; rc=$?
check "invalid YAML plain colon exits nonzero"        test "$rc" != 0
check "invalid YAML plain colon names the field"     grep -qF "unsupported Claude value for field 'description'" "$work/invalid-plain-colon.out"
check "invalid YAML plain colon writes no SSOT"      test ! -e "$Y/.agents/subagents"

Y="$work/claude-invalid-plain-dash"; mkdir -p "$Y/.claude/agents" "$Y/.agents/tools"
printf -- '---\nname: invalid-plain-dash\ndescription: - changes YAML structure\n---\n\nINVALID_PLAIN_DASH_SENTINEL\n' > "$Y/.claude/agents/invalid-plain-dash.md"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/invalid-plain-dash.out" 2>&1; rc=$?
check "invalid YAML plain dash exits nonzero"         test "$rc" != 0
check "invalid YAML plain dash names the field"      grep -qF "unsupported Claude value for field 'description'" "$work/invalid-plain-dash.out"
check "invalid YAML plain dash writes no SSOT"       test ! -e "$Y/.agents/subagents"

Y="$work/codex-duplicate-nicknames"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  'name = "duplicate-nicknames"' \
  'description = "duplicate nickname candidates"' \
  'nickname_candidates = ["Twin", "Twin"]' \
  "developer_instructions = 'DUPLICATE_NICKNAME_SENTINEL'" > "$Y/.codex/agents/duplicate-nicknames.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/duplicate-nicknames-import.out" 2>&1; rc=$?
check "duplicate nicknames exit nonzero"              test "$rc" != 0
check "duplicate nicknames explain uniqueness"       grep -qF "nickname_candidates must contain unique names" "$work/duplicate-nicknames-import.out"
check "duplicate nicknames write no SSOT"             test ! -e "$Y/.agents/subagents"

Y="$work/codex-invalid-nickname"; mkdir -p "$Y/.codex/agents" "$Y/.agents/tools"
printf '%s\n' \
  'name = "invalid-nickname"' \
  'description = "invalid nickname characters"' \
  'nickname_candidates = ["bad@name"]' \
  "developer_instructions = 'INVALID_NICKNAME_SENTINEL'" > "$Y/.codex/agents/invalid-nickname.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$Y/.agents/tools/generate-subagents.py"
( cd "$Y" && python .agents/tools/generate-subagents.py --import ) >"$work/invalid-nickname-import.out" 2>&1; rc=$?
check "invalid nickname exits nonzero"                test "$rc" != 0
check "invalid nickname explains character set"      grep -qF "nickname_candidates use only ASCII letters, digits, spaces, hyphens, and underscores" "$work/invalid-nickname-import.out"
check "invalid nickname writes no SSOT"               test ! -e "$Y/.agents/subagents"

N="$work/dual-host-name-subset"; mkdir -p "$N/.codex/agents" "$N/.agents/tools"
printf '%s\n' \
  'name = "pr_explorer"' \
  'description = "official Codex-only identity shape"' \
  "developer_instructions = '''NAME_SUBSET_SENTINEL'''" > "$N/.codex/agents/pr-explorer.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$N/.agents/tools/generate-subagents.py"
( cd "$N" && python .agents/tools/generate-subagents.py --import ) >"$work/name-subset-import.out" 2>&1; rc=$?
check "Codex-only name shape exits nonzero"           test "$rc" != 0
check "Codex-only name explains dual-host subset"    grep -qF "not dual-host compatible; use lowercase letters separated by hyphens" "$work/name-subset-import.out"
check "Codex-only name writes no SSOT"                test ! -e "$N/.agents/subagents"

N="$work/windows-reserved-name"; mkdir -p "$N/.claude/agents" "$N/.agents/tools"
printf -- '---\nname: con\ndescription: Windows reserved filename\n---\n\nWINDOWS_RESERVED_SENTINEL\n' > "$N/.claude/agents/portable-name.md"
cp "$repo/.agents/tools/generate-subagents.py" "$N/.agents/tools/generate-subagents.py"
( cd "$N" && python .agents/tools/generate-subagents.py --import ) >"$work/windows-reserved-name.out" 2>&1; rc=$?
check "Windows-reserved name exits nonzero"           test "$rc" != 0
check "Windows-reserved name explains portability"   grep -qF "agent name 'con' is reserved on Windows" "$work/windows-reserved-name.out"
check "Windows-reserved name writes no SSOT"          test ! -e "$N/.agents/subagents"

N="$work/case-colliding-names"; mkdir -p "$N/.claude/agents" "$N/.codex/agents" "$N/.agents/tools"
printf -- '---\nname: Review\ndescription: uppercase Claude identity\n---\n\nCASE_COLLISION_SENTINEL\n' > "$N/.claude/agents/Review.md"
printf '%s\n' \
  'name = "review"' \
  'description = "lowercase Codex identity"' \
  "developer_instructions = '''CASE_COLLISION_SENTINEL'''" > "$N/.codex/agents/review.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$N/.agents/tools/generate-subagents.py"
( cd "$N" && python .agents/tools/generate-subagents.py --import ) >"$work/case-collision-import.out" 2>&1; rc=$?
check "case-colliding names exit nonzero"             test "$rc" != 0
check "case-colliding names write no SSOT"            test ! -e "$N/.agents/subagents"

C="$work/source-projection-collision"; mkdir -p "$C/.agents/subagents/sourced" "$C/.claude/agents" "$C/.agents/tools"
printf '%s\n' '{"name":"sourced","description":"existing source"}' > "$C/.agents/subagents/sourced/metadata.json"
printf 'SOURCE_INSTRUCTIONS\n' > "$C/.agents/subagents/sourced/instructions.md"
printf -- '---\nname: sourced\ndescription: hand-authored projection\n---\n\nHAND_PROJECTION_SENTINEL\n' > "$C/.claude/agents/sourced.md"
cp "$repo/.agents/tools/generate-subagents.py" "$C/.agents/tools/generate-subagents.py"
git -C "$C" init -q -b main
git -C "$C" config user.email t@t.t; git -C "$C" config user.name tester
git -C "$C" commit -q --allow-empty -m init
collision_before="$(git hash-object "$C/.claude/agents/sourced.md")"
( cd "$C" && bash "$H" plan ) >"$work/source-collision-plan.out" 2>&1; rc=$?
check "source collision plan exits 0"                test "$rc" = 0
check "source collision plan requires resolution"    grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced" "$work/source-collision-plan.out"
( cd "$C" && python .agents/tools/generate-subagents.py --import ) >"$work/source-collision-import.out" 2>&1; rc=$?
check "source collision import exits nonzero"        test "$rc" != 0
check "source collision import explains conflict"   grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced" "$work/source-collision-import.out"
check "source collision import preserves projection" test "$(git hash-object "$C/.claude/agents/sourced.md")" = "$collision_before"
printf -- '---\nname: sourced\ndescription: hand-authored projection\n---\n\nHAND_PROJECTION_SENTINEL\n' > "$C/.claude/agents/sourced.md"
( cd "$C" && python .agents/tools/generate-subagents.py ) >"$work/source-collision-project.out" 2>&1; rc=$?
check "default projection collision exits nonzero"  test "$rc" != 0
check "default collision preserves projection"      test "$(git hash-object "$C/.claude/agents/sourced.md")" = "$collision_before"

C="$work/source-codex-collision"; mkdir -p "$C/.agents/subagents/sourced-codex" "$C/.codex/agents" "$C/.agents/tools"
printf '%s\n' '{"name":"sourced-codex","description":"existing source"}' > "$C/.agents/subagents/sourced-codex/metadata.json"
printf 'SOURCE_INSTRUCTIONS\n' > "$C/.agents/subagents/sourced-codex/instructions.md"
printf '%s\n' \
  'name = "sourced-codex"' \
  'description = "hand-authored Codex projection"' \
  "developer_instructions = '''HAND_CODEX_PROJECTION_SENTINEL'''" > "$C/.codex/agents/sourced-codex.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$C/.agents/tools/generate-subagents.py"
git -C "$C" init -q -b main
git -C "$C" config user.email t@t.t; git -C "$C" config user.name tester
git -C "$C" commit -q --allow-empty -m init
codex_collision_before="$(git hash-object "$C/.codex/agents/sourced-codex.toml")"
( cd "$C" && bash "$H" plan ) >"$work/source-codex-collision-plan.out" 2>&1; rc=$?
check "Codex source collision plan exits 0"          test "$rc" = 0
check "Codex source collision plan needs resolution" grep -qF "hand-authored projection conflicts with existing .agents/subagents/sourced-codex" "$work/source-codex-collision-plan.out"
( cd "$C" && python .agents/tools/generate-subagents.py --import ) >"$work/source-codex-collision-import.out" 2>&1; rc=$?
check "Codex source collision import exits nonzero"  test "$rc" != 0
check "Codex collision import preserves projection" test "$(git hash-object "$C/.codex/agents/sourced-codex.toml")" = "$codex_collision_before"
check "Codex import conflict writes no Claude side"  test ! -e "$C/.claude/agents/sourced-codex.md"
( cd "$C" && python .agents/tools/generate-subagents.py ) >"$work/source-codex-collision-project.out" 2>&1; rc=$?
check "Codex default collision exits nonzero"        test "$rc" != 0
check "Codex default preserves projection"           test "$(git hash-object "$C/.codex/agents/sourced-codex.toml")" = "$codex_collision_before"
check "Codex default conflict writes no Claude side" test ! -e "$C/.claude/agents/sourced-codex.md"

P="$work/projection-parent-conflict"; mkdir -p "$P/.claude/agents" "$P/.agents/tools"
printf -- '---\nname: parent-conflict\ndescription: projection parent is not a directory\n---\n\nPARENT_CONFLICT_SENTINEL\n' > "$P/.claude/agents/parent-conflict.md"
printf 'not a directory\n' > "$P/.codex"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
parent_before="$(git hash-object "$P/.claude/agents/parent-conflict.md")"
( cd "$P" && python .agents/tools/generate-subagents.py --import ) >"$work/projection-parent-conflict.out" 2>&1; rc=$?
check "projection parent conflict exits nonzero"      test "$rc" != 0
check "projection parent conflict names the path"    grep -qF ".codex: expected a directory" "$work/projection-parent-conflict.out"
check "projection parent conflict writes no SSOT"    test ! -e "$P/.agents/subagents"
check "projection parent preserves host input"       test "$(git hash-object "$P/.claude/agents/parent-conflict.md")" = "$parent_before"

P="$work/noncanonical-host-extension"; mkdir -p "$P/.claude/agents" "$P/.codex/agents" "$P/.agents/tools"
printf -- '---\nname: alias\ndescription: hand-authored uppercase extension\n---\n\nUPPERCASE_EXTENSION_SENTINEL\n' > "$P/.claude/agents/alias.MD"
printf '%s\n' \
  'name = "alias"' \
  'description = "Codex alias candidate"' \
  "developer_instructions = 'UPPERCASE_EXTENSION_SENTINEL'" > "$P/.codex/agents/alias.toml"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
alias_before="$(git hash-object "$P/.claude/agents/alias.MD")"
( cd "$P" && bash "$H" plan ) >"$work/noncanonical-extension-plan.out" 2>&1; rc=$?
check "noncanonical extension plan exits 0"          test "$rc" = 0
check "noncanonical extension plan explains case"   grep -qF "host agent extension must be lowercase .md" "$work/noncanonical-extension-plan.out"
( cd "$P" && python .agents/tools/generate-subagents.py --import ) >"$work/noncanonical-extension.out" 2>&1; rc=$?
check "noncanonical host extension exits nonzero"     test "$rc" != 0
check "noncanonical extension explains lowercase"    grep -qF "host agent extension must be lowercase .md" "$work/noncanonical-extension.out"
check "noncanonical extension writes no SSOT"         test ! -e "$P/.agents/subagents"
check "noncanonical extension preserves host input"  test "$(git hash-object "$P/.claude/agents/alias.MD")" = "$alias_before"

P="$work/projection-temp-conflict"; mkdir -p "$P/.claude/agents" "$P/.codex/agents/alpha.toml.tmp" "$P/.agents/tools"
printf -- '---\nname: alpha\ndescription: temporary projection conflict\n---\n\nTEMP_CONFLICT_SENTINEL\n' > "$P/.claude/agents/alpha.md"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
temp_before="$(git hash-object "$P/.claude/agents/alpha.md")"
( cd "$P" && python .agents/tools/generate-subagents.py --import ) >"$work/projection-temp-conflict.out" 2>&1; rc=$?
check "projection temp conflict exits nonzero"        test "$rc" != 0
check "projection temp conflict names the path"      grep -qF ".codex/agents/alpha.toml.tmp: temporary write path already exists" "$work/projection-temp-conflict.out"
check "projection temp conflict writes no SSOT"      test ! -e "$P/.agents/subagents"
check "projection temp preserves host input"         test "$(git hash-object "$P/.claude/agents/alpha.md")" = "$temp_before"

P="$work/stale-path-conflict"; mkdir -p "$P/.agents/subagents/alpha" "$P/.claude/agents/orphan.md" "$P/.agents/tools"
printf '%s\n' '{"name":"alpha","description":"stale path preflight"}' > "$P/.agents/subagents/alpha/metadata.json"
printf 'STALE_PATH_SOURCE\n' > "$P/.agents/subagents/alpha/instructions.md"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
( cd "$P" && python .agents/tools/generate-subagents.py ) >"$work/stale-path-conflict.out" 2>&1; rc=$?
check "stale path conflict exits nonzero"             test "$rc" != 0
check "stale path conflict names the path"           grep -qF ".claude/agents/orphan.md: expected a regular file" "$work/stale-path-conflict.out"
check "stale conflict writes no wanted projection"   test ! -e "$P/.claude/agents/alpha.md"
check "stale conflict writes no Codex projection"    test ! -e "$P/.codex/agents/alpha.toml"

P="$work/check-projection-root-file"; mkdir -p "$P/.claude" "$P/.agents/tools"
printf 'NOT_A_DIRECTORY\n' > "$P/.claude/agents"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
( cd "$P" && python .agents/tools/generate-subagents.py --check ) >"$work/check-projection-root-file.out" 2>&1; rc=$?
check "check rejects projection root file"           test "$rc" != 0
check "check names malformed projection root"       grep -qF ".claude/agents: expected a directory" "$work/check-projection-root-file.out"

P="$work/noncanonical-host-basename"; mkdir -p "$P/.agents/subagents/foo" "$P/.agents/tools"
printf '%s\n' '{"name":"foo","description":"case-only host basename"}' > "$P/.agents/subagents/foo/metadata.json"
printf 'NONCANONICAL_BASENAME_SENTINEL\n' > "$P/.agents/subagents/foo/instructions.md"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
( cd "$P" && python .agents/tools/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "basename fixture setup exits 0"               test "$rc" = 0
python - "$P/.claude/agents/foo.md" "$P/.claude/agents/Foo.md" <<'PY'
import os
import sys

source, target = sys.argv[1:]
hop = source + ".case-hop"
os.replace(source, hop)
os.replace(hop, target)
PY
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
( cd "$P" && bash "$H" plan ) >"$work/noncanonical-basename-plan.out" 2>&1; rc=$?
check "noncanonical basename plan exits 0"           test "$rc" = 0
check "noncanonical basename plan names the file"   grep -qF ".claude/agents/Foo.md" "$work/noncanonical-basename-plan.out"
( cd "$P" && python .agents/tools/generate-subagents.py --check ) >"$work/noncanonical-basename-check.out" 2>&1; rc=$?
check "check rejects noncanonical basename"         test "$rc" != 0
check "check explains noncanonical basename"        grep -qF "agent name 'Foo' is not dual-host compatible" "$work/noncanonical-basename-check.out"
( cd "$P" && python .agents/tools/generate-subagents.py ) >"$work/noncanonical-basename-write.out" 2>&1; rc=$?
check "write rejects noncanonical basename"         test "$rc" != 0
check "write creates no parallel lowercase file"    python -c 'import os,sys; names=os.listdir(sys.argv[1]); sys.exit(0 if "Foo.md" in names and "foo.md" not in names else 1)' "$P/.claude/agents"

P="$work/hidden-host-agent"; mkdir -p "$P/.claude/agents"
printf -- '---\nname: hidden\ndescription: hidden host filename\n---\n\nHIDDEN_HOST_SENTINEL\n' > "$P/.claude/agents/.hidden.md"
printf -- '---\nname: double-hidden\ndescription: double hidden host filename\n---\n\nDOUBLE_HIDDEN_HOST_SENTINEL\n' > "$P/.claude/agents/..double-hidden.md"
git -C "$P" init -q -b main
git -C "$P" config user.email t@t.t; git -C "$P" config user.name tester
git -C "$P" commit -q --allow-empty -m init
( cd "$P" && bash "$H" plan ) >"$work/hidden-host-plan.out" 2>&1; rc=$?
check "hidden host plan exits 0"                     test "$rc" = 0
check "hidden host plan names the file"             grep -qF ".claude/agents/.hidden.md" "$work/hidden-host-plan.out"
check "double-hidden host plan names the file"      grep -qF ".claude/agents/..double-hidden.md" "$work/hidden-host-plan.out"

P="$work/source-entry-file"; mkdir -p "$P/.agents/subagents/source-file" "$P/.agents/tools"
printf '%s\n' '{"name":"source-file","description":"source entry shape"}' > "$P/.agents/subagents/source-file/metadata.json"
printf 'SOURCE_ENTRY_PROJECTION_SENTINEL\n' > "$P/.agents/subagents/source-file/instructions.md"
cp "$repo/.agents/tools/generate-subagents.py" "$P/.agents/tools/generate-subagents.py"
( cd "$P" && python .agents/tools/generate-subagents.py ) >/dev/null 2>&1; rc=$?
check "source entry fixture setup exits 0"          test "$rc" = 0
rm -rf "$P/.agents/subagents/source-file"
printf 'SOURCE_ENTRY_FILE_SENTINEL\n' > "$P/.agents/subagents/source-file"
( cd "$P" && python .agents/tools/generate-subagents.py ) >"$work/source-entry-file.out" 2>&1; rc=$?
check "source entry file exits nonzero"             test "$rc" != 0
check "source entry file explains directory shape" grep -qF ".agents/subagents/source-file: expected a directory" "$work/source-entry-file.out"
check "source entry file stays byte-identical"      grep -qxF "SOURCE_ENTRY_FILE_SENTINEL" "$P/.agents/subagents/source-file"
check "source entry failure preserves projections" fixed_text_in_both "SOURCE_ENTRY_PROJECTION_SENTINEL" "$P/.claude/agents/source-file.md" "$P/.codex/agents/source-file.toml"

expect_invalid_metadata() {
  local slug="$1" json="$2" needle="$3" root="$work/source-metadata-$1"
  mkdir -p "$root/.agents/subagents/$slug" "$root/.agents/tools"
  printf '%s\n' "$json" > "$root/.agents/subagents/$slug/metadata.json"
  printf 'INVALID_SOURCE_METADATA_SENTINEL\n' > "$root/.agents/subagents/$slug/instructions.md"
  cp "$repo/.agents/tools/generate-subagents.py" "$root/.agents/tools/generate-subagents.py"
  ( cd "$root" && python .agents/tools/generate-subagents.py ) >"$work/source-metadata-$slug.out" 2>&1; rc=$?
  check "$slug metadata exits nonzero"              test "$rc" != 0
  check "$slug metadata explains type"             grep -qF "$needle" "$work/source-metadata-$slug.out"
  check "$slug metadata writes no projections"     both_absent "$root/.claude/agents/$slug.md" "$root/.codex/agents/$slug.toml"
}

expect_invalid_metadata description-type \
  '{"name":"description-type","description":["not","a","string"]}' \
  "metadata.description must be a non-empty string"
expect_invalid_metadata claude-tools-type \
  '{"name":"claude-tools-type","description":"bad tools","claude":{"tools":"Read"}}' \
  "metadata.claude.tools must be a non-empty list of strings"
expect_invalid_metadata claude-tool-comma \
  '{"name":"claude-tool-comma","description":"ambiguous tool","claude":{"tools":["Read,Write"]}}' \
  "metadata.claude.tools entries must not contain commas or surrounding whitespace"
expect_invalid_metadata claude-tool-padding \
  '{"name":"claude-tool-padding","description":"padded tool","claude":{"tools":[" Read "]}}' \
  "metadata.claude.tools entries must not contain commas or surrounding whitespace"
expect_invalid_metadata codex-model-type \
  '{"name":"codex-model-type","description":"bad model","codex":{"model":{"unexpected":true}}}' \
  "metadata.codex.model must be a non-empty string"
expect_invalid_metadata codex-sandbox-type \
  '{"name":"codex-sandbox-type","description":"bad sandbox","codex":{"sandbox_mode":false}}' \
  "metadata.codex.sandbox_mode must be a non-empty string"
expect_invalid_metadata source-unicode-scalar \
  '{"name":"source-unicode-scalar","description":"\ud800"}' \
  "metadata.description contains an invalid Unicode scalar value"

echo
if [ "$fails" -eq 0 ]; then echo "OK: agent-scaffold preflight suite passed"; exit 0; fi
echo "FAIL: $fails agent-scaffold preflight assertion(s) failed"; exit 1
