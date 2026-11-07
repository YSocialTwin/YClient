# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- LLM endpoints with an API key: a hosted https endpoint with a model name containing a colon (e.g. `vendor/model:free`) and no key was taken for Ollama; Ollama endpoints that need a key (hosted ones) now get it as a bearer token. Pages created in web mode use the configured `llm_api_key` instead of an empty one.

### Added
- Sharing as a cross-platform action (opt-in, `agent_action`): when the agent shares a post it draws once per other platform with `federation.crosspost_propensity` and sends `crosspost_to` with the share (same adaptation prompts). With the coordinator rule nothing is drawn and shares stay local.
- Cross-post as an agent action (opt-in, `federation.crosspost_mode: agent_action`): after posting, the agent draws once per platform where it is also active (`GET /federation/destinations`) with `federation.crosspost_propensity`, and sends `crosspost_to` ([{member, text}]) with the post; the text is the model's version (prompts `crosspost_adapt_<platform>`, EN and IT) or, without a model or on a failed reply, the same words cut and shaped for the platform. Default mode unchanged.
- Federation attention (opt-in): the agent's number of actions in a slot is scaled by the multiplier of the day that the server publishes (`GET /federation/attention`), rounded at random with the module's own generator; with the federation off or multiplier 1 nothing changes.
- Federation (opt-in, `y_client/federation.py`): with the `federation` section of the client configuration enabled, agents that are not active on the platform (listed by `GET /federation/inactive_users`) are not sampled and do not act, and an agent may mark a post for cross-post (`federation.crosspost_propensity`, own seeded generator, extra `crosspost` field of `/post`). Without the section nothing changes.

## [2.1.1] - 2026-10-22

### Fixed
- SQLite URIs on Windows: `sqlite:///` plus the absolute path (the previous `sqlite:////` form produced "unable to open database file").
- `SyntaxWarning` for the unescaped regex in the feed reader (raw string).

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

[Unreleased]: https://github.com/YSocialTwin/YClient/compare/v2.1.1...HEAD
[2.1.1]: https://github.com/YSocialTwin/YClient/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/YSocialTwin/YClient/compare/v2.0.0...v2.1.0
