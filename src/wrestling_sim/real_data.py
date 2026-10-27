"""Wikidata CC0 real-person catalogue: isolated from campaign save files.

Usage:
 python -m wrestling_sim.real_data sync --limit 100
 python -m wrestling_sim.real_data list
 python -m wrestling_sim.real_data seed --save saves/real_pilot.db

Only biographies are sourced. All game ratings, allegiances and contract
terms are expressly invented game-world values, not allegations about people.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_DB = Path("data/real_wrestlers.db")
SOURCE = "https://query.wikidata.org/sparql"
QID = re.compile(r"^Q[1-9][0-9]*$")
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS people (
  wikidata_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  date_of_birth TEXT,
  gender_id TEXT,
  height_cm INTEGER,
  weight_kg REAL,
  source_url TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  CHECK (height_cm IS NULL OR height_cm BETWEEN 100 AND 250),
  CHECK (weight_kg IS NULL OR weight_kg BETWEEN 25 AND 400)
);
CREATE TABLE IF NOT EXISTS source_log (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  accepted INTEGER NOT NULL,
  rejected INTEGER NOT NULL
);
"""

def connection(path: str | Path = DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn

def sparql_query(limit: int = 100) -> str:
    if not 1 <= limit <= 500:
        raise ValueError("Limit must be between 1 and 500.")
    return f"""SELECT ?person ?personLabel (SAMPLE(?dobValue) AS ?dob)
           (SAMPLE(?genderValue) AS ?gender)
           (SAMPLE(?heightValue) AS ?height)
           (SAMPLE(?massValue) AS ?mass)
WHERE {{
  ?person wdt:P106 wd:Q13474373; wdt:P31 wd:Q5.
  FILTER NOT EXISTS {{ ?person wdt:P570 ?deathDate. }}
  OPTIONAL {{ ?person wdt:P569 ?dobValue. }}
  OPTIONAL {{ ?person wdt:P21 ?genderValue. }}
  OPTIONAL {{ ?person wdt:P2048 ?heightValue. }}
  OPTIONAL {{ ?person wdt:P2067 ?massValue. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?person ?personLabel
ORDER BY ?person
LIMIT {int(limit)}"""

def fetch_wikidata(limit=100):
    url = SOURCE + "?" + urlencode({"query": sparql_query(limit), "format":"json"})
    request = Request(url, headers={"Accept":"application/sparql-results+json",
                                   "User-Agent":"RingsideSimulatorResearch/1.7 (local open-data catalogue)"})
    with urlopen(request,timeout=35) as response:
        return json.load(response)["results"]["bindings"]

def _value(row, key):
    obj = row.get(key)
    return obj.get("value") if isinstance(obj, dict) else None

def _quantity(value, unit_marker):
    if not value:
        return None
    # WDQS direct numeric bindings for quantities, generally SI meters/kilograms.
    try:
        number=float(value)
    except (TypeError,ValueError):
        return None
    converted=number*100 if unit_marker=="height" else number
    valid=(100 <= converted <= 250) if unit_marker=="height" else (25 <= converted <= 400)
    return round(converted) if unit_marker=="height" and valid else (round(converted,1) if valid else None)

def _record(row, now):
    uri=_value(row,"person") or ""
    qid=uri.rsplit("/",1)[-1]
    name=(_value(row,"personLabel") or "").strip()
    if not QID.fullmatch(qid) or not name or name==qid or len(name)>120:
        raise ValueError("Bad Wikidata identity")
    birth=_value(row,"dob")
    birth=birth[:10] if birth and re.match(r"^\d{4}-\d{2}-\d{2}",birth) else None
    gender=(_value(row,"gender") or "").rsplit("/",1)[-1]
    gender=gender if QID.fullmatch(gender) else None
    return (qid,name,birth,gender,_quantity(_value(row,"height"),"height"),
            _quantity(_value(row,"mass"),"mass"),
            "https://www.wikidata.org/wiki/"+qid,now)

def ingest(rows, path=DEFAULT_DB):
    now=datetime.now(timezone.utc).isoformat()
    accepted=rejected=0
    with connection(path) as db:
        for row in rows:
            try:
                rec=_record(row,now)
            except (ValueError,TypeError):
                rejected+=1
                continue
            db.execute("""INSERT INTO people VALUES (?,?,?,?,?,?,?,?)
              ON CONFLICT(wikidata_id) DO UPDATE SET
              display_name=excluded.display_name, date_of_birth=excluded.date_of_birth,
              gender_id=excluded.gender_id,height_cm=excluded.height_cm,
              weight_kg=excluded.weight_kg,source_url=excluded.source_url,
              retrieved_at=excluded.retrieved_at""",rec)
            accepted+=1
        db.execute("INSERT INTO source_log(source,imported_at,accepted,rejected) VALUES (?,?,?,?)",
                   (SOURCE,now,accepted,rejected))
    return {"imported":accepted,"rejected":rejected,"catalogue":str(path)}

def list_people(path=DEFAULT_DB,limit=20):
    with connection(path) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute("SELECT * FROM people ORDER BY display_name LIMIT ?",(limit,))]

def seed_game(path=DEFAULT_DB, save="saves/real_pilot.db", limit=100, seed=2026):
    """Add sourced identities as independent fictional-game free agents.

    The starter universe remains in place so the established storylines,
    division balance and champions continue to work; a fully real-only
    campaign is a separate migration.
    """
    from .starter import new_game, make_wrestler
    from .weights import ALL_ATTRIBUTES
    from .storage import save_game
    from .database import save_database
    state=new_game(seed)
    current_year=state.year
    added=0
    with connection(path) as db:
        db.row_factory=sqlite3.Row
        for row in db.execute("SELECT * FROM people ORDER BY wikidata_id LIMIT ?",(limit,)):
            wid="wd_"+row["wikidata_id"]
            if wid in state.wrestlers:
                continue
            gender=row["gender_id"]
            if gender not in ("Q6581097","Q6581072"): # unspecified: avoid falsely assigning division
                continue
            born=row["date_of_birth"]
            age=current_year-int(born[:4]) if born else 30
            if not 18<=age<=75:
                continue
            division="women" if gender=="Q6581072" else "men"
            # Neutral, explicitly synthetic attributes; NOT real performance assessments.
            synthetic={attribute:12.5 for attribute in ALL_ATTRIBUTES}
            w=make_wrestler(wid,row["display_name"],age,None,"face",synthetic,
                           division=division,growth=.5,runway=.5)
            if row["height_cm"] and 135<=row["height_cm"]<=240:
                w.height_cm=row["height_cm"]
            if row["weight_kg"] and 40<=row["weight_kg"]<=300:
                w.weight_kg=row["weight_kg"]
            w.discovery_tier="known"
            state.wrestlers[wid]=w
            added+=1
    if not added:
        raise ValueError("No eligible profiles with usable birth year and gender found.")
    save=Path(save)
    if save.exists():
        raise FileExistsError("Refusing to overwrite an existing campaign: "+str(save))
    save.parent.mkdir(parents=True,exist_ok=True)
    if save.suffix==".db":
        save_database(state,save)
    else:
        save_game(state,save)
    return {"real_identities_added":added,"save":str(save),
            "note":"Free-agent pilot; starter fictional cast is retained. Game ratings are synthetic."}

def main():
    parser=argparse.ArgumentParser(description="Sourced real-wrestler data pilot (Wikidata CC0)")
    sub=parser.add_subparsers(dest="command",required=True)
    for cmd in ("sync","list","seed"):
        sp=sub.add_parser(cmd)
        sp.add_argument("--db",default=str(DEFAULT_DB))
        sp.add_argument("--limit",type=int,default=100 if cmd!="list" else 20)
        if cmd=="seed":sp.add_argument("--save",default="saves/real_pilot.db")
    args=parser.parse_args()
    if args.command=="sync":
        result=ingest(fetch_wikidata(args.limit),args.db)
    elif args.command=="list":
        result=list_people(args.db,args.limit)
    else:
        result=seed_game(args.db,args.save,args.limit)
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
