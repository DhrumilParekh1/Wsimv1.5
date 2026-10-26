# V0.10 design — Tag Teams and Multi-Person Rivalries

**Design status:** Planned, **not implemented** in V0.9. Do not represent it as playable yet.

## 1. Persistent teams and factions

Add `Team` with ID, display name, active roster IDs, division, manager, formation week, synergy, morale, trust, preferred tactics, shared finishers, contracts (if negotiated together), history and a breakup flag. A team exists independently of a storyline; tag members do not need to have identical alignments but mismatches should create tension. Add `Faction` with 3–6 affiliated wrestlers and relationship scores for each pair; avoid conflating faction membership with tag participation. Formation and dissolution should create memory entries.

## 2. Storyline cast size

Existing `Storyline.wrestler_ids` can already contain multiple wrestlers at the **data** layer; expand the frontend creation form to allow 2–4 participants and display active allegiances, betrayals, roles (protagonist, antagonist, ally, wildcard), and changing alliances. Each storyline remains limited to two **card slots**, not two on-screen wrestlers. A four-person promo in one segment occupies one slot, and one tag match later on the same card occupies the second.

## 3. Match participants, legal rules, and titles

Extend `Segment` with a match format enum (`singles`, `tag_2v2`, `triple_threat`, `fatal_four_way`) and `sides: list[list[wrestler_id]]` rather than assuming a two-person ordered list. Validate teams/divisions, one physical match per wrestler, team membership, finish and participant count at booking time. For tag matches track **legal wrestlers, tags and illegal interference**; multi-way singles use one winner but multiple challengers. Add men's/women's tag titles only when the team engine is stable; V0.9's three initial singles belts remain.

## 4. Probabilistic micro-simulation

Use an event-based simulator rather than rolling one overall match quality score. State contains current in-ring wrestlers, legal status, stamina remaining, team position, strategy, heat, crowd fatigue, near falls, and planned finish. Each beat:

1. Determine an actor and a possible action (strike, sequence, counter, tag, double-team, setup move, pin attempt, save or interference).
2. Determine a contextual probability from ability, style fit, fatigue, chemistry, opposing defence, venue momentum, and match phase; clamp away from 0% and 100% except explicitly guaranteed story beats.
3. Roll a seeded random draw for that action. Record `success_probability`, `roll`, `success`, `fatigue_cost`, `reaction_effect`, and any storyline changes.
4. Use accumulated action results for match quality and crowd reaction. Respect the **player-booked result**; the booked finish is the final canonical beat, and action rolls affect execution and fan response rather than secretly selecting a different winner.

For 2v2 also simulate tag timing, isolation and hot-tag payoff; for 3–4 person matches adjust pacing for downtime and prevention of repetitive saves/broken-up pinfalls. Injury checks occur at the event level with a bounded overall incident rate.

## 5. Booking controls and creative choices

Expose match format, team assignments and optional tandem finishers. For four-person stories offer choices like uneasy alliance, tag betrayal, face-turn distraction or title contender tournament. A turn **must** identify its subject explicitly and carry credible buildup. Each participant can react according to personality, loyalty, owner relationship and storyline history. Creative staff can propose multi-person resolutions, but no plan should auto-book without player confirmation.

## 6. Simulation balancing and tests

Balance singles first, then 2v2, then triple threat and four-way. Check that styles, teams and crowd chemistry meaningfully influence expected outcomes; large matches should be *harder to execute consistently* but offer greater payoff with suitable stars. Include property tests for participant count, team division, replay determinism, deterministic championship holder/lineage, fatigue accounting, tag legality, creative-commitment fulfillment, crowd-volatility distribution and older save migration. Do not run the new match types against the existing singles-only `generate_highlights` function.
