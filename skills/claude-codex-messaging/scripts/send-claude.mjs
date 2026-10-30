import { readFileSync } from "node:fs";
import net from "node:net";

const usage = "Usage: node send-claude.mjs [UTF8_FILE|-]\nNo argument: read MESSAGE. Target: TARGET_CC_SOCKET / TARGET_CC_TOKEN.";
const [source, ...extra] = process.argv.slice(2);
if (source === "--help" && extra.length === 0) {
  console.log(usage);
  process.exit(0);
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (extra.length) fail(usage);
const address = process.env.TARGET_CC_SOCKET;
const token = process.env.TARGET_CC_TOKEN;
if (!address) fail("Missing TARGET_CC_SOCKET from the intended receiver");
if (process.platform === "win32" && !token) {
  fail("The native Windows inbox requires TARGET_CC_TOKEN");
}

let content;
try {
  content = source === undefined
    ? process.env.MESSAGE
    : new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(readFileSync(source === "-" ? 0 : source));
} catch {
  fail("Cannot read the message input as UTF-8");
}
if (content === undefined) fail("Supply a UTF-8 file, - for stdin, or MESSAGE");

const frames = [];
if (token) frames.push({ type: "auth", token });
frames.push({ type: "user", message: { role: "user", content } });
const wire = frames.map(frame => JSON.stringify(frame)).join("\n") + "\n";

const connection = net.createConnection({ path: address });
connection.setTimeout(5000, () => {
  connection.destroy(new Error("Inbox write timed out"));
});
connection.on("error", () => {
  console.error("Inbox submission failed; check the intended live receiver");
  process.exitCode = 1;
});
connection.once("connect", () => connection.end(wire));
connection.once("finish", () => {
  console.log("Submitted; receiver acceptance is not acknowledged");
  connection.destroy();
});
