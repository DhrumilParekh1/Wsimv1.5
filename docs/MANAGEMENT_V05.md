# RINGSIDE V0.5 — Management & world simulation design

## Key systems

### Creative decisions and card commitments

1. Creative scene changes storyline metrics and records a planned beat (kind, deadline, origin scene, fulfilled flag).
2. `management.creative_tasks` exposes a user-friendly booking suggestion and its **canonical storyline_id, kind and wrestler_ids**.
3. The Show Booker preloads this suggestion but waits for the user to add it to the card. All underlying show validations still apply.
4. The segment engine validates delivery by matching the **segment kind, linked storyline and promised participants** (not just the segment type). Appropriate delivery raises narrative coherence/hype; missing deadlines reduce fan trust and storyline metrics.
5. Storyline card limit is two segments, even if more characters are involved.

### Private dialogues

`dialogue.py` has two persistent finite-state machines.

- **Meeting:** start -> select response -> concluding response -> complete. Persuasion uses morale, relationship with owner, personality, professionalism, choice fit and low deterministic noise. A promised push is saved as an assignment and has a deadline.
- **Contract:** start -> up to 3 financial offers/counter-offers -> signed/rejected/walked away. Acceptance depends on effective salary+bonus, wrestler demands, personality, owner relationship and small seeded variance. The player may offer a compromise. No repeated same-week negotiation with that wrestler.

The frontend makes both a separate full-page interaction with dialogue bubbles, avatars and offers. Neither interaction uses an LLM currently.

### Coaching

Available specialties:
- **Fitness:** stamina, agility, athleticism.
- **Technical:** technique, workrate, selling, sequences.
- **Promo:** mic skills, charisma, character work, presence.

Coaching assignments check owner rapport, pre-existing coach/wrestler relationship, management rapport, professionalism, fatigue and personality. A wrestler can refuse; one coaching proposal per wrestler per week. Progression produces small attribute changes over weeks, modified by growth aptitude and diminishing returns near 25. Coach capacity is four trainees. Staff members receive weekly salaries.

### Scouts and discovery

Regional < National < Global coverage. Reports include noisy estimates of CA and PA; higher scouting skill reduces estimation error. Certain indie free agents require a report before formal contract talks. Scout salary and signing fees affect the company. Scout reports persist and can be used to open contract negotiations.

### Rival promotions

At each weekly advance, each non-player promotion independently:
1. Selects men’s and women’s matches from its roster.
2. Generates a promo and calculates weighted segment quality.
3. Calculates crowd response, attendance, company money and commercial movement.
4. Updates momentum/fatigue, stores segment cards and results in rival history, and publishes world-news headlines.
5. Periodically competes for available wrestlers and monitors expiring player contracts.

The player’s show quality is still simulated by the more detailed segment and match engine. Rival show quality currently uses a simpler independent approximation. The system is deterministic for the same seed, year and week.

### Calendar and weekly metrics

The current event calendar creates 13 PPVs each year at weeks 4, 8, ... 52. Premium shows have additional revenue and production costs. The calendar shows history and schedules and offers narrative build advice. Player company popularity, trust, sponsorship, finances and roster size are snapshotted after the weekly show; historical metric snapshots are not recreated for older V0.4 saves.

## API additions

- `POST /ui/meetings/start`: wrestler_id, topic
- `POST /ui/meetings/choose`: session_id, choice_id
- `POST /ui/negotiations/start`: wrestler_id
- `POST /ui/negotiations/choose`: session_id, action, salary, weeks, bonus
- `POST /ui/management/hire`: kind (coach/scout), staff_id
- `POST /ui/management/coach`: wrestler_id, coach_id
- `POST /ui/management/scout`: scout_id
- `GET /ui/state` includes calendar, weekly_metrics, world_news, rival_history, staff, assignments and session data.

## Explicit balancing assumptions (temporary)

- Underlying skills are 0–25; company metrics are 0–100.
- Scout confidence is `skill/25 * 100`; estimation error increases as skill decreases.
- Scouting uses a one-report-per-scout-per-week cadence.
- Each wrestler receives at most one coaching proposal and one private management meeting each week.
- Contract negotiation attempts are limited to one room per wrestler per week and three offers within that room.
- The specialist staff market and rival roster are fictional gameplay data, not factual profiles.

## Ollama architecture placeholder (not implemented)

Future optional path: **simulation result -> structured fact/decision envelope -> locally running Ollama model -> prose generation -> rule validation -> interface**. The LLM must not change financial or competitive simulation outcomes. Save canonical result IDs and numerical state before generating prose; allow a deterministic template fallback when Ollama is offline or emits invalid content.
