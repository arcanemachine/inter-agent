from __future__ import annotations

from pathlib import Path

import pytest

from inter_agent.adapters.claude import formatting, state


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
