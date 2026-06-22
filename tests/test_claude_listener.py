from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from inter_agent.adapters.claude import formatting, state
from inter_agent.adapters.claude.listener import (
    _PERMANENT_ERROR_CODES,
    AUTO_STARTED_SERVER_IDLE_TIMEOUT_S,
    Listener,
    PermanentError,
)


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
        assert line == "[inter-agent msg=abc cont] full text 1234 bytes at /tmp/log"


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


class TestPermanentErrors:
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
        async def fake_iter(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield json.dumps({"op": "error", "code": code, "message": "test error"})

        monkeypatch.setattr("inter_agent.adapters.claude.listener.iter_client_frames", fake_iter)
        listener = Listener(host="127.0.0.1", port=12345, name="test")
        with pytest.raises(PermanentError, match=code):
            await listener._connect_and_serve(1)

    @pytest.mark.asyncio
    async def test_non_permanent_error_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_iter(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield json.dumps({"op": "error", "code": "UNKNOWN_TARGET", "message": "not found"})

        monkeypatch.setattr("inter_agent.adapters.claude.listener.iter_client_frames", fake_iter)
        listener = Listener(host="127.0.0.1", port=12345, name="test")
        await listener._connect_and_serve(1)

    @pytest.mark.asyncio
    async def test_welcome_emits_connected_confirmation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

        async def fake_iter(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield json.dumps({"op": "welcome"})

        monkeypatch.setattr("inter_agent.adapters.claude.listener.iter_client_frames", fake_iter)
        listener = Listener(host="127.0.0.1", port=12345, name="myname")
        await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert 'connected as "myname"' in out

    @pytest.mark.asyncio
    async def test_name_taken_emits_actionable_message(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        async def fake_iter(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield json.dumps(
                {"op": "error", "code": "NAME_TAKEN", "message": "name already in use"}
            )

        monkeypatch.setattr("inter_agent.adapters.claude.listener.iter_client_frames", fake_iter)
        listener = Listener(host="127.0.0.1", port=12345, name="y")
        with pytest.raises(PermanentError, match="NAME_TAKEN"):
            await listener._connect_and_serve(1)

        out = capsys.readouterr().out
        assert '"y"' in out
        assert "unique name" in out
        assert "Listener stopped" in out

    @pytest.mark.asyncio
    async def test_name_taken_does_not_emit_generic_permanent_line(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        async def fake_iter(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield json.dumps(
                {"op": "error", "code": "NAME_TAKEN", "message": "name already in use"}
            )

        monkeypatch.setattr("inter_agent.adapters.claude.listener.iter_client_frames", fake_iter)
        listener = Listener(host="127.0.0.1", port=12345, name="y")
        with pytest.raises(PermanentError):
            await listener._connect_and_serve(1)

        assert "permanent error — giving up" not in capsys.readouterr().out


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
                "--idle-timeout",
                str(AUTO_STARTED_SERVER_IDLE_TIMEOUT_S),
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

        monkeypatch.setattr(
            "inter_agent.adapters.claude.listener.verify_server_identity", fake_verify
        )

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
            "inter_agent.adapters.claude.listener.verify_server_identity",
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
            "inter_agent.adapters.claude.listener.verify_server_identity",
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
