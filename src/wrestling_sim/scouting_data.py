"""Editorial RINGSIDE scouting estimates, not verified measurements of a person.

Public on-screen wrestling work, published achievements and relative audience
exposure inform the selected game archetypes. These numbers are subjective
2026 GAME DESIGN judgments, not independently measured stats. Private
personality, loyalty, reputation or controversy are never inferred from a name.
"""
from __future__ import annotations
import hashlib
from .weights import ALL_ATTRIBUTES
from .models import clamp

# Name | ring archetype | in-ring aptitude | on-screen microphone/character |
# public audience recognition | in-ring experience.
# These are game-editor interpretations (0–25), NOT sourced numeric facts.
CURATED = """
Cody Rhodes|story|21|23|24|21
CM Punk|character|19|25|24|24
Roman Reigns|power|20|23|25|21
Gunther|technical|24|18|22|20
Seth Rollins|allround|23|23|24|22
Drew McIntyre|power|22|22|22|21
Bron Breakker|power|21|17|20|12
Jey Uso|character|18|21|23|18
Damian Priest|power|20|18|19|17
Carmelo Hayes|aerial|23|18|18|13
Dominik Mysterio|character|18|21|21|13
Randy Orton|story|21|22|24|25
Rhea Ripley|power|22|22|24|17
Becky Lynch|story|21|24|23|20
Bianca Belair|athletic|23|20|22|16
Charlotte Flair|technical|22|21|22|23
Iyo Sky|aerial|24|18|21|21
Bayley|story|21|22|21|20
Jade Cargill|power|17|18|20|10
Tiffany Stratton|athletic|21|19|21|11
Will Ospreay|aerial|25|20|22|19
MJF|character|21|25|23|15
Kenny Omega|allround|24|20|23|23
Jon Moxley|brawler|21|21|22|20
Darby Allin|aerial|22|17|20|15
Swerve Strickland|allround|22|22|21|17
Kazuchika Okada|technical|24|20|22|23
Samoa Joe|power|22|22|21|24
Claudio Castagnoli|technical|24|16|20|24
Jay White|technical|22|21|20|18
Kyle Fletcher|athletic|23|17|18|12
Jack Perry|character|19|19|18|14
Mercedes Moné|allround|22|22|23|19
Kris Statlander|power|21|18|19|14
Willow Nightingale|power|21|21|19|13
Jamie Hayter|brawler|22|19|19|16
Riho|aerial|21|17|19|19
Tay Melo|athletic|18|18|17|12
Megan Bayne|power|20|15|17|10
Anna Jay|character|18|18|17|11
Leon Slater|aerial|22|17|19|10
Moose|power|20|17|18|17
Nic Nemeth|story|21|20|19|23
Mustafa Ali|allround|22|20|19|18
Frankie Kazarian|technical|21|19|18|25
Jeff Hardy|aerial|19|18|20|25
Matt Hardy|story|17|20|19|25
Cedric Alexander|technical|22|16|18|17
Eddie Edwards|brawler|20|18|17|22
Brian Myers|story|17|20|16|20
AJ Francis|character|16|18|16|14
Jason Hotch|allround|19|14|13|10
Indi Hartwell|story|18|19|17|13
Xia Brookside|technical|18|16|15|13
Alisha Edwards|character|16|17|14|17
Tasha Steelz|allround|18|19|16|14
Jada Stone|aerial|18|15|14|9
Heather By Elegance|character|16|17|14|13
Kiera Hogan|athletic|17|17|15|13
Elayna Black|character|17|18|16|12
Bandido|aerial|24|16|19|18
Lee Moriarty|technical|22|16|16|11
Dalton Castle|character|19|23|19|21
Shane Taylor|power|20|20|16|19
Angelico|technical|20|15|15|20
Carlie Bravo|character|16|17|13|10
Komander|aerial|23|15|17|11
Tony Nese|athletic|20|17|15|19
AR Fox|aerial|21|16|15|22
Lee Johnson|athletic|19|16|15|11
Griff Garrison|power|16|15|13|10
Serpentico|character|17|16|14|20
Athena|allround|23|21|20|17
Red Velvet|athletic|19|18|16|13
Deonna Purrazzo|technical|21|20|18|18
Billie Starkz|allround|22|17|17|9
Diamante|brawler|19|16|15|17
Trish Adora|technical|19|16|15|13
Robyn Renegade|character|17|17|14|9
Rachael Ellering|power|18|17|15|16
"""
SCOUTS={}
for raw in CURATED.strip().splitlines():
    name,archetype,ring,mic,draw,experience=raw.strip().split("|")
    SCOUTS[name]=(archetype,int(ring),int(mic),int(draw),int(experience))

ARCHETYPE_BONUSES={
    "allround":{"workrate":2,"sequences":2,"technique":1,"selling":1},
    "story":{"selling":3,"character_work":3,"sequences":2,"determination":1},
    "technical":{"technique":4,"sequences":3,"selling":2,"workrate":1},
    "power":{"presence":4,"athleticism":2,"moves":2,"determination":2,"agility":-2},
    "aerial":{"agility":4,"athleticism":3,"flair":3,"moves":2,"stamina":1},
    "athletic":{"athleticism":4,"agility":3,"stamina":2,"moves":1},
    "brawler":{"determination":3,"selling":2,"moves":2,"presence":1},
    "character":{"character_work":4,"mic_skills":2,"charisma":2,"presence":1},
}
GAME_SOURCES={
    "WWE":"https://www.wwe.com/superstars",
    "All Elite Wrestling":"https://www.allelitewrestling.com/aew-roster",
    "TNA Wrestling":"https://tnawrestling.com/roster",
    "Ring of Honor":"https://www.ringofhonor.com/roster",
}
MODEL_VERSION="editorial_2026_11_v1"

def scouting_inputs(name):
    if name in SCOUTS:
        return SCOUTS[name],"editorial"
    # Additional independently imported people have no verified career
    # metrics. Their variation is stable game fiction, NOT a real assessment.
    digest=hashlib.sha256(name.casefold().encode("utf-8")).digest()
    kinds=("allround","technical","power","aerial","athletic","story","brawler")
    return (kinds[digest[0]%len(kinds)],13+digest[1]%6,
            12+digest[2]%7,10+digest[3]%8,11+digest[4]%9),"synthetic"

def scouting_attributes(name):
    (style,ring,mic,draw,experience),confidence=scouting_inputs(name)
    # Gameplay profiles are distinct, but off-screen/private judgments remain
    # neutral instead of making invented factual claims about real people.
    attrs={key:12.5 for key in ALL_ATTRIBUTES}
    attrs.update({
        "workrate":ring,"technique":ring-1,"moves":ring-1,"sequences":ring-1,
        "selling":ring-2,"athleticism":ring-1,"agility":ring-2,"flair":ring-2,
        "stamina":ring-1,"determination":(ring+experience)/2,
        "mic_skills":mic,"charisma":mic,"character_work":mic-1,
        "presence":(ring+mic)/2,"experience":experience,
        "fan_connection":draw-1,"popularity":draw,"relevance":draw,
        "momentum":max(8,draw-3),
        "promotion":14 if confidence=="editorial" else 12.5,
        "social_media_work":12.5,
        "controversy_risk":5.0,"injury_proneness":9.0,
        "professionalism":12.5,"loyalty":12.5,"ambition":12.5,
        "face":14,"heel":14,"tweener":14,
    })
    for key,bonus in ARCHETYPE_BONUSES[style].items():
        attrs[key]+=bonus
    return ({key:round(clamp(value,0,25),2) for key,value in attrs.items()},
            {"method":MODEL_VERSION,"confidence":confidence,
             "editorial_archetype":style,
             "note":"Subjective game scouting, not factual personal ratings."})

def apply_scouting_to_wrestler(wrestler,force=False):
    # The legacy default = 12.5 for all ring skills. Never overwrite a career
    # developed by actual user play unless the developer explicitly asks.
    keyskills=("workrate","technique","moves","sequences","flair","selling")
    was_neutral=all(wrestler.attributes[k]==12.5 for k in keyskills)
    if not (force or was_neutral):
        return False
    attrs,source=scouting_attributes(wrestler.name)
    wrestler.attributes.update(attrs)
    if source["confidence"]=="editorial":
        wrestler.growth_aptitude=.44 if wrestler.age>37 else .64
        wrestler.development_runway=.38 if wrestler.age>37 else .76
    else:
        wrestler.growth_aptitude=.54
        wrestler.development_runway=.62
    return True

def upgrade_saved_campaign(path):
    """Explicit, backed-up one-time opt-in for an existing SQLite campaign."""
    import shutil
    from pathlib import Path
    from .database import load_database,save_database
    target=Path(path)
    if not target.is_file() or target.suffix!=".db":
        raise FileNotFoundError("Specify an existing .db campaign path")
    state=load_database(target)
    identities=[w for w in state.wrestlers.values() if w.id.startswith(("rw_","wd_"))]
    eligible=[w for w in identities if all(w.attributes[k]==12.5
              for k in ("workrate","technique","moves","sequences","flair","selling"))]
    if not eligible:
        return {"updated":0,"note":"No unchanged placeholder profiles; save left untouched"}
    backup=target.with_name(target.name+".before-scouting.bak")
    if backup.exists():
        raise FileExistsError("Refusing to overwrite an earlier backup: "+str(backup))
    shutil.copy2(target,backup)
    count=0
    for w in eligible:
        if apply_scouting_to_wrestler(w):
            count+=1
            state.activity_log.append({"type":"editorial_scouting_update","wrestler_id":w.id,
                         "method":MODEL_VERSION,"not_a_factual_personal_profile":True})
    save_database(state,target)
    return {"updated":count,"backup":str(backup),"save":str(target)}

if __name__=="__main__":
    import argparse,json
    parser=argparse.ArgumentParser(description="Upgrade placeholder profiles in an existing campaign")
    parser.add_argument("--save",required=True)
    args=parser.parse_args()
    print(json.dumps(upgrade_saved_campaign(args.save),indent=2))
