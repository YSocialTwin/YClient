# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [2.1.0] - 2026-10-20

### Added
- Topic sampling weighted by frequency in the moving window (only topics with count > 0); exactly one topic per generated post.
- Hashtags in canonical form: no leading `#`, apostrophes and accents kept, case-insensitive identity.
- Prompts i18n: prompts moved out of the code into `prompts_internal.json`, read through `prompt_store` with language support.
- Prompts i18n: protocol tokens and tolerant parsers (no `eval`); Italian internal prompt pack.
- Prompts i18n: localized follow action and reciprocal-follow verb; persona fragments moved into the packs.
- Prompts i18n: the client reads the prompt language and shows profile values in it.
- Memory M5: the memory engine renders its texts in the simulation prompt language.
- Memory M2: the log shows which `yclient_memory` is loaded (path, version, language); errors name the Agent Memory plugin and warn when the package ignores the language.
- `NEWS` defined in `protocol_tokens` as a legacy alias of `SHARE_LINK`.

### Changed
- Requirements aligned with the library versions shipped by YWeb.
- Shorter, purpose-oriented plugin description in `meta/info.json`.
- License: GPL-3.0-only, declared in `LICENSE`, `meta/info.json` and the README.
- README restructured on the common layout; citation updated to the published YSocial reference (Big Data & Society, 2026).

### Fixed
- Missing `prompt_store` import in the page agents (microblogging).

[Unreleased]: https://github.com/YSocialTwin/YClient/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/YSocialTwin/YClient/compare/v2.0.0...v2.1.0
