from __future__ import annotations

from enum import Enum


class ErrorCode(Enum):
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    AUTH_FAILED = "AUTH_FAILED"
    BAD_ROLE = "BAD_ROLE"
    BAD_SESSION = "BAD_SESSION"
    BAD_NAME = "BAD_NAME"
    BAD_LABEL = "BAD_LABEL"
    NAME_TAKEN = "NAME_TAKEN"
    UNKNOWN_OP = "UNKNOWN_OP"
    BAD_TEXT = "BAD_TEXT"
    TEXT_TOO_LARGE = "TEXT_TOO_LARGE"
    UNKNOWN_TARGET = "UNKNOWN_TARGET"


ERROR_CODE_VALUES: tuple[str, ...] = tuple(code.value for code in ErrorCode)
