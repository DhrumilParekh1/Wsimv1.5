"""Regression tests: real-data imports and pre-fix saves must never crash."""
from dataclasses import asdict
import pytest

from wrestling_sim.real_data import ingest
from wrestling_sim.real_universe import _make_member, build_universe, seed_universe
from wrestling_sim.starter import new_game
from wrestling_sim.storage import restore_game


def record(qid,name,weight="290"):
    return {
        "person":{"value":"https://www.wikidata.org/entity/"+qid},
        "personLabel":{"value":name},
        "dob":{"value":"1992-08-17T00:00:00Z"},
        "gender":{"value":"https://www.wikidata.org/entity/Q6581097"},
        "height":{"value":"1.85"},
        "mass":{"value":weight}
    }


@pytest.mark.parametrize("value", [40, 44.9, 260.1, 290, 300])
def test_imported_real_source_weights_fall_back_to_safe_game_defaults(value):
    wrestler=_make_member("rw_test","Example Wrestler","men",None,
                         {"weight_kg":value,"height_cm":180},0)
    assert 45 <= wrestler.weight_kg <= 260
    assert wrestler.weight_kg != value


def test_legacy_real_save_repairs_only_out_of_range_imported_profiles(tmp_path):
    state=build_universe(tmp_path/"source.db",add_independents=False)
    data=asdict(state)
    bad=data["wrestlers"]["rw_codyrhodes"]
    bad["weight_kg"]=290
    recovered=restore_game(data)
    assert recovered.wrestlers["rw_codyrhodes"].weight_kg == 90
    assert len(recovered.wrestlers)==len(state.wrestlers)
    assert recovered.wrestlers["rw_rhearipley"].name=="Rhea Ripley"
    assert recovered.championships["men_world"]["holder_id"]=="rw_codyrhodes"
    assert any(event["type"]=="real_data_profile_repair" for event in recovered.activity_log)
    # After the save has been migrated, a second load must not repair again.
    repeat=restore_game(asdict(recovered))
    assert sum(event["type"]=="real_data_profile_repair" for event in repeat.activity_log)==1


def test_real_roster_seeding_with_large_recorded_mass_round_trips(tmp_path):
    from wrestling_sim.database import load_database
    catalogue=tmp_path/"wrestlers.db"
    ingest([record("Q123456","Cody Rhodes","290")],catalogue)
    target=tmp_path/"campaign.db"
    seed_universe(catalogue,target)
    restored=load_database(target)
    assert restored.wrestlers["rw_codyrhodes"].weight_kg <= 260
    assert restored.wrestlers["rw_codyrhodes"].weight_kg != 290


def test_unrelated_invalid_custom_wrestler_remains_a_validation_error():
    data=asdict(new_game())
    data["wrestlers"]["steel"]["weight_kg"]=290
    with pytest.raises(ValueError,match="physical profile"):
        restore_game(data)
