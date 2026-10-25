import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import net from "node:net";
import { delimiter, isAbsolute, join } from "node:path";

const usage = "Usage: node steer-codex.mjs [UTF8_FILE|-]\nNo argument: read MESSAGE. Target: TARGET_THREAD_ID and TARGET_CODEX_ENDPOINT or TARGET_CODEX_HOME. Optional local proxy: CODEX_BIN (native executable or JS launcher). Requires Node.js 22.4+.";
const [source, ...extra] = process.argv.slice(2);
if (source === "--help" && extra.length === 0) {
  console.log(usage);
  process.exit(0);
}

let ws, bridge, proxy, pending, rejectOpen, fatal;
let closing = false, steerAttempted = false, nextId = 0;
const connections = new Set();
let deadline;

function abort(message) {
  if (closing || fatal) return;
  fatal = new Error(message);
  rejectOpen?.(fatal);
  if (pending) {
    clearTimeout(pending.timer);
    pending.reject(fatal);
    pending = undefined;
  }
}

function timeout() {
  if (fatal) throw fatal;
  const remaining = deadline - Date.now();
  if (remaining <= 0) throw new Error("Operation timed out");
  return Math.min(5000, remaining);
}

// Windows npm installs expose only a .cmd shim; run its JS launcher without a shell.
function codexBinary() {
  if (process.env.CODEX_BIN) return process.env.CODEX_BIN;
  if (process.platform !== "win32") return "codex";
  for (const dir of (process.env.PATH || "").split(delimiter).filter(Boolean)) {
    if (existsSync(join(dir, "codex.exe"))) return join(dir, "codex.exe");
    const launcher = join(dir, "node_modules", "@openai", "codex", "bin", "codex.js");
    if (existsSync(join(dir, "codex.cmd")) && existsSync(launcher)) return launcher;
  }
  return "codex";
}

// The native proxy forwards WebSocket bytes, not JSON lines. Keep its temporary
// loopback bridge private to one connection carrying this unguessable path.
async function proxyEndpoint(path) {
  const binary = codexBinary();
  if (/\.(cmd|bat)$/i.test(binary)) throw new Error("Use a native CODEX_BIN executable or JS launcher, not a shell wrapper");
  const secretPath = "/" + randomBytes(24).toString("hex");
  bridge = net.createServer(connection => {
    connections.add(connection);
    connection.once("close", () => connections.delete(connection));
    connection.on("error", () => connection.destroy());
    connection.setTimeout(5000, () => connection.destroy());
    let header = Buffer.alloc(0);
    function handshake(chunk) {
      header = Buffer.concat([header, chunk]);
      if (header.length > 16384) return connection.destroy();
      if (!header.includes("\r\n\r\n")) return;
      if (!header.toString("latin1").startsWith(`GET ${secretPath} HTTP/1.1\r\n`) || proxy) {
        return connection.destroy();
      }
      connection.off("data", handshake);
      connection.setTimeout(0);
      bridge.close();
      for (const other of connections) if (other !== connection) other.destroy();
      const args = ["app-server", "proxy", "--sock", path];
      try {
        proxy = /\.[cm]?js$/i.test(binary)
          ? spawn(process.execPath, [binary, ...args], { stdio: ["pipe", "pipe", "ignore"] })
          : spawn(binary, args, { stdio: ["pipe", "pipe", "ignore"] });
      } catch {
        // Windows can reject some launchers synchronously (EINVAL/EFTYPE).
        abort("Cannot launch Codex proxy; check CODEX_BIN");
        return connection.destroy();
      }
      proxy.on("error", () => abort("Cannot launch Codex proxy; check CODEX_BIN"));
      proxy.on("exit", () => abort("Codex proxy closed; check the intended live endpoint"));
      proxy.stdin.on("error", () => abort("Codex proxy write failed"));
      proxy.stdout.on("error", () => abort("Codex proxy read failed"));
      proxy.stdin.write(header);
      connection.pipe(proxy.stdin);
      proxy.stdout.pipe(connection);
    }
    connection.on("data", handshake);
  });
  await new Promise((resolve, reject) => {
    bridge.on("error", () => {
      reject(new Error("Cannot open the local Codex proxy bridge"));
      abort("Local Codex proxy bridge failed");
    });
    bridge.listen(0, "127.0.0.1", resolve);
  });
  return `ws://127.0.0.1:${bridge.address().port}${secretPath}`;
}

class RpcError extends Error {
  constructor(method, code) {
    super(`${method} rejected (RPC ${code})`);
    this.method = method;
  }
}

async function connect(endpoint, viaProxy) {
  try { ws = new WebSocket(endpoint); }
  catch { throw new Error("Cannot open the supplied WebSocket endpoint"); }
  ws.addEventListener("error", () => abort(viaProxy
    ? "Codex proxy connection failed; check the intended live endpoint and CODEX_BIN"
    : "WebSocket connection failed"));
  ws.addEventListener("close", () => abort("WebSocket connection closed"));
  ws.addEventListener("message", event => {
    try {
      const reply = JSON.parse(event.data);
      if (!reply || typeof reply !== "object" || Array.isArray(reply)) throw new Error();
      // Notifications and server requests are not acknowledgements or approvals.
      if ("method" in reply || !pending || reply.id !== pending.id) return;
      const hasError = Object.hasOwn(reply, "error");
      if (hasError === Object.hasOwn(reply, "result")) throw new Error();
      if (hasError && (!reply.error || !Number.isInteger(reply.error.code) || typeof reply.error.message !== "string")) throw new Error();
      const call = pending;
      pending = undefined;
      clearTimeout(call.timer);
      if (hasError) call.reject(new RpcError(call.method, reply.error.code));
      else call.resolve(reply.result);
    } catch { abort("Invalid JSON-RPC response"); }
  });
  let timer;
  try {
    await new Promise((resolve, reject) => {
      rejectOpen = reject;
      timer = setTimeout(() => abort("WebSocket connection timed out"), timeout());
      ws.addEventListener("open", resolve, { once: true });
    });
  } finally {
    clearTimeout(timer);
    rejectOpen = undefined;
  }
}

function request(method, params) {
  const wait = timeout();
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending = { id, method, resolve, reject, timer: setTimeout(() => abort(`${method} timed out`), wait) };
    try {
      // A closing socket silently drops frames; that steer was never attempted.
      if (ws.readyState !== WebSocket.OPEN) throw new Error("WebSocket connection closed");
      if (method === "turn/steer") steerAttempted = true;
      ws.send(JSON.stringify({ id, method, params }));
    } catch { abort("WebSocket send failed"); }
  });
}

async function steer() {
  if (extra.length) throw new Error(usage);
  const [major, minor] = process.versions.node.split(".").map(Number);
  if (major < 22 || (major === 22 && minor < 4) || typeof WebSocket === "undefined") {
    throw new Error("Node.js 22.4+ with built-in WebSocket is required");
  }
  const threadId = process.env.TARGET_THREAD_ID;
  if (!threadId) throw new Error("Missing TARGET_THREAD_ID from the intended receiver");
  let endpoint = process.env.TARGET_CODEX_ENDPOINT;
  if (!endpoint && process.env.TARGET_CODEX_HOME) {
    endpoint = "unix://" + join(process.env.TARGET_CODEX_HOME, "app-server-control", "app-server-control.sock");
  }
  if (!endpoint) throw new Error("Supply TARGET_CODEX_ENDPOINT or the intended TARGET_CODEX_HOME");
  const localPath = endpoint.startsWith("unix://") ? endpoint.slice(7) : undefined;
  if (localPath !== undefined) {
    if (!isAbsolute(localPath) || /[\r\n\0]/.test(localPath)) throw new Error("The native control socket needs an absolute path");
  } else {
    let url;
    try { url = new URL(endpoint); } catch { throw new Error("Invalid TARGET_CODEX_ENDPOINT"); }
    if (!["ws:", "wss:"].includes(url.protocol) || url.username || url.password || url.hash) {
      throw new Error("Use ws://, wss://, or unix://PATH without URL credentials or fragments");
    }
  }
  let text;
  try {
    text = source === undefined ? process.env.MESSAGE
      : new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(readFileSync(source === "-" ? 0 : source));
  } catch { throw new Error("Cannot read the message input as UTF-8"); }
  if (text === undefined) throw new Error("Supply a UTF-8 file, - for stdin, or MESSAGE");

  deadline = Date.now() + 15000;
  await connect(localPath === undefined ? endpoint : await proxyEndpoint(localPath), localPath !== undefined);
  await request("initialize", { clientInfo: { name: "claude-codex-messaging", version: "0.1.0" } });
  ws.send(JSON.stringify({ method: "initialized", params: {} }));
  const cursors = new Set();
  let cursor;
  for (;;) {
    const page = await request("thread/loaded/list", { limit: 50, ...(cursor ? { cursor } : {}) });
    if (!Array.isArray(page?.data) || !page.data.every(id => typeof id === "string")) throw new Error("Invalid loaded-thread list");
    if (page.data.includes(threadId)) break;
    if (page.nextCursor === null || page.nextCursor === undefined) throw new Error("Target thread is not loaded on this server");
    cursor = page.nextCursor;
    if (typeof cursor !== "string" || !cursor || cursors.has(cursor)) throw new Error("Invalid or repeated loaded-thread cursor");
    cursors.add(cursor);
  }
  const turns = await request("thread/turns/list", { threadId, limit: 10, sortDirection: "desc", itemsView: "notLoaded" });
  if (!Array.isArray(turns?.data)) throw new Error("Invalid active-turn list");
  const active = turns.data.filter(turn => turn?.status === "inProgress");
  if (active.length !== 1 || typeof active[0].id !== "string" || !active[0].id) {
    throw new Error("No unique active turn; nothing was sent");
  }
  const turnId = active[0].id;
  const result = await request("turn/steer", { threadId, expectedTurnId: turnId, input: [{ type: "text", text }] });
  if (result?.turnId !== turnId) throw new Error("Missing or mismatched steer acknowledgement");
  return { status: "accepted", threadId, turnId };
}

process.on("SIGINT", () => abort("Interrupted"));
process.on("SIGTERM", () => abort("Terminated"));
let exitCode = 0, output, stream = process.stdout;
try { output = await steer(); }
catch (error) {
  const rejected = error instanceof RpcError && error.method === "turn/steer";
  const status = !steerAttempted ? "not_sent" : rejected ? "rejected" : "unconfirmed";
  exitCode = status === "unconfirmed" ? 2 : 1;
  output = { status, error: error.message + (status === "unconfirmed" ? "; check target state before retrying" : "") };
  stream = process.stderr;
} finally {
  closing = true;
  bridge?.close();
  for (const connection of connections) connection.destroy();
  proxy?.stdin.destroy();
  proxy?.stdout.destroy();
  proxy?.kill();
  ws?.close();
}
await new Promise(resolve => stream.write(JSON.stringify(output) + "\n", resolve));
// A peer need not acknowledge the WebSocket close; do not leave a CLI waiting.
process.exit(exitCode);
