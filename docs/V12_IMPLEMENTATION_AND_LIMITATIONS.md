# V1.2 implementation — master worklog

## Scope and exclusions
This release implements the non-team, non-multiperson, non-stipulation workstreams from the consolidated development worklog. It does **not** add tag teams, tag championships, 2v2 matches, triple threats, four-person feuds, new referee/stipulation options, or a new match format. Existing singles match styles and current finish types remain supported.

## 1. Prestige and talent market
`industry.py` calculates a prestige score (0–100) from relative viewership (25%), fan trust (20%), storyline hype (20%), sponsor interest (15%), star power (10%), historical reputation (10%). Historical reputation changes slowly to avoid implausible one-week collapses.

`wrestler_willingness()` evaluates wages, offered roster role, company reputation, wrestler happiness, relationships, development and personality. Prestige is a factor, **not an absolute signing threshold**. Players can enquire privately or declare interest publicly in scouted/known rival talent. Pre-contract offers are allowed only when the rival wrestler has **12 or fewer weeks** on their current deal, and transfer occurs only after the contract expires. Rival promotions periodically submit transfer bids. Player acceptance, affordable fees and the wrestler's agreement must all align before a contracted wrestler can move. Monetary value remains an estimate, not a binding fee.

## 2. Contract promises and morale
`industry.py` stores promised roster status, number of appearances, championship opportunity, paid promotional exposure, coaching, or creative participation with deadlines. The player may negotiate status above a wrestler's current tier. Broken promises lower morale and management relationships; extreme dissatisfaction may lead to transfer requests or occasional refusal to perform. In-game status and personality affect the likelihood. Promises are not guaranteed to be received well and contract conversations are not auto-accepted.

## 3. Development and scouting
`traits.py` gives each fictional wrestler height, weight, and multiple structured traits; model narration receives a compact selection rather than making up family or combat history. Scout reports in `world.py` are observations with distinct current/potential accuracy and uncertainty; talent becomes discoverable according to scout coverage. Coaches use a composite effectiveness score from skill, fit, relationship, availability/workload and specialization, and the resulting growth still decreases near attribute ceilings and at high fatigue. Reports are probabilistic estimates, not exact future outcomes.

## 4. Calendar, finances and audience
New campaigns begin with a single 120-minute weekly programme and PPVs at weeks **17, 35 and 52**. `industry.expand_company()` offers investment-gated additional annual PPVs (maximum eight), and 30-minute broadcast increments (maximum 180). The owner needs sufficient cash reserves, relative prestige and viewership. A PPV is not guaranteed profitable. Past shows stay in the calendar.

`marketing.py` supports explicit cash campaigns (weekly/PPV) plus targeted segment spends, each with diminishing marginal reach. Costs are charged once in their respective accounting phase.

`fan_interest.py` models segment anticipation, fan satisfaction, main-event-vs-lower-card stakes, expectation gaps and repeat-encounter fatigue. `match_engine.py` differentiates clean/flash/interference/DQ finish satisfaction and uses per-action probability rolls, with heightened scrutiny for heavily anticipated championship or main-event finishes. Repeated pairings can become stale but rest time reduces immediate fatigue. Gameplay results remain rule-driven; Ollama does not change numerical outcomes.

## 5. UI, incidents and AI
The Show Booker winner dropdown is restricted to selected participants. Creative direction retains memory of repetition and payoff readiness. Dashboard includes prestige, actual viewership, traits, unresolved obligations, and resolved incident history. Recruitment, contract expectations, staff selection, scouting uncertainty, paid campaigns and expansion are available in the browser UI. A local favicon is provided.

Numerical show outcomes are saved before optional local Ollama requests run. The UI displays narration status independently of the factual results. A failed model call must not change winners, finish results, contracts, injuries, cash, morale or any simulated fact. Personality encounters and memories have event eligibility/cooldown safeguards and explicit resolutions.

## Verification and limits
- **93 passing Python automated tests**, including 18 new or adapted V1.2 tests and removal of obsolete assumptions about monthly PPVs.
- API smoke and save/load roundtrip tested using FastAPI TestClient.
- Python compilation and frontend JavaScript syntax checked.
- A full browser-through-server interaction check could not be completed in the present environment; verify desktop/mobile layout, all interactive form handlers and Ollama generation locally.
- The narrative voice quality, game-balance parameters, subjective traits and multi-season economic equilibria require actual gameplay balancing. New systems are a playable first implementation, not calibrated real-world predictions.
- All first-run physical profiles are fictional. Existing saves preserve their prior match results and ratings.
