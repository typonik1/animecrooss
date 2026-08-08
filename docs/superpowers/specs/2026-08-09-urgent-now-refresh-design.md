# Urgent Now and Queue Refresh Design

## Goal

Make `/now` publish an urgent fresh edit without consuming a scheduled slot, and let owners refresh only the waiting scheduled posts through a Telegram button.

## Urgent publication

`/now` obtains one candidate using the existing fresh-only, balanced, duplicate-safe selector. It does not read from, insert into, or update the `queue` table. On successful delivery, its source message and media fingerprint are written to `posted`, so scheduled selection cannot reuse it. If no candidate is eligible, the bot replies that no fresh unique video was found.

## Queue refresh

`/queue` includes an inline `🔄 Обновить очередь` button. The callback is restricted to owners. It deletes only `pending` entries for the current day, never `posted`, `skipped`, or `failed` history, then runs the normal fresh-only schedule builder. Published time slots remain occupied, while future pending slots receive newly selected videos.

## Delivery code

The existing publisher gets a queue-independent publishing path. Scheduled publishing retains status transitions in `queue`; urgent publishing shares download, caption, moderation, target send, cleanup, and `posted` deduplication, but has no queue status to mutate.

## Verification

Tests prove urgent selection bypasses the queue, no-candidate behavior returns no item, refresh removes only pending entries, and the `/queue` response carries the refresh button. Existing full tests cover caption formatting and fresh balanced selection.
