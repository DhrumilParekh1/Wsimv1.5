"""V1.12 individual performance scouting and safe legacy profile upgrades."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from wrestling_sim.scouting_profiles_v2 import (
    PROFILES, PUBLIC_KEYS, SCOUTING_NOTES, REVIEWED_ON, MODEL_VERSION)
from wrestling_sim.scouting_data import (
    scouting_attributes,scouting_attributes_v1,upgrade_saved_campaign,
    apply_scouting_to_wrestler)
from wrestling_sim.real_universe import OFFICIAL_ROSTERS,build_universe
from wrestling_sim.ratings import rating_breakdown
from wrestling_sim.database import save_database,load_database


def test_every_official_worker_and_imported_key_name_has_independent_profile():
    roster_names={name for group in OFFICIAL_ROSTERS.values()
                  for division in ("men","women") for name in group[division]}
    assert roster_names<=set(PROFILES)
    assert len(PROFILES)>=120
    assert SCOUTING_NOTES.keys()==PROFILES.keys()
    assert len(PUBLIC_KEYS)==20
    assert len({tuple(row.values()) for row in PROFILES.values()})>=len(PROFILES)-1
    # Naomi and Trinity are two stage names for the same performer.
    assert PROFILES["Naomi"]==PROFILES["Trinity"]
    assert all(set(row)==set(PUBLIC_KEYS) for row in PROFILES.values())
    assert all(0<=v<=25 for row in PROFILES.values() for v in row.values())


def test_explicit_critical_differences_in_ring_promos_audience_and_form():
    # Better top-rope skill does not imply better promos; old career status
    # must not automatically determine present athleticism or momentum.
    ospreay=PROFILES["Will Ospreay"]
    punk=PROFILES["CM Punk"]
    roman=PROFILES["Roman Reigns"]
    gunther=PROFILES["Gunther"]
    mjf=PROFILES["MJF"]
    jade=PROFILES["Jade Cargill"]
    willow=PROFILES["Willow Nightingale"]
    charlotte=PROFILES["Charlotte Flair"]
    assert ospreay["agility"]-roman["agility"]>=9
    assert punk["mic_skills"]-ospreay["mic_skills"]>=5
    assert gunther["technique"]-jade["technique"]>=10
    assert roman["popularity"]-PROFILES["Jason Hotch"]["popularity"]>=10
    assert willow["momentum"]>charlotte["momentum"]
    assert PROFILES["Jeff Hardy"]["experience"]>PROFILES["Leon Slater"]["experience"]
    assert PROFILES["Jeff Hardy"]["workrate"]<PROFILES["Leon Slater"]["workrate"]
    assert mjf["momentum"]>ospreay["momentum"]
    assert PROFILES["AJ Styles"]["workrate"]>PROFILES["AJ Francis"]["workrate"]


def test_source_metadata_is_editorial_not_pretended_fact_and_private_stats_neutral():
    for name in ("MJF","AJ Styles","Stephanie Vaquer","Roxanne Perez","Gunther"):
        attrs,source=scouting_attributes(name)
        assert source["method"]==MODEL_VERSION
        assert source["confidence"]=="individual_editorial"
        assert source["reviewed_on"]==REVIEWED_ON
        assert source["strengths"] and source["limitations"]
        assert len(source["public_evidence"])>=2
        assert attrs["professionalism"]==12.5
        assert attrs["loyalty"]==12.5
        assert attrs["controversy_risk"]==5.0
        assert attrs["injury_proneness"]==9.0
    # Less-documented imported identities remain labelled synthetic.
    attrs,source=scouting_attributes("Unverified Regional Example")
    assert source["confidence"]=="synthetic"
    assert not source["public_evidence"]


def test_real_world_universe_has_clear_rating_spread_and_individual_moves(tmp_path):
    state=build_universe(tmp_path/"source.db",add_independents=False)
    high=state.wrestlers["rw_mjf"]
    low=state.wrestlers["rw_ajfrancis"]
    assert rating_breakdown(high)["current_ability"]>rating_breakdown(low)["current_ability"]+20
    # 80 wrestlers produce 26 distinct rounded CA scores across a realistic
    # range; requiring 30 would falsely inflate or deflate individual ratings.
    assert len({round(rating_breakdown(w)["current_ability"]) for w in state.wrestlers.values()})>=25
    for name in ("MJF","Cody Rhodes","Gunther","Jade Cargill"):
        w=next(w for w in state.wrestlers.values() if w.name==name)
        attrs,_=scouting_attributes(name)
        assert w.attributes["technique"]==attrs["technique"]
        assert w.moveset
        assert w.growth_aptitude!=.5


def test_old_v1_scouting_upgrade_uses_backup_and_does_not_reset_career_state(tmp_path):
    state=build_universe(tmp_path/"source2.db",add_independents=False)
    # This fixture represents a save authored under the V1 scouting rules,
    # not a newly created save already marked V2.
    for entry in state.activity_log:
        if entry.get("type")=="scouting_method":
            entry["model"]="editorial_2026_11_v1"
    unplayed=next(w for w in state.wrestlers.values() if w.name=="MJF")
    modified=next(w for w in state.wrestlers.values() if w.name=="Cody Rhodes")
    before,_=scouting_attributes_v1("MJF")
    unplayed.attributes.update(before)
    modified.attributes.update(scouting_attributes_v1("Cody Rhodes")[0])
    modified.attributes["technique"]+=1.0  # earned a skill improvement in a campaign
    unplayed.attributes["momentum"]+=1.0    # storyline gained momentum, preserve it
    old_momentum=unplayed.attributes["momentum"]
    unplayed.contract_weeks=23
    save=tmp_path/"old_game.db"
    save_database(state,save)
    dry=upgrade_saved_campaign(save,refresh_editorial=True,dry_run=True)
    assert dry["eligible"]==1
    assert dry["skipped_modified"]>=1
    assert not Path(str(save)+".before-scouting-v2.bak").exists()
    result=upgrade_saved_campaign(save,refresh_editorial=True)
    assert result["updated"]==1
    assert Path(result["backup"]).exists()
    restored=load_database(save)
    assert restored.wrestlers[unplayed.id].attributes["workrate"]==PROFILES["MJF"]["workrate"]
    assert restored.wrestlers[unplayed.id].attributes["momentum"]==old_momentum
    assert restored.wrestlers[unplayed.id].contract_weeks==23
    assert restored.wrestlers[modified.id].attributes["technique"]==scouting_attributes_v1("Cody Rhodes")[0]["technique"]+1.0
    assert upgrade_saved_campaign(save,refresh_editorial=True)["updated"]==0


def test_browser_renders_individual_strengths_and_explicit_weaknesses(tmp_path,monkeypatch):
    from wrestling_sim.api import app,service
    state=build_universe(tmp_path/"source3.db",add_independents=False)
    monkeypatch.setattr(service,"state",state)
    client=TestClient(app)
    data=client.get("/ui/state").json()
    mjf=next(w for w in data["wrestlers"] if w["name"]=="MJF")
    assert mjf["scouting_review"]["strengths"]
    assert mjf["scouting_review"]["limitations"]
    assert mjf["ratings_method"]==MODEL_VERSION
    js=(Path(__file__).resolve().parents[1]/
        "src/wrestling_sim/web/assets/app.js").read_text(encoding="utf-8")
    assert "Current limitation" in js
    assert "Established strength" in js


def test_explicit_rebase_preserves_earned_skill_momentum_and_custom_moveset(tmp_path):
    state=build_universe(tmp_path/"source4.db",add_independents=False)
    for item in state.activity_log:
        if item.get("type")=="scouting_method":
            item["model"]="editorial_2026_11_v1"
    w=next(w for w in state.wrestlers.values() if w.name=="MJF")
    old,_=scouting_attributes_v1(w.name)
    w.attributes.update(old)
    w.attributes["workrate"]+=1.75
    w.attributes["momentum"]+=2.0
    old_moveset=list(w.moveset)
    path=tmp_path/"played_game.db"
    save_database(state,path)
    dry=upgrade_saved_campaign(path,rebase_developed=True,dry_run=True)
    assert dry["rebased"]==1
    assert not Path(str(path)+".before-scouting-v2.bak").exists()
    result=upgrade_saved_campaign(path,rebase_developed=True)
    assert result["updated"]==1 and result["rebased"]==1
    assert Path(result["backup"]).exists()
    restored=load_database(path).wrestlers[w.id]
    assert restored.attributes["workrate"]==min(25,PROFILES["MJF"]["workrate"]+1.75)
    assert restored.attributes["momentum"]==min(25,PROFILES["MJF"]["momentum"]+2.0)
    assert restored.moveset==old_moveset
    assert upgrade_saved_campaign(path,rebase_developed=True)["updated"]==0
