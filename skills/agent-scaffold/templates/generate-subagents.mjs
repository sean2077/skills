#!/usr/bin/env node
// Generate Claude Code (.claude/agents/*.md) and Codex (.codex/agents/*.toml)
// subagent files from the authoritative source in .agents/subagents/.
//
//   node tools/agent/generate-subagents.mjs           # write projections
//   node tools/agent/generate-subagents.mjs --check   # exit 1 on drift (CI / pre-commit)
//
// Source per subagent: .agents/subagents/<name>/{metadata.json, instructions.md}.
// Generated files are marked "do not edit by hand" — edit the source and re-run.
import {
  readFileSync,
  writeFileSync,
  readdirSync,
  existsSync,
  mkdirSync,
  statSync,
  rmSync,
} from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const SOURCE_DIR = join(ROOT, '.agents', 'subagents');
const CLAUDE_DIR = join(ROOT, '.claude', 'agents');
const CODEX_DIR = join(ROOT, '.codex', 'agents');
const DO_NOT_EDIT =
  'Generated from .agents/subagents/%s; do not edit by hand. Run: node tools/agent/generate-subagents.mjs';

const isDir = (p) => existsSync(p) && statSync(p).isDirectory();

function loadSubagents() {
  if (!isDir(SOURCE_DIR)) return [];
  return readdirSync(SOURCE_DIR)
    .filter((name) => !name.startsWith('_') && isDir(join(SOURCE_DIR, name)))
    .map((name) => {
      const dir = join(SOURCE_DIR, name);
      const metaPath = join(dir, 'metadata.json');
      const instrPath = join(dir, 'instructions.md');
      if (!existsSync(metaPath) || !existsSync(instrPath)) {
        throw new Error(`subagent '${name}' is missing metadata.json or instructions.md`);
      }
      const meta = JSON.parse(readFileSync(metaPath, 'utf8'));
      if (meta.name !== name) {
        throw new Error(
          `subagent '${name}': metadata.name='${meta.name}' must match directory name`
        );
      }
      let instructions = readFileSync(instrPath, 'utf8');
      if (!instructions.endsWith('\n')) instructions += '\n';
      return { name, meta, instructions };
    });
}

// YAML single-line scalar: quote only when raw would be ambiguous.
function yamlScalar(s) {
  const oneLine = String(s)
    .replace(/\s*\n\s*/g, ' ')
    .trim();
  return /^[\s>|@`"'%#&*!?{}\[\],]|:\s|\s#|^$/.test(oneLine) ? JSON.stringify(oneLine) : oneLine;
}

function renderClaude({ name, meta, instructions }) {
  const fm = [`name: ${name}`, `description: ${yamlScalar(meta.description)}`];
  const tools = meta.claude?.tools;
  if (Array.isArray(tools) && tools.length) fm.push(`tools: ${tools.join(', ')}`);
  if (meta.claude?.model) fm.push(`model: ${meta.claude.model}`);
  return `---\n${fm.join('\n')}\n---\n\n<!-- ${DO_NOT_EDIT.replace('%s', name)} -->\n\n${instructions}`;
}

// TOML basic string (JSON.stringify is a valid superset for our text, keeps raw Unicode).
const tomlStr = (s) => JSON.stringify(String(s));

function tomlMultiline(s) {
  if (s.includes("'''"))
    throw new Error("instructions cannot contain ''' (TOML multiline literal delimiter)");
  return `'''\n${s}'''`;
}

function renderCodex({ name, meta, instructions }) {
  const c = meta.codex ?? {};
  const lines = [
    `# ${DO_NOT_EDIT.replace('%s', name)}`,
    `name = ${tomlStr(name)}`,
    `description = ${tomlStr(meta.description)}`,
  ];
  if (c.model) lines.push(`model = ${tomlStr(c.model)}`);
  if (c.model_reasoning_effort)
    lines.push(`model_reasoning_effort = ${tomlStr(c.model_reasoning_effort)}`);
  if (c.sandbox_mode) lines.push(`sandbox_mode = ${tomlStr(c.sandbox_mode)}`);
  if (Array.isArray(c.nickname_candidates) && c.nickname_candidates.length) {
    lines.push(`nickname_candidates = [${c.nickname_candidates.map(tomlStr).join(', ')}]`);
  }
  lines.push(`developer_instructions = ${tomlMultiline(instructions)}`);
  return lines.join('\n') + '\n';
}

function projections(subagents) {
  const out = [];
  for (const sa of subagents) {
    out.push({ path: join(CLAUDE_DIR, `${sa.name}.md`), content: renderClaude(sa) });
    out.push({ path: join(CODEX_DIR, `${sa.name}.toml`), content: renderCodex(sa) });
  }
  return out;
}

// Generated files with no matching source (would be stale).
function orphans(subagents) {
  const expect = new Set();
  for (const sa of subagents) {
    expect.add(join(CLAUDE_DIR, `${sa.name}.md`));
    expect.add(join(CODEX_DIR, `${sa.name}.toml`));
  }
  const found = [];
  for (const [dir, ext] of [
    [CLAUDE_DIR, '.md'],
    [CODEX_DIR, '.toml'],
  ]) {
    if (!isDir(dir)) continue;
    for (const f of readdirSync(dir)) {
      const p = join(dir, f);
      if (f.endsWith(ext) && !expect.has(p)) found.push(p);
    }
  }
  return found;
}

const rel = (p) => p.slice(ROOT.length + 1);

function main() {
  const check = process.argv.includes('--check');
  const subagents = loadSubagents();
  const wanted = projections(subagents);
  const stale = orphans(subagents);

  if (check) {
    const drift = [];
    for (const { path, content } of wanted) {
      if (!existsSync(path) || readFileSync(path, 'utf8') !== content) drift.push(rel(path));
    }
    for (const p of stale) drift.push(`${rel(p)} (orphan — no source)`);
    if (drift.length) {
      console.error(`generate-subagents --check: DRIFT in ${drift.length} file(s):`);
      for (const d of drift) console.error(`  - ${d}`);
      console.error('Run: node tools/agent/generate-subagents.mjs');
      process.exit(1);
    }
    console.log(
      `generate-subagents --check: ${wanted.length} file(s) in sync (${subagents.length} subagent(s))`
    );
    return;
  }

  for (const dir of [CLAUDE_DIR, CODEX_DIR]) mkdirSync(dir, { recursive: true });
  let wrote = 0;
  for (const { path, content } of wanted) {
    if (!existsSync(path) || readFileSync(path, 'utf8') !== content) {
      writeFileSync(path, content);
      wrote++;
    }
  }
  for (const p of stale) {
    rmSync(p);
    console.log(`pruned orphan ${rel(p)}`);
  }
  console.log(
    `generate-subagents: ${subagents.length} subagent(s) · ${wrote} file(s) written · ${wanted.length - wrote} unchanged · ${stale.length} pruned`
  );
}

main();
