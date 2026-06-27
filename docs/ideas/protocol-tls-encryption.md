---
title: TLS encryption for WebSocket transport
description: Add optional or default TLS (wss://) support to encrypt message payloads and handshake metadata on the wire.
area: protocol
priority: user-prioritized
trigger: A concrete use case requires transport confidentiality, such as network or container deployment, or a security review mandates encrypted on-wire content.
source: User discussion of localhost plaintext transport and HMAC handshake scope
---

## Notes

- Support `wss://` alongside or instead of `ws://`.
- Auto-generate self-signed certificate and private key on first server start when TLS is enabled.
- Decide trust model: trust-on-first-use (TOFU), explicit certificate pin, or opt-out validation.
- Consider localhost/network default policy: opt-in for `127.0.0.1`, opt-out for other interfaces.
- Keep the existing HMAC challenge-response handshake inside the TLS tunnel for application-layer mutual authentication.
- Update client helpers, adapters, spec, and docs to discover and use the TLS endpoint.
- Evaluate TLS-PSK and Noise as certificate-free alternatives before committing to certificate-based TLS.
