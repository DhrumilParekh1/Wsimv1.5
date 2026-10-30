"""V1.9: multi-match and inaugural title tournament integration tests."""
from dataclasses import asdict
import random
import pytest
from wrestling_sim.models import Segment
from wrestling_sim.real_universe import build_universe
from wrestling_sim.simulation import simulate_segment
from wrestling_sim.game import book_show, simulate_show
from wrestling_sim.tournaments import create_tournament, pending_matches, validate_tournament_segment
from wrestling_sim.storage import restore_game
from wrestling_sim.database import save_database,load_database


def world(tmp_path):
    return build_universe(tmp_path/"source.db",add_independents=False)

def entrants(state,division="men",count=8):
    return [w.id for w in state.wrestlers.values()
            if w.company_id==state.player_company_id and w.division==division][:count]

def sample(state,kind,n,winner=None):
    ids=entrants(state,count=n)
    return Segment("match",ids,25,kind,match_format=kind,
                   planned_winner_id=winner or ids[0],
                   match_styles=["balanced","storytelling"])

@pytest.mark.parametrize("format_name,count", [("triple_threat",3),("fatal_four_way",4)])
def test_multi_person_matches_have_booked_winner_and_individual_actions(tmp_path,format_name,count):
    state=world(tmp_path)
    seg=sample(state,format_name,count)
    outcome=simulate_segment(state,seg,random.Random(9),0)
    assert outcome["winner"]==seg.planned_winner_id
    assert outcome["match_format"]==format_name
    assert len(outcome["match_engine"]["highlights"])>=5
    assert outcome["match_engine"]["format"]==format_name
    assert outcome["individual_performance"]
    assert outcome["quality"]>=0
    assert any(h.get("action") in ("counter","exchange","double_team","pin_break")
               for h in outcome["highlights"])

def test_royale_elimination_log_survivor_and_reproducibility(tmp_path):
    state=world(tmp_path)
    ids=entrants(state,count=8)
    seg=sample(state,"battle_royale",8,winner=ids[5])
    first=simulate_segment(state,seg,random.Random(2026),0)
    second=simulate_segment(state,seg,random.Random(2026),0)
    assert first["match_engine"]["eliminations"]==second["match_engine"]["eliminations"]
    assert len(first["eliminations"])==7
    assert len(set(x["wrestler_id"] for x in first["eliminations"]))==7
    assert ids[5] not in {x["wrestler_id"] for x in first["eliminations"]}
    assert first["match_engine"]["survivor_id"]==ids[5]
    assert first["winner"]==ids[5]
    assert first["highlights"][-1]["is_finish"]

def test_format_validator_rejects_wrong_counts_and_finishes():
    with pytest.raises(ValueError,match="requires"):
        Segment("match",["a","b"],18,"Bad triple",planned_winner_id="a",match_format="triple_threat")
    with pytest.raises(ValueError,match="compatible finish"):
        Segment("match",["a","b","c"],18,"Bad triple",planned_winner_id="a",match_format="triple_threat",finish_type="disqualification")
    with pytest.raises(ValueError,match="compatible finish"):
        Segment("match",["a","b","c","d"],18,"Bad royale",planned_winner_id="a",match_format="battle_royale",finish_type="flash_pin")
    with pytest.raises(ValueError,match="must appear"):
        Segment("match",["a","b","c"],18,"Wrong winner",planned_winner_id="z",match_format="triple_threat")

def test_bracket_advancement_and_final_crowns_vacant_champion(tmp_path):
    state=world(tmp_path)
    state.championships["men_world"]["holder_id"]=None
    chosen=entrants(state,count=4)
    tour=create_tournament(state,"men_world",chosen)
    assert len(tour["rounds"])==2
    semis=list(tour["rounds"][0])
    for semi in semis:
        fixture=Segment("match",semi["participants"],20,"Tournament Semi",
                        planned_winner_id=semi["participants"][0],
                        match_styles=["balanced","storytelling"],
                        tournament_id=tour["id"],tournament_match_id=semi["id"])
        validate_tournament_segment(state,fixture)
    card=[
       Segment("match",m["participants"],25,"Semi "+str(i),planned_winner_id=m["participants"][0],
               match_styles=["balanced","storytelling"],tournament_id=tour["id"],tournament_match_id=m["id"])
       for i,m in enumerate(semis)
    ]
    women=entrants(state,"women",2)
    card.append(Segment("promo",women,40,"Women Opening",storyline_id="real-women"))
    card.append(Segment("promo",[chosen[0]],20,"Spotlight"))
    show=book_show(state,"Semifinal Night",card,120)
    simulate_show(state,show.id)
    assert all(m["status"]=="complete" for m in semis)
    final=tour["rounds"][1][0]
    assert final["status"]=="ready"
    assert len(final["participants"])==2
    assert state.championships["men_world"]["holder_id"] is None
    state.week+=1
    final_seg=Segment("match",final["participants"],35,"Inaugural Final",
                      planned_winner_id=final["participants"][1],
                      match_styles=["balanced","storytelling"],tournament_id=tour["id"],
                      tournament_match_id=final["id"])
    card=[final_seg,Segment("promo",women,40,"Women's Direction",storyline_id="real-women"),
          Segment("promo",[chosen[2]],30,"Aftermath")]
    show=book_show(state,"Inaugural Title Final",card,120)
    simulate_show(state,show.id)
    assert tour["status"]=="complete"
    assert tour["winner_id"]==final_seg.planned_winner_id
    assert state.championships["men_world"]["holder_id"]==final_seg.planned_winner_id
    assert state.championships["men_world"]["lineage"][-1]["tournament_id"]==tour["id"]

def test_direct_battle_royale_crowns_vacant_belt_and_survives_save(tmp_path):
    state=world(tmp_path)
    state.championships["women_world"]["holder_id"]=None
    women=entrants(state,"women",6)
    comp=create_tournament(state,"women_world",women,"battle_royale")
    fixture=comp["rounds"][0][0]
    match=Segment("match",women,35,"Women's Inaugural Battle Royale",
                  planned_winner_id=women[-1],match_format="battle_royale",
                  match_styles=["balanced","power"],tournament_id=comp["id"],
                  tournament_match_id=fixture["id"])
    men=entrants(state,"men",2)
    card=[match,Segment("promo",men,40,"Men's Direction"),
          Segment("promo",[women[0]],30,"Inaugural Preview")]
    show=book_show(state,"Crowning Night",card,120)
    report=simulate_show(state,show.id)
    assert comp["status"]=="complete"
    assert state.championships["women_world"]["holder_id"]==women[-1]
    assert len(report["segments"][0]["eliminations"])==5
    path=tmp_path/"season.db"
    save_database(state,path)
    restored=load_database(path)
    assert restored.tournaments[comp["id"]]["status"]=="complete"
    assert restored.championships["women_world"]["holder_id"]==women[-1]
    assert restored.shows[show.id].segments[0].match_format=="battle_royale"

def test_duplicate_or_wrong_fixture_is_rejected(tmp_path):
    state=world(tmp_path)
    state.championships["men_world"]["holder_id"]=None
    tour=create_tournament(state,"men_world",entrants(state,count=4))
    m=tour["rounds"][0][0]
    wrong=Segment("match",entrants(state,count=2)[::-1],22,"Wrong",
                  planned_winner_id=entrants(state,count=2)[0],
                  match_styles=["balanced","technical"],tournament_id=tour["id"],
                  tournament_match_id=m["id"])
    validate_tournament_segment(state,wrong)  # order is not fixed
    duplicate=set()
    validate_tournament_segment(state,wrong,duplicate)
    with pytest.raises(ValueError,match="Duplicate"):
        validate_tournament_segment(state,wrong,duplicate)
    unrelated=Segment("match",entrants(state,count=3)[1:],22,"Other",
                      planned_winner_id=entrants(state,count=3)[1],
                      match_styles=["balanced","technical"],tournament_id=tour["id"],
                      tournament_match_id=m["id"])
    with pytest.raises(ValueError,match="participants"):
        validate_tournament_segment(state,unrelated)


def test_featured_eliminations_appear_late_in_chosen_order(tmp_path):
    state=world(tmp_path)
    ids=entrants(state,count=8)
    # Important booked elimination moments should occur only after other exits.
    seg=Segment("match",ids,30,"Booked elimination moments",
                match_format="battle_royale",planned_winner_id=ids[0],
                featured_eliminations=[ids[3],ids[5]],
                match_styles=["balanced","power"])
    details=simulate_segment(state,seg,random.Random(13),0)["eliminations"]
    order=[item["wrestler_id"] for item in details]
    assert order[-2:]==[ids[3],ids[5]]
    assert ids[0] not in order
    with pytest.raises(ValueError,match="Featured"):
        Segment("match",ids,30,"Bad elimination booking",match_format="battle_royale",
                planned_winner_id=ids[0],featured_eliminations=[ids[0]])
