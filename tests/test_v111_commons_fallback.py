"""Offline tests for licensed exact-name Wikimedia Commons fallback."""
import sqlite3
import wrestling_sim.real_photos as photos
from wrestling_sim.real_data import ingest

def item(qid,name):
    return {"person":{"value":"https://www.wikidata.org/entity/"+qid},
            "personLabel":{"value":name},
            "gender":{"value":"https://www.wikidata.org/entity/Q6581097"}}

def licensed(title):
    return {"title":"File:"+title,
            "imageinfo":[{"thumburl":"https://upload.wikimedia.org/wikipedia/commons/a.jpg",
                          "descriptionurl":"https://commons.wikimedia.org/wiki/File:"+title.replace(" ","_"),
                          "extmetadata":{"LicenseShortName":{"value":"CC BY 4.0"},
                                         "UsageTerms":{"value":"Creative Commons Attribution"},
                                         "LicenseUrl":{"value":"https://creativecommons.org/licenses/by/4.0/"}}}]}

def test_commons_fallback_requires_exact_subject_and_permitted_license(monkeypatch):
    def service(base,params):
        assert params.get("generator")=="search"
        return {"query":{"pages":{
            "1":licensed("Bianca Belair 2024.jpg"),
            "2":licensed("Bianca Belair and Becky Lynch 2024.jpg"),
            "3":licensed("Someone Else.jpg"),
            "4":{"title":"File:Bianca Belair NoLicense.jpg","imageinfo":[{
                 "thumburl":"https://upload.wikimedia.org/wikipedia/commons/other.jpg",
                 "descriptionurl":"https://commons.wikimedia.org/wiki/File:Bianca_Belair_NoLicense.jpg",
                 "extmetadata":{"LicenseShortName":{"value":"All rights reserved"},
                                "UsageTerms":{"value":"Non-free"}}}]}
        }}}
    monkeypatch.setattr(photos,"_get_json",service)
    answer=photos._commons_search_candidate("Bianca Belair")
    assert answer is not None
    assert "Bianca_Belair_2024" in answer["commons_page"]

def test_licensed_fallback_imports_missing_p18_with_no_unlicensed_image(tmp_path,monkeypatch):
    path=tmp_path/"people.db"
    ingest([item("Q1005","Bianca Belair"),item("Q1006","Not Covered")],path)
    def source(base,params):
        if params.get("action")=="wbgetentities":
            return {"entities":{"Q1005":{"claims":{}},"Q1006":{"claims":{}}}}
        if params.get("generator")=="search":
            return {"query":{"pages":{
                "1":licensed("Bianca Belair 2024.jpg")
            }}} if "Bianca Belair" in params["gsrsearch"] else {"query":{"pages":{}}}
        raise AssertionError(params)
    monkeypatch.setattr(photos,"_get_json",source)
    result=photos.sync_photos(path,limit=2,priority_ids=["Q1005"],commons_search=True)
    assert result["photos_imported"]==1
    stored=photos.lookup_photos(path)
    assert set(stored)=={"Q1005"}
    assert stored["Q1005"]["portrait_license"]=="CC BY 4.0"

def test_royalty_or_noncommercial_image_not_used():
    info=licensed("Bianca Belair.jpg")["imageinfo"][0]
    info["extmetadata"]["LicenseShortName"]["value"]="All rights reserved"
    assert photos._from_imageinfo(info) is None
