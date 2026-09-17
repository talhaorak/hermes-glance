# Verification scope

This file separates automated behavior checks from local GUI observations. It deliberately contains no real session titles, local user paths, screenshots or transcript excerpts.

## Reproduce

```sh
python3 -m unittest discover -s Tests/bridge -v
swift test
bash scripts/build.sh
codesign --verify --deep --strict 'dist/Hermes Glance.app'
```

Tests use synthetic protocol fixtures and temporary stores, not a real user's database. See GitHub Actions for the current result; historical local results do not replace remote CI.

## Local observations

The initial implementation was built on Apple Silicon with Swift 6.3.3 and macOS 26. A real second-monitor window was checked for saved geometry, floating level and absence of automatic foreground focus. An existing-session card opened the corresponding Hermes conversation without sending a prompt.

Compact rows were measured at 72 points pitch in the accessibility tree. Expanding one row revealed additional event lines and changed the show-more label without navigating; other rows remained collapsed. Existing sessions showed changing tool lifecycle events through the observer. Continuous outputs were approximately one second apart.

## Automated contracts

Protocol tests cover local WebSocket authentication/framing, safe read methods, replay sequence/epoch handling, disconnect cleanup, session isolation, explicit human requests, hidden/rewound/internal-message filtering and read-only fallback. Swift tests cover decoding, filters, layout budget, saved-screen geometry, expansion continuity and coalesced NDJSON publication.

## Not claimed

- Real user approval-prompt animation was not exercised; waiting projection is fixture-tested.
- Full-screen game/Space switching and all monitor arrangements are not certified.
- Named-profile/remote/independent CLI aggregation is not covered.
- Event polling is not push streaming; activity timestamps are observation timestamps.
- Tool lifecycle labels are not semantic task summaries, success proof or percent-complete estimates.
