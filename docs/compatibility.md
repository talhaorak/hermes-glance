# Hermes compatibility

Glance is an early adapter against the local Hermes Desktop runtime, not a stable public SDK client.

## Inspected baseline

The initial local integration used Hermes source commit `251e5f7c0a`. This is a development baseline, **not** a minimum supported release. Do not infer support for arbitrary releases from a version number. The current CI tests Glance against synthetic representations of the inspected protocol, not against every Hermes release.

## Contracts used

| Concern | Current contract |
|---|---|
| Local runtime discovery | `hermes_cli.main` serve/dashboard processes and loopback listeners |
| Authentication | Local index session token followed by authenticated WebSocket upgrade |
| Activity | `session.active_list`, `session.events.since`, bounded replay events/open requests |
| Fallback/identity | Read-only SQLite session/message schema and durable session key |
| Navigation | `hermes://open/<durable-session-id>` |

The event projection accepts public assistant text and tool lifecycle, not reasoning or tool argument/result bodies. It does not attach/resume or take ownership of the live session. Read-only client connections still participate in ordinary server housekeeping.

## When compatibility fails

Open connection details in the widget. If the runtime cannot be reached, the bridge may display read-only history with unknown state. An omitted profile/owner or replay gap must remain visible as a coverage limitation. Never replace missing data with made-up running/waiting state.

For bug reports, provide Hermes version/commit, Glance commit, macOS/Python versions and a redacted error category. Never paste token-bearing URLs or raw monitor output.

## Before claiming another version supported

Verify discovery/authentication, exact durable-ID routing, real text/tool updates, pending requests, reconnect and replay gaps against that version. Add fixtures preserving the behavior contract and record which parts were actually exercised. The long-term goal is an officially supported read-only observer contract or a genuine companion plugin.
