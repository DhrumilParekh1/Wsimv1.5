"""Reproducible fictional rookie generation for a newly founded company.

Names and portraits are fictional; no real-world identities or photographs are
assigned to these workers. The campaign seed and company name determine a
stable initial roster. Once created, the roster is stored in the SQLite save
and is never silently regenerated.
"""
from __future__ import annotations
import hashlib
import random
from .starter import make_wrestler
from .ratings import rating_breakdown
from .weights import ALL_ATTRIBUTES

COUNTS={"indie":(5,3),"startup":(6,4),"juggernaut":(7,4)}
FIRST_NAMES=("Adrian","Avery","Blake","Casey","Dante","Elliot","Emerson",
             "Felix","Harper","Jordan","Kai","Logan","Micah","Nico","Quinn",
             "Reese","Riley","Rowan","Sasha","Skyler","Tatum","Taylor",
             "Valen","Wren","Zane","Arlo","Briar","Remy","Milo","Nova")
LAST_NAMES=("Archer","Bishop","Cortez","Drake","Everett","Frost","Graves",
            "Hale","Irving","Jensen","Knight","Lennox","Mercer","Nash",
            "Orion","Parker","Quill","Reyes","Sloan","Sterling","Thorne",
            "Vale","West","Wilder","York","Voss","Maddox","Stone","Cross")
STYLES={
    "technical":{"technique":3.0,"sequences":2.0,"selling":1.5},
    "power":{"athleticism":2.5,"presence":2.0,"moves":2.0,"agility":-1.0},
    "aerial":{"agility":3.0,"athleticism":2.0,"flair":2.5},
    "character":{"mic_skills":3.0,"character_work":2.5,"charisma":2.0},
    "allround":{"workrate":2.0,"stamina":1.5,"sequences":1.0},
    "brawler":{"determination":2.5,"moves":1.5,"selling":1.5},
}

def _attributes(rng,style):
    attrs={key:round(rng.uniform(10.5,15.5),2) for key in ALL_ATTRIBUTES}
    for key in ("workrate","technique","moves","sequences","selling","stamina","agility",
                "athleticism","mic_skills","charisma","character_work","presence"):
        attrs[key]=round(rng.uniform(11.7,15.5),2)
    for key,delta in STYLES[style].items():
        attrs[key]=round(min(18.5,max(9.0,attrs[key]+delta)),2)
    attrs.update({"controversy_risk":5.0,"injury_proneness":round(rng.uniform(6,12),2),
                  "fan_connection":round(rng.uniform(9.5,14.0),2),
                  "popularity":round(rng.uniform(8.5,13.5),2),
                  "relevance":round(rng.uniform(9,13),2),
                  "momentum":round(rng.uniform(11,15),2),
                  "professionalism":12.5,"loyalty":12.5,
                  "ambition":round(rng.uniform(11,16),2),
                  "face":round(rng.uniform(12,18),2),
                  "heel":round(rng.uniform(12,18),2),
                  "tweener":round(rng.uniform(12,18),2),
                  "experience":round(rng.uniform(7,15),2)})
    return attrs

def generate_rookies(state,tier,company_name):
    if tier not in COUNTS:raise ValueError("Unknown company tier")
    seed=int.from_bytes(hashlib.sha256(
        f"{state.seed}|{company_name.casefold()}|{tier}|rookies-v1".encode()).digest()[:8],"big")
    rng=random.Random(seed)
    target=COUNTS[tier]
    used_names={w.name.casefold() for w in state.wrestlers.values()}
    rookies=[]
    roster_slot=0
    for division,count in zip(("men","women"),target):
        for i in range(count):
            for attempt in range(150):
                first=rng.choice(FIRST_NAMES)
                last=rng.choice(LAST_NAMES)
                ring_name=first+" "+last
                if ring_name.casefold() not in used_names:
                    break
            else:
                raise ValueError("Unable to generate unique rookie names")
            used_names.add(ring_name.casefold())
            roster_slot+=1
            style=rng.choice(tuple(STYLES))
            attrs=_attributes(rng,style)
            role=rng.choice(("face","heel","tweener"))
            experience=rng.choice(("balanced","ambitious","cooperative","independent"))
            wid=f"gen_{seed:x}_{roster_slot:02d}"
            salary=(230 if tier=="indie" else 440 if tier=="startup" else 1000)+rng.randint(0,170)
            rookie=make_wrestler(wid,ring_name,rng.randint(20,33),"player",
                     role,attrs,salary=salary,contract_weeks=rng.randint(40,65),
                     growth=round(rng.uniform(.40,.82),2),
                     runway=round(rng.uniform(.52,.90),2),
                     division=division,personality=experience)
            rookie.card_tier=rng.choice(("lower_mid_card","mid_card","mid_card"))
            rookie.discovery_tier="regional"
            # Neutral-midrange overall and noticeable skill variation.
            ability=rating_breakdown(rookie)["current_ability"]
            if not 39<=ability<=70:
                raise AssertionError(f"Generated rookie rating out of realistic midrange: {ability}")
            rookies.append(rookie)
    return rookies


def upgrade_campaign_roster(save_path):
    """Opt-in, backed-up upgrade for a previously founded company.

    Do not add duplicates, never silently reroll existing rookies, and do
    not modify a non-custom or a pre-foundation save.
    """
    import shutil
    from pathlib import Path
    from .database import load_database, save_database
    from .company_creation import TIERS
    path=Path(save_path)
    if not path.is_file() or path.suffix.lower()!=".db":
        raise FileNotFoundError("Provide an existing .db RINGSIDE campaign save")
    state=load_database(path)
    foundations=[entry for entry in state.campaigns if entry.get("type")=="company_foundation"]
    if not foundations:
        raise ValueError("Found a new promotion in the game before adding generated rookies")
    tier=foundations[-1].get("tier")
    if tier not in COUNTS:
        raise ValueError("Unrecognized founding company tier")
    generated=[w for w in state.wrestlers.values()
               if w.id.startswith("gen_") and w.company_id=="player"]
    expected=sum(COUNTS[tier])
    if len(generated)==expected:
        return {"added":0,"roster_size":sum(w.company_id=="player"
                                           for w in state.wrestlers.values()),
                "note":"All generated wrestlers already exist; nothing changed"}
    if generated:
        raise ValueError("Partial generated roster found; refusing to reroll or duplicate workers")
    candidates=generate_rookies(state,tier,state.player_company.name)
    if any(w.id in state.wrestlers for w in candidates):
        raise ValueError("Generated IDs already exist; refusing to overwrite")
    backup=path.with_name(path.name+".before-rookies.bak")
    if backup.exists():
        raise FileExistsError("Backup already exists; refusing overwrite: "+str(backup))
    shutil.copy2(path,backup)
    for wrestler in candidates:
        state.wrestlers[wrestler.id]=wrestler
    state.player_company.roster_limit=max(
        state.player_company.roster_limit,
        TIERS[tier]["roster_limit"],
        sum(w.company_id=="player" for w in state.wrestlers.values()))
    state.activity_log.append({
        "type":"generated_roster_added",
        "tier":tier,"ids":[w.id for w in candidates],
        "source":"fictional_game_generation","year":state.year,"week":state.week})
    state.news.append(f"{len(candidates)} original developmental wrestlers have signed with {state.player_company.name}.")
    save_database(state,path)
    return {"added":len(candidates),"total_men":COUNTS[tier][0],
            "total_women":COUNTS[tier][1],"backup":str(backup),
            "roster_size":sum(w.company_id=="player" for w in state.wrestlers.values()),
            "save":str(path)}

if __name__=="__main__":
    import argparse,json
    parser=argparse.ArgumentParser(description="Backfill generated rookies into an existing player-owned campaign")
    parser.add_argument("--save",required=True,help="Existing .db game save")
    args=parser.parse_args()
    try:
        print(json.dumps(upgrade_campaign_roster(args.save),indent=2))
    except (ValueError,FileNotFoundError,FileExistsError) as exc:
        parser.exit(1,"RINGSIDE generated roster: "+str(exc)+"\n")
