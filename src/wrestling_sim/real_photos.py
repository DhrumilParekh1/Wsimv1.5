"""Identity-verified, license-checked portraits from Wikimedia Commons.

Wikidata entity P18 -> Commons imageinfo/extmetadata, never fuzzy search
for a face. All photos remain remotely hosted by their original publisher;
the local SQLite catalogue stores source, author, licence and a thumbnail URL.
Per-batch progress is printed immediately to avoid apparently stuck commands.
"""
from __future__ import annotations
from datetime import datetime,timezone
import html
import json
import re
import sqlite3
import sys
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen

WIKIDATA="https://www.wikidata.org/w/api.php"
COMMONS="https://commons.wikimedia.org/w/api.php"
USER_AGENT="RINGSIDE-Wrestling-Simulator/1.10 (https://github.com/DhrumilParekh1/Wsimv1.5)"
SCHEMA="""CREATE TABLE IF NOT EXISTS portraits (
    wikidata_id TEXT PRIMARY KEY REFERENCES people(wikidata_id),
    url TEXT NOT NULL, commons_page TEXT NOT NULL,
    author TEXT NOT NULL, license TEXT NOT NULL, license_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);"""
PERMITTED=("cc by","cc-by","cc0","public domain","pd-old","pd-self","cc by-sa")

class PhotoSourceError(RuntimeError):
    """A provider/network failure; do not silently make dozens of retries."""

def _progress(message):
    print("[RINGSIDE Photos] "+message,file=sys.stderr,flush=True)

def _get_json(base,params):
    request=Request(base+"?"+urlencode(params),headers={
        "Accept":"application/json","User-Agent":USER_AGENT})
    try:
        with urlopen(request,timeout=15) as response:
            data=json.load(response)
    except HTTPError as exc:
        host=urlparse(base).hostname
        if exc.code==429:
            raise PhotoSourceError(
                f"{host} is rate limiting requests (429). Stop and try later; "
                "successfully imported photos are already saved.") from exc
        if exc.code==403:
            raise PhotoSourceError(
                f"{host} denied the request (403); check network or service access. "
                "Do not repeatedly retry.") from exc
        raise PhotoSourceError(f"{host}: HTTP {exc.code}. "
                               "Already imported photos remain saved.") from exc
    except (URLError,TimeoutError,OSError) as exc:
        raise PhotoSourceError(f"Cannot reach {urlparse(base).hostname}: {exc}. "
                               "The network connection or service timed out.") from exc
    if not isinstance(data,dict) or data.get("error"):
        raise PhotoSourceError(f"{urlparse(base).hostname} returned an API error.")
    return data

def _strip_html(value):
    return re.sub(r"<[^>]*>","",html.unescape(value or "")).strip()[:240]

def _valid_image(url):
    parsed=urlparse(url)
    return parsed.scheme=="https" and parsed.hostname in (
        "upload.wikimedia.org","commons.wikimedia.org")

def _from_imageinfo(entry):
    ext=entry.get("extmetadata") or {}
    short=_strip_html(ext.get("LicenseShortName",{}).get("value",""))
    usage=_strip_html(ext.get("UsageTerms",{}).get("value",""))
    terms=(short+" "+usage).lower()
    if not any(token in terms for token in PERMITTED):
        return None
    image=entry.get("thumburl") or entry.get("url") or ""
    page=entry.get("descriptionurl") or ""
    license_url=ext.get("LicenseUrl",{}).get("value","")
    if not license_url and ("public domain" in terms or "cc0" in terms):
        license_url=page
    if not (_valid_image(image) and urlparse(page).hostname=="commons.wikimedia.org"
            and urlparse(license_url).scheme=="https"):
        return None
    return {
        "url":image,
        "commons_page":page,
        "author":_strip_html(ext.get("Artist",{}).get("value","")) or "See Wikimedia Commons",
        "license":short or usage,
        "license_url":license_url,
    }

def _metadata(image_title):
    """Keep a single-file API for old scripts and offline regression tests."""
    data=_get_json(COMMONS,{"action":"query","format":"json","prop":"imageinfo",
        "iiprop":"url|extmetadata","iiurlwidth":350,"titles":"File:"+image_title})
    for item in data.get("query",{}).get("pages",{}).values():
        if item.get("imageinfo"):
            return _from_imageinfo(item["imageinfo"][0])
    return None

def _batch_metadata(titles):
    """Use one Commons metadata request instead of one per wrestler."""
    if not titles:
        return {}
    if len(titles)==1:
        return {titles[0]:_metadata(titles[0])}
    data=_get_json(COMMONS,{"action":"query","format":"json","prop":"imageinfo",
        "iiprop":"url|extmetadata","iiurlwidth":350,
        "titles":"|".join("File:"+title for title in titles)})
    found={}
    for page in data.get("query",{}).get("pages",{}).values():
        if not page.get("imageinfo"):
            continue
        title=page.get("title","")
        if title.startswith("File:"):
            found[title[5:].replace("_"," ")]=_from_imageinfo(page["imageinfo"][0])
    return found

def _commons_search_candidate(name):
    """Fallback for missing P18. Search Commons with the verified wrestler's
    exact ring name. Only select a clearly titled solo portrait with a valid
    reuse licence; ambiguous photo results are deliberately ignored.
    """
    from .real_universe import normalize_name
    data=_get_json(COMMONS,{
        "action":"query","format":"json","generator":"search",
        "gsrsearch":f'intitle:"{name}"',"gsrnamespace":6,"gsrlimit":8,
        "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":350})
    selected=[]
    key=normalize_name(name)
    for page in data.get("query",{}).get("pages",{}).values():
        title=page.get("title","")
        if not title.startswith("File:") or key not in normalize_name(title):
            continue
        stem=title[5:].rsplit(".",1)[0].replace("_"," ").casefold()
        # Pictures whose filename advertises multiple subjects are not
        # reliable single-person portraits.
        if any(token in " "+stem+" " for token in (" and "," with "," vs "," versus "," group "," crowd "," team "," duo ")):
            continue
        if not page.get("imageinfo"):
            continue
        metadata=_from_imageinfo(page["imageinfo"][0])
        if metadata:
            selected.append(metadata)
    # Multiple acceptable files for the same person can be fine, but keep
    # deterministic ordering and never return a non-licensed image.
    return sorted(selected,key=lambda item:item["commons_page"])[0] if selected else None


def prioritized_photo_ids(save_path):
    """Read participants from one game save; do not write to the save."""
    from .database import load_database
    from .real_universe import normalize_name
    from .real_data import connection
    state=load_database(save_path)
    roster=[w for w in state.wrestlers.values() if w.company_id==state.player_company_id]
    roster.sort(key=lambda w:w.name.casefold())
    ids=[]
    linked={entry.get("wrestler_id"):entry.get("wikidata_id")
            for entry in state.activity_log
            if entry.get("type")=="real_roster_provenance" and entry.get("wikidata_id")}
    for w in roster:
        qid=linked.get(w.id) or (w.id[3:] if w.id.startswith("wd_") else None)
        if qid:ids.append(qid)
    return list(dict.fromkeys(ids))

def resolve_roster_identities(path,limit=80,offset=0):
    """Exact roster name or alias AND Wikidata professional-wrestler occupation.

    Skip ambiguous identities rather than silently assigning the wrong photo.
    Each successful identity commits immediately to survive interruption.
    """
    from .real_data import connection
    from .real_universe import OFFICIAL_ROSTERS,normalize_name
    if not 1<=limit<=80 or not 0<=offset<80:
        raise ValueError("Roster resolution needs limit 1..80 and offset 0..79")
    names=[name for group in OFFICIAL_ROSTERS.values()
           for division in ("men","women") for name in group[division]]
    selected=names[offset:offset+limit]
    accepted=skipped=previous=0
    with connection(path) as db:
        known={normalize_name(row[0]) for row in db.execute("SELECT display_name FROM people")}
        for i,name in enumerate(selected,1):
            _progress(f"Identities {i}/{len(selected)} · {name}")
            if normalize_name(name) in known:
                previous+=1
                continue
            search=_get_json(WIKIDATA,{"action":"wbsearchentities","format":"json",
                                  "language":"en","type":"item","search":name,"limit":5})
            qids=[hit["id"] for hit in search.get("search",[])
                  if re.fullmatch(r"Q[1-9][0-9]*",hit.get("id",""))]
            if not qids:
                skipped+=1
                continue
            details=_get_json(WIKIDATA,{"action":"wbgetentities","format":"json",
                                  "ids":"|".join(qids),"props":"labels|aliases|claims"})
            valid=[]
            for qid in qids:
                entity=details.get("entities",{}).get(qid,{})
                occupations=entity.get("claims",{}).get("P106",[])
                is_wrestler=any(x.get("mainsnak",{}).get("datavalue",{}).get("value",{}).get("id")=="Q13474373"
                               for x in occupations)
                labels=[entity.get("labels",{}).get("en",{}).get("value","")]
                labels.extend(x.get("value","") for x in entity.get("aliases",{}).get("en",[]))
                if is_wrestler and any(normalize_name(label)==normalize_name(name) for label in labels):
                    valid.append(qid)
            if len(valid)!=1:
                skipped+=1
                continue
            qid=valid[0]
            db.execute("""INSERT OR IGNORE INTO people
              (wikidata_id,display_name,source_url,retrieved_at)
              VALUES (?,?,?,?)""",(qid,name,"https://www.wikidata.org/wiki/"+qid,
                                      datetime.now(timezone.utc).isoformat()))
            db.commit()
            accepted+=1
            known.add(normalize_name(name))
    _progress(f"Roster identities finished: {accepted} matched, {previous} already known, {skipped} unresolved")
    return {"matched_roster_identities":accepted,"already_known":previous,"unresolved":skipped}

def sync_photos(path,limit=100,priority_ids=None,commons_search=False):
    """Prioritize curated ring names; fetch photo metadata in 25-file batches."""
    from .real_data import connection
    from .scouting_data import SCOUTS
    if not 1<=limit<=500:
        raise ValueError("Photo sync limit must be 1..500")
    imported=skipped=0
    now=datetime.now(timezone.utc).isoformat()
    with connection(path) as db:
        db.executescript(SCHEMA)
        pending=db.execute("""SELECT wikidata_id,display_name FROM people WHERE
             wikidata_id NOT IN (SELECT wikidata_id FROM portraits)
             ORDER BY wikidata_id""").fetchall()
        priority=set(priority_ids or [])
        pending=sorted(pending,key=lambda row:(0 if row[0] in priority else 1,
                                                0 if row[1] in SCOUTS else 1,row[0]))[:limit]
        _progress(f"{len(pending)} people selected; curated roster identities prioritized.")
        for index in range(0,len(pending),25):
            batch=pending[index:index+25]
            ids=[r[0] for r in batch]
            _progress(f"Photos {index+1}–{index+len(batch)} / {len(pending)}: checking Wikidata")
            data=_get_json(WIKIDATA,{"action":"wbgetentities","ids":"|".join(ids),
                            "props":"claims","format":"json"})
            entities=data.get("entities",{})
            file_by_id={}
            for qid in ids:
                claims=entities.get(qid,{}).get("claims",{}).get("P18",[])
                filename=claims[0].get("mainsnak",{}).get("datavalue",{}).get("value") if claims else None
                if isinstance(filename,str) and len(filename)<=240:
                    file_by_id[qid]=filename
                else:
                    if commons_search:
                        name=next((name for rowid,name in batch if rowid==qid),None)
                        if name:
                            _progress(f"No P18: checking licensed Commons photos for {name}")
                            match=_commons_search_candidate(name)
                            if match:
                                db.execute("INSERT OR REPLACE INTO portraits VALUES(?,?,?,?,?,?,?)",
                                    (qid,match["url"],match["commons_page"],match["author"],
                                     match["license"],match["license_url"],now))
                                imported+=1
                                continue
                    skipped+=1
            unique=list(dict.fromkeys(file_by_id.values()))
            details={}
            for start in range(0,len(unique),25):
                part=unique[start:start+25]
                _progress(f"Photos {index+1}–{index+len(batch)}: verifying {len(part)} Commons licences")
                details.update(_batch_metadata(part))
            for qid,filename in file_by_id.items():
                info=details.get(filename) or details.get(filename.replace("_"," "))
                if not info:
                    skipped+=1
                    continue
                db.execute("INSERT OR REPLACE INTO portraits VALUES(?,?,?,?,?,?,?)",
                    (qid,info["url"],info["commons_page"],info["author"],
                     info["license"],info["license_url"],now))
                imported+=1
            db.commit()
            _progress(f"Saved {imported} licensed photos so far; {skipped} unavailable/unsuitable.")
    return {"photos_imported":imported,"missing_or_unlicensed":skipped,
            "examined":len(pending),"catalogue":str(path)}

def lookup_photos(path):
    """Read cached photo metadata without any network requests."""
    from .real_data import connection
    with connection(path) as db:
        if not db.execute("""SELECT 1 FROM sqlite_master
                           WHERE type='table' AND name='portraits'""").fetchone():
            return {}
        rows=db.execute("""SELECT wikidata_id,url,author,license,license_url,commons_page
                           FROM portraits""").fetchall()
    return {qid:{"portrait_url":url,"portrait_author":author,
                 "portrait_license":license,"portrait_license_url":license_url,
                 "portrait_source":page}
            for qid,url,author,license,license_url,page in rows}
