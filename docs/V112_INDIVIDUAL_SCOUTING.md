# RINGSIDE V1.12 — Individual Wrestler Performance Scouting

## What changed

The V1.10/V1.11 scouting algorithm applied a few headline fields to every
wrestler and then copied generic "technical", "aerial", "power" or "character"
bonuses. As a consequence, present-day working ability and career history
were compressed into similar scores. The new V1.12 approach removes those
archetype bonuses for every reviewed performer and **authors 20 different
public-performance attributes per wrestler**.

All 80 workers in the original WWE/AEW/TNA/ROH roster AND 46 commonly imported
recognizable performers have distinct public ability reviews (126 stage-name
profiles; Naomi and Trinity intentionally share the same underlying review).
Additional obscure imported names remain synthetic provisional scouting
estimates: a name alone is not evidence of real wrestling ability.

### Public 0–25 attributes reviewed individually

- **In-ring execution**: workrate, technique, moves, sequences, flair, athleticism,
  agility, determination *as an on-screen performance trait*, selling, stamina.
- **Character and speaking**: mic skills, charisma, character work, presence.
- **Audience/business**: fan connection, popularity, relevance,
  momentum (recent 2025/26 booking), promotion.
- **Career history**: experience (long-term résumé, which must not be treated
  as the same thing as present workrate).

An elite 2026 microphone performer can have average aerial ability; a
historically iconic star can have much lower **current** in-ring scores than
the star's career peak; current title runs and attention can boost form
without automatically making a wrestler a top technical worker.

Each wrestler has a candid **Established strength** and **Current limitation**
in the profile window. Potential is calculated from their resulting ability
and a separate growth/runway factor. Generated move sets now reflect actual
attribute values rather than old neutral initial defaults.

### Examples of independent attribute ratings (0–25)

| Wrestler | Mic | Technique | Agility | Experience | Recent form |
| --- | ---: | ---: | ---: | ---: | ---: |
| CM Punk | 25 | 17 | 12 | 25 | 23 |
| Will Ospreay | 20 | 24 | 25 | 21 | 19 |
| MJF | 25 | 20 | 17 | 19 | 25 |
| Gunther | 18 | 25 | 16 | 21 | 22 |
| Roman Reigns | 22 | 15 | 15 | 22 | 21 |
| Jade Cargill | 17 | 12 | 17 | 10 | 19 |
| Willow Nightingale | 22 | 19 | 20 | 15 | 24 |
| AJ Styles | 20 | 22 | 18 | 25 | 15 |
| Stephanie Vaquer | 20 | 24 | 22 | 16 | 25 |

All numbers are **editorial game-design evaluations**, not independently
measured medical, behavioral or athletic data. Disagreement is expected;
the goal is transparent strong differentiation, not pretending that public
match quality has an objective precision of a single point.

### Sources and methodology

Public contextual evidence available in the UI:

- The 2026 PWI 500: https://www.cagematch.net/en/?id=97&nr=583
- The 2026 PWI Women's 250: https://www.fightful.com/wrestling/stephanie-vaquer-tops-2026-pwi-womens-250/
- Weekly PWI rankings (results, promotion activity): https://pwi-online.com/pwi-ratings/
- WWE roster: https://www.wwe.com/superstars
- AEW roster: https://www.allelitewrestling.com/aew-roster
- TNA roster: https://tnawrestling.com/roster
- ROH roster: https://www.ringofhonor.com/roster

PWI annual rankings consider *in-universe win/loss, company push, title
achievements and activity*, and must NOT be interpreted as a pure metric of
physical skills or technical quality. They inform **current achievement
and momentum**, not every element of the final game score.

Reviews are dated November 21, 2026. The next seasonal update should update
public facing 2027 booking/match data separately from accumulated in-game
stats to avoid overriding player-created stories.

**Private traits are deliberately neutral**: loyalty, professionalism,
personal controversy, injury proneness and off-camera ambition cannot
be inferred from ring names or matches, and remain simulated defaults.
They are not negative allegations about real people. Unknown/poorly documented
independent wrestlers retain deterministic synthetic game ratings until a
specific individual review is available.

## Playing with fresh ratings

After merging PR #14, run from the actual Git repository directory:

    git checkout main
    git pull origin main
    py -m pip install -e ".[dev]"
    py -m pytest -q

Start a completely new company and use a NEW save filename:

    py -m wrestling_sim.cli --save saves/V112_IndividualRatings.db web

## Refresh ratings in your EXISTING campaign

**Stop the RINGSIDE server first. Do not operate on a live save.**

First see how many legacy neutral/V1 scouting profiles can safely update:

    py -m wrestling_sim.scouting_data --save saves/YOUR_SAVE.db --refresh-editorial --dry-run

Then upgrade only those unchanged legacy ratings:

    py -m wrestling_sim.scouting_data --save saves/YOUR_SAVE.db --refresh-editorial

A pre-upgrade backup ending in .before-scouting-v2.bak is created. The
migration skips wrestlers whose ring skills have diverged from their original
V1 public scouting values (e.g. earned training improvements).

If you have a PLAYED V1 save and still want a new baseline applied, you may
explicitly rebase developed talent, which preserves earned skill improvements
as offsets from the old baseline, saves the original as a backup, and avoids
repeating the upgrade:

    py -m wrestling_sim.scouting_data --save saves/YOUR_SAVE.db --rebase-developed --dry-run
    py -m wrestling_sim.scouting_data --save saves/YOUR_SAVE.db --rebase-developed

The rebase option is intentionally separate and not automatic; it can
substantially affect match difficulty, market values, potential and long-term
economics. Keep the backup if results are unsatisfactory.

The command will refuse to overwrite an existing backup filename; do not
delete a previous backup casually. Original game contracts, storylines,
titles, morale and manually assigned movesets are preserved.

## Testing

- All 126 reviewed individual performance matrices have exactly 20 distinct
  public scores, validated range 0..25.
- Contrasting specialist abilities have meaningful gaps.
- New real-world saves and old-import pilot saves use individual profiles for
  recognized names, preserving explicitly synthetic labels for obscure names.
- First-run rating variation, profile strength/limitation presentation, CLI
  upgrades, old-V1 safe detection and explicit developed-skill rebasing are
  covered in regression tests.
- CI also tests the browser syntax and fresh Docker installation.

## Limitations

The game ratings are directional, strong editorial evaluations informed by
observed public achievements, **not objective measurements that could be
made precise "to perfection"**. Inactive or sparsely documented wrestlers
need additional manual research instead of invented numerical certainty.
