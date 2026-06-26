"""Tests for the Pi listener's reconnect behavior."""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path

import pytest

from inter_agent.adapters.pi import listener
from inter_agent.adapters.pi.listener import (
    _PERMANENT_ERROR_CODES,
    PermanentError,
    run_listener,
)


class TestPermanentErrorCodes:
    def test_codes_match_expected_set(self) -> None:
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


class TestRunListenerReconnect:
    @pytest.mark.asyncio
    async def test_gives_up_after_deadline(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The listener exits non-zero once the reconnect deadline is reached."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

        # Server never available and auto-start fails.
        monkeypatch.setattr(listener, "endpoint_available", lambda host, port: False)
        monkeypatch.setattr(listener, "_start_server", lambda host, port: None)

        real_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            await real_sleep(0.001)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        # Advance the loop clock so the deadline is immediately exceeded.
        fake_time = 100.0
        loop = asyncio.get_running_loop()

        class FakeLoop:
            def time(self) -> float:
                return fake_time

        monkeypatch.setattr(loop, "time", FakeLoop().time)

        result = await run_listener(host="127.0.0.1", port=12345, name="test", deadline_s=0.0)
        assert result == 1

    @pytest.mark.asyncio
    async def test_exits_on_permanent_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The listener exits immediately when the server sends a permanent error."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(listener, "endpoint_available", lambda host, port: True)

        call_count = 0

        async def fake_connect_and_stream(
            host: str, port: int, name: str, label: str | None, output: io.TextIOBase
        ) -> None:
            nonlocal call_count
            call_count += 1
            raise PermanentError("NAME_TAKEN: name already in use")

        monkeypatch.setattr(listener, "_connect_and_stream", fake_connect_and_stream)

        result = await run_listener(host="127.0.0.1", port=12345, name="test")
        assert result == 1
        assert call_count == 1  # no retry on permanent error

    @pytest.mark.asyncio
    async def test_reconnects_after_connection_closed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The listener reconnects when the connection drops normally."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(listener, "endpoint_available", lambda host, port: True)

        call_count = 0

        async def fake_connect_and_stream(
            host: str, port: int, name: str, label: str | None, output: io.TextIOBase
        ) -> None:
            nonlocal call_count
            call_count += 1
            output.write(json.dumps({"op": "welcome", "assigned_name": name}) + "\n")
            if call_count >= 3:
                raise asyncio.CancelledError()
            # Simulate a normal close — caller will reconnect.

        monkeypatch.setattr(listener, "_connect_and_stream", fake_connect_and_stream)

        real_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            await real_sleep(0.001)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        with pytest.raises(asyncio.CancelledError):
            await run_listener(host="127.0.0.1", port=12345, name="test")
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_auto_starts_server_when_not_running(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """The listener auto-starts the server when the endpoint is unavailable."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

        verify_calls: list[tuple[str, int]] = []

        def fake_verify(host: str, port: int) -> bool:
            verify_calls.append((host, port))
            return len(verify_calls) > 2

        monkeypatch.setattr(listener, "endpoint_available", fake_verify)

        started: list[bool] = []

        class FakeProc:
            pid = 12345

        def fake_start_server(host: str, port: int) -> FakeProc:
            started.append(True)
            return FakeProc()

        monkeypatch.setattr(listener, "_start_server", fake_start_server)

        async def fake_connect_and_stream(
            host: str, port: int, name: str, label: str | None, output: io.TextIOBase
        ) -> None:
            raise asyncio.CancelledError()

        monkeypatch.setattr(listener, "_connect_and_stream", fake_connect_and_stream)

        real_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            await real_sleep(0.001)

        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        with pytest.raises(asyncio.CancelledError):
            await run_listener(host="127.0.0.1", port=12345, name="test")
        assert started == [True]
        assert len(verify_calls) >= 2


class TestConnectAndStream:
    @pytest.mark.asyncio
    async def test_prints_welcome_frame(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_connect_and_stream prints the welcome frame to stdout."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("INTER_AGENT_SESSION_ID", raising=False)

        import websockets as ws_module

        sent_frames: list[str] = []

        class FakeWsWithData:
            def __init__(self) -> None:
                self._frames = [
                    json.dumps({"op": "welcome", "assigned_name": "test"}),
                ]
                self._idx = 0

            async def send(self, data: str) -> None:
                sent_frames.append(data)

            def __aiter__(self) -> FakeWsWithData:
                return self

            async def __anext__(self) -> str:
                if self._idx >= len(self._frames):
                    raise StopAsyncIteration
                frame = self._frames[self._idx]
                self._idx += 1
                return frame

        class FakeConnectWithData:
            async def __aenter__(self) -> FakeWsWithData:
                return FakeWsWithData()

            async def __aexit__(self, *args: object) -> None:
                pass

        monkeypatch.setattr(ws_module, "connect", lambda url: FakeConnectWithData())

        out = io.StringIO()
        from inter_agent.adapters.pi.listener import _connect_and_stream

        await _connect_and_stream("127.0.0.1", 12345, "test", None, out)
        lines = out.getvalue().strip().split("\n")
        assert json.loads(lines[0])["op"] == "welcome"
        hello = json.loads(sent_frames[0])
        assert hello["name"] == "test"
        assert hello["session_id"] != "test"

    @pytest.mark.asyncio
    async def test_raises_permanent_error_on_name_taken(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_connect_and_stream raises PermanentError on NAME_TAKEN."""
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))

        import websockets as ws_module

        class FakeWsWithError:
            async def send(self, data: str) -> None:
                pass

            def __aiter__(self) -> FakeWsWithError:
                return self

            async def __anext__(self) -> str:
                return json.dumps(
                    {"op": "error", "code": "NAME_TAKEN", "message": "name already in use"}
                )

        class FakeConnectWithError:
            async def __aenter__(self) -> FakeWsWithError:
                return FakeWsWithError()

            async def __aexit__(self, *args: object) -> None:
                pass

        monkeypatch.setattr(ws_module, "connect", lambda url: FakeConnectWithError())

        out = io.StringIO()
        from inter_agent.adapters.pi.listener import _connect_and_stream

        with pytest.raises(PermanentError, match="NAME_TAKEN"):
            await _connect_and_stream("127.0.0.1", 12345, "test", None, out)
