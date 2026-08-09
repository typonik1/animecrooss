# Fresh Balanced Deduplication Design

## Goal

Publish only fresh, active, previously unseen edits while distributing scheduled posts across configured sources and always adding the formatted VPN link.

## Selection

Only messages from the last seven days are eligible. Each source is filtered by age, media constraints, advertisement rules, activity threshold, and deduplication. Eligible items are sorted by activity within their source, then selected round-robin across sources. If there are not enough fresh unique items, slots remain empty; the bot never falls back to archive posts.

## Restart-safe deduplication

At process startup, the reader scans recent video posts in the target channel and imports their media fingerprints into SQLite. This reconstructs deduplication after Render replaces its ephemeral filesystem. A fingerprint uses exact byte size, because Telegram changes the document id and may lose duration, width, and height when a bot reuploads the same file. The publisher explicitly preserves the source video attributes on new uploads. If the target history cannot be read, the bot logs the error and keeps the in-process SQLite safeguard.

## Caption

Every caption ends with the existing hashtags and an HTML link whose visible label is `Лучший VPN` and target is `https://t.me/NosokVPNBot?start=partner_8235497168`.

## Verification

Tests cover round-robin selection, activity ordering, no archive fallback, target-history import, and exact VPN-link rendering.
