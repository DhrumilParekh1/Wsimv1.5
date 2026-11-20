# V1.10: Welcome, wrestler data, portraits and deployment preview

## Run from a fresh installation (Windows)

    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q
    py -m wrestling_sim.cli --save saves/V110_Fresh.db web

When the new .db file does not exist, the browser starts with an offline 80-name real-world roster, original welcome arena, and company setup screen. Existing saves never reset automatically. Enter a company name instead of seeing leaked template code. The WWE bypass button is removed.

## Real wrestler portraits

Run from the nested project repository folder, with internet access:

    py -m wrestling_sim.real_data photos --resolve-roster --limit 80

The importer now displays progress for each identity and group of images, prefers curated roster names, checks exact Wikidata wrestling identities, and retrieves image and Commons license metadata in batches. Source, author, license, and licensed image URL are saved in data/real_wrestlers.db. It does not download or bundle photos. People with uncertain identities or no suitable Commons license continue to show the fallback avatar. Not all roster photographs can be guaranteed. If the source blocks access with HTTP 403/429, the tool reports the error and preserves committed work. No user game save needs to be re-created just to show these new photos.

If a different photo catalogue is used, set RINGSIDE_REAL_DATA_DB for the server and pass the --db option during import.

## Update editorial scores in an existing save

Stop the server and use the appropriate existing campaign path:

    py -m wrestling_sim.scouting_data --save saves/custom_2026.db

This upgrades ONLY still-neutral placeholder real-name profiles; it saves an automatic .before-scouting.bak file first and refuses to overwrite an existing backup. Already developed/edited wrestlers are not changed. It is an explicit opt-in; do not run it on saves you want to preserve unchanged.

All 80 curated ring names have distinct scouting/game balance scores informed by public on-screen work and career accomplishments. These estimates are NOT measured objective ratings. Newly imported independent profiles receive stable synthetic game-only ratings. Private personal attributes, including loyalty and controversy, remain neutral defaults and are not claims about real people. A missing reliable birth date is labelled Age unverified in the UI instead of treating the simulated age-30 fallback as biographical fact.

Official roster name sources:
- https://www.wwe.com/superstars
- https://www.allelitewrestling.com/aew-roster
- https://tnawrestling.com/roster
- https://www.ringofhonor.com/roster

## Company audience baseline method (November 2026)

These are single-programme U.S. viewer benchmarks, not total company reach or global Netflix viewing. All financial figures, prestige history, sponsorship and fan-trust scores are explicitly modelled game values.

- WWE: 1,236,689 game-viewership proxy, based on 2026 YTD U.S. SmackDown Nielsen audience reported through Nov 6. https://trnbckl.net/ratings/smackdown/
- AEW: 661,378 proxy, based on 2026 YTD U.S. Dynamite Nielsen audience reported through Nov 11. https://trnbckl.net/ratings/dynamite/
- TNA: ~208,000 proxy, approximate mean of selected Sep 2026 AMC Impact broadcasts (184k/232k/207k). https://wrestlenomics.com/articles/2026/tna-impact-sep-10-on-amc-232000-viewers-0-03-p18-49-rating-tv-ratings-analysis/
- ROH: 50,000, explicitly fictional streaming-viewing proxy. There is no comparable public Nielsen benchmark, so this is not represented as observed audience data.

The initial game budgets are NOT actual WWE, AEW, TNA or ROH cash-on-hand or corporate revenue. They are differentiated game starting funds only.

## Docker private-preview setup

From the repository root:

    docker build -t ringside:preview .
    docker volume create ringside_saves
    docker run --name ringside-preview -p 127.0.0.1:8000:8000 -v ringside_saves:/data ringside:preview

Open http://127.0.0.1:8000/; the app generates /data/campaign.db if absent. Persistent saves and optional photo metadata stay in /data. To fetch portraits inside the container:

    docker exec ringside-preview python -m wrestling_sim.real_data photos --db /data/real_wrestlers.db --resolve-roster --limit 80

**Security warning: PRIVATE PREVIEW ONLY.** The server currently uses ONE globally shared GameService and has no user authentication, per-account state or authorization. Anyone who can reach the API can change the shared save. DO NOT expose this build to the open internet or claim public multi-user readiness. Before public deployment implement authenticated sessions, per-user save isolation, CSRF/rate limits, backup/recovery and monitoring, and secure Ollama access. Docker health is available at /health.

## Acceptance checklist

- Open a never-used save filename: welcome -> enter -> own-company setup.
- No raw JavaScript expression or WWE bypass button in company-name wizard.
- First-run 80 profiles have varied CA/PA; known bio dates only shown as sourced.
- Photo import prints progress; licensed photos show with attribution; uncertain faces stay fallback.
- Existing save resumes without reset; opt-in scouting upgrade backs up before changing placeholder stats.
- Test first matches, championships, tournaments and save/reload.

Earlier proposed indie draft, six generated wrestlers, manual alignment creation, and storyline-free initial tournament setup remain separate pending features.
