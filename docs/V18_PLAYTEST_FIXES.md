# RINGSIDE V1.8 — Playtest repair release

This branch addresses eight reported gameplay and interface issues. It does not automatically alter existing campaigns. Creating a custom company backs up the original saved game.

## Upgrade once merged

    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q

## Download licensed portrait references

Run from project root with internet:

    py -m wrestling_sim.real_data photos --resolve-roster --limit 100

The importer uses exact Wikidata identity and professional wrestler occupation checks. It reads P18 Wikimedia Commons photos, validates license metadata, and saves verified URLs and author/license/source references in data/real_wrestlers.db. A wrestler without a suitably licensed, matching photograph still displays a fallback avatar.

This is an opt-in, network-dependent sync. It does not download copyrighted publicity images from promotion websites or cache photos locally. Some portraits may remain unavailable. If your catalogue is stored elsewhere, set RINGSIDE_REAL_DATA_DB and use the --db argument.

## Create your independent promotion

Use a NEW real-world campaign to access the setup wizard:

    py -m wrestling_sim.real_data seed-universe --save saves/custom_2026.db
    py -m wrestling_sim.cli --save saves/custom_2026.db web

Choose the company name and level: indie ($75k, 1+1 draft picks, 45-min shows), startup ($400k, 2+2, 60-min shows), or financially backed juggernaut ($2.5m, 3+3, 90-min shows). WWE, AEW, TNA and ROH remain game competitors. Drafts and contracts are fictional simulation mechanics, not statements about real-life availability.

For an indie start with one man and one woman, book at least one segment for each division; singles matches still require two participants.

## Booker and narrative improvements

- Match title selections require a champion participant in the correct division. Invalid selections are rejected on the backend.
- Singles matches need two different wrestlers; a solo in-ring promo is valid.
- A solo, non-storyline promo has its own topical directions, and may add an interrupting wrestler; only two-person promos can select a ringside brawl.
- Recent win/loss topics require a relevant historical result; champion topics require the performer to hold a title.
- Match highlights show up to three currently revealed beats per page with Previous/Next controls. The viewer preserves its page between asynchronous updates.
- Press answers give qualitative reactions, while exact changes remain saved in press question effect records. Neutral has zero immediate change.
- Ollama commentary cannot introduce other named wrestlers or duplicate near-identical promo dialogue. Deterministic text remains the fallback when validation fails.
- Standalone segments no longer claim to have ongoing feud context in their analysis.

## Verification

GitHub Actions runs pytest and node --check. On the current working branch, the test suite passes; live local gameplay, external Wikidata/Commons service availability, and real Ollama generation require user acceptance testing. Keep your existing saves and report further issues after playing several weeks.
