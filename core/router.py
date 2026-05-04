from __future__ import annotations


class RouterMiddleware:
    """Future hook point (rate limits, channels, policy)."""

    async def before_route(self, _sender_session_id: str, _message: dict[str, object]) -> None:
        return None
