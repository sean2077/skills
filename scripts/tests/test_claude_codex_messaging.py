#!/usr/bin/env python3
"""Exercise the bundled sender against disposable IPC endpoints, not real CC sessions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENDER = ROOT / "skills/claude-codex-messaging/scripts/send-claude.mjs"
TOKEN = "fixture-token-never-echo"
TEXT = '消息 "quotes" \\ backslash `backtick` $literal\r\nsecond line\n'
NODE = shutil.which("node")
if NODE is None:
    raise RuntimeError("Node.js is required to test the bundled inbox sender")

# Node provides the same real Unix-socket / Windows-pipe API as the sender.
# The receiver intentionally sends no acceptance response.
RECEIVER = r"""
import net from "node:net";
import { writeFileSync } from "node:fs";
const [address, capture, mode] = process.argv.slice(1);
const server = net.createServer(connection => {
  writeFileSync(capture + ".connected", "");
  if (mode === "stall") {
    connection.pause();
    return;
  }
  const chunks = [];
  connection.on("data", chunk => chunks.push(chunk));
  connection.on("end", () => {
    writeFileSync(capture, Buffer.concat(chunks));
    server.close();
  });
});
server.on("error", error => {
  console.error(error.code);
  process.exit(1);
});
server.listen(address, () => console.log("ready"));
setTimeout(() => process.exit(2), 20000).unref();
"""


class ClaudeInboxSenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cc-msg-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.env = os.environ.copy()
        for name in ("TARGET_CC_SOCKET", "TARGET_CC_TOKEN", "MESSAGE"):
            self.env.pop(name, None)
        self.env["TARGET_CC_SOCKET"] = (
            r"\\.\pipe\cc-msg-" + uuid.uuid4().hex
            if os.name == "nt" else str(self.work / "inbox.sock")
        )
        self.env["TARGET_CC_TOKEN"] = TOKEN

    def run_sender(self, *args, text=None, env=None, script=SENDER):
        result = subprocess.run(
            [NODE, str(script), *map(str, args)],
            cwd=self.work,
            env=self.env if env is None else env,
            input=None if text is None else text.encode("utf-8"),
            capture_output=True,
            timeout=15,
        )
        result.stdout = result.stdout.decode("utf-8")
        result.stderr = result.stderr.decode("utf-8")
        return result

    @contextmanager
    def receiver(self, mode="capture"):
        capture = self.work / "wire.bin"
        process = subprocess.Popen(
            [NODE, "--input-type=module", "-e", RECEIVER,
             self.env["TARGET_CC_SOCKET"], str(capture), mode],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            self.assertEqual("ready\n", process.stdout.readline())
            yield process, capture
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)

    def assert_submission(self, result, process, capture, content, token=TOKEN):
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertLess(len(result.stdout), 128)
        self.assertNotIn(TOKEN, result.stdout)
        if content:
            self.assertNotIn(content, result.stdout)
        _, stderr = process.communicate(timeout=10)
        self.assertEqual(0, process.returncode, stderr)
        wire = capture.read_bytes()
        self.assertTrue(wire.endswith(b"\n"))
        actual = [json.loads(line) for line in wire.splitlines()]
        expected = []
        if token:
            expected.append({"type": "auth", "token": token})
        expected.append({"type": "user", "message": {"role": "user", "content": content}})
        self.assertEqual(expected, actual)

    def assert_failure(self, result):
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertTrue(result.stderr)
        self.assertLess(len(result.stderr), 180)
        self.assertNotIn(TOKEN, result.stderr)
        self.assertNotIn(TEXT, result.stderr)

    def test_message_environment_preserves_native_frames_without_ack(self):
        self.env["MESSAGE"] = TEXT
        with self.receiver() as (process, capture):
            self.assert_submission(self.run_sender(), process, capture, TEXT)

    def test_file_from_installed_path_preserves_large_text_and_overrides_message(self):
        message = TEXT * 12000  # Deliberately too large for a typical single env value.
        source = self.work / "发送 note.txt"
        source.write_bytes(message.encode("utf-8"))
        installed = self.work / "installed skill" / "scripts" / SENDER.name
        installed.parent.mkdir(parents=True)
        shutil.copyfile(SENDER, installed)
        self.env["MESSAGE"] = "stale environment text"
        with self.receiver() as (process, capture):
            self.assert_submission(
                self.run_sender(source.name, script=installed),
                process, capture, message,
            )

    def test_stdin_overrides_message_and_preserves_trailing_newlines(self):
        self.env["MESSAGE"] = "stale environment text"
        with self.receiver() as (process, capture):
            self.assert_submission(self.run_sender("-", text=TEXT), process, capture, TEXT)

    def test_empty_message_remains_valid(self):
        self.env["MESSAGE"] = ""
        with self.receiver() as (process, capture):
            self.assert_submission(self.run_sender(), process, capture, "")

    @unittest.skipIf(os.name == "nt", "Unauthenticated inbox input is Unix-only")
    def test_unix_auth_is_optional(self):
        self.env.pop("TARGET_CC_TOKEN")
        self.env["MESSAGE"] = TEXT
        with self.receiver() as (process, capture):
            self.assert_submission(self.run_sender(), process, capture, TEXT, token=None)

    @unittest.skipUnless(os.name == "nt", "Native Windows token requirement")
    def test_windows_requires_receiver_token(self):
        self.env.pop("TARGET_CC_TOKEN")
        self.env["MESSAGE"] = TEXT
        result = self.run_sender()
        self.assert_failure(result)
        self.assertIn("TARGET_CC_TOKEN", result.stderr)

    def test_missing_target_does_not_use_senders_inherited_cc_identity(self):
        self.env["CLAUDE_CODE_MESSAGING_SOCKET"] = self.env.pop("TARGET_CC_SOCKET")
        self.env["CLAUDE_CODE_MESSAGING_TOKEN"] = TOKEN
        self.env["MESSAGE"] = TEXT
        result = self.run_sender()
        self.assert_failure(result)
        self.assertIn("TARGET_CC_SOCKET", result.stderr)

    def test_missing_input_is_rejected(self):
        result = self.run_sender()
        self.assert_failure(result)
        self.assertIn("MESSAGE", result.stderr)

    def test_missing_file_is_rejected_before_connecting(self):
        with self.receiver() as (_, capture):
            result = self.run_sender(self.work / "absent.txt")
            self.assert_failure(result)
            self.assertIn("message input", result.stderr)
            self.assertFalse(Path(str(capture) + ".connected").exists())

    def test_unavailable_inbox_never_reports_success(self):
        self.env["MESSAGE"] = TEXT
        self.assert_failure(self.run_sender())

    def test_write_timeout_is_bounded(self):
        source = self.work / "large.txt"
        source.write_bytes(b"x" * (8 * 1024 * 1024))
        with self.receiver("stall") as (process, capture):
            self.assert_failure(self.run_sender(source))
            self.assertTrue(Path(str(capture) + ".connected").exists())
            self.assertIsNone(process.poll())

    def test_help_needs_no_receiver_and_extra_arguments_are_rejected(self):
        env = self.env.copy()
        env.pop("TARGET_CC_SOCKET")
        result = self.run_sender("--help", env=env)
        self.assertEqual(0, result.returncode)
        self.assertIn("Usage:", result.stdout)
        self.assertEqual("", result.stderr)
        self.assert_failure(self.run_sender("one", "two"))


if __name__ == "__main__":
    unittest.main()
