# RINGSIDE V1.11 — New-player rosters and frontend freshness

## Fix the stale browser

V1.10 was merged, but the latest screenshots still show the old company-name
JavaScript expression and WWE bypass, and not the welcome screen. That source
is not present in GitHub main. The likely cause is an older Python server,
an incorrect project folder, or a cached frontend bundle.

V1.11 marks the HTML as no-store and uses new CSS/JS version query parameters.
The new endpoint http://127.0.0.1:8000/ui/build-info confirms that the
frontend_version is 1.11.0 and reports the save_path.

Stop the OLD game server using Ctrl+C in its terminal. From the actual nested
Git repo folder, run these commands one at a time:

    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q

Start a brand-new campaign with a filename that does not exist:

    py -m wrestling_sim.cli --save saves/V111_Fresh.db web

Visit http://127.0.0.1:8000/ and hard reload with Ctrl+Shift+R.
The original arena welcome screen should show ENTER RINGSIDE; the company
name input should be blank with an example placeholder. No WWE bypass exists.

## Generated wrestlers appear automatically after the main draft

| Starting tier | Drafted wrestlers | Generated men | Generated women | Total |
| --- | --- | ---: | ---: | ---: |
| Indie | 1+1 | 5 | 3 | 10 |
| Startup | 2+2 | 6 | 4 | 14 |
| Backed juggernaut | 3+3 | 7 | 4 | 17 |

Fictional wrestlers have original generated identities, role/alignment,
movesets, midrange CA, varied potential, salaries and contracts. Generated
talent is stored permanently in the save, not regenerated upon a reload.
Newly founded promotions begin without fabricated rivalries and with vacant
championships.

If an OLD save has only the main draft picks, stop the server, then run this
opt-in, automatic-backup upgrade (change the path):

    py -m wrestling_sim.generated_roster --save saves/V110_Fresh.db

It creates a before-rookies.bak backup and adds only the missing rookies,
expanding roster capacity appropriately. Rerunning an upgraded campaign will
not create duplicates. Saves that already have a partial generated roster
are not silently overwritten.

## Licensed real-person photos

Real-world photographs are available only when the external catalogue contains
a correctly matched identity and a suitable license. The browser cannot
guarantee that every performer has such a photo. To prioritize YOUR signed
wrestlers and search Commons cautiously when a Wikidata P18 photo is absent,
run the following from the repo folder:

    py -m wrestling_sim.real_data photos --resolve-roster --limit 100 --commons-search --save saves/V111_Fresh.db

Replace the save path with your own active campaign. The importer:
- Checks exact stage names and Wikidata professional-wrestler occupation.
- Puts the game's actual signed wrestlers first in the photo sync queue.
- Tries Wikimedia Commons images whose filename clearly identifies that
  wrestler as a single subject, and verifies a reusable license/attribution.
- Rejects ambiguous, unlicensed or restricted images.
- Stores source links and author credit, not image files, in the catalogue.

Use http://127.0.0.1:8000/ui/portrait-status to inspect missing names and
the number of licensed images. Refresh the browser after importing. If your
source uses a different photo database, set RINGSIDE_REAL_DATA_DB for the
game server and use the importer's --db argument.

## Deployment security

This is a private/single-user Docker preview, NOT public multi-user hosting.
It still needs authenticated accounts, per-user save isolation and secure
API authorization to safely serve players on the public internet.

## Test coverage

Python regression tests cover Indie/Startup/Juggernaut generated roster sizes,
unique and persistent fictional identities, the safe old-save upgrade,
browser version and non-cache root, approved photo-license fallback and
missing-photo reporting, plus the earlier game-engine tests. GitHub CI also
syntax-checks JavaScript and boots a fresh Docker campaign.
