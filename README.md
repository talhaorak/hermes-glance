# Hermes Glance

[![CI](https://github.com/talhaorak/hermes-glance/actions/workflows/ci.yml/badge.svg)](https://github.com/talhaorak/hermes-glance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**A compact, local-first second-monitor companion for Hermes Desktop on macOS.**

Keep your main screen on your work. Glance keeps ongoing Hermes sessions visible in an independent floating window, highlights explicit input requests, and opens the corresponding conversation when you click its title.

> **Early alpha · community project · not an official Nous Research product.**
> This is a standalone macOS application, not yet an installable Hermes plugin. It observes runtime activity; it does **not yet produce meaningful semantic task summaries**. A tool name alone is often insufficient context. Improving that is the first [roadmap](ROADMAP.md) priority.

## What works today

- **Second-screen window:** saved position/size, display selector, always-on-top toggle and hide-to-menu-bar behavior.
- **Compact session list:** Active/All/Waiting filters; expand individual rows for up to twelve recent event lines.
- **Live activity observation:** assistant text and tool lifecycle events, fetched approximately once per second over a local authenticated WebSocket RPC connection—not push streaming.
- **Attention signals:** authoritative waiting requests appear first with a subtle amber pulse; Reduce Motion is respected.
- **Existing-session handoff:** title/arrow opens the durable session link in Hermes; expanding details does not navigate or send a message.

## Build and run

Requires **macOS 13+**, **Swift 5.9+**, **Python 3.10+**, and an already working local Hermes Desktop installation. Apple Silicon is locally verified; Intel and the minimum macOS deployment target are not yet manually verified. No external Swift or Python packages are required.

```sh
git clone https://github.com/talhaorak/hermes-glance.git
cd hermes-glance
python3 -m unittest discover -s Tests/bridge -v
bash scripts/build.sh
open 'dist/Hermes Glance.app'
```

The build script runs the Swift tests, builds a native `.app`, bundles the observer and ad-hoc signs it. **It is not Developer ID signed or notarized.** No public binary release is promised yet; see [security guidance](SECURITY.md). Install Apple command-line developer tools and a suitable Python if they are not already available.

Hermes Desktop must remain running. The observer attempts to discover a compatible local backend. An incompatible or unreachable runtime produces a visible warning rather than invented session state.

## Using the widget

The first launch chooses a secondary display when available. Drag the window or use **… → Ekrana taşı** to move it. **Her zaman üstte** controls floating behavior. Closing the window hides it; use the menu-bar leaf icon to show or quit it.

The current interface is primarily Turkish:

| Label | Meaning |
|---|---|
| Aktif / Tümü / Bekleyen | Active / All / Waiting |
| Daha fazla / Daha az | Show more / Show less |
| Çalışıyor / Bekliyor | Running / Waiting |
| Canlı | Runtime-backed activity, not a guarantee that text just changed |
| Bağlantı ve kapsam | Connection and coverage details |

The widget does not automatically resize your existing window after an update. Rows are intentionally compact; expand only the session you need to inspect.

## Honest limitations

- **Meaning, not just motion, is unfinished.** Current activity may say `Tool finished: read_file`; it is not an evidence-backed explanation of overall progress. No LLM summaries or progress percentages are generated.
- **Coverage is scoped.** The current adapter observes verified sessions in the selected local profile/runtime. It does not aggregate every independent CLI, gateway, remote backend or profile. Named-profile navigation is not end-to-end verified.
- **The integration is version-sensitive.** It uses internal Hermes runtime event/auth contracts and SQLite schema. See [compatibility](docs/compatibility.md); no broad version-support claim is made.
- **Events are bounded.** Polling is about one second, replay gaps are reported, and fallback text is persisted conversation history—not terminal stdout. Event timestamps are observation times, not guaranteed generation times.
- **Desktop behavior varies.** Window flags support multiple Spaces/full-screen auxiliary visibility; actual full-screen game/Space transitions and live approval-prompt animation have not been manually verified on every setup.

## Privacy

Data stays local. There is no analytics, cloud upload, model request or automatic approval. The observer uses a loopback connection and a read-only database handle; it does not intentionally write Hermes session/configuration files. Connecting still triggers normal Hermes client-heartbeat bookkeeping.

Session titles and assistant text can be private. **Do not post raw monitor JSON, transcripts, tokens or unredacted screenshots.** Thinking/reasoning events and tool argument/result payloads are excluded, but assistant prose is not comprehensively secret-redacted. Details: [SECURITY.md](SECURITY.md).

## Architecture and diagnostics

```text
Hermes local runtime ── read-only event RPC (~1 Hz) ─┐
                                                   ├─ Python observer ─ NDJSON ─ SwiftUI/AppKit widget
Hermes state.db ─────── read-only fallback ──────────┘                              │
                                                                       existing-session deep link
```

```sh
python3 bridge/monitor.py --once  # Private session data may appear in stdout
swift test
```

`GLANCE_PYTHON` and `GLANCE_BRIDGE` override trusted executable/script paths. `HERMES_GLANCE_URL` selects an explicit loopback HTTP runtime. `HERMES_HOME` selects the session store; the observer also accepts `--home` and `--profile`. These overrides do not imply verified cross-profile GUI navigation.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md), [ROADMAP.md](ROADMAP.md), [verification notes](VERIFICATION.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). See the [Hermes catalog publication guide](docs/plugin-catalog.md) for the distinction between a native companion and an installable plugin. Issues and small PRs are welcome. For security concerns use [private reporting](https://github.com/talhaorak/hermes-glance/security/advisories/new).

## License and affiliation

[MIT](LICENSE) © Talha Orak. Hermes is a separate project by [Nous Research](https://github.com/NousResearch/hermes-agent). Glance is an independent companion, not an endorsed or bundled Hermes component.
