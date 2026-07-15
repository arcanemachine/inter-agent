from __future__ import annotations

from pathlib import Path

import pytest

from inter_agent.adapters.claude import dedup


class TestDedup:
    def test_first_send_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False

    def test_identical_send_within_window_is_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False
        assert dedup.is_duplicate_send("me", "a", "hello") is True

    def test_different_text_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False
        assert dedup.is_duplicate_send("me", "a", "world") is False

    def test_different_target_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False
        assert dedup.is_duplicate_send("me", "b", "hello") is False

    def test_different_sender_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False
        assert dedup.is_duplicate_send("you", "a", "hello") is False

    def test_expired_entry_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        import time

        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "a", "hello") is False

        # Shift the recorded timestamp well past the dedup window.
        cache = dedup._read_cache(dedup._dedup_path())
        key = next(iter(cache))
        cache[key] = time.time() - (dedup.DEDUP_WINDOW_S + 10)
        dedup._atomic_write(dedup._dedup_path(), cache)

        assert dedup.is_duplicate_send("me", "a", "hello") is False

    def test_corrupt_cache_is_treated_as_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        path = dedup._dedup_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")
        # Corrupt cache must not raise and must allow the send through.
        assert dedup.is_duplicate_send("me", "a", "hello") is False


class TestPublishDedup:
    def test_first_publish_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False

    def test_identical_publish_within_window_is_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False
        assert dedup.is_duplicate_publish("me", "updates", "hello") is True

    def test_different_channel_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False
        assert dedup.is_duplicate_publish("me", "other", "hello") is False

    def test_different_text_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False
        assert dedup.is_duplicate_publish("me", "updates", "world") is False

    def test_different_sender_is_not_duplicate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False
        assert dedup.is_duplicate_publish("you", "updates", "hello") is False

    def test_publish_does_not_collide_with_send(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("INTER_AGENT_DATA_DIR", str(tmp_path))
        assert dedup.is_duplicate_send("me", "updates", "hello") is False
        # A publish with the same channel/text/sender is still delivered.
        assert dedup.is_duplicate_publish("me", "updates", "hello") is False
