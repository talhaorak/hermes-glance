# Product direction

## Why this exists

Hermes Desktop provides a rich conversation surface. A second-monitor observer serves a different job: keep several ongoing sessions visible while another application occupies the main screen. Glance should answer **which work, what is happening, what changed, and do I need to act?**

The alpha already supplies compact independent visibility and exact-session navigation. Raw labels such as `Tool finished: execute_code` are a known product gap, **not** an adequate answer to those questions. The project is useful as an observation shell, not yet a semantic work-status dashboard.

## Priorities, not promises

1. **Meaningful status:** preserve the latest user-facing assistant commentary, separate task summary from current tool activity, and show the latest concrete result. Add project/workspace identity so truncated session titles remain distinguishable. Every claim must point to source evidence; no invented percent-complete or inferred success.
2. **Attention inbox:** distinguish explicit questions, approval requests, failures, genuine completion and connection loss. Add local unread/acknowledged state, quiet hours and opt-in notifications. “No recent event” must not mean “stuck.”
3. **Better glanceability:** adjustable density/text size, hover/full title, expandable task timeline and last-change age. Keep a stable row order, per-session pinning and accessibility options.
4. **Reliable integration:** a documented read-only event adapter, negotiated capabilities, multi-profile scope, replay-gap recovery and tests against supported Hermes releases. Prefer a genuine companion plugin over relying forever on internal runtime contracts.
5. **Distribution:** English/Turkish localization, signed/notarized macOS builds, reproducible release artifacts and then a catalog submission with an honest native-app/plugin distinction.

## Summary strategy

Start without an LLM: prioritize explicit assistant progress/commentary and completed-result messages; retain tool activity as secondary detail. A future optional summarizer must be opt-in, disclose provider/cost/data transfer, cache by source change, and never send private transcripts to a service by default.

## Not planned by default

Glance is not another chat client. It will not auto-approve actions, silently send prompts, take ownership of sessions, or modify Hermes core. Other operating systems may be future contributors' work; they are not currently supported.
