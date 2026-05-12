# Error Codes

Protocol errors are returned as `{"op":"error","code":"...","message":"..."}`. The `code` field is stable for clients and adapters; `message` is human-readable context and may vary.

| Code | Trigger condition | Client expectation |
| --- | --- | --- |
| `PROTOCOL_ERROR` | The first frame is not `hello`, a frame is invalid JSON, a frame is not a JSON object, or `hello.capabilities` is missing or not an object. | Treat the connection as invalid and reconnect with a valid protocol frame. |
| `AUTH_FAILED` | `hello.token` does not match the server token. | Do not retry until token state has been refreshed or corrected. |
| `TOO_MANY_CONNECTIONS` | A valid connection attempt would exceed the configured active connection limit. | Close unused sessions or increase the local connection limit. |
| `BAD_ROLE` | `hello.role` is missing or is not `agent` or `control`, or an agent-role session attempts a control-only operation such as `shutdown`. | Send a valid role or use a control-role connection for control-only operations. |
| `BAD_SESSION` | `hello.session_id` is missing, empty, or not a string. | Generate and send a string session ID. |
| `SESSION_TAKEN` | `hello.session_id` is already active on another connection. | Reconnect after the previous connection closes or generate a new session ID. |
| `BAD_NAME` | An agent `hello.name` is missing or fails routing-name validation. | Choose a lowercase routing name matching the documented name format. |
| `BAD_LABEL` | `hello.label` is present but is neither a string nor `null`. | Omit the label, send `null`, or send a string display label. |
| `NAME_TAKEN` | An agent routing name is already connected. | Choose a different routing name or disconnect the existing session. |
| `UNKNOWN_OP` | A post-handshake frame uses an unsupported `op`. | Use a supported core operation or an extension envelope. |
| `BAD_TEXT` | A `send` or `broadcast` operation has a non-string `text`. | Send message text as a string. |
| `BAD_CUSTOM_TYPE` | A `custom` operation has a missing, empty, non-string, or oversized `custom_type`. | Send a non-empty custom type within the configured byte limit. |
| `TEXT_TOO_LARGE` | A direct or broadcast message exceeds configured UTF-8 byte text limits (`INTER_AGENT_DIRECT_MAX` or `INTER_AGENT_BROADCAST_MAX`). | Shorten or split the message. |
| `CUSTOM_PAYLOAD_TOO_LARGE` | A `custom.payload` exceeds the configured JSON-encoded UTF-8 byte limit (`INTER_AGENT_CUSTOM_PAYLOAD_MAX`). | Shorten or split the custom payload. |
| `UNKNOWN_TARGET` | A direct `send` or targeted `custom` operation names no connected target. | Refresh session presence and retry with a connected routing name. |
| `AMBIGUOUS_TARGET` | A direct `send` or targeted `custom` operation uses a prefix that matches multiple connected targets. | Retry with a longer prefix or exact routing name. |
