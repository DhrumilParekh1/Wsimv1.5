"""V1.10 onboarding, editorial scouting, economic benchmarks and photo coverage."""
from pathlib import Path
import pytest
from wrestling_sim.scouting_data import SCOUTS,scouting_attributes,upgrade_saved_campaign
from wrestling_sim.real_universe import OFFICIAL_ROSTERS,build_universe
from wrestling_sim.realistic_economy import BENCHMARKS
from wrestling_sim.service import GameService
from wrestling_sim.company_creation import is_eligible_for_company_creation
from wrestling_sim.ratings import rating_breakdown
from wrestling_sim.weights import ALL_ATTRIBUTES

def test_every_curated_wrestler_has_distinct_scouting_profile():
    names={n for group in OFFICIAL_ROSTERS.values()
           for div in ("men","women") for n in group[div]}
    assert names==set(SCOUTS)
    profiles={n:scouting_attributes(n)[0] for n in names}
    assert len({tuple(attrs.values()) for attrs in profiles.values()})>=70
    assert all(set(attrs)==set(ALL_ATTRIBUTES) for attrs in profiles.values())
    assert all(0<=value<=25 for attrs in profiles.values() for value in attrs.values())
    assert profiles["Will Ospreay"]["agility"]>profiles["Roman Reigns"]["agility"]
    assert profiles["MJF"]["mic_skills"]>profiles["Claudio Castagnoli"]["mic_skills"]
    assert profiles["Gunther"]["technique"]>profiles["Jey Uso"]["technique"]
    # Never make negative claims about private character from an editorial profile.
    assert {p["loyalty"] for p in profiles.values()}=={12.5}
    assert {p["professionalism"] for p in profiles.values()}=={12.5}
    assert {p["controversy_risk"] for p in profiles.values()}=={5.0}

def test_additional_sourced_identity_has_repeatable_non_neutral_game_scoring():
    a,source_a=scouting_attributes("Invented Test Name")
    b,source_b=scouting_attributes("Invented Test Name")
    assert a==b
    assert source_a==source_b
    assert source_a["confidence"]=="synthetic"
    assert a["workrate"]!=12.5

def test_real_universe_has_differentiated_workrate_and_evidence_markers(tmp_path):
    state=build_universe(tmp_path/"empty_public_catalogue.db",add_independents=False)
    assert len(state.wrestlers)==80
    values=[rating_breakdown(w)["current_ability"] for w in state.wrestlers.values()]
    assert len(set(values))>=40
    assert any(entry.get("type")=="scouting_method" and
               entry.get("scores_are_game_estimates") is True for entry in state.activity_log)
    assert all(entry.get("not_comparable_to_full_global_reach") is True
               for entry in state.activity_log if entry.get("type")=="company_audience_baseline")

def test_competitor_audiences_obey_observed_order_with_unverifiable_roh_label():
    assert BENCHMARKS["player"]["viewership"]>BENCHMARKS["rival"]["viewership"]
    assert BENCHMARKS["rival"]["viewership"]>BENCHMARKS["circuit"]["viewership"]
    assert BENCHMARKS["circuit"]["viewership"]>BENCHMARKS["royal"]["viewership"]
    assert BENCHMARKS["royal"]["audience_modelled"] is True
    assert BENCHMARKS["player"]["audience_source"].startswith("https://")
    assert BENCHMARKS["player"]["prestige_history"]>BENCHMARKS["rival"]["prestige_history"]

def test_first_browser_run_generates_real_company_setup_without_a_prior_save(tmp_path,monkeypatch):
    monkeypatch.setenv("RINGSIDE_START_MODE","real")
    monkeypatch.setenv("RINGSIDE_REAL_DATA_DB",str(tmp_path/"empty_catalogue.db"))
    file=tmp_path/"first_visitor.db"
    assert not file.exists()
    service=GameService(file)
    assert file.exists()
    assert service.state.year==2026 and service.state.week==1
    assert is_eligible_for_company_creation(service.state)
    assert len(service.state.wrestlers)>=80
    # Same path re-opens campaign; never silently restarts or rewrites saves.
    service.state.player_company.money+=113
    service.save()
    restored=GameService(file)
    assert restored.state.player_company.money==service.state.player_company.money

def test_scouting_upgrade_backups_existing_save_and_skips_non_placeholder_profiles(tmp_path):
    from wrestling_sim.database import save_database,load_database
    state=build_universe(tmp_path/"people.db",add_independents=False)
    path=tmp_path/"played.db"
    save_database(state,path)
    result=upgrade_saved_campaign(path)
    assert result["updated"]==0
    # Emulate a legacy real-world profile with neutral ratings.
    existing=load_database(path)
    w=existing.wrestlers["rw_codyrhodes"]
    for name in ("workrate","technique","moves","sequences","flair","selling"):
        w.attributes[name]=12.5
    save_database(existing,path)
    result=upgrade_saved_campaign(path)
    assert result["updated"]==1
    assert Path(result["backup"]).exists()
    loaded=load_database(path)
    assert loaded.wrestlers["rw_codyrhodes"].attributes["workrate"]>=19
    assert upgrade_saved_campaign(path)["updated"]==0

def test_js_onboarding_has_literal_bug_removed_and_user_welcome():
    asset=Path(__file__).resolve().parents[1]/"src/wrestling_sim/web/assets/app.js"
    text=asset.read_text(encoding="utf-8")
    assert 'value="\x24{safe(model.companyName)}"' not in text
    assert 'data-skip-company-setup' not in text
    assert 'data-enter-ringside' in text
    assert "welcomeView()" in text

def test_batch_photos_does_not_require_one_metadata_call_per_wrestler(monkeypatch):
    import wrestling_sim.real_photos as photos
    calls=[]
    def fake(base,params):
        calls.append((base,params))
        return {"query":{"pages":{
            "1":{"title":"File:Wrestler One.jpg","imageinfo":[{
                "thumburl":"https://upload.wikimedia.org/wikipedia/commons/one.jpg",
                "descriptionurl":"https://commons.wikimedia.org/wiki/File:Wrestler_One.jpg",
                "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
                               "UsageTerms":{"value":"Creative Commons Attribution-Share Alike"},
                               "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"}}}]},
            "2":{"title":"File:Wrestler Two.jpg","imageinfo":[{
                "thumburl":"https://upload.wikimedia.org/wikipedia/commons/two.jpg",
                "descriptionurl":"https://commons.wikimedia.org/wiki/File:Wrestler_Two.jpg",
                "extmetadata":{"LicenseShortName":{"value":"All rights reserved"},
                               "UsageTerms":{"value":"Non-free"}}}]}}}}
    monkeypatch.setattr(photos,"_get_json",fake)
    found=photos._batch_metadata(["Wrestler One.jpg","Wrestler Two.jpg"])
    assert len(calls)==1
    assert found["Wrestler One.jpg"]["license"]=="CC BY-SA 4.0"
    assert found["Wrestler Two.jpg"] is None
