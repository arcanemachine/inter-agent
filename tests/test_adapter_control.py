from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from inter_agent.adapters import control


async def _async_ok_handler(op: str, channel: str) -> dict[str, object]:
    return {"op": "subscribe_ok", "channel": channel}


@pytest.fixture
def base_data_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_socket_path_is_bounded_and_stable(base_data_dir: Path, tmp_path: Path) -> None:
    path = control.control_socket_path("claude", "127.0.0.1", 16837, "agent-a", base_data_dir)
    assert path.parent == base_data_dir / control.CONTROL_DIR_NAME
    assert path.name.startswith("control-claude-")
    assert path.name.endswith(".sock")
    digest_part = path.name[len("control-claude-") : -len(".sock")]
    assert len(digest_part) == 16
    assert all(c in "0123456789abcdef" for c in digest_part)

    # Stable across calls with identical inputs.
    assert path == control.control_socket_path(
        "claude", "127.0.0.1", 16837, "agent-a", base_data_dir
    )
    # Distinct name, host, port, or adapter all differ.
    assert path != control.control_socket_path(
        "claude", "127.0.0.1", 16837, "agent-b", base_data_dir
    )
    assert path != control.control_socket_path("pi", "127.0.0.1", 16837, "agent-a", base_data_dir)
    assert path != control.control_socket_path(
        "claude", "127.0.0.2", 16837, "agent-a", base_data_dir
    )
    # Host normalization does not change the digest for trailing case/whitespace.
    assert path == control.control_socket_path(
        "claude", " 127.0.0.1 ", 16837, "agent-a", base_data_dir
    )


def test_control_dir_permissions(base_data_dir: Path) -> None:
    path = control.control_dir(base_data_dir)
    assert path.exists()
    assert path.stat().st_mode & 0o777 == 0o700


async def _serve(
    path: Path,
    handler: control.RequestHandler,
) -> tuple[control.ControlServer, asyncio.Task[None]]:
    server = control.ControlServer(path, handler)
    started = await server.start()
    assert started is True
    return server, asyncio.create_task(asyncio.sleep(0))  # placeholder task


async def test_round_trip_returns_protocol_ack(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 16837, "agent-a", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        assert op == "subscribe"
        assert channel == "updates"
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    assert await server.start() is True
    try:
        response = await control.request(
            "pi", "127.0.0.1", 16837, "agent-a", base_data_dir, "subscribe", "updates"
        )
    finally:
        await server.stop()

    assert response == {"op": "subscribe_ok", "channel": "updates"}
    assert not path.exists()


async def test_server_socket_permissions(base_data_dir: Path) -> None:
    path = control.control_socket_path("claude", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        await server.stop()


async def test_request_missing_listener_raises_control_error(
    base_data_dir: Path,
) -> None:
    with pytest.raises(control.ControlError):
        await control.request(
            "pi", "127.0.0.1", 16837, "agent-a", base_data_dir, "subscribe", "updates"
        )


async def test_live_endpoint_is_not_replaced(base_data_dir: Path) -> None:
    path = control.control_socket_path("claude", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    first = control.ControlServer(path, handler)
    assert await first.start() is True
    try:
        second = control.ControlServer(path, handler)
        assert await second.start() is False
        # The live socket is untouched.
        assert path.exists()
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        await first.stop()
    assert not path.exists()


async def test_stale_socket_is_replaced_after_failed_liveness(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("claude", "127.0.0.1", 1, "n", base_data_dir)
    # Leave a stale socket file with no listener behind it.
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    path.touch()
    os.chmod(path, 0o600)

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    assert await server.start() is True
    try:
        # A request reaches the new server, not a refused old one.
        response = await control.request(
            "claude", "127.0.0.1", 1, "n", base_data_dir, "subscribe", "x"
        )
        assert response["op"] == "subscribe_ok"
    finally:
        await server.stop()
    assert not path.exists()


async def test_malformed_request_rejected_cleanly(base_data_dir: Path) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        raise AssertionError("handler must not run for malformed request")

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(path))
        writer.write(b"not-json\n")
        await writer.drain()
        raw = await reader.readline()
        payload = json.loads(raw.decode("utf-8"))
        assert payload["op"] == "error"
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


async def test_unsupported_op_rejected(base_data_dir: Path) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        raise AssertionError("handler must not run for unsupported op")

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(path))
        # Exactly the allowed keys, but an unsupported op.
        writer.write(json.dumps({"op": "publish", "channel": "x"}).encode() + b"\n")
        await writer.drain()
        raw = await reader.readline()
        payload = json.loads(raw.decode("utf-8"))
        assert payload["op"] == "error"
        assert payload["code"] == "BAD_OP"
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


async def test_request_with_extra_keys_rejected(base_data_dir: Path) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        raise AssertionError("handler must not run for request with extra keys")

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(path))
        writer.write(
            json.dumps({"op": "subscribe", "channel": "x", "secret": "leak"}).encode() + b"\n"
        )
        await writer.drain()
        raw = await reader.readline()
        payload = json.loads(raw.decode("utf-8"))
        assert payload["op"] == "error"
        assert payload["code"] == "BAD_REQUEST"
        assert "only op and channel" in payload["message"]
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


async def test_oversized_server_request_rejected_not_raised(base_data_dir: Path) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        raise AssertionError("handler must not run for oversized request")

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(path))
        # A genuinely oversized line (well past the 64 KiB cap) with no newline
        # would make readline raise LimitOverrunError before any length check.
        writer.write(b"x" * (control.CONTROL_MAX_REQUEST_BYTES + 4096) + b"\n")
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=control.CONTROL_TIMEOUT_S + 1)
        payload = json.loads(raw.decode("utf-8"))
        assert payload["op"] == "error"
        assert payload["code"] == "REQUEST_TOO_LARGE"
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


async def test_request_at_cap_is_accepted(base_data_dir: Path) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)
    seen: list[str] = []

    async def handler(op: str, channel: str) -> dict[str, object]:
        seen.append(channel)
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        # Build a valid request whose on-wire size sits just under the cap.
        channel = "c" * (control.CONTROL_MAX_REQUEST_BYTES - 40)
        response = await control.request(
            "pi", "127.0.0.1", 1, "n", base_data_dir, "subscribe", channel
        )
        assert response["op"] == "subscribe_ok"
        assert seen == [channel]
    finally:
        await server.stop()


async def test_request_payload_only_op_and_channel_decoded(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)
    seen: list[tuple[str, str]] = []

    async def handler(op: str, channel: str) -> dict[str, object]:
        seen.append((op, channel))
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        response = await control.request(
            "pi", "127.0.0.1", 1, "n", base_data_dir, "unsubscribe", "updates"
        )
    finally:
        await server.stop()

    assert seen == [("unsubscribe", "updates")]
    assert response == {"op": "subscribe_ok", "channel": "updates"}
    assert control.SUPPORTED_OPS == frozenset({"subscribe", "unsubscribe"})


async def test_handler_timeout_returns_error_not_traceback(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        await asyncio.sleep(control.CONTROL_TIMEOUT_S + 1)
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        reader, writer = await asyncio.open_unix_connection(str(path))
        writer.write(json.dumps({"op": "subscribe", "channel": "x"}).encode() + b"\n")
        await writer.drain()
        raw = await asyncio.wait_for(reader.readline(), timeout=control.CONTROL_TIMEOUT_S + 1)
        payload = json.loads(raw.decode("utf-8"))
        assert payload["op"] == "error"
        writer.close()
        await writer.wait_closed()
    finally:
        await server.stop()


async def test_stop_does_not_unlink_endpoint_taken_over(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    first = control.ControlServer(path, handler)
    await first.start()
    try:
        # Simulate another listener taking over the path: replace the socket
        # file with a fresh inode while keeping the filename.
        path.unlink()
        path.touch()
        os.chmod(path, 0o600)
        taken_over_inode = path.stat().st_ino
        assert taken_over_inode != first._inode

        await first.stop()
        # first.stop must not unlink because it no longer owns the endpoint.
        assert path.exists()
        assert path.stat().st_ino == taken_over_inode
    finally:
        if path.exists():
            path.unlink()


async def test_request_oversized_response_raises_control_error(
    base_data_dir: Path,
) -> None:
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def handler(op: str, channel: str) -> dict[str, object]:
        # Returning a huge payload makes the listener write an oversized line
        # back, which the client must convert to a clean ControlError.
        return {"op": "subscribe_ok", "channel": "x" * (control.CONTROL_MAX_REQUEST_BYTES + 4096)}

    server = control.ControlServer(path, handler)
    await server.start()
    try:
        with pytest.raises(control.ControlError):
            await control.request("pi", "127.0.0.1", 1, "n", base_data_dir, "subscribe", "x")
    finally:
        await server.stop()


async def test_request_malformed_response_raises_control_error(
    base_data_dir: Path,
) -> None:
    """A non-JSON response from the listener surfaces as a clean ControlError."""
    path = control.control_socket_path("pi", "127.0.0.1", 1, "n", base_data_dir)

    async def noop_handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    class GarbageServer(control.ControlServer):
        async def _handle_connection(self, reader, writer):  # type: ignore[no-untyped-def]
            try:
                await reader.readline()
                writer.write(b"not-json\n")
                await writer.drain()
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    server = GarbageServer(path, noop_handler)
    await server.start()
    try:
        with pytest.raises(control.ControlError):
            await control.request("pi", "127.0.0.1", 1, "n", base_data_dir, "subscribe", "x")
    finally:
        await server.stop()


def test_control_dir_raises_on_permission_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "d"
    base.mkdir()
    (base / control.CONTROL_DIR_NAME).mkdir()

    def boom(path: str, mode: int) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr("inter_agent.adapters.control.os.chmod", boom)
    with pytest.raises(OSError):
        control.control_dir(base)


async def test_start_returns_false_and_no_socket_on_chmod_failure(
    monkeypatch: pytest.MonkeyPatch, base_data_dir: Path
) -> None:
    path = control.control_socket_path("claude", "127.0.0.1", 1, "n", base_data_dir)
    real_chmod = os.chmod

    def boom(path_obj: str | os.PathLike[str], mode: int) -> None:
        if str(path_obj) == str(path):
            raise OSError("permission denied")
        real_chmod(path_obj, mode)

    monkeypatch.setattr("inter_agent.adapters.control.os.chmod", boom)

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)
    assert await server.start() is False
    # Fail closed: no permissive socket left behind, and the server is closed.
    assert not path.exists()
    assert server._server is None
    # The control directory still exists and is usable for other data.
    assert path.parent.exists()


async def test_request_surfaces_dir_setup_failure_as_control_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "d"

    def always_boom(path_obj: object, mode: int) -> None:
        raise OSError("denied")

    monkeypatch.setattr("inter_agent.adapters.control.os.chmod", always_boom)
    # control_socket_path -> control_dir -> chmod raises; request must wrap it.
    with pytest.raises(control.ControlError):
        await control.request("pi", "127.0.0.1", 1, "n", base, "subscribe", "updates")


async def test_chmod_failure_unlinks_only_just_bound_endpoint(
    monkeypatch: pytest.MonkeyPatch, base_data_dir: Path
) -> None:
    """On a chmod failure after a successful bind, start() removes only the
    endpoint this server just bound (the inode captured immediately after
    bind) and leaves unrelated siblings untouched."""
    path = control.control_socket_path("claude", "127.0.0.1", 1, "race", base_data_dir)
    sibling = path.parent / "sibling-file"
    sibling.write_text("unrelated", encoding="utf-8")

    async def handler(op: str, channel: str) -> dict[str, object]:
        return {"op": "subscribe_ok", "channel": channel}

    server = control.ControlServer(path, handler)

    def boom(p: str | os.PathLike[str], mode: int) -> None:
        if str(p) == str(path):
            raise OSError("permission denied")

    monkeypatch.setattr("inter_agent.adapters.control.os.chmod", boom)

    started = await server.start()
    assert started is False
    assert server._server is None
    # Fail-closed: the just-bound endpoint is removed; the sibling is untouched.
    assert not path.exists()
    assert sibling.exists()
    assert sibling.read_text(encoding="utf-8") == "unrelated"
    sibling.unlink()


async def test_unlink_owned_preserves_replaced_endpoint(tmp_path: Path) -> None:
    """_unlink_owned must never remove an endpoint whose inode/dev no longer
    match the captured bound identity, even when a replacement file sits on the
    same path (the setup-time replacement race)."""
    path = tmp_path / "control.sock"
    path.touch()
    os.chmod(path, 0o600)
    captured_replacement = (-1, -2)

    server = control.ControlServer(path, _async_ok_handler)

    # The on-disk file has a DIFFERENT identity than the captured one.
    on_disk = path.stat()
    assert (on_disk.st_ino, on_disk.st_dev) != captured_replacement

    await server._unlink_owned(*captured_replacement)
    # Replacement preserved: the non-matching on-disk file is left untouched.
    assert path.exists()
    assert path.stat().st_ino == on_disk.st_ino
    path.unlink()


async def test_unlink_owned_removes_matching_endpoint(tmp_path: Path) -> None:
    """_unlink_owned removes the endpoint when the on-disk identity still
    matches the captured bound identity (the normal shutdown / setup-failure
    still-owned case)."""
    path = tmp_path / "control.sock"
    path.touch()
    os.chmod(path, 0o600)
    captured = path.stat()

    server = control.ControlServer(path, _async_ok_handler)
    await server._unlink_owned(captured.st_ino, captured.st_dev)
    assert not path.exists()
