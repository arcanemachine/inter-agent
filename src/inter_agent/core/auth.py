from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Protocol

AUTH_METHOD = "hmac-sha256"
SERVER_PROOF_DOMAIN = "inter-agent/server-proof/v1"
CLIENT_PROOF_DOMAIN = "inter-agent/client-proof/v1"


class AuthError(RuntimeError):
    """Raised when challenge-response authentication fails."""


class AuthProtocolError(RuntimeError):
    """Raised when a peer does not speak the auth handshake protocol."""


class HandshakeWebSocket(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...


@dataclass(frozen=True)
class AuthChallenge:
    server_nonce: str
    server_proof: str


def generate_nonce() -> str:
    """Return a high-entropy URL-safe nonce for auth handshakes."""
    return secrets.token_urlsafe(32)


def canonical_hello_transcript(hello: dict[str, object]) -> str:
    """Return the canonical hello fields bound into auth proofs."""
    payload = {
        "role": hello.get("role"),
        "session_id": hello.get("session_id"),
        "name": hello.get("name"),
        "label": hello.get("label"),
        "capabilities": hello.get("capabilities"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _proof_message(
    domain: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> bytes:
    transcript = canonical_hello_transcript(hello)
    return f"{domain}\n{client_nonce}\n{server_nonce}\n{transcript}".encode()


def generate_proof(
    secret: str,
    domain: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> str:
    """Generate a hex HMAC-SHA-256 auth proof."""
    return hmac.new(
        secret.encode("utf-8"),
        _proof_message(domain, client_nonce=client_nonce, server_nonce=server_nonce, hello=hello),
        hashlib.sha256,
    ).hexdigest()


def server_proof(
    secret: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> str:
    return generate_proof(
        secret,
        SERVER_PROOF_DOMAIN,
        client_nonce=client_nonce,
        server_nonce=server_nonce,
        hello=hello,
    )


def client_proof(
    secret: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> str:
    return generate_proof(
        secret,
        CLIENT_PROOF_DOMAIN,
        client_nonce=client_nonce,
        server_nonce=server_nonce,
        hello=hello,
    )


def verify_server_proof(
    proof: str,
    secret: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> bool:
    expected = server_proof(
        secret,
        client_nonce=client_nonce,
        server_nonce=server_nonce,
        hello=hello,
    )
    return hmac.compare_digest(proof, expected)


def verify_client_proof(
    proof: str,
    secret: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> bool:
    expected = client_proof(
        secret,
        client_nonce=client_nonce,
        server_nonce=server_nonce,
        hello=hello,
    )
    return hmac.compare_digest(proof, expected)


def auth_object(client_nonce: str) -> dict[str, object]:
    return {"method": AUTH_METHOD, "client_nonce": client_nonce}


def build_hello(
    *,
    role: str,
    session_id: str,
    name: str,
    label: str | None = None,
    capabilities: dict[str, object] | None = None,
    client_nonce: str | None = None,
) -> dict[str, object]:
    nonce = client_nonce or generate_nonce()
    payload: dict[str, object] = {
        "op": "hello",
        "auth": auth_object(nonce),
        "role": role,
        "session_id": session_id,
        "name": name,
        "capabilities": {} if capabilities is None else capabilities,
    }
    if label is not None:
        payload["label"] = label
    return payload


def client_nonce_from_hello(hello: dict[str, object]) -> str | None:
    auth = hello.get("auth")
    if not isinstance(auth, dict):
        return None
    if auth.get("method") != AUTH_METHOD:
        return None
    nonce = auth.get("client_nonce")
    if not isinstance(nonce, str) or not nonce:
        return None
    return nonce


def build_auth_challenge(
    secret: str,
    *,
    client_nonce: str,
    hello: dict[str, object],
    server_nonce: str | None = None,
) -> dict[str, object]:
    nonce = server_nonce or generate_nonce()
    return {
        "op": "auth_challenge",
        "method": AUTH_METHOD,
        "server_nonce": nonce,
        "server_proof": server_proof(
            secret,
            client_nonce=client_nonce,
            server_nonce=nonce,
            hello=hello,
        ),
    }


def parse_auth_challenge(payload: dict[str, object]) -> AuthChallenge:
    if payload.get("op") != "auth_challenge" or payload.get("method") != AUTH_METHOD:
        raise AuthProtocolError("expected auth_challenge")
    server_nonce = payload.get("server_nonce")
    proof = payload.get("server_proof")
    if not isinstance(server_nonce, str) or not server_nonce:
        raise AuthProtocolError("auth_challenge missing server_nonce")
    if not isinstance(proof, str) or not proof:
        raise AuthProtocolError("auth_challenge missing server_proof")
    return AuthChallenge(server_nonce=server_nonce, server_proof=proof)


def build_auth_response(
    secret: str,
    *,
    client_nonce: str,
    server_nonce: str,
    hello: dict[str, object],
) -> dict[str, object]:
    return {
        "op": "auth_response",
        "client_proof": client_proof(
            secret,
            client_nonce=client_nonce,
            server_nonce=server_nonce,
            hello=hello,
        ),
    }


def _text_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        return frame.decode("utf-8")
    return frame


def _json_object(raw: str) -> dict[str, object]:
    payload: object = json.loads(raw)
    if not isinstance(payload, dict):
        raise AuthProtocolError("auth frame must be a JSON object")
    return {str(key): value for key, value in payload.items()}


async def client_handshake(ws: HandshakeWebSocket, secret: str, hello: dict[str, object]) -> str:
    """Run client side challenge-response and return the final server frame."""
    client_nonce = client_nonce_from_hello(hello)
    if client_nonce is None:
        raise AuthProtocolError("hello missing auth client_nonce")

    await ws.send(json.dumps(hello))
    challenge_raw = _text_frame(await ws.recv())
    challenge_payload = _json_object(challenge_raw)
    if challenge_payload.get("op") == "error":
        return challenge_raw
    challenge = parse_auth_challenge(challenge_payload)
    if not verify_server_proof(
        challenge.server_proof,
        secret,
        client_nonce=client_nonce,
        server_nonce=challenge.server_nonce,
        hello=hello,
    ):
        raise AuthError("server authentication failed")

    await ws.send(
        json.dumps(
            build_auth_response(
                secret,
                client_nonce=client_nonce,
                server_nonce=challenge.server_nonce,
                hello=hello,
            )
        )
    )
    return _text_frame(await ws.recv())
