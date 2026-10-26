# RINGSIDE 0.7 — Personality, scripted movesets, injuries, and AI highlights

This version builds on V0.6. **Gameplay numbers and events remain authoritative in Python.** Ollama is an optional text-only layer. When Ollama is disabled or down, normal deterministic highlights and dialogue continue to work.

## The two-layer architecture

1. Python selects who participates, what moves a performer has learned, which moves are attempted, which planned finish takes place, audience response, injury outcomes, contract answers, and morale/relationship changes.
2. The event facts are saved to JSON before AI enhancement.
3. Ollama gets a read-only snapshot of relevant context (wrestler persona, audience reaction, moveset, fixed event text, and conversation history).
4. Ollama can supply short flavour text **alongside** the event, saved under `ai_flavour`; it does not overwrite `text`, move names, match winners, injuries, financial figures, signed terms, or decision effects.
5. Responses are validated as a batch before saving anything. A bad response leaves the saved event unchanged. Real local Ollama behaviour may vary; the tests use mocked model responses.

## Wrestler move libraries

Every wrestler has a persistent `moveset` array on their entity. Move entries have `{name, style, finisher}`. Starter talent has individually assigned move families, with a recognizable finishing move. Newly created or older-save wrestlers receive a starter move library from attributes. Styles: technical, high_flying, power, brawl, storytelling. The balanced match style samples each actor's existing assigned moves.

In match simulations, selection is per performer: the simulator prefers moves matching the booked styles, falling back to **that same performer's** moveset if necessary. Clean finishes can use the winner's assigned finisher. The API allows roster moveset editing through `PUT /wrestlers/{id}/moveset` with 3–20 distinct valid entries. Movesets are displayed in the wrestler profile. An interactive move editor UI is not yet included.

Promos, interviews, returns, contract-signing angles, confrontations and backstage scenes generate timed, non-graphic event descriptions without wrestling moves. A promo brawl affects the conclusion and can carry a small injury risk.

## Injury proneness and recovery

`injury_proneness` is a **0–25** raw attribute, where 0 means less injury-prone and 25 means more injury-prone. It affects per-appearance injury probabilities but is intentionally excluded from the generic Current Ability weighted average. Injuries restrict bookability and market availability independently of performance ability.

The fictional gameplay injury roll per **wrestler, per match** is:

```
base = 0.001 + (injury_proneness / 25) * 0.012
risk = min(0.10, base * duration_factor * stipulation_factor * intensity_factor * fatigue_factor)
duration_factor = clamp(duration / 16, 0.70, 1.85)
fatigue_factor = 1 + fatigue / 28
```

Stipulation multipliers: standard 1.00; submission 1.03; ironman 1.30; no DQ 1.40; cage 1.80; extreme 2.20. Intensity multipliers: measured 0.70; standard 1.00; high 1.40. A promo brawl uses 22% of the raw base risk, capped at 1%. These are **gameplay balancing inputs, not real-world medical statistics**.

Injury **duration given an injury occurs** is sampled from a weighted distribution:

| Category | Conditional frequency | Weeks missed |
|---|---:|---:|
| Short | 78% | 1–3 |
| Medium | 19% | 4–12 |
| Long | 3% | 13–52 |

Active injury: `Wrestler.injury`; previous records: `Wrestler.injury_history`. Every weekly progression decrements `weeks_remaining`; at zero, the performer is automatically cleared and a news item is generated. Booking validation rejects injured wrestlers and the roster/profile UI displays their absence. Promised segments still require players to manage creative commitments appropriately.

## Ollama actions

- Private room: **Generate personality-aware reply** in wrestler meetings and contract negotiations. The optional model can refer to the selected personality, current role, relationships, morale, conversation, outcome and real contract status. It cannot change whether an offer was accepted.
- Live show replay: **Ollama: enhance [segment] highlights** for matches *and* non-match segments. The original timed beats are always visible.
- Existing V0.6 social posts and show recaps remain supported.
- API: `POST /ui/ollama/dialogue` `{ "kind": "meeting" | "contract", "session_id": "..." }`.
- API: `POST /ui/ollama/highlights` `{ "show_id": "...", "segment_index": 0 }`.

## Windows setup

Start the regular game by running `start_game.bat`, or use `start_with_ollama.bat` after installing Ollama and `ollama pull llama3.2`. By default, the local address is `http://127.0.0.1:11434`. The installed model can be chosen with `RINGSIDE_OLLAMA_MODEL`. Requests have a short timeout; AI text is optional and can be retried, while the base game remains playable.

**Backups:** Stop the old server, copy V0.6 `saves/game.json` into V0.7's `saves` folder, and restart. The loader adds default movesets and injury attributes to older saves while keeping the original ratings/records intact.

## Limitations / upcoming work

- Moveset editing is supported by the backend but doesn't yet have a move-selection builder in the frontend.
- Ollama enhancement is on-demand for the currently viewed segment or most recent dialogue response to avoid pausing every show on multiple local model requests.
- Injuries currently have broad time-based categories and are not a medical model. A future rehab/coaching layer may introduce medical staff and return-to-ring risk.
- Browser screenshots from the isolated test environment may not contain portraits because local `/assets` URL loading is restricted outside the actual game server. Images work from the normal web app server.
