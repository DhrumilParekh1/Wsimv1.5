"""V1.9 8-person bracket, independent final and API serialization coverage."""
from dataclasses import asdict
import pytest
from wrestling_sim.real_universe import build_universe
from wrestling_sim.tournaments import create_tournament,validate_tournament_segment,record_result
from wrestling_sim.models import Segment
from wrestling_sim.storage import restore_game


def test_eight_person_bracket_advances_only_simulated_winners(tmp_path):
    state=build_universe(tmp_path/"sources.db",add_independents=False)
    state.championships["men_world"]["holder_id"]=None
    people=[w.id for w in state.wrestlers.values()
            if w.company_id=="player" and w.division=="men"][:8]
    tour=create_tournament(state,"men_world",people,"single_elimination")
    assert [len(round) for round in tour["rounds"]]==[4,2,1]
    assert len(state.tournaments)==1
    fixture=tour["rounds"][0][0]
    seg=Segment("match",fixture["participants"],15,"Opening Quarter Final",
                planned_winner_id=fixture["participants"][0],
                match_styles=["balanced","technical"],tournament_id=tour["id"],
                tournament_match_id=fixture["id"])
    validate_tournament_segment(state,seg)
    record_result(state,seg,{"winner":seg.planned_winner_id,"crowd":60},"show-1")
    assert fixture["status"]=="complete"
    assert tour["rounds"][1][0]["status"]=="waiting"
    assert state.championships["men_world"]["holder_id"] is None
    with pytest.raises(ValueError,match="not ready"):
        validate_tournament_segment(state,seg)
    for m in tour["rounds"][0][1:]:
        seg=Segment("match",m["participants"],15,"Quarter Final",
                    planned_winner_id=m["participants"][0],
                    match_styles=["balanced","technical"],tournament_id=tour["id"],
                    tournament_match_id=m["id"])
        record_result(state,seg,{"winner":seg.planned_winner_id,"crowd":60},"show-1")
    assert all(m["status"]=="ready" for m in tour["rounds"][1])
    restored=restore_game(asdict(state))
    tour=restored.tournaments[tour["id"]]
    assert tour["rounds"][0][0]["winner_id"]==people[0]
    assert tour["rounds"][1][0]["participants"]==[people[0],people[2]]
    for m in tour["rounds"][1]:
        seg=Segment("match",m["participants"],15,"Semi Final",
                    planned_winner_id=m["participants"][0],
                    match_styles=["balanced","technical"],tournament_id=tour["id"],
                    tournament_match_id=m["id"])
        record_result(restored,seg,{"winner":seg.planned_winner_id,"crowd":66},"show-2")
    final=tour["rounds"][2][0]
    assert final["status"]=="ready"
    seg=Segment("match",final["participants"],20,"Final",planned_winner_id=final["participants"][1],
                match_styles=["balanced","technical"],tournament_id=tour["id"],
                tournament_match_id=final["id"])
    result={"winner":seg.planned_winner_id,"crowd":79}
    record_result(restored,seg,result,"show-3")
    assert restored.championships["men_world"]["holder_id"]==seg.planned_winner_id
    assert tour["status"]=="complete"
    assert result["championship"]["inaugural"] is True

def test_cannot_create_duplicate_competitions_or_mix_divisions(tmp_path):
    state=build_universe(tmp_path/"sources.db",add_independents=False)
    state.championships["men_world"]["holder_id"]=None
    men=[w.id for w in state.wrestlers.values() if w.company_id=="player" and w.division=="men"][:4]
    women=[w.id for w in state.wrestlers.values() if w.company_id=="player" and w.division=="women"]
    with pytest.raises(ValueError,match="division"):
        create_tournament(state,"men_world",men[:3]+women[:1])
    create_tournament(state,"men_world",men)
    with pytest.raises(ValueError,match="active"):
        create_tournament(state,"men_world",men)

def test_direct_three_and_four_way_title_rounds(tmp_path):
    state=build_universe(tmp_path/"sources.db",add_independents=False)
    state.championships["women_world"]["holder_id"]=None
    women=[w.id for w in state.wrestlers.values() if w.company_id=="player" and w.division=="women"][:4]
    t=create_tournament(state,"women_world",women[:3],"triple_threat")
    f=t["rounds"][0][0]
    assert f["match_format"]=="triple_threat"
    seg=Segment("match",women[:3],22,"Crowning Three Way",match_format="triple_threat",
                planned_winner_id=women[2],match_styles=["balanced","storytelling"],
                tournament_id=t["id"],tournament_match_id=f["id"])
    validate_tournament_segment(state,seg)
    record_result(state,seg,{"winner":women[2],"crowd":70},"show-1")
    assert state.championships["women_world"]["holder_id"]==women[2]
    state.championships["men_intercontinental"]["holder_id"]=None
    men=[w.id for w in state.wrestlers.values() if w.company_id=="player" and w.division=="men"][:4]
    t2=create_tournament(state,"men_intercontinental",men,"fatal_four_way")
    assert t2["rounds"][0][0]["match_format"]=="fatal_four_way"
