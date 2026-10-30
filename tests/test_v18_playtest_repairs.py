"""V1.8 playtest acceptance checks, all offline."""
import random
from pathlib import Path
import pytest

from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.press_and_incidents import conference, answer_press
from wrestling_sim.real_universe import build_universe
from wrestling_sim.company_creation import create_company, is_eligible_for_company_creation, TIERS
from wrestling_sim.game import book_show
from wrestling_sim.efficient_narrative import _only_segment_people
from wrestling_sim.highlights import generate_segment_highlights


@pytest.mark.parametrize("tier,count,money,minutes", [
    ("indie",1,75_000,45),("startup",2,400_000,60),
    ("juggernaut",3,2_500_000,90)
])
def test_custom_company_creation_drafts_two_divisions(tmp_path,tier,count,money,minutes):
    start=build_universe(tmp_path/"people.db",add_independents=False)
    assert is_eligible_for_company_creation(start)
    men=[w.id for w in start.wrestlers.values() if w.company_id=="player" and w.division=="men"][:count]
    women=[w.id for w in start.wrestlers.values() if w.company_id=="player" and w.division=="women"][:count]
    created=create_company(start,"Test Promotion",tier,men,women)
    assert created.player_company.name=="Test Promotion"
    assert created.player_company.money==money
    assert created.player_company.show_minutes==minutes
    assert "wwe" in created.companies and created.companies["wwe"].name=="WWE"
    assert len(created.companies)==5
    assert all(created.wrestlers[wid].company_id=="player" for wid in men+women)
    assert not is_eligible_for_company_creation(created)
    assert created.championships["men_world"]["holder_id"] is None
    assert start.player_company.name=="WWE"


def test_indie_broadcast_can_book_solo_promo_for_both_divisions(tmp_path):
    start=build_universe(tmp_path/"people.db",add_independents=False)
    man=next(w.id for w in start.wrestlers.values() if w.company_id=="player" and w.division=="men")
    woman=next(w.id for w in start.wrestlers.values() if w.company_id=="player" and w.division=="women")
    state=create_company(start,"Small Local Wrestling","indie",[man],[woman])
    show=book_show(state,"First Event",[
        Segment("promo",[man],25,"Men's Showcase",promo_topic="ambitions"),
        Segment("promo",[woman],20,"Women's Showcase",promo_topic="address_fans"),
    ],duration=45)
    assert show.duration==45
    assert len(show.segments)==2


@pytest.mark.parametrize("choice",["neutral","candid","back"])
def test_press_feedback_is_non_numeric_and_neutral_is_zero(choice):
    state=new_game()
    session=conference(state)
    question=session["questions"][0]
    answer_press(state,question["id"],choice)
    assert "changed fan trust by" not in question["outcome"]
    assert isinstance(question["effects"]["fan_trust"],float)
    if choice=="neutral":
        assert question["effects"]["fan_trust"]==0.0
        assert question["effects"]["owner_relationship"]==0.0
        assert question["effects"]["sponsor_interest"]==0


def test_title_promo_eligibility_server_side():
    state=new_game()
    nonchamp=next(w.id for w in state.wrestlers.values() if w.company_id=="player" and w.division=="men" and all(b["holder_id"]!=w.id for b in state.championships.values()))
    invalid=Segment("promo",[nonchamp],30,"Claim Championship",promo_topic="open_challenge")
    valid=Segment("promo",["steel"],12,"Champion Addresses Fans",promo_topic="title_reign")
    # Champion validation triggers during book_show, before saving.
    with pytest.raises(ValueError,match="reigning champion"):
        book_show(state,"Invalid challenge",[
            invalid,Segment("promo",["vale"],20,"Women"),
            Segment("match",["steel","phoenix"],50,"Men",planned_winner_id="steel")
        ],duration=120)
    assert valid.promo_topic=="title_reign"


def test_solo_promo_topic_generates_specific_beats():
    state=new_game()
    seg=Segment("promo",["steel"],10,"A New Era",promo_topic="ambitions")
    beats=generate_segment_highlights(state,seg,random.Random(4))
    assert beats
    assert all("Alex Phoenix" not in b["text"] for b in beats)


def test_ollama_isolation_rejects_other_named_wrestlers(tmp_path):
    state=build_universe(tmp_path/"people.db",add_independents=False)
    seg={"participants":["rw_rhearipley","rw_beckylynch"]}
    assert _only_segment_people("Rhea Ripley addresses Becky Lynch during the promo.",seg,state)
    assert not _only_segment_people("Cody Rhodes made that promo feel dull.",seg,state)


def test_promo_interruption_requires_two():
    with pytest.raises(ValueError,match="interrupted promo"):
        Segment("promo",["steel"],10,"Wrong Solo Interruption",promo_interrupt=True)
    assert Segment("promo",["steel","phoenix"],10,"Interrupting Promo",promo_interrupt=True).promo_interrupt
