#!/usr/bin/env python3
"""Exercise the steer CLI over real WebSockets, without a live Codex session."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENDER = ROOT / "skills/claude-codex-messaging/scripts/steer-codex.mjs"
NODE = shutil.which("node")
if NODE is None:
    raise RuntimeError("Node.js is required to test the bundled steer sender")

THREAD = "11111111-2222-4333-8444-555555555555"
TURN = "active-turn-fixture"
# A leading U+FEFF also checks that decoding preserves a literal UTF-8 BOM.
TEXT = '\ufeff消息 "quotes" \\ backslash `backtick` $literal\r\nsecond line\n'

# A raw-byte relay stands in for the native Codex executable. This verifies the
# bridge/launcher boundary, not Codex's AF_UNIX implementation or authentication.
PROXY = r"""
import net from "node:net";
import { writeFileSync } from "node:fs";
writeFileSync(process.env.FIXTURE_PROXY_CAPTURE, JSON.stringify(process.argv.slice(2)));
const connection = net.createConnection({
  host: "127.0.0.1", port: Number(process.env.FIXTURE_PROXY_PORT),
});
connection.on("error", () => process.exit(3));
connection.on("close", () => process.exit(0));
process.stdin.pipe(connection);
connection.pipe(process.stdout);
"""


class WebSocketFixture:
    """Small RFC 6455 server with literal App Server response fixtures."""

    def __init__(self, mode="accept"):
        self.mode = mode
        self.messages = []
        self.connections = 0
        self.error = None
        self.finished = threading.Event()
        self.stop = threading.Event()
        self.connection = None
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.2)
        self.endpoint = "ws://127.0.0.1:{}".format(self.listener.getsockname()[1])
        self.worker = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self):
        self.worker.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        if self.connection is not None:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
        self.listener.close()
        self.worker.join(3)
        if self.worker.is_alive():
            raise AssertionError("WebSocket fixture did not stop")
        if self.error is not None and exc[0] is None:
            raise self.error

    def send(self, value, opcode=1):
        payload = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        size = len(payload)
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([size])
        elif size < 65536:
            header += b"\x7e" + struct.pack("!H", size)
        else:
            header += b"\x7f" + struct.pack("!Q", size)
        self.connection.sendall(header + payload)

    def receive(self, stream):
        chunks = []
        while True:
            head = stream.read(2)
            if not head:
                return None
            if len(head) != 2 or not head[1] & 0x80:
                raise AssertionError("Client must send complete, masked WebSocket frames")
            opcode, size = head[0] & 15, head[1] & 127
            if size in (126, 127):
                width = 2 if size == 126 else 8
                size = int.from_bytes(stream.read(width), "big")
            if size > 2 * 1024 * 1024:
                raise AssertionError("Unexpectedly large fixture frame")
            mask, payload = stream.read(4), stream.read(size)
            if len(mask) != 4 or len(payload) != size:
                return None
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 8:
                self.send(payload, opcode=8)
                return None
            if opcode == 9:
                self.send(payload, opcode=10)
                continue
            if opcode not in (0, 1):
                raise AssertionError("Expected a text frame")
            chunks.append(payload)
            if head[0] & 0x80:
                return json.loads(b"".join(chunks))

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    self.connection, _ = self.listener.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
            self.connections += 1
            self.connection.settimeout(25)
            with self.connection.makefile("rb") as stream:
                request = stream.readline()
                if not request.startswith(b"GET "):
                    raise AssertionError("Expected WebSocket HTTP Upgrade")
                headers = {}
                for _ in range(50):
                    line = stream.readline()
                    if line in (b"\r\n", b""):
                        break
                    name, value = line.decode("ascii").split(":", 1)
                    headers[name.lower()] = value.strip()
                accept = base64.b64encode(hashlib.sha1(
                    (headers["sec-websocket-key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
                    .encode("ascii")
                ).digest())
                self.connection.sendall(
                    b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                    b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n"
                )
                while not self.stop.is_set():
                    message = self.receive(stream)
                    if message is None:
                        break
                    self.messages.append(message)
                    if not self.respond(message):
                        break
        except (BrokenPipeError, ConnectionResetError):
            pass  # Abrupt sender cleanup is a valid transport close.
        except OSError as error:
            if not self.stop.is_set():
                self.error = error
        except BaseException as error:
            self.error = error
        finally:
            if self.connection is not None:
                self.connection.close()
            self.finished.set()

    def respond(self, message):
        method = message.get("method")
        if method == "initialized":
            return True
        request_id = message["id"]
        if method == "initialize":
            if self.mode == "initialize-error":
                self.send({"id": request_id, "error": {"code": -32602, "message": TEXT}})
                return True
            result = {"userAgent": "codex-fixture"}
        elif method == "thread/loaded/list":
            if self.mode == "unloaded":
                result = {"data": [], "nextCursor": None}
            elif self.mode == "cursor-loop":
                result = {"data": ["unrelated-thread"], "nextCursor": "same-cursor"}
            elif self.mode == "paginate" and "cursor" not in message["params"]:
                result = {"data": ["unrelated-thread"], "nextCursor": "page-two"}
            else:
                result = {"data": [THREAD], "nextCursor": None}
        elif method == "thread/turns/list":
            data = [{"id": "finished-turn", "status": "completed", "items": []}]
            if self.mode != "idle":
                data.append({"id": TURN, "status": "inProgress", "items": []})
            if self.mode == "ambiguous-turn":
                data.append({"id": "other-active-turn", "status": "inProgress", "items": []})
            result = {"data": data, "nextCursor": None}
        elif method == "turn/steer":
            if self.mode == "rejected":
                self.send({"id": request_id, "error": {"code": -32600, "message": TEXT}})
                return True
            if self.mode == "disconnect":
                return False
            if self.mode == "stall":
                return True
            if self.mode == "invalid-json":
                self.send(b"{invalid-json")
                return True
            if self.mode == "missing-result":
                self.send({"id": request_id})
                return True
            if self.mode == "mixed-result-error":
                self.send({"id": request_id, "result": {"turnId": TURN},
                           "error": {"code": -32600, "message": TEXT}})
                return True
            result = {"turnId": "different-turn" if self.mode == "wrong-turn" else TURN}
        else:
            raise AssertionError("Unexpected operation: " + str(method))
        if self.mode == "notifications":
            self.send({"method": "turn/started", "params": {"threadId": "unrelated-thread"}})
            self.send({"id": "unrelated-id", "result": {"turnId": "wrong-turn"}})
        self.send({"id": request_id, "result": result})
        return True


class CodexSteerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-steer-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.env = os.environ.copy()
        for name in ("TARGET_THREAD_ID", "TARGET_CODEX_ENDPOINT", "TARGET_CODEX_HOME", "CODEX_BIN", "MESSAGE"):
            self.env.pop(name, None)
        self.env.update(TARGET_THREAD_ID=THREAD, MESSAGE=TEXT)

    def run_sender(self, fixture=None, *args, text=None, env=None, script=SENDER, set_endpoint=True):
        env = (self.env if env is None else env).copy()
        if fixture is not None and set_endpoint:
            env["TARGET_CODEX_ENDPOINT"] = fixture.endpoint
        result = subprocess.run(
            [NODE, str(script), *map(str, args)], cwd=self.work, env=env,
            input=text if text is None or isinstance(text, bytes) else text.encode("utf-8"),
            capture_output=True, timeout=20,
        )
        result.stdout = result.stdout.decode("utf-8")
        result.stderr = result.stderr.decode("utf-8")
        if fixture is not None and fixture.connections:
            self.assertTrue(fixture.finished.wait(3), "Sender left its WebSocket open")
            if fixture.error is not None:
                raise fixture.error
            fixture.listener.setblocking(False)
            try:
                unexpected, _ = fixture.listener.accept()
            except BlockingIOError:
                pass
            else:
                unexpected.close()
                self.fail("Sender retried on a second connection")
            finally:
                fixture.listener.settimeout(0.2)
        return result

    def assert_status(self, result, status, code):
        self.assertEqual(code, result.returncode, result.stdout + result.stderr)
        output, empty = (result.stdout, result.stderr) if code == 0 else (result.stderr, result.stdout)
        self.assertEqual("", empty)
        self.assertLess(len(output), 600)
        self.assertNotIn(TEXT, output)
        value = json.loads(output)
        self.assertEqual(status, value["status"])
        return value

    def assert_trace(self, fixture, *, steers=1, pages=1, turns=1):
        methods = [message["method"] for message in fixture.messages]
        self.assertEqual(
            ["initialize", "initialized"] + ["thread/loaded/list"] * pages
            + ["thread/turns/list"] * turns + ["turn/steer"] * steers,
            methods,
        )
        self.assertNotIn("id", fixture.messages[1])
        for message in fixture.messages:
            if message["method"] == "thread/loaded/list":
                self.assertEqual(50, message["params"]["limit"])
            elif message["method"] == "thread/turns/list":
                self.assertEqual({"threadId": THREAD, "limit": 10,
                                  "sortDirection": "desc", "itemsView": "notLoaded"},
                                 message["params"])

    def assert_accepted(self, fixture, result, content=TEXT, pages=1):
        self.assertEqual({"status": "accepted", "threadId": THREAD, "turnId": TURN},
                         self.assert_status(result, "accepted", 0))
        self.assert_trace(fixture, pages=pages)
        self.assertEqual({"threadId": THREAD, "expectedTurnId": TURN,
                          "input": [{"type": "text", "text": content}]},
                         fixture.messages[-1]["params"])

    def test_environment_message_and_exact_rpc_sequence(self):
        with WebSocketFixture() as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture))

    def test_file_from_installed_path_overrides_environment_without_text_loss(self):
        text = TEXT * 6000
        message = self.work / "发送 note.txt"
        message.write_bytes(text.encode("utf-8"))
        installed = self.work / "installed skill" / "scripts" / SENDER.name
        installed.parent.mkdir(parents=True)
        shutil.copyfile(SENDER, installed)
        self.env["MESSAGE"] = "stale environment"
        with WebSocketFixture() as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture, message.name, script=installed), text)

    def test_stdin_overrides_environment_and_preserves_line_endings(self):
        self.env["MESSAGE"] = "stale environment"
        with WebSocketFixture() as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture, "-", text=TEXT))

    def test_empty_text_remains_an_explicit_input_item(self):
        self.env["MESSAGE"] = ""
        with WebSocketFixture() as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture), "")

    def test_loaded_threads_are_paginated_and_stop_when_target_is_found(self):
        with WebSocketFixture("paginate") as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture), pages=2)
            self.assertEqual({"limit": 50}, fixture.messages[2]["params"])
            self.assertEqual({"limit": 50, "cursor": "page-two"}, fixture.messages[3]["params"])

    def test_repeated_cursor_cannot_loop_or_fall_back(self):
        with WebSocketFixture("cursor-loop") as fixture:
            self.assert_status(self.run_sender(fixture), "not_sent", 1)
            self.assert_trace(fixture, steers=0, pages=2, turns=0)

    def test_unloaded_thread_is_not_resumed_or_queued(self):
        with WebSocketFixture("unloaded") as fixture:
            self.assert_status(self.run_sender(fixture), "not_sent", 1)
            self.assert_trace(fixture, steers=0, turns=0)

    def test_no_unique_active_turn_does_not_start_or_send(self):
        for mode in ("idle", "ambiguous-turn"):
            with self.subTest(mode=mode), WebSocketFixture(mode) as fixture:
                self.assert_status(self.run_sender(fixture), "not_sent", 1)
                self.assert_trace(fixture, steers=0)

    def test_initialization_error_is_unsent_and_does_not_echo_server_text(self):
        with WebSocketFixture("initialize-error") as fixture:
            self.assert_status(self.run_sender(fixture), "not_sent", 1)
            self.assertEqual(["initialize"], [message["method"] for message in fixture.messages])

    def test_steer_rejection_is_not_retried_or_changed_to_another_operation(self):
        with WebSocketFixture("rejected") as fixture:
            self.assert_status(self.run_sender(fixture), "rejected", 1)
            self.assert_trace(fixture)

    def test_lost_or_invalid_confirmation_is_reported_as_unconfirmed(self):
        for mode in ("disconnect", "wrong-turn", "missing-result", "mixed-result-error", "invalid-json"):
            with self.subTest(mode=mode), WebSocketFixture(mode) as fixture:
                self.assert_status(self.run_sender(fixture), "unconfirmed", 2)
                self.assert_trace(fixture)

    def test_missing_confirmation_times_out_without_resending(self):
        with WebSocketFixture("stall") as fixture:
            self.assert_status(self.run_sender(fixture), "unconfirmed", 2)
            self.assert_trace(fixture)

    def test_notifications_and_unrelated_responses_do_not_acknowledge_requests(self):
        with WebSocketFixture("notifications") as fixture:
            self.assert_accepted(fixture, self.run_sender(fixture))

    def test_local_endpoint_uses_raw_proxy_and_explicit_target_paths(self):
        launcher = self.work / "codex launcher.mjs"
        launcher.write_text(PROXY, encoding="utf-8")
        capture = self.work / "proxy-args.json"
        for explicit in (False, True):
            with self.subTest(explicit=explicit), WebSocketFixture() as fixture:
                env = self.env.copy()
                env.update(
                    CODEX_BIN=str(launcher), TARGET_CODEX_HOME=str(self.work / "接收方 home"),
                    FIXTURE_PROXY_CAPTURE=str(capture),
                    FIXTURE_PROXY_PORT=str(fixture.listener.getsockname()[1]),
                )
                address = Path(env["TARGET_CODEX_HOME"]) / "app-server-control/app-server-control.sock"
                if explicit:
                    address = self.work / "explicit socket.sock"
                    env["TARGET_CODEX_ENDPOINT"] = "unix://" + str(address)
                self.assert_accepted(fixture, self.run_sender(fixture, env=env, set_endpoint=False))
                self.assertEqual(["app-server", "proxy", "--sock", str(address)],
                                 json.loads(capture.read_text(encoding="utf-8")))

    def test_invalid_input_is_rejected_before_connecting(self):
        for case in ("missing-thread", "missing-input", "missing-file", "extra-args"):
            with self.subTest(case=case), WebSocketFixture() as fixture:
                env = self.env.copy()
                args = []
                if case == "missing-thread":
                    env["CODEX_THREAD_ID"] = env.pop("TARGET_THREAD_ID")
                elif case == "missing-input":
                    env.pop("MESSAGE")
                elif case == "missing-file":
                    args = ["absent-message.txt"]
                else:
                    args = ["one", "two"]
                self.assert_status(self.run_sender(fixture, *args, env=env), "not_sent", 1)
                self.assertEqual(0, fixture.connections)
                self.assertEqual([], fixture.messages)

    def test_missing_target_does_not_use_senders_home_or_history(self):
        self.env["CODEX_HOME"] = str(self.work / "senders-home")
        self.assert_status(self.run_sender(), "not_sent", 1)

    def test_invalid_utf8_is_rejected_before_connecting(self):
        source = self.work / "invalid-utf8.txt"
        source.write_bytes(b"before \xff after\n")
        for from_stdin in (False, True):
            with self.subTest(stdin=from_stdin), WebSocketFixture() as fixture:
                result = self.run_sender(
                    fixture, "-" if from_stdin else str(source),
                    text=source.read_bytes() if from_stdin else None,
                )
                self.assert_status(result, "not_sent", 1)
                self.assertEqual(0, fixture.connections)
                self.assertEqual([], fixture.messages)

    def test_unsupported_endpoint_is_unsent(self):
        self.env["TARGET_CODEX_ENDPOINT"] = "https://127.0.0.1:1"
        self.assert_status(self.run_sender(), "not_sent", 1)

    def test_unavailable_endpoint_is_unsent(self):
        # Keep a reserved socket bound but not listening, avoiding a port-reuse race.
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            self.env["TARGET_CODEX_ENDPOINT"] = "ws://127.0.0.1:{}".format(reserved.getsockname()[1])
            self.assert_status(self.run_sender(), "not_sent", 1)

    def test_help_needs_no_receiver(self):
        env = self.env.copy()
        env.pop("TARGET_THREAD_ID")
        result = self.run_sender(None, "--help", env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertIn("Usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
