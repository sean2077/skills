import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import net from "node:net";
import { constants as osConstants } from "node:os";
import { delimiter, isAbsolute, join, resolve } from "node:path";

const usage = [
  "Usage: node steer-codex.mjs [UTF8_FILE|-]",
  "       node steer-codex.mjs --auto [--no-queue] [UTF8_FILE|-]",
  "       node steer-codex.mjs --check",
  "No argument: read MESSAGE. --check: query the receiver's live turn without sending.",
  "--auto: send now when possible or queue once if the live route is unavailable.",
  "--no-queue: require live delivery without adding a queued message.",
  "Target: TARGET_THREAD_ID and TARGET_CODEX_ENDPOINT or TARGET_CODEX_HOME.",
  "For local queue fallback, set the receiver's absolute TARGET_CODEX_HOME.",
  "Add TARGET_CODEX_SQLITE_HOME when the receiver uses a CODEX_SQLITE_HOME override.",
  "Optional Codex executable: CODEX_BIN (native executable or JS launcher). Requires Node.js 22.4+.",
].join("\n");
const args = process.argv.slice(2);
if (args[0] === "--help" && args.length === 1) {
  console.log(usage);
  process.exit(0);
}

let ws, bridge, proxy, pending, rejectOpen, fatal;
let closing = false, attemptedMethod, nextId = 0, cancelQueue;
const connections = new Set();
let deadline;
const threadUuid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

function abort(error) {
  if (closing || fatal) return;
  fatal = typeof error === "string" ? new Error(error) : error;
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

function spawnCodex(args, options) {
  const binary = codexBinary();
  if (/\.(cmd|bat)$/i.test(binary)) throw new Error("Use a native CODEX_BIN executable or JS launcher, not a shell wrapper");
  const jsLauncher = /\.[cm]?js$/i.test(binary);
  const executable = jsLauncher || /[/\\]/.test(binary) ? resolve(binary) : binary;
  return jsLauncher
    ? spawn(process.execPath, [executable, ...args], options)
    : spawn(executable, args, options);
}

class RouteError extends Error {
  constructor(reason, message) {
    super(message);
    this.reason = reason;
  }
}

function proxyConnectError(stderr) {
  const detail = /^Error: failed to connect to socket at [^\r\n]+\r?\n\s*Caused by:\r?\n[^\r\n]*\(os error (\d+)\)\s*$/.exec(stderr);
  const code = Number(detail?.[1]);
  if (code === osConstants.errno.ENOENT) {
    return new RouteError("control_socket_missing", "Codex control socket path is missing; verify the receiver's endpoint or Codex home");
  }
  if (code === osConstants.errno.ECONNREFUSED || (process.platform === "win32" && code === 10061)) {
    return new RouteError("control_socket_refused", "Codex control socket refused the connection; check the receiver's live App Server endpoint");
  }
  return new RouteError("control_proxy_failed", "Codex proxy closed before connecting; check the intended live endpoint and CODEX_BIN");
}

// The native proxy forwards WebSocket bytes, not JSON lines. Keep its temporary
// loopback bridge private to one connection carrying this unguessable path.
async function proxyEndpoint(path) {
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
      try {
        proxy = spawnCodex(["app-server", "proxy", "--sock", path], { stdio: "pipe" });
      } catch {
        // Windows can reject some launchers synchronously (EINVAL/EFTYPE).
        abort("Cannot launch Codex proxy; check CODEX_BIN");
        return connection.destroy();
      }
      proxy.on("error", () => abort("Cannot launch Codex proxy; check CODEX_BIN"));
      let stderr = "", forwardedOutput = false;
      proxy.stderr.on("data", chunk => {
        if (stderr.length < 4096) stderr += chunk.subarray(0, 4096 - stderr.length).toString();
      });
      proxy.stdout.once("data", () => { forwardedOutput = true; });
      // Wait for stderr before closing the bridge, so the WebSocket error
      // cannot hide a known socket failure during the handshake.
      proxy.on("close", () => {
        if (!forwardedOutput) abort(proxyConnectError(stderr));
        connection.end();
      });
      proxy.stdin.on("error", error => {
        if (error.code !== "EPIPE" && error.code !== "ERR_STREAM_DESTROYED") abort("Codex proxy write failed");
      });
      proxy.stdout.on("error", () => abort("Codex proxy read failed"));
      proxy.stdin.write(header);
      connection.pipe(proxy.stdin);
      proxy.stdout.pipe(connection, { end: false });
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
  const reason = viaProxy ? "control_proxy_failed" : "websocket_unavailable";
  ws.addEventListener("error", () => abort(new RouteError(reason, viaProxy
    ? "Codex proxy connection failed; check the intended live endpoint and CODEX_BIN"
    : "WebSocket connection failed")));
  ws.addEventListener("close", () => abort(new RouteError(reason, "WebSocket connection closed")));
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
      timer = setTimeout(() => abort(new RouteError(reason, "WebSocket connection timed out")), timeout());
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
    // A closing socket silently drops frames. This request never left the client.
    if (ws.readyState !== WebSocket.OPEN) {
      abort(new RouteError("websocket_unavailable", "WebSocket connection closed"));
      return;
    }
    try {
      if (method === "turn/steer" || method === "turn/start") attemptedMethod = method;
      ws.send(JSON.stringify({ id, method, params }));
    } catch { abort("WebSocket send failed"); }
  });
}

async function connectToLoadedThread(threadId, endpoint, localPath) {
  deadline = Date.now() + 15000;
  await connect(localPath === undefined ? endpoint : await proxyEndpoint(localPath), localPath !== undefined);
  await request("initialize", { clientInfo: { name: "agent-messaging", version: "0.1.0" } });
  ws.send(JSON.stringify({ method: "initialized", params: {} }));
  const cursors = new Set();
  let cursor;
  for (;;) {
    const page = await request("thread/loaded/list", { limit: 50, ...(cursor ? { cursor } : {}) });
    if (!Array.isArray(page?.data) || !page.data.every(id => typeof id === "string")) throw new Error("Invalid loaded-thread list");
    if (page.data.includes(threadId)) break;
    if (page.nextCursor === null || page.nextCursor === undefined) {
      throw new RouteError("thread_not_loaded", "Target thread is not loaded on this server; verify the thread ID and the server that owns it");
    }
    cursor = page.nextCursor;
    if (typeof cursor !== "string" || !cursor || cursors.has(cursor)) throw new Error("Invalid or repeated loaded-thread cursor");
    cursors.add(cursor);
  }
}

function closeLiveConnection() {
  if (closing) return;
  closing = true;
  bridge?.close();
  for (const connection of connections) connection.destroy();
  proxy?.stdin.destroy();
  proxy?.stdout.destroy();
  proxy?.stderr.destroy();
  proxy?.kill();
  ws?.close();
}

function isLocalDirectory(path) {
  return path && isAbsolute(path) && !/[\r\n\0]/.test(path) &&
    statSync(path, { throwIfNoEntry: false })?.isDirectory();
}

function queueFallback(reason, threadId, text, endpoint, home) {
  if (!threadUuid.test(threadId)) {
    throw new RouteError(reason, "Queue fallback requires the receiver's exact thread UUID");
  }
  if (text.includes("\0")) {
    throw new RouteError(reason, "Native Codex queue cannot take NUL bytes in its message argument");
  }

  // Queue through the reachable receiver even if it has not loaded the chat.
  // If the connection failed, only fall back to a caller-confirmed local home.
  const remote = reason === "thread_not_loaded";
  const args = ["queue", "--thread", threadId, `--message=${text}`];
  const env = { ...process.env };
  if (remote) {
    args.push("--remote", endpoint);
  } else {
    if (!isLocalDirectory(home)) {
      throw new RouteError(reason, "Live endpoint unavailable. Supply the receiver's existing absolute TARGET_CODEX_HOME to queue locally");
    }
    for (const key of Object.keys(env)) {
      const name = process.platform === "win32" ? key.toUpperCase() : key;
      if (name === "CODEX_HOME" || name === "CODEX_SQLITE_HOME") delete env[key];
    }
    env.CODEX_HOME = home;
    const sqliteHome = process.env.TARGET_CODEX_SQLITE_HOME;
    if (sqliteHome) {
      if (!isLocalDirectory(sqliteHome)) throw new RouteError(reason, "Set TARGET_CODEX_SQLITE_HOME to the receiver's existing absolute SQLite home");
      env.CODEX_SQLITE_HOME = sqliteHome;
    }
  }
  closeLiveConnection();

  return new Promise((resolve, reject) => {
    let child;
    const launchError = error => error.code === "E2BIG"
      ? "Message exceeded the native queue argument limit"
      : "Cannot launch native Codex queue. Check CODEX_BIN";
    try {
      // A trusted sender project could otherwise override the receiver's SQLite home.
      child = spawnCodex(args, { env, cwd: remote ? undefined : home, stdio: ["ignore", "pipe", "ignore"] });
    } catch (error) {
      reject(new RouteError(reason, launchError(error)));
      return;
    }
    if (child.pid !== undefined) attemptedMethod = "codex queue";

    let stdout = "";
    const timer = setTimeout(() => cancelQueue("Native Codex queue timed out"), 10000);
    function finish(error, queueId) {
      if (!cancelQueue) return;
      clearTimeout(timer);
      cancelQueue = undefined;
      if (error) reject(new RouteError(reason, error));
      else resolve({ status: "queued", threadId, queueId, reason });
    }
    cancelQueue = message => {
      child.kill();
      child.stdout.destroy();
      finish(message);
    };
    child.once("error", error => finish(launchError(error)));
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", chunk => { stdout = (stdout + chunk).slice(-4096); });
    child.once("close", code => {
      const match = /^Queued message ([0-9a-f-]+) for thread ([0-9a-f-]+)\.$/im.exec(stdout);
      if (code === 0 && match && threadUuid.test(match[1]) &&
          match[2].toLowerCase() === threadId.toLowerCase()) {
        finish(undefined, match[1]);
      } else {
        const detail = Number.isInteger(code) && code !== 0 ? ` (exit ${code})` : "";
        finish(`Native Codex queue did not confirm the message${detail}`);
      }
    });
  });
}

async function run() {
  const mode = args[0];
  const checkOnly = mode === "--check";
  const automatic = mode === "--auto";
  const options = automatic || checkOnly ? args.slice(1) : args;
  const liveOnly = automatic && options[0] === "--no-queue";
  const [source, ...extra] = liveOnly ? options.slice(1) : options;
  if (extra.length || (checkOnly && source !== undefined)) {
    throw new Error("Invalid arguments. Run with --help for usage.");
  }
  const [major, minor] = process.versions.node.split(".").map(Number);
  if (major < 22 || (major === 22 && minor < 4) || typeof WebSocket === "undefined") {
    throw new Error("Node.js 22.4+ with built-in WebSocket is required");
  }
  const threadId = process.env.TARGET_THREAD_ID;
  if (!threadId) throw new Error("Missing TARGET_THREAD_ID from the intended receiver");
  if (process.env.CODEX_THREAD_ID?.toLowerCase() === threadId.toLowerCase()) {
    throw new Error("Target is the sender's own thread; use the receiver's thread ID");
  }
  const home = process.env.TARGET_CODEX_HOME;
  const endpoint = process.env.TARGET_CODEX_ENDPOINT ||
    (home && "unix://" + join(home, "app-server-control", "app-server-control.sock"));
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
  if (!checkOnly) {
    try {
      text = source === undefined ? process.env.MESSAGE
        : new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(readFileSync(source === "-" ? 0 : source));
    } catch { throw new Error("Cannot read the message input as UTF-8"); }
    if (text === undefined) throw new Error("Supply a UTF-8 file, - for stdin, or MESSAGE");
  }

  try {
    await connectToLoadedThread(threadId, endpoint, localPath);
    if (automatic) {
      // The server chooses start or steer atomically against its live turn.
      const result = await request("turn/start", { threadId, input: [{ type: "text", text }] });
      const turnId = result?.turn?.id;
      if (typeof turnId !== "string" || !turnId) throw new Error("Missing turn input acknowledgement");
      return { status: "accepted", threadId, turnId };
    }
  } catch (error) {
    if (!automatic || liveOnly || attemptedMethod || !(error instanceof RouteError)) throw error;
    return queueFallback(error.reason, threadId, text, endpoint, home);
  }
  const summary = await request("thread/read", { threadId, includeTurns: false });
  if (summary?.thread?.id !== threadId) throw new Error("Invalid target thread metadata");
  const runtimeStatus = summary.thread.status?.type;
  if (checkOnly && runtimeStatus === "idle") return { status: "idle", threadId };
  if (runtimeStatus !== "active") throw new Error("Target thread has no active turn; nothing was sent");
  // A restart can leave older history marked inProgress. Only the newest turn
  // is a candidate, and expectedTurnId guards against a stale or changed turn.
  const turns = await request("thread/turns/list", { threadId, limit: 1, sortDirection: "desc", itemsView: "notLoaded" });
  if (!Array.isArray(turns?.data)) throw new Error("Invalid active-turn list");
  const [active] = turns.data;
  if (turns.data.length !== 1 || active?.status !== "inProgress" || typeof active.id !== "string" || !active.id) {
    throw new Error("No unique active turn; nothing was sent");
  }
  const turnId = active.id;
  if (checkOnly) return { status: "active", threadId, turnId };
  const result = await request("turn/steer", { threadId, expectedTurnId: turnId, input: [{ type: "text", text }] });
  if (result?.turnId !== turnId) throw new Error("Missing or mismatched steer acknowledgement");
  return { status: "accepted", threadId, turnId };
}

process.on("SIGINT", () => (cancelQueue || abort)("Interrupted"));
process.on("SIGTERM", () => (cancelQueue || abort)("Terminated"));
let exitCode = 0, output, stream = process.stdout;
try { output = await run(); }
catch (error) {
  const rejected = error instanceof RpcError && error.method === attemptedMethod;
  const status = !attemptedMethod ? "not_sent" : rejected ? "rejected" : "unconfirmed";
  exitCode = status === "unconfirmed" ? 2 : 1;
  output = {
    status,
    ...(error instanceof RouteError ? { reason: error.reason } : {}),
    error: error.message + (status === "unconfirmed" ? "; check target state before retrying" : ""),
  };
  stream = process.stderr;
} finally {
  closeLiveConnection();
}
await new Promise(resolve => stream.write(JSON.stringify(output) + "\n", resolve));
// A peer need not acknowledge the WebSocket close; do not leave a CLI waiting.
process.exit(exitCode);
