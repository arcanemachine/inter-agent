from inter_agent.core.client import build_hello
from inter_agent.core.shared import control_hello, validate_name


def test_build_hello_payload() -> None:
    payload = build_hello("tok", "sess-1", "agent-a")
    assert payload["op"] == "hello"
    assert payload["role"] == "agent"
    assert payload["token"] == "tok"


def test_control_hello_payload() -> None:
    payload = control_hello("tok", "ctl-1")
    assert payload["op"] == "hello"
    assert payload["role"] == "control"


def test_validate_name() -> None:
    assert validate_name("agent-a")
    assert not validate_name("Agent-A")
