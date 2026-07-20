-- Removes only sessions with ZERO associated events and ZERO training value:
--   1. label IS NULL, event_count = 0        (78 rows — pure dead orphans)
--   2. label = 'bot', event_count = 0        (2 rows  — dead labeled rows)
--   3. label = 'human', event_count = 0      (1 row   — today's own automated test session)
--   4. label IN ('allow', 'block')           (80 rows — live /api/predict logging, never used for training)
-- Total: 161 rows. Verified 2026-07-20: zero of these have any associated
-- `events` or `session_features` rows, so nothing else needs to cascade.
-- Does NOT touch any bot/human training session (394 rows, 73,226 events) —
-- those are untouched by this WHERE clause entirely.
-- Does NOT touch the 124 label-IS-NULL-with-real-events sessions (ambiguous,
-- possibly still recoverable for future manual labeling — left alone per
-- explicit decision not to bulk-delete those).

DELETE FROM sessions
WHERE (label IS NULL AND event_count = 0)
   OR (label = 'bot' AND event_count = 0)
   OR (label = 'human' AND event_count = 0)
   OR label IN ('allow', 'block');

-- Expect: DELETE 161
