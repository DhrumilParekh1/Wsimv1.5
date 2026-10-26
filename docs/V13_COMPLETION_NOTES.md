# RINGSIDE V1.3 — Issue #16–#21 completion notes

V1.3 keeps the singles-match simulation and existing stipulations unchanged. It improves the UI, recruitment feedback, interpretation of results, moveset structure and the narrative layer. It also introduces **SQLite persistence** for local campaigns.

## Wrestler presentation (#16)
- Traits now appear in a dedicated wrapping panel rather than overlapping the height/weight, title and roster role information.
- Mobile layouts wrap the profile information and cards.

## Match-style and moveset design (#17)
The match engine has explicit editable style weight maps in `src/wrestling_sim/match_engine.py`.

| Style | Primary strengths |
| --- | --- |
| Balanced | Workrate, sequences, technique, selling, moves |
| Technical | Technique 26%, workrate 20%, sequences 18%, selling 14%, moves 10%, stamina 7%, determination 5% |
| High flying | Agility 24%, athleticism 22%, moves 20%, sequences 15%, flair 9%, selling 5%, stamina 5% |
| Power | Athleticism 25%, moves 22%, presence 16%, stamina 15%, selling 12%, determination 10% |
| Brawl | Determination 22%, selling 18%, presence 17%, stamina 15%, moves 14%, character work 9%, workrate 5% |
| Storytelling | Character work 16%, sequences 16%, moves 13%, flair 10%, athleticism 7%, agility 6%, selling 16%, technique 10%, determination 6% |

Two-style matches blend 65/35 and three-style matches blend 55/30/15. The weighted attribute fit affects both match profile scoring and simulated move execution probability. **Move count itself does not increase scores**. Starter movesets now consist of four foundations, one finisher, and two optional flair/signature moves. Custom sets are validated at 3–8 moves, with exactly one finisher and at most three additional signature moves (the 3-move lower bound preserves older custom save compatibility). Existing saved preset lists longer than eight are migrated to concise default movesets.

## Talent Market (#18–#19)
- Rival talent cards place the wrestler information, price and both action buttons in independent responsive blocks.
- **Private enquiries** create pending entries. A report is delivered on the **following in-game week**, after weekly progression.
- Reports include interest, approximate salary expectation, current contract length and scouting confidence where available. An outstanding report appears in the inbox and must be acknowledged before the next week.
- **Public interest** generates grounded fan-social discussion and news immediately, but does **not** sign or transfer any wrestler. Its enquiry report still arrives next week.
- The normal pre-contract and contracted-transfer restrictions remain in place.

## Report verdict and Ollama (#20–#21)
- Every segment carries an **engine-authored analysis**, including the difference between fan expectation and satisfaction and primary positive and negative factors.
- Fan social uses the engine verdict rather than just crowd score. Ollama receives that verdict and fixed canonical event context before generating reactions.
- Obvious contradictions such as calling a poor match an *instant classic* are rejected; the existing engine-based text is retained.
- Automatic Ollama generation is extended to produce **in-character promo and backstage dialogue** using traits, alignment, mic skills, personality, relevant prior memories and actual simulated beats. It cannot award titles, invent injuries or overwrite results.
- Narrative requests still depend on a working local Ollama installation. A failed AI request does not affect the simulated show.

## SQLite saves
- The default app save is `saves/game.db`, built with Python's built-in `sqlite3` (no extra database service to install).
- SQLite stores an atomic complete GameState snapshot and searchable indexes for wrestlers, storylines, shows, memories and recruitment enquiries.
- If `saves/game.db` does not exist but `saves/game.json` does, the game **imports** the JSON save on first launch and retains the original JSON file untouched.
- The simulation still uses the GameState dataclasses as the single in-memory rules authority. JSON save/load is retained for tests and the CLI where explicitly requested.
- Back up the entire `saves` folder before upgrading or changing a campaign.

## Testing / limits
- Original regressions plus new tests for SQLite round-trips, JSON import, weights, compact movesets, delayed enquiries and narrative contradiction filtering.
- Live local Ollama response speed and complete end-to-end browser operation must be tested on the player's Windows machine; container-level browser access to the local API can be blocked by policy.
- The database is designed for a **single-player local process**, not a shared multi-user online server.
