"""Real promotion universe acceptance tests: offline, no HTTP or live WDQS."""
import pytest
from wrestling_sim.real_data import ingest, sparql_query
from wrestling_sim.real_universe import OFFICIAL_ROSTERS, build_universe, seed_universe, normalize_name


def sample_record(qid,name,gender="Q6581097"):
    return {
        "person":{"value":"https://www.wikidata.org/entity/"+qid},
        "personLabel":{"value":name},
        "dob":{"value":"1994-08-20T00:00:00Z"},
        "gender":{"value":"https://www.wikidata.org/entity/"+gender},
        "height":{"value":"1.8"},
        "mass":{"value":"86"}
    }


def test_snapshots_are_grounded_and_unique():
    assert len(OFFICIAL_ROSTERS)==4
    names=[]
    for row in OFFICIAL_ROSTERS.values():
        assert row["source"].startswith("https://")
        assert len(row["men"])>=8 and len(row["women"])>=5
        names.extend(row["men"])
        names.extend(row["women"])
    assert len(names)==len(set(map(normalize_name,names)))


def test_wikidata_pages_are_offset_and_repeatable():
    q=sparql_query(100,200)
    assert "OFFSET 200" in q
    assert "ORDER BY ?person" in q
    with pytest.raises(ValueError): sparql_query(100,-1)
    with pytest.raises(ValueError): sparql_query(100,5001)


def test_campaign_has_four_real_promotions_balanced_divisions(tmp_path):
    source=tmp_path/"biographies.db"
    ingest([sample_record("Q123456","Cody Rhodes"),
            sample_record("Q123457","Sample Independent"),
            sample_record("Q123458","Independent Woman","Q6581072")],source)
    state=build_universe(source)
    assert state.companies["player"].name=="WWE"
    assert state.companies["rival"].name=="All Elite Wrestling"
    assert len(state.wrestlers)>=82
    for cid in ("player","rival","circuit","royal"):
        assert sum(w.company_id==cid and w.division=="men" for w in state.wrestlers.values())>=2
        assert sum(w.company_id==cid and w.division=="women" for w in state.wrestlers.values())>=2
    cody=state.wrestlers["rw_codyrhodes"]
    assert cody.height_cm==180
    assert cody.attributes["workrate"]==12.5
    assert not any(w.id=="steel" for w in state.wrestlers.values())
    assert state.championships["men_world"]["holder_id"]=="rw_codyrhodes"
    assert all(all(wid in state.wrestlers for wid in s.wrestler_ids)
               for s in state.storylines.values())
    assert any(x.get("wikidata_id")=="Q123456" for x in state.activity_log)


def test_real_campaign_db_round_trip_no_overwrite(tmp_path):
    from wrestling_sim.database import load_database
    source=tmp_path/"source.db"
    ingest([sample_record("Q88888","One Independent")],source)
    path=tmp_path/"real_universe.db"
    result=seed_universe(source,path)
    assert result["by_promotion"]["WWE"]==20
    loaded=load_database(path)
    assert len(loaded.wrestlers)==result["people"]
    assert loaded.companies["player"].name=="WWE"
    assert loaded.wrestlers["rw_rhearipley"].name=="Rhea Ripley"
    with pytest.raises(FileExistsError): seed_universe(source,path)
