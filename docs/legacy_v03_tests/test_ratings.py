import copy
import pytest
from wrestling_sim.models import Wrestler
from wrestling_sim.ratings import rating_breakdown
from wrestling_sim.weights import ALL_ATTRIBUTES


def test_four_scores_in_range(world):
    for wrestler in world.wrestlers.values():
        result = rating_breakdown(wrestler)
        for value in result.values():
            assert 0 <= value <= 100
        assert result['potential_ability'] >= result['current_ability']


def test_all_25_yields_maximum_rating():
    attrs = dict.fromkeys(ALL_ATTRIBUTES, 25.0)
    attrs['controversy_risk'] = 0.0
    w = Wrestler('perfect', 'Perfect Fictional Performer', 25, None, attrs,
                growth_aptitude=1, development_runway=1)
    scores = rating_breakdown(w)
    for field in ['match', 'promo', 'commercial', 'backstage', 'current_ability', 'potential_ability', 'market_value']:
        assert scores[field] == pytest.approx(100)


def test_zero_attributes_valid_and_low_rating():
    attrs = dict.fromkeys(ALL_ATTRIBUTES, 0.)
    attrs['controversy_risk'] = 25
    w = Wrestler('rookie', 'Rookie', 18, None, attrs,
                growth_aptitude=0, development_runway=1, availability=0)
    scores = rating_breakdown(w)
    assert scores['current_ability'] == 0
    assert scores['potential_ability'] == 0
    assert scores['market_value'] == 0


def test_role_switch_changes_promo_without_changing_skills(world):
    w = copy.deepcopy(world.wrestlers['steel'])
    heel = rating_breakdown(w)['promo']
    w.role = 'face'
    face = rating_breakdown(w)['promo']
    assert heel > face


def test_proficiency_changes_when_role_switches(world):
    w = copy.deepcopy(world.wrestlers['steel'])
    baseline = rating_breakdown(w)['current_ability']
    w.attributes['heel'] = 5
    assert rating_breakdown(w)['current_ability'] < baseline


def test_fatigue_not_baked_into_ca(world):
    w = copy.deepcopy(world.wrestlers['phoenix'])
    ca = rating_breakdown(w)['current_ability']
    w.fatigue = 25
    assert rating_breakdown(w)['current_ability'] == ca
