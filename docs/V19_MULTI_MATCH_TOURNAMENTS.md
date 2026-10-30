# RINGSIDE V1.9: Multi-person wrestling and inaugural championship competitions

This expansion introduces multi-person matches and persistent title competitions
without altering historical singles match results or requiring real-life outcomes.

## How matches are booked

Show Booker -> Segment category: Match -> Match format:

* Singles: exactly 2 wrestlers (existing engine, unchanged).
* Triple Threat: exactly 3 wrestlers. A single pinfall/submission concludes the match.
* Fatal Four-Way: exactly 4 wrestlers. Interruption, recovery and temporary partnerships affect performance.
* Battle Royale: 4 to 20 wrestlers. Every elimination is logged; the last booked survivor wins.

Select performers within one division and a named winner. The engine draws actions
from movesets and combines physical technique, stamina, selling, agility, ring
sequences and character chemistry. RNG affects move execution and audience
satisfaction, **never overrides the booked winner**.

Battle Royale has an optional "Featured late eliminations" multi-select for
booker-selected dramatic moments. Those eliminations take place after the
ordinary eliminations, in the displayed selection order. Wrestlers eliminated
early accumulate less fatigue and medical exposure. Everyone still has regular
injury-proneness logic.

## Crown the inaugural champions

Open **Tournaments** in the left navigation. Choose a **vacant** championship.
Pick a method:

* Single elimination: select exactly four or eight same-division active wrestlers.
  The engine creates 2 or 3 rounds. Book the "ready" fixtures through the
  Tournament Office. Semi-final and final opponents are populated by **actual**
  simulated booked winners across weeks. Brackets and fixtures persist in the
  SQLite save.
* Triple Threat: select exactly three same-division wrestlers; book the
  ready title-crowning fixture.
* Fatal Four-Way: select exactly four.
* Battle Royale: select four to twenty.

Click **Prepare match in Booker**, select the winner and book the entire show as
usual. Tournament fixtures have a fixed format and exact participants; the
server rejects tampering, duplicates and premature finals. The title remains
vacant until the title-deciding final actually finishes. Tournament match
segments should have "Non-title match" selected in the ordinary title dropdown:
the tournament awards the title automatically when the final completes.

During inaugural tournaments the first-week show needs **both divisions
represented**, but does not need pre-existing rivalries. Other gameplay
requirements (weekly runtime, press conferences and Inbox items) remain.

Only the player's promotion can create inaugural tournaments for its vacant
titles; tournaments do not rewrite real-world title histories.

## Install and test

After the GitHub PR is merged:

    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q
    py -m wrestling_sim.cli --save saves/custom_2026.db web

Use a save containing a player-owned company with enough signed active
wrestlers in the desired division. The currently outstanding indie-roster
expansion feature is separate: a starting company with only one wrestler per
division cannot run a four-person competition until more talent is signed.

## Regression coverage

* Separate Triple Threat and Fatal Four-Way action generation
* Seed-deterministic Battle Royale elimination sequences, fixed winners and
  featured late elimination events
* 4-person bracket with real show booking and simulation across two weeks
* 8-person bracket across three rounds
* Vacant championship awards, repeat-fixture rejection and division filters
* Save/restore round-trip of tournaments and their title histories
* Browser JavaScript syntax check

Ollama only enhances already-simulated narrative facts and never controls
wins, substitutions, brackets or eliminations.
