"""Regression tests for browser dashboard and stateful narrative decisions."""
from dataclasses import asdict
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.api import app, service
from wrestling_sim.decisions import available_decisions, choose_option
from wrestling_sim.game import book_show, simulate_show, advance_week
from wrestling_sim.models import Segment
from wrestling_sim.starter import new_game
from wrestling_sim.storage import load_game, save_game


def test_owner_choices_change_persistent_state(tmp_path):
    world = new_game()
    events = available_decisions(world)
    assert {e['kind'] for e in events} == {'creative', 'locker_room'}
    initial = world.storylines['steel-phoenix'].hype
    result = choose_option(world, events[0]['id'], 'escalate')
    assert result['effects']['storyline_hype'] != 0
    assert world.storylines['steel-phoenix'].hype != initial
    assert events[0]['id'] in world.decisions
    assert len(available_decisions(world)) == len(events) - 1
    assert len(world.activity_log) == 1
    with pytest.raises(ValueError, match='already'):
        choose_option(world, events[0]['id'], 'escalate')
    save_game(world, tmp_path/'game.json')
    restored = load_game(tmp_path/'game.json')
    assert asdict(restored) == asdict(world)
    advance_week(restored)
    assert len(available_decisions(restored)) >= 2


def test_choices_validate_and_sponsor_costs():
    world = new_game()
    with pytest.raises(ValueError, match='Invalid decision option'):
        choose_option(world, available_decisions(world)[0]['id'], 'nonexistent')
    advance_week(world)
    sponsor = next(e for e in available_decisions(world) if e['kind'] == 'sponsors')
    cash_before = world.player_company.money
    outcome = choose_option(world, sponsor['id'], 'campaign')
    assert outcome['effects']['cash'] == -3500
    assert world.player_company.money == cash_before - 3500


def test_match_engine_breakdown_and_singles_limit():
    world = new_game()
    show = book_show(world, 'V2 Main Event', [Segment('match', ['steel', 'phoenix'], 18, 'Main event',
                                                       storyline_id='steel-phoenix', planned_winner_id='phoenix')])
    report = simulate_show(world, show.id)
    match = report['segments'][0]
    assert match['winner'] == 'phoenix'
    assert set(match['match_details']) == {'ring_execution', 'stamina_readiness', 'finish_credibility', 'execution_modifier'}
    assert -6 <= match['match_details']['execution_modifier'] <= 6
    assert 0 <= match['quality'] <= 100


def test_web_ui_endpoints_and_game_flow(tmp_path):
    old_path, old_state = service.path, service.state
    try:
        service.path = tmp_path / 'web_game.json'
        service.state = new_game(2026)
        client = TestClient(app)
        page = client.get('/')
        assert page.status_code == 200
        assert 'RINGSIDE' in page.text
        assert client.get('/assets/styles.css').status_code == 200
        assert client.get('/assets/app.js').status_code == 200
        assert client.get('/assets/portraits/phoenix.svg').status_code == 200
        before = client.get('/ui/state').json()
        assert before['year'] == 2026
        assert len(before['wrestlers']) >= 10
        assert before['decisions']
        decision = before['decisions'][0]
        response = client.post('/ui/choices',json={'event_id':decision['id'], 'option_id':decision['options'][0]['id']})
        assert response.status_code == 200
        assert client.post('/ui/choices',json={'event_id':decision['id'], 'option_id':decision['options'][0]['id']}).status_code == 400
        assert len(client.get('/ui/state').json()['decisions']) == len(before['decisions'])-1
        new_show = client.post('/shows/book',json={'name':'Broadcast One','segments':[
            {'kind':'match','title':'Steel vs Phoenix', 'duration':18, 'wrestler_ids':['steel','phoenix'],
             'planned_winner_id':'phoenix', 'storyline_id':'steel-phoenix'}]})
        assert new_show.status_code == 200, new_show.text
        show_id = new_show.json()['id']
        assert client.post(f'/shows/{show_id}/simulate').status_code == 200
        assert client.post('/weeks/advance').status_code == 200
        final = client.get('/ui/state').json()
        assert final['week'] == 2
        assert any(s['simulated'] for s in final['shows'])
        assert final['finance']
    finally:
        service.path, service.state = old_path, old_state
