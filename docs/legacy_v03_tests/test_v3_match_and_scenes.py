"""V0.3 acceptance tests: booking style, finishes, choices, commitments, old saves."""
from dataclasses import asdict
import json
import pytest
from fastapi.testclient import TestClient

from wrestling_sim.api import app, service
from wrestling_sim.game import advance_week, book_show, simulate_show
from wrestling_sim.models import Segment
from wrestling_sim.scenes import start_scene, choose_scene, scene_overview
from wrestling_sim.starter import new_game
from wrestling_sim.storage import save_game, load_game


def match(**kwargs):
    return Segment(kind='match', wrestler_ids=['steel', 'phoenix'], duration=20,
                   title='Showdown', storyline_id='steel-phoenix',
                   planned_winner_id='phoenix', **kwargs)


def test_styles_change_performance():
    a, b = new_game(), new_game()
    x = simulate_show(a, book_show(a, 'A', [match(match_style='technical')]).id)['segments'][0]
    y = simulate_show(b, book_show(b, 'A', [match(match_style='power')]).id)['segments'][0]
    assert x['match_engine']['style'] == 'technical'
    assert x['match_engine']['psychology'] >= 0
    assert x['match_engine']['style_fit'] != y['match_engine']['style_fit']
    assert x['quality'] != y['quality']
    assert len(x['match_engine']['beats']) == 3
    assert x['winner'] == 'phoenix'


def test_finish_has_distinct_fan_effects():
    a, b = new_game(), new_game()
    clean = simulate_show(a, book_show(a, 'A', [match(finish_type='clean')]).id)['segments'][0]
    dq = simulate_show(b, book_show(b, 'A', [match(finish_type='disqualification')]).id)['segments'][0]
    assert clean['fan_trust_delta'] > dq['fan_trust_delta']
    assert clean['crowd'] > dq['crowd']
    assert dq['match_engine']['finish'] == 'disqualification'


@pytest.mark.parametrize('kwargs', [
    {'match_style': 'made_up'}, {'finish_type': 'nope'},
    {'stipulation': 'fictional'}, {'intensity': 'max'},
    {'stipulation': 'no_disqualification', 'finish_type': 'disqualification'},
    {'stipulation': 'submission', 'finish_type': 'flash_pin'},
    {'stipulation': 'ironman', 'finish_type': 'time_limit_draw'},
])
def test_invalid_match_combo_raises(kwargs):
    with pytest.raises(ValueError):
        match(**kwargs)


def test_time_limit_draw_has_no_winner():
    world = new_game()
    seg = Segment('match', ['steel', 'phoenix'], 18, 'Limit', finish_type='time_limit_draw')
    report = simulate_show(world, book_show(world, 'Limit', [seg]).id)['segments'][0]
    assert report['winner'] is None
    assert 'time limit' in report['narrative']
    with pytest.raises(ValueError, match='draw'):
        match(finish_type='time_limit_draw')


def complete_scene(world, first='challenge', second='match'):
    start_scene(world, 'steel-phoenix')
    key = f'scene-{world.year}-{world.week}-steel-phoenix'
    choose_scene(world, key, first)
    return choose_scene(world, key, second)


def test_scene_branching_and_delivery(tmp_path):
    world = new_game()
    start_scene(world, 'steel-phoenix')
    key = 'scene-2026-1-steel-phoenix'
    assert scene_overview(world)[0]['step'] == 0
    with pytest.raises(ValueError, match='Invalid'):
        choose_scene(world, key, 'nonsense')
    step2 = choose_scene(world, key, 'challenge')
    assert step2['step'] == 1
    assert {'match', 'confrontation'} == {o['id'] for o in step2['options']}
    final = choose_scene(world, key, 'match')
    assert final['status'] == 'complete'
    with pytest.raises(ValueError, match='complete'):
        choose_scene(world, key, 'match')
    with pytest.raises(ValueError, match='already started'):
        start_scene(world, 'steel-phoenix')
    save_game(world, tmp_path/'campaign.json')
    recovered = load_game(tmp_path/'campaign.json')
    assert asdict(recovered) == asdict(world)
    assert recovered.storylines['steel-phoenix'].planned_beat['kind'] == 'match'
    report = simulate_show(recovered, book_show(recovered, 'Deliver', [match()]).id)
    assert report['segments'][0]['planned_beat_delivered'] is True
    assert recovered.storylines['steel-phoenix'].planned_beat['fulfilled'] is True
    advance_week(recovered)
    assert not any('Fans lose patience' in event for event in recovered.news)


def test_missed_promise_lowers_trust():
    world = new_game()
    complete_scene(world)
    initial_coherence = world.storylines['steel-phoenix'].coherence
    advance_week(world)
    assert world.week == 2
    advance_week(world)
    assert world.week == 3
    assert world.storylines['steel-phoenix'].planned_beat == {}
    assert world.storylines['steel-phoenix'].coherence < initial_coherence
    assert any('Fans lose patience' in event for event in world.news)


def test_v02_save_loads_without_v3_keys(tmp_path):
    world = new_game()
    payload = asdict(world)
    payload.pop('scenes', None)
    for story in payload['storylines'].values():
        story.pop('planned_beat', None)
    p = tmp_path/'old_save.json'
    p.write_text(json.dumps(payload), encoding='utf-8')
    restored = load_game(p)
    assert restored.scenes == {}
    assert restored.storylines['steel-phoenix'].planned_beat == {}
    assert restored.week == 1


def test_scene_api_and_match_api(tmp_path):
    old_state, old_path = service.state, service.path
    try:
        service.state, service.path = new_game(), tmp_path/'web.json'
        client = TestClient(app)
        before = client.get('/ui/state').json()
        assert before['scenes'][0]['status'] == 'not_started'
        response = client.post('/ui/scenes/start', json={'storyline_id':'steel-phoenix'})
        assert response.status_code == 200, response.text
        scene = response.json()
        response = client.post('/ui/scenes/choose',json={'scene_id':scene['id'],'option_id':'mind_games'})
        assert response.status_code == 200, response.text
        assert response.json()['step'] == 1
        response = client.post('/ui/scenes/choose',json={'scene_id':scene['id'],'option_id':'promo'})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == 'complete'
        assert client.post('/ui/scenes/choose',json={'scene_id':scene['id'],'option_id':'promo'}).status_code == 400
        book = client.post('/shows/book',json={'name':'PROMISED', 'segments':[{
            'kind':'promo','wrestler_ids':['steel','phoenix'],'duration':6,
            'title':'Promo promise','storyline_id':'steel-phoenix'}]})
        assert book.status_code == 200, book.text
        result = client.post(f"/shows/{book.json()['id']}/simulate")
        assert result.status_code == 200
        assert result.json()['segments'][0]['planned_beat_delivered']
        assert client.get('/assets/app.js').status_code == 200
        assert 'creativeView' in client.get('/assets/app.js').text
    finally:
        service.state, service.path = old_state, old_path
