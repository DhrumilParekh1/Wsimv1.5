"""Offline validation: no internet needed for the real-roster importer tests."""
import pytest
from wrestling_sim.real_data import _record, ingest, list_people, seed_game, sparql_query

def wd(qid,name,gender="Q6581097",dob="1990-05-01T00:00:00Z"):
    return {"person":{"value":"http://www.wikidata.org/entity/"+qid},
            "personLabel":{"value":name},
            "dob":{"value":dob},
            "gender":{"value":"http://www.wikidata.org/entity/"+gender},
            "height":{"value":"1.85"},
            "mass":{"value":"94"}}

def test_query_is_bounded():
    assert "wd:Q13474373" in sparql_query(25)
    assert "LIMIT 25" in sparql_query(25)
    with pytest.raises(ValueError):sparql_query(1000)

def test_catalogue_ingestion_and_provenance(tmp_path):
    path=tmp_path/"source.db"
    result=ingest([wd("Q44437","Sample Person"),wd("Q0","Invalid")],path)
    assert result["imported"]==1 and result["rejected"]==1
    people=list_people(path)
    assert len(people)==1
    assert people[0]["height_cm"]==185
    assert people[0]["source_url"]=="https://www.wikidata.org/wiki/Q44437"
    ingest([wd("Q44437","Updated Name")],path)
    assert list_people(path)[0]["display_name"]=="Updated Name"

def test_seed_does_not_overwrite_or_replace_starter(tmp_path):
    db=tmp_path/"source.db"
    ingest([wd("Q44437","Sample Person")],db)
    dest=tmp_path/"pilot.json"
    result=seed_game(db,dest)
    assert result["real_identities_added"]==1
    from wrestling_sim.storage import load_game
    state=load_game(dest)
    assert state.wrestlers["wd_Q44437"].name=="Sample Person"
    assert state.wrestlers["wd_Q44437"].company_id is None
    assert state.wrestlers["wd_Q44437"].attributes["workrate"]==12.5
    assert "steel" in state.wrestlers
    with pytest.raises(FileExistsError):seed_game(db,dest)
