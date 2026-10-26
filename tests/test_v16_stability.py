"""V1.6 regression tests for contextual owner requests and mandatory press."""
import pytest
from wrestling_sim.starter import new_game
from wrestling_sim.decisions import available_decisions, choose_option
from wrestling_sim.press_and_incidents import conference, answer_press
from wrestling_sim.game import advance_week, inbox_blockers


def test_no_arbitrary_weekly_spotlight_complaint():
    state = new_game()
    for wrestler in state.wrestlers.values():
        wrestler.morale = 20
        wrestler.owner_relationship = 20
        wrestler.wants_release = False
    assert not any(item['kind'] == 'locker_room' for item in available_decisions(state))


def test_complaint_requires_dissatisfaction_and_has_cooldown():
    state = new_game()
    wrestler = next(w for w in state.wrestlers.values()
                   if w.company_id == state.player_company_id)
    wrestler.morale = 4
    wrestler.owner_relationship = 5
    matches = [event for event in available_decisions(state)
               if event['kind'] == 'locker_room']
    assert matches
    choose_option(state, matches[0]['id'], 'listen')
    state.week += 1
    assert not any(event['kind'] == 'locker_room'
                   and event['wrestler_id'] == wrestler.id
                   for event in available_decisions(state))


def test_press_is_blocker_and_requires_all_questions():
    state = new_game()
    press = conference(state)
    assert press and not press['completed']
    assert any(entry['kind'] == 'press' for entry in inbox_blockers(state))
    # The backend must reject advance before any other state mutations.
    with pytest.raises(ValueError, match='show|Press Conference'):
        advance_week(state)
    for q in press['questions']:
        answer_press(state, q['id'], 'candid')
    assert press['completed']
    assert not any(entry['kind'] == 'press' for entry in inbox_blockers(state))
