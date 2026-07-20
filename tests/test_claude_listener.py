from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from inter_agent.adapters.claude import formatting, state
from inter_agent.adapters.claude.listener import (
    _PERMANENT_ERROR_CODES,
    AUTO_STARTED_SERVER_IDLE_TIMEOUT_S,
    Listener,
    PermanentError,
)


class FakeSession:
    """Stand-in for AgentSession used by listener unit tests.

    Yields a fixed sequence of raw frame strings and records channel ops so
    the control bridge and reconnect-resubscribe paths can be exercised
    without a live server or websocket auth handshake.
    """

    def __init__(self, frames: list[str]) -> None:
        self._frames = list(frames)
        self.subscribe_calls: list[str] = []
        self.unsubscribe_calls: list[str] = []

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def _gen(self) -> AsyncIterator[str]:
        for frame in self._frames:
            yield frame

    def __aiter__(self) -> AsyncIterator[str]:
        return self._gen()

    async def subscribe(self, channel: str) -> dict[str, object]:
        self.subscribe_calls.append(channel)
        return {"op": "subscribe_ok", "channel": channel}

    async def unsubscribe(self, channel: str) -> dict[str, object]:
        self.unsubscribe_calls.append(channel)
        return {"op": "unsubscribe_ok", "channel": channel}


def patch_session(monkeypatch: pytest.MonkeyPatch, frames: list[str]) -> FakeSession:
    session = FakeSession(frames)
    monkeypatch.setattr(
        "inter_agent.adapters.claude.listener.AgentSession",
        lambda *args, **kwargs: session,
    )
    return session


class TestFormatting:
    def test_sanitize_strips_ansi(self) -> None:
        text = "\x1b[31mred\x1b[0m"
        assert formatting.sanitize_for_stdout(text) == "red"

    def test_sanitize_replaces_newlines(self) -> None:
        text = "line1\nline2\rline3"
        assert formatting.sanitize_for_stdout(text) == "line1↵line2↵line3"

    def test_truncate_short_text(self) -> None:
        text = "short"
        truncated, was_truncated, full_len = formatting.truncate_for_stdout(text, cap=10)
        assert truncated == "short"
        assert was_truncated is False
        assert full_len == 5

    def test_truncate_long_text(self) -> None:
        text = "a" * 1000
        truncated, was_truncated, full_len = formatting.truncate_for_stdout(text, cap=10)
        assert truncated == "a" * 10
        assert was_truncated is True
        assert full_len == 1000

    def test_format_notification_direct(self) -> None:
        line = formatting.format_notification("abc", "agent-a", "hello", "agent-b")
        assert line == '[inter-agent msg=abc from="agent-a" kind="direct" to="agent-b"] hello'

    def test_format_notification_broadcast(self) -> None:
        line = formatting.format_notification("abc", "agent-a", "hello")
        assert line == '[inter-agent msg=abc from="agent-a" kind="broadcast"] hello'

    def test_format_truncated_notification(self) -> None:
        text = "x" * (formatting.STDOUT_CAP + 10)
        line = formatting.format_notification("abc", "agent-a", text)
        assert "truncated=" in line
        assert line.startswith('[inter-agent msg=abc from="agent-a" kind="broadcast" truncated=')

    def test_format_truncation_pointer(self) -> None:
        line = formatting.format_truncation_pointer("abc", 1234, Path("/tmp/log"))
        assert (
            line == "[inter-agent msg=abc cont] full text 1234 bytes — "
            "run: inter-agent-claude messages abc"
        )


class TestState:
    def test_claude_data_dir_under_core_data_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        path = state.claude_data_dir()
        assert path == tmp_path / "claude-sessions"
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o700

    def test_write_and_read_session_state(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        state.write_session_state(123, {"name": "test", "session_id": "abc"})
        read = state.read_session_state(123)
        assert read == {"name": "test", "session_id": "abc"}

    def test_delete_session_state(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        state.write_session_state(123, {"name": "test"})
        state.delete_session_state(123)
        assert state.read_session_state(123) is None

    def test_acquire_lock_prevents_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        fd = state.acquire_lock(456)
        assert fd is not None
        fd2 = state.acquire_lock(456)
        assert fd2 is None
        state.release_lock(fd)

    def test_find_listener_state_direct_hit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        key = state._resolve_listener_key()
        state.write_session_state(key, {"name": "found"})
        found, path = state.find_listener_state()
        assert found == {"name": "found"}
        assert path == state.session_path(key)

    def test_resolve_listener_key_skips_inter_agent_claude_argv0(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The matcher must not match the `inter-agent-claude` entry-point.

        Regression: a substring "claude" check matched the entry-point
        script name itself, so the walk returned the CLI's own PID instead
        of the Claude Code host ancestor.
        """
        # Simulate process tree: self (inter-agent-claude) -> bash -> claude host
        claude_host_pid = 999000
        bash_pid = 999001
        self_pid = 999002

        def fake_ppid_of(pid: int) -> int | None:
            return {self_pid: bash_pid, bash_pid: claude_host_pid, claude_host_pid: None}[pid]

        def fake_cmdline_bytes(pid: int) -> bytes:
            return {
                self_pid: b"/usr/bin/inter-agent-claude\x00send\x00",
                bash_pid: b"/bin/bash\x00-c\x00inter-agent-claude send\x00",
                claude_host_pid: b"claude\x00--dangerously-skip-permissions\x00",
            }[pid]

        class FakePath:
            def __init__(self, target: str) -> None:
                self._target = target
                self.pid = target.split("/")[-1]

            def exists(self) -> bool:
                return True

            def read_bytes(self) -> bytes:
                # target form: /proc/<pid>/cmdline
                pid_str = self._target.split("/")[-2]
                return fake_cmdline_bytes(int(pid_str))

            def __truediv__(self, other: str) -> FakePath:
                return FakePath(self._target + "/" + other)

        def fake_path(*parts: str) -> FakePath:
            return FakePath("/".join(parts))

        monkeypatch.setattr(os, "getpid", lambda: self_pid)
        monkeypatch.setattr(state, "_ppid_of", fake_ppid_of)
        monkeypatch.setattr(state, "Path", fake_path)
        monkeypatch.setattr(os.path, "basename", lambda p: p.rsplit("/", 1)[-1])

        assert state._resolve_listener_key() == claude_host_pid

    def test_unlink_if_matches_requires_same_nonce(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        state.write_session_state(789, {"session_id": "abc", "nonce": "xyz"})
        path = state.session_path(789)
        assert state.unlink_if_matches(path, {"session_id": "abc", "nonce": "wrong"}) is False
        assert path.exists()
        assert state.unlink_if_matches(path, {"session_id": "abc", "nonce": "xyz"}) is True
        assert not path.exists()

    def test_read_message_by_id_returns_latest_match(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        log = state.messages_log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            json.dumps({"msg_id": "m1", "from_name": "x", "text": "first"})
            + "\n"
            + json.dumps({"msg_id": "m2", "from_name": "y", "text": "second"})
            + "\n"
            + json.dumps({"msg_id": "m1", "from_name": "x", "text": "first-replayed"})
            + "\n",
            encoding="utf-8",
        )
        record = state.read_message_by_id("m1")
        assert record is not None
        assert record["text"] == "first-replayed"
        assert record["from_name"] == "x"

    def test_read_message_by_id_missing_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        log = state.messages_log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            json.dumps({"msg_id": "m1", "from_name": "x", "text": "first"}) + "\n",
            encoding="utf-8",
        )
        assert state.read_message_by_id("nope") is None

    def test_read_message_by_id_no_log_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert state.read_message_by_id("m1") is None

    def test_read_message_by_id_skips_corrupt_lines(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        log = state.messages_log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "not json at all\n"
            + json.dumps({"msg_id": "m1", "from_name": "x", "text": "ok"})
            + "\n",
            encoding="utf-8",
        )
        record = state.read_message_by_id("m1")
        assert record is not None
        assert record["text"] == "ok"

    def test_append_message_record_trims_oldest_records(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        for i in range(10):
            state.append_message_record(f"m{i}", "sender", f"text-{i}", max_bytes=240)

        log = state.messages_log_path()
        assert log.stat().st_size <= 240
        assert state.read_message_by_id("m0") is None
        latest = state.read_message_by_id("m9")
        assert latest is not None
        assert latest["text"] == "text-9"

    def test_append_message_record_keeps_valid_jsonl_after_trim(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        for i in range(8):
            state.append_message_record(f"m{i}", "sender", "x" * 20, max_bytes=180)

        lines = state.messages_log_path().read_text(encoding="utf-8").splitlines()
        assert lines
        for line in lines:
            payload = json.loads(line)
            assert isinstance(payload, dict)
            assert str(payload["msg_id"]).startswith("m")

    def test_append_message_record_sets_restrictive_permissions(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        state.append_message_record("m1", "sender", "text")

        mode = state.messages_log_path().stat().st_mode & 0o777
        assert mode == 0o600

    def test_messages_log_max_bytes_uses_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(state.MESSAGES_LOG_MAX_BYTES_ENV, "1234")
        assert state.messages_log_max_bytes() == 1234

    def test_messages_log_max_bytes_ignores_invalid_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(state.MESSAGES_LOG_MAX_BYTES_ENV, "0")
        assert state.messages_log_max_bytes() == state.MESSAGES_LOG_MAX_BYTES
        monkeypatch.setenv(state.MESSAGES_LOG_MAX_BYTES_ENV, "nope")
        assert state.messages_log_max_bytes() == state.MESSAGES_LOG_MAX_BYTES


class TestChannels:
    @pytest.mark.asyncio
    async def test_channel_msg_emits_channel_kind(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        message = {
            "op": "msg",
            "msg_id": "m1",
            "from_name": "agent-a",
            "channel": "updates",
            "text": "hello",
        }
        patch_session(monkeypatch, [json.dumps(message)])
        listener = Listener(host="127.0.0.1", port=12345, name="agent-b")
        await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert 'kind="channel" channel="updates"' in out
        assert 'kind="direct"' not in out
        assert 'kind="broadcast"' not in out
        assert "hello" in out

    def test_suppresses_only_own_channel_messages(self) -> None:
        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent-b", output=out)

        listener._on_msg(
            {
                "op": "msg",
                "msg_id": "self-channel",
                "from_name": "agent-b",
                "channel": "updates",
                "text": "suppress me",
            }
        )
        listener._on_msg(
            {
                "op": "msg",
                "msg_id": "self-direct",
                "from_name": "agent-b",
                "to": "agent-b",
                "text": "keep direct",
            }
        )
        listener._on_msg(
            {
                "op": "msg",
                "msg_id": "other-channel",
                "from_name": "agent-a",
                "channel": "updates",
                "text": "keep channel",
            }
        )

        output = out.getvalue()
        assert "suppress me" not in output
        assert "keep direct" in output
        assert "keep channel" in output

    @pytest.mark.asyncio
    async def test_reapply_subscriptions_on_welcome(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
        session = patch_session(monkeypatch, [json.dumps({"op": "welcome"})])
        listener = Listener(host="127.0.0.1", port=12345, name="agent-b")
        listener._desired_channels = {"updates", "build"}
        await listener._connect_and_serve(1)

        assert session.subscribe_calls == ["build", "updates"]
        # Desired set is retained across a reconnect.
        assert listener._desired_channels == {"updates", "build"}

    @pytest.mark.asyncio
    async def test_explicit_shutdown_clears_desired_channels(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
        monkeypatch.setattr(state, "_resolve_listener_key", lambda: 123)
        monkeypatch.setattr(state, "acquire_lock", lambda ppid: 1)
        monkeypatch.setattr(state, "release_lock", lambda fd: None)
        monkeypatch.setattr(state, "delete_session_state", lambda ppid: None)
        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.endpoint_available", lambda h, p: True
        )
        session = patch_session(monkeypatch, [json.dumps({"op": "welcome"})])
        listener = Listener(host="127.0.0.1", port=12345, name="agent-b", output=io.StringIO())
        listener._desired_channels = {"updates"}

        async def stop_immediately(self: Listener, ppid: int) -> None:
            self._stop.set()

        monkeypatch.setattr(Listener, "_connect_and_serve", stop_immediately)
        await listener.run()

        # _connect_and_serve never ran (it was patched), but run's finally must
        # clear the desired set on explicit shutdown.
        assert session.subscribe_calls == []
        assert listener._desired_channels == set()

    def test_permanent_error_codes_set_contents(self) -> None:
        assert _PERMANENT_ERROR_CODES == frozenset(
            {
                "AUTH_FAILED",
                "BAD_LABEL",
                "BAD_NAME",
                "BAD_ROLE",
                "BAD_SESSION",
                "NAME_TAKEN",
                "SESSION_TAKEN",
                "TOO_MANY_CONNECTIONS",
            }
        )

    @pytest.mark.parametrize("code", list(_PERMANENT_ERROR_CODES))
    @pytest.mark.asyncio
    async def test_permanent_error_raised_for_code(
        self, monkeypatch: pytest.MonkeyPatch, code: str
    ) -> None:
        patch_session(
            monkeypatch,
            [json.dumps({"op": "error", "code": code, "message": "test error"})],
        )
        listener = Listener(host="127.0.0.1", port=12345, name="test")
        with pytest.raises(PermanentError, match=code):
            await listener._connect_and_serve(1)

    @pytest.mark.asyncio
    async def test_session_setup_exit_becomes_permanent_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FailedSession:
            async def __aenter__(self) -> FailedSession:
                raise SystemExit("server authentication failed")

            async def __aexit__(self, *args: object) -> None:
                return None

        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.AgentSession",
            lambda *args, **kwargs: FailedSession(),
        )
        listener = Listener(host="127.0.0.1", port=12345, name="test")

        with pytest.raises(
            PermanentError,
            match="SESSION_SETUP_FAILED: server authentication failed",
        ):
            await listener._connect_and_serve(1)

    @pytest.mark.asyncio
    async def test_non_permanent_error_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        patch_session(
            monkeypatch,
            [json.dumps({"op": "error", "code": "UNKNOWN_TARGET", "message": "not found"})],
        )
        listener = Listener(host="127.0.0.1", port=12345, name="test")
        await listener._connect_and_serve(1)

    @pytest.mark.asyncio
    async def test_welcome_emits_connected_confirmation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
        patch_session(monkeypatch, [json.dumps({"op": "welcome"})])
        listener = Listener(host="127.0.0.1", port=12345, name="myname")
        await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert 'connected as "myname"' in out

    @pytest.mark.asyncio
    async def test_duplicate_msg_id_emits_once(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        message = {
            "op": "msg",
            "msg_id": "m1",
            "from_name": "agent-a",
            "text": "hello",
            "to": "agent-b",
        }
        patch_session(monkeypatch, [json.dumps(message), json.dumps(message)])
        listener = Listener(host="127.0.0.1", port=12345, name="agent-b")
        await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert out.count("msg=m1") == 1
        assert out.count("hello") == 1

    @pytest.mark.asyncio
    async def test_name_taken_raises_for_run_retry_handling(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patch_session(
            monkeypatch,
            [json.dumps({"op": "error", "code": "NAME_TAKEN", "message": "name already in use"})],
        )
        listener = Listener(host="127.0.0.1", port=12345, name="y")
        with pytest.raises(PermanentError, match="NAME_TAKEN"):
            await listener._connect_and_serve(1)

        assert capsys.readouterr().out == ""

    @pytest.mark.asyncio
    async def test_name_taken_does_not_emit_generic_permanent_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        patch_session(
            monkeypatch,
            [json.dumps({"op": "error", "code": "NAME_TAKEN", "message": "name already in use"})],
        )
        listener = Listener(host="127.0.0.1", port=12345, name="y")
        with pytest.raises(PermanentError):
            await listener._connect_and_serve(1)

        assert "permanent error — giving up" not in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_run_retries_name_taken_once(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.endpoint_available",
            lambda h, p: True,
        )
        seen_names: list[str] = []

        async def fake_connect_and_serve(self: Listener, ppid: int) -> None:
            seen_names.append(self.name)
            if len(seen_names) == 1:
                raise PermanentError("NAME_TAKEN", "name already in use")
            self._stop.set()

        monkeypatch.setattr(Listener, "_connect_and_serve", fake_connect_and_serve)

        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent", output=out)

        assert await listener.run() == 0
        assert seen_names == ["agent", "agent-2"]
        assert 'retrying as "agent-2"' in out.getvalue()

    @pytest.mark.asyncio
    async def test_run_stops_after_name_taken_retry_is_taken(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.endpoint_available",
            lambda h, p: True,
        )
        seen_names: list[str] = []

        async def fake_connect_and_serve(self: Listener, ppid: int) -> None:
            seen_names.append(self.name)
            raise PermanentError("NAME_TAKEN", "name already in use")

        monkeypatch.setattr(Listener, "_connect_and_serve", fake_connect_and_serve)

        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent", output=out)

        assert await listener.run() == 1
        assert seen_names == ["agent", "agent-2"]
        assert 'retrying as "agent-2"' in out.getvalue()
        assert 'name "agent-2" is already in use after retry' in out.getvalue()


class TestDuplicateListener:
    @pytest.mark.asyncio
    async def test_same_name_reports_already_connected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(state, "_resolve_listener_key", lambda: 123)
        monkeypatch.setattr(state, "acquire_lock", lambda ppid: None)
        monkeypatch.setattr(
            state,
            "read_session_state",
            lambda ppid: {"name": "agent-c", "listener_pid": 456, "session_id": "sid"},
        )
        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent-c", output=out)

        assert await listener.run() == 0
        assert 'already connected as "agent-c"' in out.getvalue()
        assert "no new listener started" in out.getvalue()

    @pytest.mark.asyncio
    async def test_different_name_reports_existing_listener(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(state, "_resolve_listener_key", lambda: 123)
        monkeypatch.setattr(state, "acquire_lock", lambda ppid: None)
        monkeypatch.setattr(
            state,
            "read_session_state",
            lambda ppid: {"name": "agent-b", "listener_pid": 456, "session_id": "sid"},
        )
        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent-c", output=out)

        assert await listener.run() == 0
        assert 'already running as "agent-b"' in out.getvalue()
        assert 'connecting as "agent-c"' in out.getvalue()

    @pytest.mark.asyncio
    async def test_duplicate_start_before_state_exists_is_clear(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(state, "_resolve_listener_key", lambda: 123)
        monkeypatch.setattr(state, "acquire_lock", lambda ppid: None)
        monkeypatch.setattr(state, "read_session_state", lambda ppid: None)
        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="agent-c", output=out)

        assert await listener.run() == 0
        assert "already starting or running" in out.getvalue()
        assert "no new listener started" in out.getvalue()


class TestAutoStart:
    def test_start_server_uses_explicit_adapter_idle_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        class FakeProc:
            pid = 12345

        def fake_popen(args: list[str], stdout: object, stderr: object) -> FakeProc:
            calls.append(args)
            return FakeProc()

        monkeypatch.setattr("inter_agent.adapters.claude.listener.subprocess.Popen", fake_popen)

        listener = Listener(host="127.0.0.1", port=12345, name="test")
        proc = listener._start_server()

        assert isinstance(proc, FakeProc)
        assert calls == [
            [
                sys.executable,
                "-m",
                "inter_agent.core.server",
                "--host",
                "127.0.0.1",
                "--port",
                "12345",
                "--idle-timeout",
                str(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S),
                "--no-tls",
            ]
        ]

    @pytest.mark.asyncio
    async def test_start_server_called_when_not_running(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        verify_calls: list[tuple[str, int]] = []

        def fake_verify(host: str, port: int) -> bool:
            verify_calls.append((host, port))
            return len(verify_calls) > 2

        monkeypatch.setattr("inter_agent.adapters.claude.listener.endpoint_available", fake_verify)

        started: list[bool] = []

        class FakeProc:
            pid = 12345

        def fake_start_server(self: Listener) -> FakeProc:
            started.append(True)
            return FakeProc()

        monkeypatch.setattr(Listener, "_start_server", fake_start_server)

        async def fake_connect_and_serve(self: Listener, ppid: int) -> None:
            self._stop.set()

        monkeypatch.setattr(Listener, "_connect_and_serve", fake_connect_and_serve)

        listener = Listener(host="127.0.0.1", port=12345, name="test")
        result = await listener.run()
        assert result == 0
        assert started == [True]
        assert len(verify_calls) >= 2

    @pytest.mark.asyncio
    async def test_returns_error_when_server_start_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.endpoint_available",
            lambda h, p: False,
        )
        monkeypatch.setattr(Listener, "_start_server", lambda self: None)

        listener = Listener(host="127.0.0.1", port=12345, name="test")
        result = await listener.run()
        assert result == 1

    @pytest.mark.asyncio
    async def test_returns_error_when_server_never_comes_up(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.endpoint_available",
            lambda h, p: False,
        )

        class FakeProc:
            pid = 12345

        monkeypatch.setattr(Listener, "_start_server", lambda self: FakeProc())

        real_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            await real_sleep(0.001)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        out = io.StringIO()
        listener = Listener(host="127.0.0.1", port=12345, name="test", output=out)
        result = await listener.run()
        assert result == 1
        assert "did not become available in time" in out.getvalue()


class TestControlFailurePaths:
    @pytest.mark.asyncio
    async def test_socket_chmod_failure_disables_control_and_keeps_listener_usable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A socket chmod failure must not leave a permissive socket nor break
        the listener: control is disabled and the welcome still prints."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
        patch_session(monkeypatch, [json.dumps({"op": "welcome"})])
        real_chmod = os.chmod

        def boom(path_obj: str | os.PathLike[str], mode: int) -> None:
            if str(path_obj).endswith(".sock"):
                raise OSError("permission denied")
            real_chmod(path_obj, mode)

        monkeypatch.setattr("inter_agent.adapters.control.os.chmod", boom)
        listener = Listener(host="127.0.0.1", port=12345, name="myname")
        # Must not raise (no reconnect loop / traceback).
        await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert 'connected as "myname"' in out
        assert "subscribe/unsubscribe unavailable" in out
        assert listener._control_server is None

    @pytest.mark.asyncio
    async def test_control_dir_failure_disables_control_and_keeps_listener_usable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A control-directory permission failure surfaces as 'unavailable' and
        leaves the listener usable; no socket is created."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path_factory.mktemp("d")))
        patch_session(monkeypatch, [json.dumps({"op": "welcome"})])
        real_chmod = os.chmod

        def boom(path_obj: str | os.PathLike[str], mode: int) -> None:
            if str(path_obj).endswith("/control"):
                raise OSError("permission denied")
            real_chmod(path_obj, mode)

        monkeypatch.setattr("inter_agent.adapters.control.os.chmod", boom)
        listener = Listener(host="127.0.0.1", port=12345, name="myname")
        await listener._connect_and_serve(1)  # must not raise

        out = capsys.readouterr().out
        assert 'connected as "myname"' in out
        assert "control socket unavailable" in out
        assert listener._control_server is None
