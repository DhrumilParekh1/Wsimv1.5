# RINGSIDE V1.3 — Management, Narrative & UI Repairs

**Release scope:** Implements the consolidated management-and-economy worklog while deliberately retaining **singles matches only** and **existing stipulations**. Tag-team matches, multi-person feuds/matches, additional match stipulations and tag-team titles remain deferred.

## Run on Windows

Open PowerShell in the extracted `RINGSIDE_Wrestling_Simulator_v1_2` folder and run:

```powershell
.\start_game.bat
```

Browse to **http://127.0.0.1:8000/**. For automatic narrative generation, install Ollama and pull the configured `llama3.2` model. The mathematical simulator remains functional if local narration is unavailable.

**Save migration:** Stop your previous game, back up your entire `saves` folder, and copy its `game.json` into V1.3's `saves` folder (if present). RINGSIDE V1.3 automatically imports that JSON game into `saves/game.db` on the first launch. The legacy JSON is preserved. New campaigns still begin with a 120-minute weekly show and three annual PPVs (weeks 17, 35, 52).

## New in V1.3

- **SQLite local save database** with automatic import from JSON, atomic snapshots and searchable indexes (no database installation required).
- **Responsive wrestler profiles and rival talent cards** that keep traits and recruitment actions visible.
- **Rebalanced match styles** with explicit weighted skill maps, and five core moves (including one finisher) plus optional signatures.
- **Delayed recruitment enquiries**: pending this week, report to Inbox next week. Public declarations affect news and social discussion immediately.
- **Explainable match verdicts**: expectations versus satisfaction, strengths, concerns and contextual consequences.
- **Automatic Ollama promo dialogue** with character personality, traits and history; anti-contradiction checks for social reactions.

See `docs/V13_COMPLETION_NOTES.md` for detailed rules, migration information and known limitations.

## V1.2 systems

- **Promotion prestige:** an index out of 100 based on comparative viewership, fan trust, active storyline hype, sponsor interest, current top performers and slowly changing historical reputation.
- **Transfers and recruitment:** private enquiry/public declarations, future contracts in the final 12 weeks, promised card status and career opportunities, player-controlled responses to rivals' bids, and explicit wrestler acceptance. Active exclusive deals cannot be bypassed by pre-contracts.
- **Contract promises and morale:** time-bound pledges to give status, appearances, title opportunities, marketing, creative involvement or coaching. Met promises improve cooperation; missed deadlines reduce morale and trust; very unhappy wrestlers may request release and occasionally resist bookings.
- **Scouting:** distinct current/potential-judgement metrics, observation-dependent accuracy, uncertain estimated valuation and contract timing.
- **Coaching:** development rate now reflects coaching quality, personality compatibility, relationship, workload, wrestler potential and fatigue.
- **Roster traits:** persistent fictional heights, weights, and multi-trait profiles (giants, underdogs, luchadores, second generation, etc.) that feed scene context, fan anticipation and model prompts.
- **Audience response:** feud position/stakes, expectations, quality, repetition fatigue, title significance, finish satisfaction and performance accountability influence crowd satisfaction and fan trust.
- **Broadcasting and PPVs:** three annual PPVs initially; expensive reputation- and audience-gated purchases can increase the yearly PPV count or expand the weekly broadcast from 120 to 150–180 minutes.
- **Advertising:** weekly and PPV cash campaigns alongside segment-level cash marketing with diminishing returns and affordability checks.
- **Legacy repairs retained:** participant-filtered winner selection, contextual creative-direction choices, asynchronous show narration, in-game loading status, incident personality filtering and resolved backstage memories.
- **Presentation:** company prestige and weekly viewership, wrestler trait profiles and promises, scout uncertainty, interactive recruitment, campaign and calendar controls, favicon and enriched segment reactions.

See `docs/V12_IMPLEMENTATION_AND_LIMITATIONS.md` for how these modules interact, what is not implemented, and known testing limits.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

**93 automated tests passed** on the packaged source as of this build. `node --check` validates frontend syntax. Full live desktop/mobile browser testing and local Ollama throughput remain to be verified on the target computer.

---

# RINGSIDE v1.1 — Repairs & Narration Reliability

**What changed:** Winner dropdown restricted to booked performers; creative-direction maturity, repetition and escalation caps; real dollar advertising budgets with affordability checks and diminishing returns; backstage incident generation filtered by history/personality; resolved incident recaps; show simulation saved before asynchronous Ollama narration with actual job status and a loading screen.

**Start Windows:** Open PowerShell in this folder and run `./start_game.bat`. Visit http://127.0.0.1:8000/. Install Ollama and pull `llama3.2` first for automatic narrative.

**Model settings:** `RINGSIDE_OLLAMA_MODEL=llama3.2`, `RINGSIDE_OLLAMA_URL=http://127.0.0.1:11434`, `RINGSIDE_OLLAMA_TIMEOUT=50` (seconds per bounded request). Narration happens on a worker thread. Game scores remain valid regardless of model availability.

**Save migrations:** Back up your V1.0 `saves/game.json`, then copy it to the V1.1 `saves/` folder. Old `promotion_effort` fields are recognized. Existing show results and budgets are not retroactively recalculated.

**Tests:** `python -m pip install -e ".[dev]"` then `python -m pytest -q`.

See `docs/V11_REPAIR_NOTES.md` for implementation and limitations.

---

# RINGSIDE V1.0 — Wrestling Promotion Simulator

Playable local, text-driven fictional wrestling management game with a Python simulation engine and browser interface.

## Run on Windows

1. Install Python 3.11+ and extract the ZIP into its own folder.
2. Open the folder containing `pyproject.toml` and `start_game.bat`.
3. Run `.\start_game.bat` in PowerShell (or double-click the file in File Explorer).
4. Visit http://127.0.0.1:8000/ and leave the server terminal open.

To use the automatic narrative layer, run local Ollama with the configured model (default `llama3.2`):

```powershell
ollama pull llama3.2
ollama serve
```

The game's simulation logic and local text-mode fallback still work if Ollama is unavailable; a narration warning will be shown. No manually triggered Ollama button is needed.

## New in V1.0

- Creative Inbox notifications now route to the **Creative Room**, with the resolved scene creating a bookable promise.
- Singles matches **require an explicit winner**, including DQ finishes. Time-limit draws have been removed from new bookings.
- Roster tiers now imply realistic appearance/protection expectations. Demotions and neglected main eventers can request meetings in the Inbox.
- **Market values are now currency figures**, calculated from wages and commercial earning power. Contracted competitors can receive a monetary buyout proposal, requiring two separate acceptances.
- **Pairwise chemistry** is persistent, relationship/experience/stylistic-fit based, and grows or declines with shared appearances.
- **Press Conferences** have 216 contextual question formats, four role-sensitive response choices, weekly question sets and lasting outcomes.
- **Random Backstage Incidents** have 250 base scenario formats. At least two incidents are generated each game week; both must be handled in the Inbox to advance. Rare major and critical events are possible.
- Existing divisions, championships, creative staff, coaches, scouting, sponsorships, audience expectations, automatic Ollama narration, movesets, injury simulation, and micro-event RNG remain intact.

## Upgrading from V0.9

Stop your previous server. Back up the previous `saves/game.json` and copy it into the V1.0 `saves/` folder **before** launching. Existing histories, ratings and contracts will be restored. Legacy winnerless bookings are normalized to a named finish when loaded, without overwriting previously simulated result reports.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

See [`docs/FRONT_OFFICE_V10.md`](docs/FRONT_OFFICE_V10.md) for formulas, RNG rules, templates, and documented current limitations. See `docs/TAG_TEAMS_AND_MULTIPERSON_V09.md` for the planned multiplayer expansion.


## V1.4 backstage incident choices (preview build)
Backstage incidents now have category-specific options and probabilistic outcomes based on
personality, morale and relationships. Approved mentorships persist across weeks and
contribute modest technique/sequence development. Recorded resolutions appear in the
weekly recap. The live highlight view preserves its outer scroll position when moving
through highlights. Creative direction from prepared tasks is reflected in the booking form.
