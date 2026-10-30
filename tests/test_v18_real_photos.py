"""V1.8 source-verified photo ingestion and safe fallback tests (offline)."""
from wrestling_sim.real_data import ingest
from wrestling_sim.real_photos import sync_photos, lookup_photos, resolve_roster_identities
from wrestling_sim.real_universe import build_universe
from wrestling_sim.api import _portrait_data
import wrestling_sim.real_photos as photos


def person(qid,name):
    return {"person":{"value":"https://www.wikidata.org/entity/"+qid},
            "personLabel":{"value":name},
            "gender":{"value":"https://www.wikidata.org/entity/Q6581097"}}


def test_commons_license_metadata_and_identity_lookup(tmp_path,monkeypatch):
    db=tmp_path/"profiles.db"
    ingest([person("Q1005","Sample Wrestler")],db)
    def response(base,params):
        if params["action"]=="wbgetentities":
            return {"entities":{"Q1005":{"claims":{"P18":[{"mainsnak":{"datavalue":{"value":"Example.png"}}}]}}}}
        return {"query":{"pages":{"1":{"imageinfo":[{
            "thumburl":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Example.png/200px-Example.png",
            "descriptionurl":"https://commons.wikimedia.org/wiki/File:Example.png",
            "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
                           "UsageTerms":{"value":"Creative Commons Attribution-Share Alike"},
                           "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
                           "Artist":{"value":"<b>Photographer</b>"}}
        }]}}}}
    monkeypatch.setattr(photos,"_get_json",response)
    result=sync_photos(db,limit=10)
    assert result["photos_imported"]==1
    item=lookup_photos(db)["Q1005"]
    assert item["portrait_author"]=="Photographer"
    assert item["portrait_license"]=="CC BY-SA 4.0"


def test_unlicensed_photos_are_rejected(tmp_path,monkeypatch):
    db=tmp_path/"profiles.db"
    ingest([person("Q1005","Sample Wrestler")],db)
    def response(base,params):
        if params["action"]=="wbgetentities":
            return {"entities":{"Q1005":{"claims":{"P18":[{"mainsnak":{"datavalue":{"value":"Bad.jpg"}}}]}}}}
        return {"query":{"pages":{"1":{"imageinfo":[{
            "thumburl":"https://upload.wikimedia.org/wikipedia/commons/bad.jpg",
            "descriptionurl":"https://commons.wikimedia.org/wiki/File:Bad.jpg",
            "extmetadata":{"LicenseShortName":{"value":"All rights reserved"},
                           "UsageTerms":{"value":"Non-free"},
                           "LicenseUrl":{"value":"https://example.com/license"},
                           "Artist":{"value":"Person"}}
        }]}}}}
    monkeypatch.setattr(photos,"_get_json",response)
    assert sync_photos(db,10)["photos_imported"]==0
    assert lookup_photos(db)=={}


def test_roster_resolver_requires_exact_occupation_and_name(tmp_path,monkeypatch):
    db=tmp_path/"profiles.db"
    def response(base,params):
        if params["action"]=="wbsearchentities":
            return {"search":[{"id":"Q34567","label":"Cody Rhodes"}]}
        return {"entities":{"Q34567":{
            "labels":{"en":{"value":"Cody Rhodes"}},
            "aliases":{"en":[]},
            "claims":{"P106":[{"mainsnak":{"datavalue":{"value":{"id":"Q13474373"}}}}]}
        }}}
    monkeypatch.setattr(photos,"_get_json",response)
    result=resolve_roster_identities(db,limit=1)
    assert result["matched_roster_identities"]==1
    with __import__("sqlite3").connect(db) as connection:
        assert connection.execute("SELECT display_name FROM people").fetchone()[0]=="Cody Rhodes"


def test_later_photo_sync_enriches_existing_real_campaign(tmp_path,monkeypatch):
    db=tmp_path/"profiles.db"
    state=build_universe(db,add_independents=False)
    ingest([person("Q1005","Cody Rhodes")],db)
    with __import__("sqlite3").connect(db) as connection:
        connection.executescript(photos.SCHEMA)
        connection.execute("INSERT INTO portraits VALUES(?,?,?,?,?,?,?)",
            ("Q1005","https://upload.wikimedia.org/wikipedia/commons/a.jpg",
             "https://commons.wikimedia.org/wiki/File:a.jpg",
             "A photographer","CC BY 4.0",
             "https://creativecommons.org/licenses/by/4.0/","2026-10-28T01:00:00Z"))
    monkeypatch.setenv("RINGSIDE_REAL_DATA_DB",str(db))
    result=_portrait_data(state)
    assert result["rw_codyrhodes"]["portrait_author"]=="A photographer"
