# Contributing

Hermes Glance is an early macOS companion, not an official Hermes product. Small, tested contributions are welcome; open an issue before a large change.

## Development

Use macOS, Swift 5.9+ and Python 3.10+. No external language packages are required.

```sh
python3 -m unittest discover -s Tests/bridge -v
swift test
bash scripts/build.sh
```

Python protocol fixtures use a local test server and temporary databases; they do not require a live Hermes installation. `Tests` is capitalized for case-sensitive filesystems.

## Changes we welcome

1. Useful, evidence-backed activity summaries rather than raw tool names.
2. Runtime compatibility fixtures, reconnect behavior and clear coverage reporting.
3. Accessible compact layouts, localization and multi-monitor improvements.
4. Safe multi-profile identity and exact-session navigation.
5. Reproducible packaging and signing documentation.

## Pull requests

Use a topic branch. Describe the problem, behavior change and actual test commands/results. Add a failing regression before a bug fix. Keep UI, bridge and tests scoped; preserve existing JSON consumers. Do not patch Hermes core, auto-answer requests, attach to/take ownership of a running session, or silently add cloud calls.

Do not submit `.build`, `dist`, real transcripts, credentials or private screenshots. Use clearly labeled synthetic fixtures. Share only redacted diagnostics. We do not require a CLA; contributions use the MIT license. Commits should accurately reflect their author and any voluntarily supplied co-authors.

For a vulnerability, follow SECURITY.md rather than filing a public issue with secrets.
