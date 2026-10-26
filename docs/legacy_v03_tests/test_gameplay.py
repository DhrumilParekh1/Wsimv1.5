import pytest
from wrestling_sim.game import advance_week, book_show, create_storyline, offer_contract, simulate_show
from wrestling_sim.models import Segment
from wrestling_sim.ratings import rating_breakdown


def default_card():
    return [
        Segment('promo', ['steel', 'phoenix'], 7, 'Warning', 'steel-phoenix',
                20, None, 'slow_burn'),
        Segment('match', ['cruz', 'knox'], 15, 'Singles', None,
                18, 'cruz', 'advance'),
        Segment('confrontation', ['steel', 'phoenix'], 8, 'Confrontation', 'steel-phoenix',
                20, None, 'escalate'),
    ]


def test_show_advances_storyline_and_finances(world):
    initial_cash = world.player_company.money
    initial_hype = world.storylines['steel-phoenix'].hype
    show = book_show(world, 'First Light', default_card())
    report = simulate_show(world, show.id)
    assert 0 <= report['crowd'] <= 100
    assert 0 <= report['quality'] <= 100
    assert report['segments'][1]['winner'] == 'cruz'
    assert world.shows[show.id].simulated
    assert world.storylines['steel-phoenix'].hype != initial_hype
    assert world.player_company.money != initial_cash
    assert world.financial_history[-1]['reason'] == 'event'
    assert len(world.storylines['steel-phoenix'].history) == 2


def test_deterministic_simulation_with_same_seed(world):
    from wrestling_sim.starter import new_game
    another = new_game(world.seed)
    a = simulate_show(world, book_show(world, 'Light', default_card()).id)
    b = simulate_show(another, book_show(another, 'Light', default_card()).id)
    assert a == b


def test_cannot_book_other_company_wrestler(world):
    with pytest.raises(ValueError, match='not on your active roster'):
        book_show(world, 'Illicit', [Segment('promo', ['storm'], 5, 'Rival Promo')])


def test_one_match_per_wrestler_per_show(world):
    with pytest.raises(ValueError, match='one match'):
        book_show(world, 'Double Duty', [
            Segment('match', ['cruz', 'knox'], 10, 'One'),
            Segment('match', ['cruz', 'phoenix'], 10, 'Two'),
        ])


def test_prevent_old_show_advance(world):
    book_show(world, 'Pending', [Segment('promo', ['steel'], 5, 'Demand')])
    with pytest.raises(ValueError, match='Simulate'):
        advance_week(world)


def test_contract_opportunity(world):
    assert world.wrestlers['orbit'].company_id is None
    outcome = offer_contract(world, 'orbit', 100000, 52, 100)
    assert outcome['accepted']
    assert world.wrestlers['orbit'].company_id == 'player'
    assert world.wrestlers['orbit'].contract_weeks == 52


def test_exclusive_contract_protected(world):
    with pytest.raises(ValueError, match='exclusive'):
        offer_contract(world, 'storm', 20000, 52)


def test_time_and_weekly_costs(world):
    initial_money = world.player_company.money
    result = advance_week(world)
    assert world.week == 2
    assert world.player_company.money == initial_money - result['payroll'] - result['fixed_costs']
    assert world.wrestlers['steel'].contract_weeks == 21


def test_storyline_member_validation(world):
    with pytest.raises(ValueError, match='Storyline participants'):
        create_storyline(world, 'Imposter', ['storm', 'phoenix'])
    story = create_storyline(world, 'New Rivalry', ['vale', 'collins'])
    with pytest.raises(ValueError, match='must belong'):
        book_show(world, 'Wrong Card', [Segment('promo', ['steel'], 5, 'Wrong', story.id)])


def test_wrestler_progression_changes_stats_slowly(world):
    before = world.wrestlers['phoenix'].attributes['workrate']
    advance_week(world)
    after = world.wrestlers['phoenix'].attributes['workrate']
    assert abs(after - before) < .1


def test_potential_affected_by_runway(world):
    w = world.wrestlers['phoenix']
    pa = rating_breakdown(w)['potential_ability']
    w.development_runway = .05
    assert rating_breakdown(w)['potential_ability'] < pa
