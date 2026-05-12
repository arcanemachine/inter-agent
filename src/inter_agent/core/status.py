from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoreCommandStatus:
    """Static command capabilities exposed to host adapters."""

    list_supported: bool


def command_status() -> CoreCommandStatus:
    """Return core command capabilities that do not require a live server."""
    return CoreCommandStatus(list_supported=True)
