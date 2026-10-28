"""Regression checks for standalone fan analysis and title-holder eligibility."""
import pytest

from wrestling_sim.report_analysis import analyze_segment
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.championships import check_title_match


def test_standalone_promo_analysis_never_claims_a_storyline():
    analysis=analyze_segment({
        "kind":"promo","quality":31.4,"crowd":32,
        "storyline_id":None,"audience":{"expected_quality":80,"satisfaction":31.9}
    })
    words=" ".join(analysis["positives"]).lower()
    assert "some storyline" not in words
    assert "ongoing show narrative" not in words
    assert "no ongoing rivalry" in words


def test_storyline_promo_keeps_storyline_analysis():
    analysis=analyze_segment({
        "kind":"promo","quality":31.4,"crowd":32,
        "storyline_id":"steel-phoenix",
        "audience":{"expected_quality":80,"satisfaction":31.9}
    })
    assert "storyline context" in " ".join(analysis["positives"]).lower()


def test_belt_needs_current_champion_as_participant():
    state=new_game()
    belt=state.championships["men_world"]
    title="men_world"
    good=Segment("match",["steel","phoenix"],20,"Title Match",
                 planned_winner_id="steel",championship_id=title)
    check_title_match(state,good)
    belt["holder_id"]=None
    with pytest.raises(ValueError,match="current champion"):
        check_title_match(state,good)
    belt["holder_id"]="steel"
    wrong=Segment("match",["phoenix","knox"],20,"Wrong Challenger",
                  planned_winner_id="phoenix",championship_id=title)
    with pytest.raises(ValueError,match="current champion"):
        check_title_match(state,wrong)
