from __future__ import annotations

from typing import Any


class RouterMiddleware:
    """Future hook point (rate limits, channels, policy)."""

    async def before_route(self, _sender_session_id: str, _message: dict[str, Any]) -> None:
        return None
