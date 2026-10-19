# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

Changes made since the last published state of `main`, newest first:

- Topic sampling: weight = count, only topics with count > 0 in the moving window
- Frequency-weighted choice of the post topic (count+1, moving window)
- Select exactly one topic per generated post
- Hashtags: canonical form without '#', apostrophes and accents kept in the tag, case-insensitive identity
- Fix missing prompt_store import in page agents (microblogging)
- protocol_tokens: define NEWS (legacy alias of SHARE_LINK read by the forum client)
- M2: log which yclient_memory is loaded (path, version, language)
- M2: memory errors name the Agent Memory plugin; warn when the package ignores the language
- M5: memory engine renders its texts in the simulation prompt language
- Prompts i18n step 5: localize the follow action and the reciprocal-follow verb
- Prompts i18n step 5: move the remaining English persona fragments into the packs
- Prompts i18n step 5: client reads the prompt language and shows profile values in it
- Prompts i18n step 4: Italian internal prompt pack
- Prompts i18n step 3: prompt_store language support
- Prompts i18n step 2: protocol_tokens reaction tokens
- Prompts i18n step 2: protocol tokens, tolerant parsers, no eval
- Prompts i18n step 1: move prompts out of the code (prompt_store, prompts_internal.json)
- i18n: shorter, purpose-oriented plugin descriptions
