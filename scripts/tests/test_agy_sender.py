#!/usr/bin/env python3
"""Check native-client invocation with a disposable executable, not live agy sessions."""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENDER = ROOT / "skills/agent-messaging/scripts/send-agy.mjs"
NODE = shutil.which("node")
if NODE is None:
    raise RuntimeError("Node.js is required to test the bundled agy sender")

CONVERSATION = "11111111-2222-4333-8444-555555555555"
ADDRESS = "127.0.0.1:43210"
TOKEN = "fixture-target-token-never-echo"
TEXT = '\ufeff消息 "quotes" \\ backslash `backtick` $literal\r\nsecond line\n'

# Python is a real native executable on all CI platforms. A script named
# "agentapi" in its cwd accepts the same argv the sender gives to agy; no shell
# or test-only launcher support is needed in the production sender.
AGY = r"""
import json
import os
import socket
import sys
import threading

with open(os.environ["FIXTURE_AGY_CAPTURE"], "a", encoding="utf-8") as capture:
    capture.write(json.dumps({
        "argv": sys.argv[1:],
        "address": os.environ.get("ANTIGRAVITY_LS_ADDRESS"),
        "token": os.environ.get("ANTIGRAVITY_CSRF_TOKEN"),
        "sender_context": {
            name: os.environ[name] for name in (
                "ANTIGRAVITY_SOURCE_METADATA", "ANTIGRAVITY_CONVERSATION_ID",
                "ANTIGRAVITY_PROJECT_ID", "ANTIGRAVITY_TRAJECTORY_ID",
            ) if name in os.environ
        },
        "unrelated": os.environ.get("FIXTURE_AGY_UNRELATED"),
        "pid": os.getpid(),
    }) + "\n")

if os.environ.get("FIXTURE_AGY_READY_PORT"):
    with socket.create_connection(("127.0.0.1", int(os.environ["FIXTURE_AGY_READY_PORT"])), timeout=5) as ready:
        ready.sendall(b"ready")

# Deliberately try to expose native diagnostics. The sender must keep its own
# status output bounded and never echo the payload or credential from them.
for stream in (sys.stdout, sys.stderr):
    print(os.environ["ANTIGRAVITY_CSRF_TOKEN"], file=stream, flush=True)
    print(sys.argv[-1], file=stream, flush=True)

mode = os.environ.get("FIXTURE_AGY_MODE", "success")
if mode == "stall":
    threading.Event().wait(60)
elif mode == "failure":
    raise SystemExit(7)
"""


class AgySenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="agy-msg-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.capture = self.work / "calls.jsonl"
        (self.work / "agentapi").write_text(AGY, encoding="utf-8")
        self.env = os.environ.copy()
        for name in list(self.env):
            if name.startswith(("TARGET_AGY_", "ANTIGRAVITY_", "FIXTURE_AGY_")):
                del self.env[name]
        for name in ("MESSAGE", "AGY_BIN"):
            self.env.pop(name, None)
        self.env.update({
            "AGY_BIN": sys.executable,
            "TARGET_AGY_LS_ADDRESS": ADDRESS,
            "TARGET_AGY_CSRF_TOKEN": TOKEN,
            "TARGET_AGY_CONVERSATION_ID": CONVERSATION,
            "ANTIGRAVITY_LS_ADDRESS": "127.0.0.1:43211",
            "ANTIGRAVITY_CSRF_TOKEN": "fixture-sender-token-never-echo",
            "ANTIGRAVITY_CONVERSATION_ID": "different-sender-conversation",
            "ANTIGRAVITY_SOURCE_METADATA": "fixture-sender-source-metadata",
            "ANTIGRAVITY_PROJECT_ID": "fixture-sender-project",
            "ANTIGRAVITY_TRAJECTORY_ID": "fixture-sender-trajectory",
            "FIXTURE_AGY_CAPTURE": str(self.capture),
            "FIXTURE_AGY_UNRELATED": "preserve-unrelated-environment",
            "PYTHONUTF8": "1",
        })

    def run_sender(self, *args, text=None, env=None, script=SENDER):
        result = subprocess.run(
            [NODE, str(script), *map(str, args)],
            cwd=self.work,
            env=self.env if env is None else env,
            input=text if text is None or isinstance(text, bytes) else text.encode("utf-8"),
            capture_output=True,
            timeout=20,
        )
        result.stdout = result.stdout.decode("utf-8")
        result.stderr = result.stderr.decode("utf-8")
        return result

    def calls(self):
        if not self.capture.exists():
            return []
        return [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]

    def assert_status(self, result, status, exit_code):
        self.assertEqual(exit_code, result.returncode, result.stderr)
        output = result.stdout if exit_code == 0 else result.stderr
        other = result.stderr if exit_code == 0 else result.stdout
        self.assertEqual("", other)
        self.assertEqual(status, json.loads(output)["status"])
        self.assertLess(len(output), 1024)
        for secret in (TOKEN, self.env["ANTIGRAVITY_CSRF_TOKEN"], TEXT):
            self.assertNotIn(secret, output)

    def assert_submission(self, result, content):
        self.assert_status(result, "submitted", 0)
        calls = self.calls()
        self.assertEqual(1, len(calls), "Expected exactly one native invocation")
        self.assertEqual(
            ["send-message", "--", CONVERSATION, content],
            calls[0]["argv"],
        )
        self.assertEqual(ADDRESS, calls[0]["address"])
        self.assertEqual(TOKEN, calls[0]["token"])
        self.assertEqual({}, calls[0]["sender_context"])
        self.assertEqual("preserve-unrelated-environment", calls[0]["unrelated"])
        if content:
            self.assertNotIn(content, result.stdout + result.stderr)

    def assert_not_launched(self, result):
        self.assert_status(result, "not_sent", 1)
        self.assertEqual([], self.calls())

    def test_environment_message_uses_receiver_and_native_args_once(self):
        self.env["MESSAGE"] = TEXT
        self.assert_submission(self.run_sender(), TEXT)

    def test_file_from_installed_path_preserves_text_and_overrides_message(self):
        content = TEXT * 40
        source = self.work / "发送 note.txt"
        source.write_bytes(content.encode("utf-8"))
        installed = self.work / "installed skill" / "scripts" / SENDER.name
        installed.parent.mkdir(parents=True)
        shutil.copyfile(SENDER, installed)
        self.env["MESSAGE"] = "stale message"
        self.assert_submission(self.run_sender(source.name, script=installed), content)

    def test_stdin_overrides_message_and_preserves_trailing_newlines(self):
        self.env["MESSAGE"] = "stale message"
        self.assert_submission(self.run_sender("-", text=TEXT), TEXT)

    def test_leading_option_text_and_shell_metacharacters_stay_one_argument(self):
        content = '--title=not-an-option; $(touch should-not-exist) "quotes" & |\n'
        self.assert_submission(self.run_sender("-", text=content), content)
        self.assertFalse((self.work / "should-not-exist").exists())

    def test_empty_message_is_preserved(self):
        self.env["MESSAGE"] = ""
        self.assert_submission(self.run_sender(), "")

    def test_each_target_field_is_required_despite_inherited_sender_environment(self):
        self.env["MESSAGE"] = TEXT
        for field in ("LS_ADDRESS", "CSRF_TOKEN", "CONVERSATION_ID"):
            with self.subTest(field=field):
                env = self.env.copy()
                del env["TARGET_AGY_" + field]
                self.assert_not_launched(self.run_sender(env=env))

    def test_self_target_is_rejected_before_launch(self):
        self.env["ANTIGRAVITY_CONVERSATION_ID"] = CONVERSATION
        self.env["MESSAGE"] = TEXT
        self.assert_not_launched(self.run_sender())

    def test_missing_message_and_unreadable_file_do_not_launch(self):
        self.assert_not_launched(self.run_sender())
        self.assert_not_launched(self.run_sender(self.work / "absent.txt"))

    def test_invalid_utf8_file_and_stdin_do_not_launch(self):
        source = self.work / "invalid.txt"
        source.write_bytes(b"before \xff after\n")
        self.assert_not_launched(self.run_sender(source))
        self.assert_not_launched(self.run_sender("-", text=b"before \xff after\n"))

    def test_nul_message_does_not_launch(self):
        self.assert_not_launched(self.run_sender("-", text=b"before\x00after"))

    def test_missing_executable_is_not_sent(self):
        self.env["MESSAGE"] = TEXT
        self.env["AGY_BIN"] = str(self.work / "absent-agy")
        self.assert_not_launched(self.run_sender())

    def test_shell_launchers_are_rejected_before_execution(self):
        self.env["MESSAGE"] = TEXT
        for suffix in (".cmd", ".BAT"):
            with self.subTest(suffix=suffix):
                self.env["AGY_BIN"] = str(self.work / ("agy" + suffix))
                self.assert_not_launched(self.run_sender())

    def test_native_failure_is_unconfirmed_without_retry_or_leaked_diagnostics(self):
        self.env["MESSAGE"] = TEXT
        self.env["FIXTURE_AGY_MODE"] = "failure"
        self.assert_status(self.run_sender(), "unconfirmed", 2)
        self.assertEqual(1, len(self.calls()))

    def test_native_timeout_is_bounded_and_never_retried(self):
        self.env["MESSAGE"] = TEXT
        self.env["FIXTURE_AGY_MODE"] = "stall"
        try:
            self.assert_status(self.run_sender(), "unconfirmed", 2)
            self.assertEqual(1, len(self.calls()))
        finally:
            # Clean up the fixture if a regression leaves it alive after the
            # sender's own timeout. The PID is written by this test's child.
            for call in self.calls():
                try:
                    os.kill(call["pid"], signal.SIGTERM)
                except OSError:
                    pass

    @unittest.skipIf(os.name == "nt", "targeted POSIX signals are not Windows console events")
    def test_interruption_stops_native_client_and_reports_unconfirmed_once(self):
        self.env.update(MESSAGE=TEXT, FIXTURE_AGY_MODE="stall")
        for signum in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=signum), socket.socket() as ready:
                self.capture.unlink(missing_ok=True)
                ready.bind(("127.0.0.1", 0))
                ready.listen(1)
                ready.settimeout(5)
                env = self.env.copy()
                env["FIXTURE_AGY_READY_PORT"] = str(ready.getsockname()[1])
                process = subprocess.Popen(
                    [NODE, str(SENDER)], cwd=self.work, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                try:
                    with ready.accept()[0] as connection:
                        connection.settimeout(5)
                        with connection.makefile("rb") as stream:
                            self.assertEqual(b"ready", stream.read(5))
                    self.assertEqual(1, len(self.calls()))
                    child_pid = self.calls()[0]["pid"]
                    process.send_signal(signum)
                    stdout, stderr = process.communicate(timeout=3)
                    result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
                    self.assert_status(result, "unconfirmed", 2)
                    self.assertEqual(1, len(self.calls()))
                    with self.assertRaises(ProcessLookupError):
                        os.kill(child_pid, 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate(timeout=3)
                    for call in self.calls():
                        try:
                            os.kill(call["pid"], signal.SIGKILL)
                        except OSError:
                            pass

    def test_help_needs_no_receiver_and_extra_arguments_do_not_launch(self):
        env = self.env.copy()
        for field in ("LS_ADDRESS", "CSRF_TOKEN", "CONVERSATION_ID"):
            del env["TARGET_AGY_" + field]
        result = self.run_sender("--help", env=env)
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertEqual([], self.calls())
        self.assert_not_launched(self.run_sender("one", "two"))


if __name__ == "__main__":
    unittest.main()
