import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";

const usage = "Usage: node send-agy.mjs [UTF8_FILE|-]\nNo argument: read MESSAGE. Target: TARGET_AGY_LS_ADDRESS, TARGET_AGY_CSRF_TOKEN and TARGET_AGY_CONVERSATION_ID. Optional AGY_BIN: native agy executable.";
const [source, ...extra] = process.argv.slice(2);
if (source === "--help" && extra.length === 0) {
  console.log(usage);
  process.exit(0);
}

function fail(message) {
  console.error(JSON.stringify({ status: "not_sent", message }));
  process.exit(1);
}

if (extra.length) fail(usage);
const address = process.env.TARGET_AGY_LS_ADDRESS;
const token = process.env.TARGET_AGY_CSRF_TOKEN;
const conversation = process.env.TARGET_AGY_CONVERSATION_ID;
// Keep every field mandatory: native agy 1.5.14 exits 0 silently without
// sending when its address or token variable is absent.
if (!address || !token || !conversation) {
  fail("Require TARGET_AGY_LS_ADDRESS, TARGET_AGY_CSRF_TOKEN and TARGET_AGY_CONVERSATION_ID from the intended receiver");
}
if (conversation === process.env.ANTIGRAVITY_CONVERSATION_ID) {
  fail("Target is the sender's own conversation; use the receiver's identity");
}

const binary = process.env.AGY_BIN || (process.platform === "win32" ? "agy.exe" : "agy");
if (/\.(cmd|bat)$/i.test(binary)) {
  fail("Use a native AGY_BIN executable, not a shell wrapper");
}

let content = process.env.MESSAGE;
if (source !== undefined) {
  let bytes;
  try {
    bytes = readFileSync(source === "-" ? 0 : source);
  } catch {
    fail("Cannot read the message input");
  }
  try {
    content = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    fail("Cannot read the message input as UTF-8");
  }
}
if (content === undefined) fail("Supply a UTF-8 file, - for stdin, or MESSAGE");
if (content.includes("\0")) fail("Native agy message arguments cannot contain NUL");

// Use the receiver's live server, not an inherited sender endpoint. A source
// step from another language server is not valid receiver-side attribution.
const env = {
  ...process.env,
  ANTIGRAVITY_LS_ADDRESS: address,
  ANTIGRAVITY_CSRF_TOKEN: token,
};
for (const name of ["ANTIGRAVITY_SOURCE_METADATA", "ANTIGRAVITY_CONVERSATION_ID",
  "ANTIGRAVITY_PROJECT_ID", "ANTIGRAVITY_TRAJECTORY_ID"]) delete env[name];
let child;
try {
  child = spawn(binary, ["agentapi", "send-message", "--", conversation, content], {
    env, stdio: "ignore", windowsHide: true, shell: false,
  });
} catch {
  fail("Cannot launch native agy; check AGY_BIN and message argument size");
}

let launched = false, finished = false, stopReason;
function stop(message) {
  if (finished || stopReason) return;
  stopReason = message;
  clearTimeout(timer);
  child.kill("SIGKILL");
}
const timer = setTimeout(() => stop("Native agy timed out; inspect the receiver before resending"), 10000);
process.on("SIGINT", () => stop("Native agy interrupted; inspect the receiver before resending"));
process.on("SIGTERM", () => stop("Native agy terminated; inspect the receiver before resending"));

function finish(status, message) {
  if (finished) return;
  finished = true;
  clearTimeout(timer);
  const output = JSON.stringify({ status, message });
  if (status === "submitted") console.log(output);
  else console.error(output);
  process.exitCode = status === "submitted" ? 0 : status === "not_sent" ? 1 : 2;
}

child.once("spawn", () => { launched = true; });
child.once("error", () => finish(launched ? "unconfirmed" : "not_sent", launched
  ? "Native agy failed after launch; inspect the receiver before resending"
  : "Cannot launch native agy; check AGY_BIN and message argument size"));
child.once("exit", (code) => {
  if (stopReason) {
    finish("unconfirmed", stopReason);
  } else if (code === 0) {
    finish("submitted", "Native agy reported success; model consumption is not confirmed");
  } else {
    finish("unconfirmed", "Native agy did not report success; inspect the receiver before resending");
  }
});
