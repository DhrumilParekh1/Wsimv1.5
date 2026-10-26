# V0.9 — Event-level randomness, titles, promotion and fan narration

## In-ring and promo probabilities

For each modelled in-ring action, the simulation engine uses the acting wrestler's move/sequence/technique/stamina blend, fatigue, match length, chosen styles and the chosen move's type to construct a bounded success probability. A fresh draw from the show's **seeded PRNG** decides whether the move connects or is countered. For each promo, confrontation and backstage scene, a separate draw comes from mic skills, charisma, character work, presence and fatigue. Each attempt records `rng_roll`, `success_chance` and `successful` in the JSON report, but the UI shows only the commentary, not raw technical details.

The action quality adjustment is approximately:

`mean( (int(success) - action_probability) * 14 )` for matches;

`mean( (int(success) - action_probability) * 13 )` for verbal scenes.

This is centered on zero **conditional on the action probabilities**, so capable performers are already rewarded by baseline skills rather than receiving a double bonus for easy moves. It mainly introduces chance-driven execution variance; quality also includes selected-style fit, chemistry, story continuity, match duration/psychology, small residual RNG and rare exceptional outcomes. The finish **remains the player's booked finish**, not an RNG-selected winner.

Example: if an attempt's probability is 0.72 and the RNG draws 0.31, the move succeeds; if it draws 0.89, it is countered. Individual rolls change highlights and the accumulated score. Replaying the same save + show seed generates the same outcomes. Different booking changes can change the random-call sequence: do not compare only two RNG results and assume causation.

Existing management decisions, media requests, contract negotiations, staff advice, turns and injuries already employ independently seeded RNG. V0.9 does not yet simulate *every real-world micro-action*; the simulated micro-events represent narrative beats rather than frame-by-frame wrestling physics.

## Advertising versus ability

Each segment uses 0–25 `promotion_effort` as **money spent and advance attention**, not technical booking quality. The approximate cash cost for a segment is `round(45 * promotion_effort^1.25)` dollars, charged to the show. Audience response receives a bounded visibility shift (approximately -5.5 to +5.5 on 0–100 crowd reaction); viewer growth has a modest campaign awareness component. Overspending beyond current funds is forbidden. `booking_quality` remains readable in legacy saves but is no longer exposed to the player.

## Championship prestige

Each company stores a separate championship registry. Each initial belt has a division, prestige score, current holder, successful defence count and lineage. A title match must include its current holder, be in the correct division, and have a valid booked finish. The champion earns a small relevance/popularity/momentum adjustment, and the title gains or loses prestige based on crowd reception. Title bouts add a bounded event revenue uplift; they cannot alone make a financially disastrous show profitable.

## Ollama failures and independent retries

V0.8 required one enormous structured JSON result for every highlight, social post, segment reaction and the overall fan report. A single schema violation discarded all four outputs. V0.9 retains that full attempt but can independently ask for social posts and a smaller fan report when the batch fails. No invalid output is labelled as generated; factual results remain locked, and the game records separate warnings about the failing task. Each segment additionally has a factual engine-produced sentiment summary when Ollama is offline or incomplete. As before, a real local model is required to generate AI prose; integration has been tested with mock responses, not with the user's installed model.
