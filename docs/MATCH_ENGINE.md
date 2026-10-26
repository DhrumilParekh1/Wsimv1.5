# Match + Creative Simulation — V0.3

## Principles

- Wrestler raw stats: **0–25**; most performance and result scores: **0–100**.
- A wrestler's Current Ability is a scouting metric. The match engine **never directly resolves a match using CA**.
- Scripted finishes are player-owned; the engine determines match quality, crowd reception, reactions, hype, morale, and trust changes.
- RNG uses a deterministic per-show seed and symmetric triangular distributions; repeated identical games lead to identical reports.

## Match scoring flow

1. Calculate category performance from wrestler stats according to `weights.MATCH_WEIGHTS`.
2. Compute five broad segment factors: `performers`, `story`, `chemistry`, `booking`, and `pacing`; combine them using `weights.SEGMENT_WEIGHTS['match']`.
3. Compute detailed per-match terms from `match_engine.py`:
   - **Style fit**: weighted mix of skills chosen for balanced, technical, high-flying, power, brawl, or storytelling. All style weights sum to 1.
   - **Psychology**: `0.29 × selling + 0.24 × sequences + 0.25 × experience + 0.22 × character_work`, each converted to 0–100.
   - **Stipulation fit**: a different stat blend for submission, no-DQ, Ironman; standard is a neutral baseline of 76.
   - **Stamina readiness**: effective workload depends on duration, intensity, and pre-existing wrestler fatigue.
   - **Finish credibility**: booked winner's momentum, opponent's momentum, and storyline hype.
4. Apply a **bounded** execution adjustment of approximately `[-12,+12]` points and triangular show RNG. No one new parameter can override all core ratings.
5. Calculate crowd reception from match quality, fan connection, storyline hype and crowd fatigue. Finish type modifies the reception and can affect trust, hype, and coherence separately.
6. Update persistent attributes, fan trust, storylines, and finances via `game.simulate_show`.

```
styleFit = average_over_wrestlers(4 * sum(styleWeight_i * rawStat_i))
psychology = .29*selling + .24*sequences + .25*experience + .22*characterWork
staminaReadiness = clamp(100 - max(0,workload-10)*1.12 + ...)
execution = clamp(.12*(styleFit-72) + .09*(psychology-75)
                  + .085*(staminaReadiness-75) + .06*(stipulationFit-75)
                  + .04*(finishCredibility-75), -12, 12)
```

The full formula lives in `match_engine.match_profile`, which is the authoritative source. Score coefficients are prototype values to be calibrated through repeated season simulations.

### Finish design

| Finish | Typical audience effect | Story effect |
|---|---|---|
| Clean | More credible conclusion | Trust/coherence tend to benefit |
| Flash pin | Surprising | May build another chapter |
| Interference | More immediate buzz | Trust/coherence risk |
| Disqualification | Frustrating to fans | Leaves the rivalry unresolved |
| Time-limit draw | Anticipation or disappointment | Needs adequate buildup |

The booked winner is not randomly overturned. Invalid combinations are rejected: no-DQ + DQ, submission-only + flash pin, time-limit draw + booked winner, etc.

## Branching scenes and consequences

A scene is keyed by `year`, `week`, and `storyline`. One active scene per storyline/week, at most two decisions. Every decision is saved to `GameState.scenes` and the activity/news logs. The first decision creates storyline changes using the wrestlers' relevant performance skills and a small deterministic random term. The second creates a concrete `Storyline.planned_beat`.

A promised segment attached to that exact storyline within the current or next show week grants continuity, hype, and coherence benefits. Unfulfilled promises trigger a trust/coherence penalty when advancing beyond the next week. These are intentionally modest prototype effects.

## Next simulation upgrades

1. Add tag/team matches and multi-person matches with collaboration/chemistry logic.
2. Refine face-vs-heel-specific crowd expectations and audience segments.
3. Make creative promises more contextual to past match history and relationship networks.
4. Add match-agent strategy, credible long-term injuries/availability, referee/outside involvement, and more result-specific narrative.
5. Calibrate distributions with thousands of simulated weeks instead of subjective coefficients alone.
6. Add rival-company booking AI with dynamic talent needs, negotiations, and broadcasting competition.


## V0.4 additions

The V0.4 workload system uses a separate fatigue accumulator (0–25) with a UI stamina bar calculated as `100 – 4*fatigue`. Match length, intensity, and stipulation affect fatigue costs. New stipulations include cage and extreme. Timed highlights are stored under `result.segments[*].match_engine.highlights` with minute, action text, the move, and the acting wrestler ID. Promo brawls apply a fatigue multiplier and may create extra hype when an established storyline supports them. The frontend replays highlights as a step-through after show simulation. Full rule details: `docs/GAMEPLAY_RULES_V04.md`.
