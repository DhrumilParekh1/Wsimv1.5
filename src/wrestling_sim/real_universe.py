"""Opt-in real-world-inspired roster universe.

The four roster snapshots are curated excerpts of public OFFICIAL promotion
roster pages, not a representation of exclusive contracts. Wrestler stats,
relationships, alignments, salaries and championship outcomes are invented
values belonging solely to the game. Dated provenance is saved in activity_log.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import re
import unicodedata

ROSTER_REVIEW_DATE = "2026-10-28"
OFFICIAL_ROSTERS = {
    "player": {
        "name":"WWE",
        "source":"https://www.wwe.com/superstars",
        "men":(
            "Cody Rhodes","CM Punk","Roman Reigns","Gunther","Seth Rollins",
            "Drew McIntyre","Bron Breakker","Jey Uso","Damian Priest",
            "Carmelo Hayes","Dominik Mysterio","Randy Orton"
        ),
        "women":(
            "Rhea Ripley","Becky Lynch","Bianca Belair","Charlotte Flair",
            "Iyo Sky","Bayley","Jade Cargill","Tiffany Stratton"
        ),
    },
    "rival": {
        "name":"All Elite Wrestling",
        "source":"https://www.allelitewrestling.com/aew-roster",
        "men":(
            "Will Ospreay","MJF","Kenny Omega","Jon Moxley","Darby Allin",
            "Swerve Strickland","Kazuchika Okada","Samoa Joe",
            "Claudio Castagnoli","Jay White","Kyle Fletcher","Jack Perry"
        ),
        "women":(
            "Mercedes Moné","Kris Statlander","Willow Nightingale","Jamie Hayter",
            "Riho","Tay Melo","Megan Bayne","Anna Jay"
        ),
    },
    "circuit": {
        "name":"TNA Wrestling",
        "source":"https://tnawrestling.com/roster",
        "men":(
            "Leon Slater","Moose","Nic Nemeth","Mustafa Ali","Frankie Kazarian",
            "Jeff Hardy","Matt Hardy","Cedric Alexander","Eddie Edwards",
            "Brian Myers","AJ Francis","Jason Hotch"
        ),
        "women":(
            "Indi Hartwell","Xia Brookside","Alisha Edwards","Tasha Steelz",
            "Jada Stone","Heather By Elegance","Kiera Hogan","Elayna Black"
        ),
    },
    "royal": {
        "name":"Ring of Honor",
        "source":"https://www.ringofhonor.com/roster",
        "men":(
            "Bandido","Lee Moriarty","Dalton Castle","Shane Taylor","Angelico",
            "Carlie Bravo","Komander","Tony Nese","AR Fox","Lee Johnson",
            "Griff Garrison","Serpentico"
        ),
        "women":(
            "Athena","Red Velvet","Deonna Purrazzo","Billie Starkz",
            "Diamante","Trish Adora","Robyn Renegade","Rachael Ellering"
        ),
    },
}

def normalize_name(name: str) -> str:
    value=unicodedata.normalize("NFKD",name.casefold())
    return re.sub(r"[^a-z0-9]","",value.encode("ascii","ignore").decode("ascii"))

def _biographies(catalogue):
    from .real_data import connection
    with connection(catalogue) as db:
        db.row_factory=__import__("sqlite3").Row
        return {normalize_name(row["display_name"]):dict(row)
                for row in db.execute("SELECT * FROM people")}

def _make_member(person_id, name, division, employer, biographical, ordinal):
    from .starter import make_wrestler
    from .weights import ALL_ATTRIBUTES
    # All numerical scores are explicit synthetic defaults. In particular,
    # personality, loyalty, professionalism and controversy are NOT asserted
    # as real information about these performers.
    rating={a:12.5 for a in ALL_ATTRIBUTES}
    rating["controversy_risk"]=5.0
    rating["injury_proneness"]=9.0
    born=biographical.get("date_of_birth") if biographical else None
    try:
        year=int(born[:4]) if born else None
    except (ValueError,TypeError):
        year=None
    age=2026-year if year and 1950<=year<=2008 else 30
    w=make_wrestler(person_id,name,age,employer,"face",rating,
                   salary=2000 if employer=="player" else 1800,
                   contract_weeks=52,division=division,
                   growth=.5,runway=.5,personality="balanced")
    w.card_tier="main_event" if ordinal<3 else "upper_mid_card" if ordinal<6 else "mid_card"
    if biographical:
        h=biographical.get("height_cm")
        weight=biographical.get("weight_kg")
        if isinstance(h,int) and 135<=h<=240:
            w.height_cm=h
        if isinstance(weight,(int,float)) and 45<=weight<=260:
            w.weight_kg=weight
    return w

def build_universe(catalogue="data/real_wrestlers.db", seed=2026, add_independents=True):
    """Build a new, non-destructive game campaign from sourced public names.

    Roster affiliation is a snapshot appearance in official roster pages. The
    simulation models exclusive company assignments only for gameplay.
    """
    from .starter import new_game
    from .models import Storyline
    from .world import bootstrap_world, add_world_news
    from .audience import ensure_expectations
    from .press_and_incidents import ensure_incidents
    from .real_data import connection
    state=new_game(seed)
    biographies=_biographies(catalogue)
    state.wrestlers={}
    state.storylines={}
    # Wipe generated events involving the fictional starter talent.
    state.news=[]
    state.world_news=[]
    state.weekly_metrics=[]
    state.incidents=[]
    state.memories=[]
    state.talent_concerns=[]
    state.chemistry={}
    state.activity_log=[]
    state.scenes={}
    state.social_posts=[]
    state.interactions=[]
    state.press_conferences={}
    state.assignments={}
    state.shows={}
    for coach in state.coaches.values():
        coach["relationships"]={}
    ids_by_name={}
    provenance=[]
    for company_id, detail in OFFICIAL_ROSTERS.items():
        company=state.companies[company_id]
        company.name=detail["name"]
        company.roster_limit=30
        # Explicitly invented economy values; not claims of audited revenue.
        scenario={
            "player":(2500000,75,72),
            "rival":(1800000,68,65),
            "circuit":(950000,52,49),
            "royal":(750000,45,46),
        }
        company.money,company.popularity,company.sponsor_interest=scenario[company_id]
        company.viewership=max(1000,round(25000+company.popularity*4500))
        # Financial strength is an intentionally synthetic starting scenario,
        # never a claim about real-world finances, contract or gate receipts.
        for division in ("men","women"):
            for ordinal,name in enumerate(detail[division]):
                slug=normalize_name(name)
                if slug in ids_by_name:
                    raise ValueError("Duplicate official roster identity: "+name)
                wid="rw_"+slug
                identity=biographies.get(slug)
                wrestler=_make_member(wid,name,division,company_id,identity,ordinal)
                state.wrestlers[wid]=wrestler
                ids_by_name[slug]=wid
                provenance.append({"type":"real_roster_provenance",
                    "wrestler_id":wid, "source_name":name,
                    "listed_by":detail["name"],"source_url":detail["source"],
                    "snapshot_reviewed":ROSTER_REVIEW_DATE,
                    "wikidata_id":identity["wikidata_id"] if identity else None,
                    "actual_contract_verified":False})
    if add_independents:
        with connection(catalogue) as db:
            db.row_factory=__import__("sqlite3").Row
            for record in db.execute("SELECT * FROM people ORDER BY wikidata_id"):
                slug=normalize_name(record["display_name"])
                if slug in ids_by_name:continue
                sex=record["gender_id"]
                if sex not in ("Q6581097","Q6581072"):continue
                division="women" if sex=="Q6581072" else "men"
                wid="wd_"+record["wikidata_id"]
                if wid in state.wrestlers:continue
                member=_make_member(wid,record["display_name"],division,None,dict(record),20)
                member.salary_weekly=0
                member.contract_weeks=0
                member.discovery_tier="known"
                state.wrestlers[wid]=member
                provenance.append({"type":"real_roster_provenance","wrestler_id":wid,
                    "source_name":record["display_name"],
                    "listed_by":None,"source_url":record["source_url"],
                    "snapshot_reviewed":record["retrieved_at"],
                    "actual_contract_verified":False})
    if len(state.wrestlers)<80:
        raise ValueError("Real universe roster is incomplete")
    # Game-created storylines, not claims that these rivalries really exist.
    state.storylines["real-men"]=Storyline(
        "real-men","Cody Rhodes vs Gunther (Simulated Rivalry)",
        [ids_by_name[normalize_name("Cody Rhodes")],
         ids_by_name[normalize_name("Gunther")]],
        hype=45,fan_investment=47,coherence=75)
    state.storylines["real-women"]=Storyline(
        "real-women","Rhea Ripley vs Becky Lynch (Simulated Rivalry)",
        [ids_by_name[normalize_name("Rhea Ripley")],
         ids_by_name[normalize_name("Becky Lynch")]],
        hype=45,fan_investment=47,coherence=75)
    for belt_id,holder,name in (
        ("men_world","Cody Rhodes","WWE World Championship (Simulated)"),
        ("men_intercontinental","Gunther","WWE Intercontinental Championship (Simulated)"),
        ("women_world","Rhea Ripley","WWE Women's World Championship (Simulated)")
    ):
        belt=state.championships[belt_id]
        belt["name"]=name
        belt["holder_id"]=ids_by_name[normalize_name(holder)]
        belt["lineage"]=[{"week":1,"winner_id":belt["holder_id"],
                         "previous_holder_id":None,"change":True,
                         "match_title":"Game starting champion, not an actual title record"}]
    # Drop fictional relationships and stock initial world metrics.
    for w in state.wrestlers.values():
        w.relationships={}
    state.activity_log.extend(provenance)
    state.news.append(
        "Real-identity roster scenario loaded. Salaries, contracts, rankings, "
        "personalities, alignments and titles are fictional GAME parameters.")
    for story in state.storylines.values():
        ensure_expectations(state,story)
    bootstrap_world(state)
    state.world_news=[]
    add_world_news(state,"industry","Real-world-inspired universe ready",
                   "Promotion roster names are sourced from public lists; all gameplay terms are simulated.")
    ensure_incidents(state)
    return state

def seed_universe(catalogue="data/real_wrestlers.db", save="saves/real_universe.db",
                  seed=2026, add_independents=True):
    """Save a real-name game universe, never clobber an existing campaign."""
    from .storage import save_game
    from .database import save_database
    dest=Path(save)
    if dest.exists():
        raise FileExistsError("Campaign already exists: "+str(dest))
    state=build_universe(catalogue,seed,add_independents)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.suffix==".db":
        save_database(state,dest)
    else:
        save_game(state,dest)
    return {"saved":str(dest),"people":len(state.wrestlers),
            "by_promotion":{c.name:sum(w.company_id==c.id for w in state.wrestlers.values())
                            for c in state.companies.values()},
            "independent":sum(w.company_id is None for w in state.wrestlers.values()),
            "note":"Roster identities are sourced. All contracts, finances and ratings are game simulations."}
