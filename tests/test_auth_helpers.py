from __future__ import annotations

from inter_agent.core.auth import (
    build_hello,
    canonical_hello_transcript,
    client_proof,
    server_proof,
    verify_client_proof,
    verify_server_proof,
)


def test_canonical_hello_transcript_binds_expected_fields_only() -> None:
    hello = build_hello(
        role="agent",
        session_id="session-a",
        name="agent-a",
        label="Agent A",
        capabilities={"z": True, "core": {"version": "0.1"}},
        client_nonce="client-nonce",
    )
    hello["extra"] = "ignored"

    assert canonical_hello_transcript(hello) == (
        '{"capabilities":{"core":{"version":"0.1"},"z":true},'
        '"label":"Agent A","name":"agent-a","role":"agent",'
        '"session_id":"session-a"}'
    )


def test_proof_generation_is_deterministic_and_domain_separated() -> None:
    hello = build_hello(
        role="agent",
        session_id="session-a",
        name="agent-a",
        capabilities={},
        client_nonce="client-nonce",
    )

    server = server_proof(
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
    client = client_proof(
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )

    assert server == "931ed9f127808f1aeaffa4b9583f91381993f1a65d636dfcb255162677fc3f0c"
    assert client == "f7dd2a1ceca62429a9f3540e23663f53967146e9e8e2cb4dc031200ea8ea1b78"
    assert server != client


def test_proof_verification_succeeds_and_fails() -> None:
    hello = build_hello(
        role="control",
        session_id="ctl",
        name="control",
        capabilities={},
        client_nonce="client-nonce",
    )
    server = server_proof(
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
    client = client_proof(
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )

    assert verify_server_proof(
        server,
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
    assert not verify_server_proof(
        server,
        "wrong-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
    assert verify_client_proof(
        client,
        "shared-secret",
        client_nonce="client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
    assert not verify_client_proof(
        client,
        "shared-secret",
        client_nonce="other-client-nonce",
        server_nonce="server-nonce",
        hello=hello,
    )
