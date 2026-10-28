"""Wikimedia Commons photo importer for the user's real wrestler catalogue.

Opt-in network operation, license-checked, with source and author attribution.
A verified match requires a Wikidata ID. Missing identities retain an avatar.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import sqlite3
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import re
import html

WIKIDATA="https://www.wikidata.org/w/api.php"
COMMONS="https://commons.wikimedia.org/w/api.php"
USER_AGENT="RINGSIDE-Wrestling-Simulator/1.8 (https://github.com/DhrumilParekh1/Wsimv1.5)"
SCHEMA="""CREATE TABLE IF NOT EXISTS portraits (
    wikidata_id TEXT PRIMARY KEY REFERENCES people(wikidata_id),
    url TEXT NOT NULL, commons_page TEXT NOT NULL,
    author TEXT NOT NULL, license TEXT NOT NULL, license_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);"""
PERMITTED=("cc by", "cc-by", "cc0", "public domain", "pd-old", "pd-self", "cc by-sa")

def _get_json(base,params):
    request=Request(base+"?"+urlencode(params),headers={
        "Accept":"application/json","User-Agent":USER_AGENT})
    with urlopen(request,timeout=35) as response:
        data=json.load(response)
    if not isinstance(data,dict) or "error" in data:
        raise RuntimeError("Image metadata provider rejected the request")
    return data

def _strip_html(value):
    return re.sub(r"<[^>]*>", "", html.unescape(value or "")).strip()[:240]

def _valid_image(url):
    p=urlparse(url)
    return p.scheme=="https" and p.hostname in ("upload.wikimedia.org", "commons.wikimedia.org")

def _metadata(image_title):
    data=_get_json(COMMONS,{"action":"query","format":"json","prop":"imageinfo",
        "iiprop":"url|extmetadata","iiurlwidth":250,"titles":"File:"+image_title})
    for item in data.get("query",{}).get("pages",{}).values():
        details=item.get("imageinfo") or []
        if not details:
            continue
        entry=details[0]
        ext=entry.get("extmetadata") or {}
        license_name=_strip_html(ext.get("LicenseShortName",{}).get("value",""))
        usage=_strip_html(ext.get("UsageTerms",{}).get("value",""))
        if not any(pattern in (license_name+" "+usage).lower() for pattern in PERMITTED):
            return None
        image=entry.get("thumburl") or entry.get("url") or ""
        page=entry.get("descriptionurl") or ""
        license_url=ext.get("LicenseUrl",{}).get("value","")
        if not (_valid_image(image) and urlparse(page).hostname=="commons.wikimedia.org"
                and urlparse(license_url).scheme=="https"):
            return None
        author=_strip_html(ext.get("Artist",{}).get("value","")) or "See Commons attribution"
        return {"url":image,"commons_page":page,"author":author,
                "license":license_name,"license_url":license_url}
    return None

def sync_photos(path,limit=100):
    """Only reuse exact Wikidata IDs, never fuzzy-face matching."""
    from .real_data import connection
    if not 1<=limit<=500:
        raise ValueError("Limit must be 1..500")
    imported=skipped=0
    now=datetime.now(timezone.utc).isoformat()
    with connection(path) as db:
        db.executescript(SCHEMA)
        people=db.execute("""SELECT wikidata_id FROM people WHERE
            wikidata_id NOT IN (SELECT wikidata_id FROM portraits)
            ORDER BY wikidata_id LIMIT ?""",(limit,)).fetchall()
        qids=[row[0] for row in people]
        for start in range(0,len(qids),40):
            batch=qids[start:start+40]
            response=_get_json(WIKIDATA,{"action":"wbgetentities","ids":"|".join(batch),
                "props":"claims","format":"json"})
            entities=response.get("entities") or {}
            for qid in batch:
                claims=entities.get(qid,{}).get("claims",{}).get("P18",[])
                if not claims:
                    skipped+=1
                    continue
                file=claims[0].get("mainsnak",{}).get("datavalue",{}).get("value")
                if not isinstance(file,str) or len(file)>240:
                    skipped+=1
                    continue
                try:
                    info=_metadata(file)
                except (OSError,RuntimeError,ValueError,KeyError):
                    skipped+=1
                    continue
                if not info:
                    skipped+=1
                    continue
                db.execute("INSERT OR REPLACE INTO portraits VALUES(?,?,?,?,?,?,?)",
                    (qid,info["url"],info["commons_page"],info["author"],
                     info["license"],info["license_url"],now))
                imported+=1
        db.commit()
    return {"photos_imported":imported,"missing_or_unlicensed":skipped,
            "examined":len(qids),"catalogue":str(path)}

def lookup_photos(path):
    """Single read per API request; no network calls while rendering."""
    from .real_data import connection
    with connection(path) as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='portraits'").fetchone()
        if not exists:
            return {}
        rows=db.execute("""SELECT wikidata_id,url,author,license,license_url,commons_page
                           FROM portraits""").fetchall()
    return {qid:{"portrait_url":url,"portrait_author":author,
                 "portrait_license":license_name,"portrait_license_url":license_url,
                 "portrait_source":page}
            for qid,url,author,license_name,license_url,page in rows}
