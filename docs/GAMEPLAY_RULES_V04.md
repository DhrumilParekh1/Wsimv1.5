# RINGSIDE V0.4 — Simulation Rules and Design Notes

## Weekly booking gates

- Fixed weekly show duration: 120 minutes; confirmed segment runtime must be between 100 and 120 minutes inclusive.
- Every show must have at least one **active storyline segment** in each of the men's and women's divisions.
- A storyline may appear in no more than two segments on that week's card.
- Mixed-division storyline creation and segment booking are rejected.
- One singles match per wrestler per show, at most 12 segments, valid wrestlers signed to your company, and no new weekly show until the existing one has been simulated.
- Week advancement requires that the current week's show is simulated.
- Storyline promises are checked when their required segment is simulated; missing them when due damages coherence and trust.

## Energy and match workload

Each wrestler carries 0–25 fatigue. UI energy = `max(0, 100 – 4 × fatigue)`; attributes use 0–25, while overall and storyline ratings use 0–100.

After a match: `fatigue += duration × 0.28 × stipulation_multiplier × intensity_multiplier`.

Stipulations: standard `1.00`; no disqualification `1.30`; submission `1.12`; Ironman `1.40`; cage `1.55`; extreme `1.75`.

Intensities: measured `0.78`; standard `1.00`; high `1.35`.

A non-match promo/segment costs `duration × 0.055` fatigue, rising to `duration × 0.18` for a brawl. Media assignments (if accepted) cost `2.0` fatigue = 8 energy points. Fatigue remains clamped to 0–25.

Weekly recovery: `4 + stamina_attribute/7 + professionalism_attribute/25` fatigue points, clamped. This is an initial balancing formula and may change.

## Creative staff and recommendations

Current default head: Morgan Reed, 13/25 skill. Candidate recommendations estimate storyline fit using hype, investment, and coherence, with noise inversely related to the writer's skill. Better staff reduces advice noise, but the player always decides, and RNG/statistics still govern reception. Hiring charges a signing fee/buyout and recurring weekly salary.

## Relationships, promotions, and promise tracking

Wrestlers have a current owner-relationship meter (0–25), personality archetype, morale, professionalism, and loyalty. Media acceptance is a seeded chance calculated from these traits and current fatigue. A wrestler can refuse an appearance without consuming energy; a declined request closes the weekly opportunity. Interactions alter morale and relationship with the owner, and a promised push becomes an obligation until delivered or overdue. Regular segments alter performer-to-performer relationships depending on reception and whether the story involves betrayal. Every third week may generate a locker-room dispute decision.

## Time-stamped match text

The match engine evaluates style, psychology, stipulated finish, stamina readiness, and limited seeded randomness. It builds chronological scripted highlights (move attempt, counter, sequence, and booked finish). Longer matches produce more highlights up to a cap. The browser 'live recap' is a **step-through of the precomputed result**, ensuring that saves remain deterministic and decisions cannot alter the match midway through playback. No granular violent or injury descriptions are generated.
