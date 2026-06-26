from inter_agent.core.auth import AUTH_METHOD
from inter_agent.core.client import build_hello
from inter_agent.core.shared import control_hello, validate_name


def test_build_hello_payload() -> None:
    payload = build_hello("sess-1", "agent-a")
    assert payload["op"] == "hello"
    assert payload["role"] == "agent"
    auth = payload["auth"]
    assert isinstance(auth, dict)
    assert auth["method"] == AUTH_METHOD
    assert isinstance(auth["client_nonce"], str)
    assert "token" not in payload
    assert "label" not in payload


def test_build_hello_payload_with_label() -> None:
    payload = build_hello("sess-1", "agent-a", "Agent A")
    assert payload["label"] == "Agent A"


def test_control_hello_payload() -> None:
    payload = control_hello("ctl-1")
    assert payload["op"] == "hello"
    assert payload["role"] == "control"
    assert "token" not in payload


def test_validate_name() -> None:
    assert validate_name("agent-a")
    assert not validate_name("Agent-A")
