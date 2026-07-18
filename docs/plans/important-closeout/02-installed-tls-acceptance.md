# Installed cross-adapter TLS acceptance

Status: concrete; queued after Pi mailbox

## Goal

Prove that the installed Pi and Claude Code integration paths interoperate over `wss://`, not merely that core server/client unit tests pass. Fix only defects exposed by this acceptance.

## Existing baseline

Core TLS already provides host-based defaults, explicit enable/disable, self-signed material generation, configured certificate/key paths, restrictive POSIX permissions, and client trust of the selected certificate. Focused core/config verification passed 15 tests during planning. Existing Pi/Claude live adapter tests primarily exercise plaintext endpoints.

## Required matrix

Run real server/listener/helper paths for both adapters against one TLS server:

1. generated default certificate/key in an isolated data directory;
2. explicit TLS enable on loopback;
3. Pi listener + Claude listener authenticate and appear in list;
4. Pi-to-Claude and Claude-to-Pi direct messages;
5. broadcast delivery;
6. subscribe/unsubscribe, publish in both directions, channel diagnostics, and publisher exclusion;
7. status/list/control helper behavior over TLS;
8. reconnect after TLS server restart using the same state/certificate;
9. plaintext client rejection against the TLS endpoint;
10. wrong/untrusted certificate failure with bounded actionable diagnostics;
11. Pi settings propagation of `tls`, `tlsCert`, `tlsKey`, and `dataDir`;
12. Claude wrapper/helper propagation through its normal environment/config path.

Use `unused_tcp_port` and isolated home/config/state paths. Never read or log real user secrets.

## Test architecture

Add one bounded cross-adapter TLS integration module or extend the existing cross-adapter matrix only if that keeps fixtures understandable. Start `run_server(..., tls=True)` with isolated state. Launch actual adapter listener APIs/helper CLIs rather than replacing TLS construction with mocks. Assertions must observe delivered protocol/adapter output.

Separate tests may cover:

- generated material and permission assertions;
- installed-config environment propagation in Pi/Claude static/wrapper tests;
- expected failure diagnostics.

Avoid certificate/network tests that depend on external hosts or machine-global trust stores.

## Defect policy

If the matrix fails:

- fix TLS/config propagation at the owning layer;
- keep core semantics universal;
- do not add host-specific endpoint/state defaults;
- do not disable certificate validation merely to pass;
- do not broaden the documented localhost single-user threat model;
- add a regression test before the fix.

If no defect is found, this item may be test/documentation-only.

## Non-goals

- No mTLS, public CA automation, certificate rotation service, TOFU database, federation, or remote multi-user security claim.
- No change to loopback plaintext default or non-loopback TLS default.
- No replacement with TLS-PSK or Noise.
- No claim that transport encryption makes hostile same-user or multi-tenant operation safe.

## Documentation requirements

Update evergreen docs only for verified behavior. State clearly:

- adapters inherit the same endpoint/TLS configuration as core;
- generated certificates require shared/reachable state or explicit cert configuration;
- TLS and HMAC authentication are both required when TLS is enabled;
- remote/multi-user hardening remains outside the baseline.

## Focused checks

The activation packet must name exact tests. In the monorepo baseline include:

```bash
uv run pytest \
  tests/test_tls_transport.py \
  tests/test_config_resolution.py \
  tests/integration/test_pi_adapter_live.py \
  tests/integration/test_claude_adapter_live.py \
  tests/integration/test_cross_adapter_pubsub_live.py -q
./run-checks.sh
git diff --check
```

Run Pi type/build/format and strict Claude plugin validation if integration/config assets change.

## End-to-end acceptance

Start an isolated loopback TLS server with generated material, connect one Pi and one Claude adapter through their normal helpers, exchange direct and channel messages both ways, inspect channels, restart the server, and observe successful authenticated reconnection. Then attempt one plaintext connection and one client using an unrelated certificate; both must fail without exposing secrets or tracebacks.
