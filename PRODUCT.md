# Hermes Glance

## Purpose
A quiet, independent macOS widget on the user's second monitor. The primary display can remain in a full-screen app while Hermes Desktop works behind it. Glance is an observer, not another agent or chat client.

## Acceptance criteria
1. Launch a real native .app and place it on a secondary display when available. Persist size/location and offer screen selection; never steal focus during refresh. Allow always-on-top and full-screen auxiliary visibility.
2. Show real active Hermes sessions with title, state and latest activity in compact two-line rows. Default view excludes idle history; target at least seven collapsed rows in a 400×680 window. Expand an individual row with “Daha fazla” to show additional recent lines without navigating away. Distinguish runtime state from durable history. Never manufacture progress or call an idle chat “waiting for input”.
3. Put authoritative input/approval requests first with a clear amber label. Show disconnected/unknown honestly, retaining no misleading claim of liveness.
4. Clicking an identified session opens that exact existing session in Hermes Desktop; no new sessions, prompt submission, approval or interruption.
5. Keep data local and read-only. No credentials in output, no configuration changes or patches to Hermes, no modifications to other profiles. Native window and tests live here.

## Visual direction
Warm off-white compact list, sage running states, amber for actionable waiting. Remove the oversized logo and badges: one narrow header plus filters. Slow amber pulse only on attention rails/dots, respecting Reduce Motion; no flashing whole window. Expanded text is opt-in per session. Live runtime events drive current activity; transport cadence and fallback must be honest, with no reasoning-token display.

## Architecture
Native SwiftUI/AppKit application, a local Python observer emitting newline-delimited JSON, and the existing Hermes session navigation mechanism. Separate components can be tested independently. Any integration limits must be documented in README and surfaced in the UI, not hidden by plausible fallback labels.

## Verification plan
Unit tests for state projection, transcript bounding, waiting prioritization, filters, schema decoding and screen geometry. Live observer smoke test against this installation. Build and launch the packaged app, inspect its real window and second-monitor placement, exercise existing-session navigation without sending a prompt. Pending-input test through a read-only controlled fixture unless a real pending request exists. Document live versus fixture evidence separately.
