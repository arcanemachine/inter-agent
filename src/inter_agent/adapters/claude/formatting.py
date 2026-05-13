"""Stdout notification formatting for the Claude Code Monitor listener."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
STDOUT_CAP = 400


def sanitize_for_stdout(text: str) -> str:
    """Strip ANSI codes and replace control characters for safe stdout output."""
    text = ANSI_RE.sub("", text)
    out: list[str] = []
    for ch in text:
        if ch == "\t":
            out.append(ch)
        elif ch in "\n\r":
            out.append("↵")
        elif unicodedata.category(ch).startswith("C"):
            continue
        else:
            out.append(ch)
    return "".join(out)


def truncate_for_stdout(text: str, cap: int = STDOUT_CAP) -> tuple[str, bool, int]:
    """Return (truncated_text, was_truncated, full_length)."""
    full_len = len(text)
    if full_len <= cap:
        return text, False, full_len
    return text[:cap], True, full_len


def format_notification(
    msg_id: str,
    from_name: str,
    text: str,
    to: str | None = None,
) -> str:
    """Format a single inbound message as a Monitor notification line."""
    sanitized = sanitize_for_stdout(text)
    truncated, was_truncated, full_len = truncate_for_stdout(sanitized)
    kind = f' kind="direct" to="{to}"' if to else ' kind="broadcast"'
    if was_truncated:
        return (
            f'[inter-agent msg={msg_id} from="{from_name}"{kind} '
            f"truncated={full_len}] {truncated}"
        )
    return f'[inter-agent msg={msg_id} from="{from_name}"{kind}] {truncated}'


def format_truncation_pointer(msg_id: str, full_len: int, log_path: Path) -> str:
    """Emit a continuation pointer for truncated messages."""
    return f"[inter-agent msg={msg_id} cont] " f"full text {full_len} bytes at {log_path}"
