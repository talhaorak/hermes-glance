# Security and privacy

## Scope

This is pre-1.0 software. Security fixes target `main`; there is no promised long-term support window. It is not a sandbox for untrusted local processes.

## Reporting

Use [GitHub private vulnerability reporting](https://github.com/talhaorak/hermes-glance/security/advisories/new). If that channel is unavailable, open an issue requesting a private contact **without exploit details, credentials, logs or transcripts**. Do not disclose private user information publicly. Response times are best effort.

## Data boundary

The observer connects only to a loopback Hermes runtime, obtains its local session token in memory, and uses observational RPC methods. It opens the session database read-only. Credentials are not intentionally logged, put in command arguments or persisted by Glance. The WebSocket connection invokes Hermes's normal client bookkeeping; read-only means no prompts, approvals, session creation or intentional session-store writes, not zero server bookkeeping.

Assistant text and session titles can still contain private content. Glance is visible on your screen and to screen sharing. Monitor JSON output contains conversation data: do not paste it unredacted into an issue. Reasoning events, tool arguments and tool-result payloads are excluded; this is **not** comprehensive secret redaction of assistant prose.

There is no analytics, remote upload, model call or automatic approval. A session link opens the existing Hermes handler. Local runtime authentication and event formats are internal integration contracts, not a security-stable public API.

## Distribution

Source builds are ad-hoc signed, not Developer ID signed/notarized. Do not disable Gatekeeper globally. Review source, build locally, and use normal per-app macOS approval if appropriate. Replacing the observer with `GLANCE_BRIDGE` or Python with `GLANCE_PYTHON` executes that chosen local program; use trusted paths only.
