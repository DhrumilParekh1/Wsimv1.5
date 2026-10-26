# RINGSIDE V1.0 — front office, talent, chemistry, press and incidents

## Changes implemented

### Creative-room routing
- The creative Inbox notification opens the Creative Room. The `/ui/choices` shortcut deliberately rejects creative Inbox actions.
- The two-part creative meeting sets a concrete segment promise. On completion, its Inbox notification is considered handled; the separate promised segment remains a required booking obligation.
- Regular creative promises are still transferred to Show Booker via prefilled segments.

### Wins and divisions
- Every **new** singles bout must have an explicit awarded winner. Clean, flash-pin, interference and disqualification are accepted finishes with an explicit winner; draws are excluded from new bookings.
- Legacy winnerless bouts are migrated to a named awarded finish when loading older saves. Historical results stay in saved report snapshots.
- Tag-team and multiplayer matches remain deferred. The 100–120 minute, one men’s and one women’s storyline, and two segments per storyline limits remain.

### Roster tiers and expectations
- `main_event` ~90% appearances over a recent window; `upper_mid_card` ~70%; `mid_card` ~50%; `lower_mid_card` ~35%; `jobber` ~20%. These are **expectations**, not hard weekly quotas.
- Status demotions reduce morale and relationship, proportionate to the distance fallen. A private talent issue enters the Inbox. You can promise, explain, or set firm expectations. The result depends on the wrestler's morale, relationship, professionalism and personality, with seeded RNG.
- Playing-time expectations are checked once a wrestler has enough observed weeks; recent losses for a main-eventer generate protection concerns. Very surprising losses against much-lower-card talent also risk an immediate complaint.
- Public and private promises are tracked. Fulfillment or failure changes the wrestler's trust.

### Market value in dollars
- An estimated monetary value is computed from annual guaranteed wages, wrestling-market demand, projected commercial drawing power, potential upside, and contract coverage, then adjusted for injury availability. It is **not** a guaranteed purchase price.
- Under contract talent can receive a *buyout proposal*: the selling promotion and the wrestler make independent seeded decisions. Both must agree. Accepted deals transfer cash to the selling promotion and salary/contract terms to the new company. Unavailable cash or a full roster blocks the proposal.
- Existing free-agent and renewal negotiations remain available and use the monetary value in the expected-wage estimate.

### Chemistry
- A persistent pairwise score out of 100 is created from reciprocal relationships, stylistic workrate fit, character compatibility, shared storyline familiarity and experience. No single component accounts for more than 27%.
- Scores develop after shared segments, informed by segment quality and relationship, with small per-event noise. Backstage incidents may affect a pair's relationship and chemistry.
- Simulation uses persistent chemistry for match/promo evaluation. This is designed to support future tag teams and three-/four-person feuds.

### Press conferences
- 18 question patterns × 12 framing contexts = **216 question formats**, then populated with actual wrestlers and rivals. The interface delivers three selected questions each week.
- There are four context-aware dialogue responses per question (864 distinct question/response combinations before real names and company context). Their effects differ by response and seeded noise; they can affect fan trust, the owner/wrestler relationship, sponsor interest, and promised future exposure.
- Questions and responses persist in saves, with a record of outcomes. Press participation is currently optional and doesn't prevent advancing the week.

### Random incidents
- 25 situation families × 10 narrative framings = **250 base event formats**, with dynamically assigned wrestlers and severity.
- Two unique incidents are seeded at the start of each week. They are Inbox obligations, and advancing the week requires resolving both.
- Each has four responses and a deterministic outcome roll modified by wrestler personality and owner relationship. Outcomes affect relevant state: morale, locker-room relations, cash, sponsor interest, relevant performance traits, momentum, trust, and chemistry.
- Event severity weights: minor 39/60, moderate 17/60, major 3/60, critical 1/60. A rare critical outcome has much bigger impact; it does not automatically end a wrestler's contract.
- All incidents and decisions survive save/load. Subsequent weekly events are generated from the game seed and date.

## Fairness and reproducibility
- Choices **do not** directly select outcomes: contextual odds are calculated and then a seeded random roll is made.
- Reloading an existing event does not reroll an already chosen outcome.
- Multiple individual wrestling actions continue to use micro-event RNG and the match engine remains authoritative.
- Ollama remains automatically enabled for the existing narrative situations; new press and incident mechanics use authoritative game data, not AI-authored numbers.

## Still out of scope
- Tag titles, tag matches, trios or four-way matches, and 3-/4-person feud simulation (chemistry foundation added here).
- A full multi-round buyout/transfer negotiation room with counteroffers (a first-round buyout proposal is available).
- Hundreds of hand-authored unique conversations: the press and incident libraries are **combinatorial templates**, supporting hundreds of contextual instances; authoring/editing a broad corpus is a future phase.
