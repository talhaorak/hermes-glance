# Publishing in the Hermes ecosystem

## Current status

Hermes Glance is an independent macOS companion, **not currently a Hermes plugin**. Publishing this repository does not put it in the official catalog. No upstream issue, catalog PR or Discord announcement has been submitted as part of initial publication.

The catalog's admission CI requires a supported plugin manifest and successful plugin validation. There is no verified published policy that admits standalone native applications without an installable integration. A manifest-only package may pass technical validation, but that is not evidence that an empty wrapper for this app is eligible.

## Recommended path

1. **Ship honestly as a companion:** public source, MIT license, install instructions, real scope/limitations and reproducible tests. Before a promotional release, add sanitized screenshots and useful activity summaries; English-first UI and Turkish localization would improve accessibility to the community.
2. **Ask about placement:** show maintainers the native-app use case and ask whether a community showcase is appropriate, or whether an installable companion integration is expected. Do not imply approval.
3. **Build a real integration if accepted:** for example, a read-only event adapter or Desktop SDK status surface that genuinely works inside Hermes, with the native window distributed separately. Preserve local-only behavior and profile boundaries. Neither a Python backend nor a Desktop half is universally mandatory; choose a package that actually supplies the declared capability.
4. **Prepare a versioned, validated package:** release/tag, supported manifest, complete documentation, accurate capabilities, security-scan review and a reachable full 40-character commit SHA. Catalog code must not update itself outside the reviewed pin process.
5. **Submit the catalog PR:** add `plugin-catalog/hermes-glance.yaml` to `NousResearch/hermes-agent`; a maintainer reviews/merges it. Use `tier: community`, `category: desktop`, `platforms: [macos]` if that remains accurate. Later SHA updates require new reviewed PRs.

## Exact references

| Reference | Purpose |
|---|---|
| [Public plugins page](https://hermes-agent.nousresearch.com/docs/plugins) | Where accepted plugins appear |
| [Catalog guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugin-catalog) | User/author workflow |
| [Registry policy and schema](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md) | Admission rules and YAML fields |
| [Admission CI](https://github.com/NousResearch/hermes-agent/blob/main/.github/workflows/plugin-catalog-ci.yml) | Manifest, validation and security gates |
| [Desktop Plugin SDK](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk) | Genuine Desktop integration and unified packaging |

The source of truth is the YAML registry inside the main Hermes repository, not a separate registry repository. Website/Desktop use generated `plugins.json`; CLI resolution uses generated `plugin-catalog.json`. Do not manually edit these generated feeds.

The catalog requires `name`, HTTPS `repo`, `sha`, `description` and `maintainer`. Declare actual capabilities and pin images to reviewed GitHub-hosted content where possible. `dangerous` scanner findings fail admission; `caution` requires human review. Catalog inclusion is a point-in-time review, not a sandbox or a comprehensive security audit. Recheck current policy before submitting; an older two-week-release-age rule is not in the currently inspected catalog README.

Once a real plugin package exists, validate it with:

```sh
hermes plugins validate <plugin-directory>
# From a Hermes checkout with the proposed YAML entry:
python3 scripts/validate_plugin_catalog.py plugin-catalog/
```

The [plugin development guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins) also points authors to the Nous Research Discord `#plugins-skills-and-skins` channel for promotion. Posting there does not admit a project to the catalog.

## Draft placement inquiry — not submitted

**Title:** Catalog eligibility / community showcase: Hermes Glance macOS companion

> I maintain [Hermes Glance](https://github.com/talhaorak/hermes-glance), a standalone SwiftUI macOS companion with a local Python read-only observer. It provides a second-screen view of Hermes session activity without replacing Hermes Desktop.
>
> It currently does not ship a Hermes plugin manifest or Desktop SDK extension, so I am not presenting it as compatible with `hermes plugins install`.
>
> Is there an appropriate community showcase or companion-app listing for this project? If the plugin catalog requires an installable integration, would a genuine read-only Glance bridge and/or Desktop SDK component be an appropriate submission while the native app remains separately distributed?
>
> Installation, scope and limitations are documented in the repository. It is currently an early source-build alpha, with meaningful semantic summaries still on the roadmap. I would welcome packaging guidance before proposing a catalog entry.
