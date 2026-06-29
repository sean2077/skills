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

const BANNER = 'do not edit by hand';

// --- Adoption (--import): turn hand-authored host agent files into SSOT sources ---

// Parse a Claude Code agent markdown (YAML frontmatter + body). Returns null when it
// has no frontmatter. Only the keys this generator emits are understood
// (name / description / tools / model); anything else is ignored.
function parseClaudeAgent(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) return null;
  const [, fm, rawBody] = m;
  const meta = {};
  for (const line of fm.split('\n')) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!kv) continue;
    let v = kv[2].trim();
    if (v.startsWith('"') && v.endsWith('"')) {
      try {
        v = JSON.parse(v);
      } catch {
        v = v.slice(1, -1);
      }
    } else if (v.startsWith("'") && v.endsWith("'")) {
      v = v.slice(1, -1);
    }
    meta[kv[1]] = v;
  }
  const tools = meta.tools
    ? meta.tools
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    : [];
  return {
    name: meta.name,
    description: meta.description || '',
    tools,
    model: meta.model,
    body: rawBody.replace(/^\n+/, ''),
  };
}

// Parse a Codex agent TOML (only the keys this generator emits).
function parseCodexAgent(text) {
  const scalar = (key) => {
    const m = text.match(new RegExp('^' + key + '\\s*=\\s*(.+)$', 'm'));
    if (!m) return undefined;
    const raw = m[1].trim();
    try {
      return JSON.parse(raw);
    } catch {
      return raw.replace(/^["']|["']$/g, '');
    }
  };
  let nicks;
  const nm = text.match(/^nickname_candidates\s*=\s*\[(.*)\]\s*$/m);
  if (nm) {
    try {
      nicks = JSON.parse('[' + nm[1] + ']');
    } catch {
      nicks = undefined;
    }
  }
  const di = text.match(/developer_instructions\s*=\s*'''\n([\s\S]*?)'''/);
  return {
    name: scalar('name'),
    description: scalar('description') || '',
    model: scalar('model'),
    model_reasoning_effort: scalar('model_reasoning_effort'),
    sandbox_mode: scalar('sandbox_mode'),
    nickname_candidates: nicks,
    instructions: di ? di[1] : '',
  };
}

// Collect hand-authored host agent files (no SSOT source yet, no generated banner),
// keyed by subagent name, merging the Claude (.md) and Codex (.toml) sides.
function collectAdoptable() {
  const byName = new Map();
  const consider = (dir, ext, kind) => {
    if (!isDir(dir)) return;
    for (const f of readdirSync(dir)) {
      if (!f.endsWith(ext)) continue;
      const name = f.slice(0, -ext.length);
      if (isDir(join(SOURCE_DIR, name))) continue; // already an SSOT source
      const text = readFileSync(join(dir, f), 'utf8');
      if (text.includes(BANNER)) continue; // a generated projection, not hand-authored
      const e = byName.get(name) || { name };
      e[kind] = kind === 'claude' ? parseClaudeAgent(text) : parseCodexAgent(text);
      byName.set(name, e);
    }
  };
  consider(CLAUDE_DIR, '.md', 'claude');
  consider(CODEX_DIR, '.toml', 'codex');
  return byName;
}

// Write each adoptable host agent back as a .agents/subagents/<name>/ source.
function importHandAuthored() {
  let imported = 0;
  for (const [name, e] of collectAdoptable()) {
    const cc = e.claude;
    const cx = e.codex;
    if (!cc && !cx) continue;
    const meta = { name, description: (cc && cc.description) || (cx && cx.description) || '' };
    const claude = {};
    if (cc && cc.tools && cc.tools.length) claude.tools = cc.tools;
    if (cc && cc.model) claude.model = cc.model;
    if (Object.keys(claude).length) meta.claude = claude;
    const codex = {};
    if (cx) {
      if (cx.model) codex.model = cx.model;
      if (cx.model_reasoning_effort) codex.model_reasoning_effort = cx.model_reasoning_effort;
      if (cx.sandbox_mode) codex.sandbox_mode = cx.sandbox_mode;
      if (cx.nickname_candidates && cx.nickname_candidates.length)
        codex.nickname_candidates = cx.nickname_candidates;
    }
    if (Object.keys(codex).length) meta.codex = codex;
    let instructions = cc && cc.body && cc.body.trim() ? cc.body : cx ? cx.instructions : '';
    if (!instructions.endsWith('\n')) instructions += '\n';
    const dir = join(SOURCE_DIR, name);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, 'metadata.json'), JSON.stringify(meta, null, 2) + '\n');
    writeFileSync(join(dir, 'instructions.md'), instructions);
    const from = [cc && '.claude/agents', cx && '.codex/agents'].filter(Boolean).join(' + ');
    console.log(`adopted ${name} → ${rel(dir)} (from ${from})`);
    imported++;
  }
  console.log(
    imported
      ? `--import: adopted ${imported} hand-authored subagent(s) into ${rel(SOURCE_DIR)}`
      : '--import: no hand-authored subagents to adopt'
  );
  return imported;
}

function main() {
  if (process.argv.includes('-h') || process.argv.includes('--help')) {
    console.log(
      [
        'generate-subagents.mjs — project .agents/subagents/ into Claude Code + Codex agent files.',
        '',
        'Usage:',
        '  node generate-subagents.mjs           write .claude/agents/*.md + .codex/agents/*.toml',
        '  node generate-subagents.mjs --check   exit 1 on drift (CI / pre-commit); writes nothing',
        '  node generate-subagents.mjs --import  adopt hand-authored .claude/agents + .codex/agents into .agents/subagents/, then project',
        '  node generate-subagents.mjs -h|--help  show this help',
        '',
        'Source per subagent: .agents/subagents/<name>/{metadata.json, instructions.md}.',
      ].join('\n')
    );
    return;
  }
  const check = process.argv.includes('--check');
  if (process.argv.includes('--import') && !check) importHandAuthored();
  const subagents = loadSubagents();
  const wanted = projections(subagents);
  const stale = orphans(subagents);

  if (check) {
    const drift = [];
    for (const { path, content } of wanted) {
      if (!existsSync(path) || readFileSync(path, 'utf8') !== content) drift.push(rel(path));
    }
    for (const p of stale) {
      const hand = !readFileSync(p, 'utf8').includes(BANNER);
      drift.push(`${rel(p)} (orphan — ${hand ? 'hand-authored; run --import to adopt' : 'no source'})`);
    }
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
  let pruned = 0;
  for (const p of stale) {
    if (readFileSync(p, 'utf8').includes(BANNER)) {
      rmSync(p);
      pruned++;
      console.log(`pruned orphan ${rel(p)}`);
    } else {
      console.error(
        `kept ${rel(p)} — hand-authored (no generated banner). Run --import to adopt it, or delete it by hand.`
      );
    }
  }
  console.log(
    `generate-subagents: ${subagents.length} subagent(s) · ${wrote} file(s) written · ${wanted.length - wrote} unchanged · ${pruned} pruned`
  );
}

main();
