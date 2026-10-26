# V0.8 — Audience, Memory and Automatic AI Narrative Design

## Core authority model

The **engine** decides all game mechanics first. Ollama is always invoked at the supported narrative points but it cannot change engine values. The narrative service can write to `ai_flavour` text fields, `fan_report` and fan-post `text` only, after complete validation. Scores, sentiment, injuries, winners, terms, contracts, roles, moves, time and all changes to persistent world state come only from Python.

If Ollama cannot connect to local `127.0.0.1:11434`, cannot find `RINGSIDE_OLLAMA_MODEL`, or returns malformed output, the game records a visible `narrative_alerts` warning and displays underlying canonical highlights. **It does not claim that AI was generated** and it does not roll back the completed simulation.

### Automatic narration invocation points

- `POST /ui/meetings/start`, `/ui/meetings/choose`: selected personality-based wrestler reply, with relevant long-term memories supplied.
- `POST /ui/negotiations/choose`: selected personality-based wrestler contract counter/reply. Contract terms and acceptance probability remain fixed.
- `POST /shows/{id}/simulate`: one bounded JSON-schema batch that narrates selected original highlights across matches, promos, interviews and backstage scenes, adds per-segment fan reaction, an overall fan report, and fictional fan social posts of fixed sentiment. All generated text is additive to canonical facts.

Older separate prose API endpoints are retained for compatibility, but the browser has **no buttons or options** for opting in to AI generation.

## Viewership and the economy

`Company.viewership` is an integer count. New promotions start with a 2026 audience estimate initialized from historical legacy company popularity using `25,000 + legacy_popularity * 4,500`. It is a **fictional balancing assumption**, not an actual Nielsen metric. Existing v0.7 saves migrate automatically. The player promotion updates after a show:

`growth = clamp((average_crowd-59)/440 + (fan_trust-50)/3000, -0.095,+0.095)`

Rare unexpected star-making/flop moments modify this growth by `fame_delta * 0.014` per extraordinary segment. `viewership_new = max(1000, round(viewership_old * (1 + growth)))`.

Rival company viewership changes independently according to its weekly simulated show quality. Viewership affects streaming revenue; attendance remains limited by venue capacity.

Internal `Company.popularity` remains only for backward compatibility and older competitor balancing; **player-facing company success displays viewer counts instead**. Individual wrestlers still retain a popularity attribute (0–25), representing fame.

## Variance and pacing

`audience.duration_risk()` returns a bounded score adjustment and length-band explanation:

| Band | Matches | Other segments | Distribution |
|---|---|---|---|
| Short | below 7 min | below 3 min | Triangle(-16, +4), mode -5; fans more likely to feel short-changed |
| Medium | 7–22 min | 3–11 min | Triangle(-4, +4), mode 0; comparatively stable |
| Long | over 22 min | over 11 min | Triangle(-A, +A), mode 0; large rewards and large disappointments possible |

`A = min(24, 12 + (duration-threshold)*0.72)`. Certain demanding stipulations add a small additional symmetric uncertainty term, *alongside their existing fatigue/injury risks*. This is intentionally illustrative and can be rebalanced after player feedback.

Rare surprise outcomes use an initial **0.7% chance per segment**. The probability that the surprise is a breakout rather than a flop is `clamp((quality + crowd)/2 - 40)/45` (bounded to 6%–94%). A qualifying event applies an illustrative ±2.2–5.0 change to participant popularity, relevance and momentum on the 0–25 scale, and changes viewer growth; it is recorded in the memory system.

## Storyline fan expectations

Each storyline stores `expectations` with `type`, `label`, `support` and optional `wrestler_id`. Current templates include a credible clean resolution, slow development, and role turns; the schema supports betrayal expectations. New campaigns generate stable seeded expectations, while old saves create them when loaded.

`resolve_expectations()` tracks consecutive served and ignored expectations. Fulfilling an expectation can briefly raise investment; repeatedly fulfilling everything becomes predictable, producing a negative modifier after several consecutive compliance events. Ignoring all desires several times also lowers investment. Fans are **not guaranteed to be correct** and the game does not require the player to follow them.

Booking a role turn requires both the wrestler and new alignment on the same storyline segment. Success depends on the character's target-role proficiency, character work, the story's coherence, momentum, build duration, segment context, and controlled variance. Fans expecting the turn can react positively, but following the expectation never guarantees success.

## Narrative memories

`GameState.memories` is a bounded (700 item) ledger containing event type, year/week, wrestler IDs, storyline ID, intensity, description, and trust/relationship effects. `memories.relevant_memories()` ranks a wrestler's personal and shared history by importance, relationship to the current cast/story, recency and special historical event weighting.

Prior betrayals/poorly handled creative promises can reduce chemistry or meeting rapport. Long-term memories are included in personality-aware Ollama dialogue, where writers are prompted to reference only relevant established facts. The dashboard displays recent important episodes and storyline profiles display the past moments connected to participating wrestlers. This is **not a free-form chatbot memory database**; the stored facts are generated from confirmed simulation events, remain auditable and can be used without Ollama.

## Validation and caveats

- Gameplay RNG is seeded and stored game results are immutable after simulation.
- Ollama output is subject to schema, length, URL, safety, move-library and event checks; invalid responses are rejected as a group.
- A single model request per show limits latency, but a large, slow local model may take tens of seconds. The model never generates arbitrary new segments or writes outcomes to the database.
- Legacy saved shows have their original match outcomes and audience metrics preserved; V0.8 fan reactions are generated automatically for *newly simulated* shows, not retroactively asserted as existing.
- Fan-expectation percentages and viewership estimates are fictional design parameters for testing, not real-world audience analytics.
