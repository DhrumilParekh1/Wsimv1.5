# RINGSIDE V1.8 — Real-name wrestling universe

This build offers a NEW campaign with public, source-attributed wrestler ring names from the official roster listings of WWE, AEW, TNA and ROH. It intentionally does not modify existing saves, nor assert that any featured performer is under an exclusive contract.

### Data sources (official roster listings; checked October 28, 2026)
- WWE: https://www.wwe.com/superstars
- All Elite Wrestling: https://www.allelitewrestling.com/aew-roster
- TNA Wrestling: https://tnawrestling.com/roster
- Ring of Honor: https://www.ringofhonor.com/roster
- Wikidata CC0: https://www.wikidata.org/ (for additional birth dates, physical facts and independent profiles when available)

This is a SELECTED snapshot of 80 people (12 men and 8 women listed by each promotion), not a live exhaustive licensed roster feed. Affiliations on official listings do not necessarily represent exclusive contracts. ROH and AEW may share talent; the sim assigns distinct wrestlers to companies to preserve balanced gameplay, and these assignments must not be presented as actual employment status.

### Windows setup (from project root after merging PR)
    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q

Your existing 100 Wikidata profiles are retained in data/real_wrestlers.db. To try adding non-overlapping pages, run:
    py -m wrestling_sim.real_data sync --limit 100 --offset 100
    py -m wrestling_sim.real_data sync --limit 100 --offset 200
    py -m wrestling_sim.real_data list --limit 20

Every query saves into the same source catalogue with ID-based de-duplication. Wikidata response quality, service availability and source changes may vary.

### Start the REAL-NAME universe, not the older pilot
    py -m wrestling_sim.real_data seed-universe --save saves/real_universe.db
    py -m wrestling_sim.cli --save saves/real_universe.db web

If that filename already exists, the tool REFUSES to overwrite it. To start again, specify a new save path such as saves/real_universe_v2.db. Do not reset/delete your original saves.

### What is real and what is fictional
- Real: publicly listed stage names; official source URLs; optional biographical dates/heights/weights matched to Wikidata; snapshot metadata.
- Fictional/game-only: scores (0–25), personalities, behavior, morale, salaries, contracts, promotion cash and popularity, heel/face turns, injuries and incidents, booking rivalries, belts and title holders, staff, and talent availability.
- Simulation pay and wrestler affiliation are not independently verified employment facts.
- Missing biographical age defaults to age 30 for the simulation. Default size values are generated game settings, not sourced physical measurements.
- The four current companies and 80 curated names are included without downloading new website markup; Wikidata sync expands the game-world independent roster.
- Current wrestlers are people, and the game should not imply that invented conflicts or controversy are true about them.

### Gameplay focus
You play WWE in this scenario, with AEW, TNA and ROH simulated as rivals. Each begins with 12 men, 8 women, and fictional in-game budgets. WWE gets two intentionally invented starting feuds to satisfy minimum weekly booking constraints. Saved in-game title holders are fiction, not a statement about actual 2026 championships.

The existing rules still require a full show card, press conference, and resolution of all Inbox blockers before a week can advance. Run 8–12 weeks and share issues you find.
