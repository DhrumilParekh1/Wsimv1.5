# RINGSIDE V1.1 — Repair notes

## Ollama

- `POST /shows/{id}/simulate` calculates and saves numerical outcomes synchronously, then queues the auto-narration job.
- `GET /shows/{id}/narration-status` reports `queued`, `running`, `completed` or `failed`.
- A worker operates on a deep copy and merges *only narrative fields* after successful processing; unrelated later management actions are preserved.
- `efficient_narrative.py` uses independent bounded requests for reports, posts, and sets of three segment recaps. One model failure cannot invalidate other sections.
- For the local `llama3.2` model, adjust `RINGSIDE_OLLAMA_TIMEOUT` if generation is slow. It is never necessary to regenerate the entire simulation.
- A fallback to original deterministic highlights and fan sentiment is retained whenever Ollama fails. An unavailable Ollama response is labelled honestly.
- Current limitation: personality-aware dialogue from smaller meeting endpoints is still synchronous; large local prompts can pause those specific interactions.

## Show Booker

- Winner choices are recalculated whenever either match participant changes. The backend also validates every winner.
- Marketing is entered in **dollars per segment**; full card costs must fit available funds. The model uses a logarithmic, saturated visibility response, so tenfold spending does not guarantee tenfold audience gain.
- Older saves containing `promotion_effort` are still valid, using the old cost formula for those segments.

## Storylines

- `creative_logic.py` evaluates storyline age, number of prior segments, consecutive repetition and escalation level.
- A premature Resolve penalizes trust, hype, coherence and the performers' relevance.
- Repeated Escalate has an escalation ceiling and eventually backfires; Slow Burn and Advance stagnate when repeated; a Twist needs coherent foreshadowing.
- Creative outcomes are available in the saved segment report for debugging and balancing.

## Backstage incidents

- Selection is seeded and contextual. The director avoids repeating the same event family for a wrestler in the past three weeks and avoids assigning multiple incidents to the same talent in one week when the roster is big enough.
- Solo events no longer create fictitious self-chemistry.
- A resolved incident now records the player choice and the result, visible in Previously in RINGSIDE.

## Not yet verified

The 75 Python regression tests and JavaScript syntax check pass in the development environment. A live Ollama installation and live full-browser gameplay on the player's own Windows computer remain to be tested. Static browser verification is limited by restrictions on the local test server in the development container.
