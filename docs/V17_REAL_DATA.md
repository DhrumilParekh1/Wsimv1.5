# RINGSIDE V1.7 — Real wrestler data pilot

This is an **opt-in pilot**, not a replacement for the entire starter universe.

## What is genuinely sourced

The Python importer queries the Wikidata Query Service for living people whose occupation is **professional wrestler (Q13474373)**, and stores the resulting Wikidata IDs, names, birthdays, gender IDs, available height and weight, source URL, and retrieval timestamp in an isolated SQLite catalogue.

Wikidata structured data is CC0. The importer deliberately does not fetch photographs, copyrighted media, private information, or third-party game ratings. Individual biographies may still be inaccurate or incomplete; verify before shipping a public game.

## Run on Windows (project root)

    py -m wrestling_sim.real_data sync --limit 100
    py -m wrestling_sim.real_data list --limit 10
    py -m wrestling_sim.real_data seed --save saves/real_pilot.db --limit 100
    py -m wrestling_sim.cli --save saves/real_pilot.db web

A successful sync requires internet and a responsive Wikidata SPARQL service. It reports the actual number of accepted and rejected source records. Never claim 100 profiles were downloaded merely because --limit is 100.

## How the pilot plays

- Existing fictional wrestlers, companies, champions and storylines remain in the scenario to preserve V1.6 compatibility.
- Real sourced wrestler identities join the **free-agent pool** for recruiting/scouting.
- Dynamic game attributes are initialized at neutral **12.5 / 25** as obviously **fictional placeholders**, NOT real-world ratings or evidence of professionalism, controversy, loyalty or personal relationships.
- Real birth years and gender information are only used when present. Missing or nonbinary/other gender data are not automatically forced into the game's current binary roster divisions.
- Current real-world employment and private contract salaries are not inferred or scraped. These imported people begin as free agents **within this fictional game world**, which makes no statement about real contractual availability.
- The import creates a fresh save and will not overwrite an existing one. Source catalogue and campaign database are separate.

## Future full real-world start

A real-only company/roster launch requires replacing the starter champions and storylines, making roster division more inclusive and configurable, independently verifying current employment, and creating a transparent, player-editable rating method. Do not turn uncertain biography into invented facts or unlicensed intellectual property.

## Tests

    py -m pytest -q

The tests use offline fake Wikidata response records, so they test parsing, SQL persistence, save protection and game loading without claiming live Wikidata availability.
