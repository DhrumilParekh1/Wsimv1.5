from dataclasses import asdict
from fastapi.testclient import TestClient
from wrestling_sim.api import app, service
from wrestling_sim.game import book_show, simulate_show
from wrestling_sim.models import Segment
from wrestling_sim.starter import new_game
from wrestling_sim.storage import save_game, load_game


def test_save_load_round_trip(tmp_path):
    game = new_game(123)
    game.storylines['steel-phoenix'].hype = 92
    show = book_show(game, 'First Night', [Segment('promo', ['steel', 'phoenix'], 7, 'Promo', 'steel-phoenix')])
    simulate_show(game, show.id)
    save_game(game, tmp_path / 'save.json')
    restored = load_game(tmp_path / 'save.json')
    assert asdict(restored) == asdict(game)
    assert restored.shows[show.id].simulated
    assert restored.storylines['steel-phoenix'].history


def test_api_game_flow(tmp_path):
    old_path = service.path
    old_state = service.state
    try:
        service.path = tmp_path / 'api.json'
        service.state = new_game(2026)
        client = TestClient(app)
        assert client.get('/health').status_code == 200
        assert client.get('/wrestlers/phoenix').json()['ratings']['potential_ability'] > 0
        response = client.post('/shows/book', json={
            'name': 'The Debut',
            'segments': [{'kind': 'promo', 'title': 'The Warning',
                          'wrestler_ids': ['steel', 'phoenix'],
                          'duration': 6, 'storyline_id': 'steel-phoenix'}]
        })
        assert response.status_code == 200, response.text
        show_id = response.json()['id']
        report = client.post(f'/shows/{show_id}/simulate')
        assert report.status_code == 200
        assert len(report.json()['segments']) == 1
        assert client.post('/weeks/advance').status_code == 200
        assert service.path.exists()
        assert load_game(service.path).week == 2
    finally:
        service.path = old_path
        service.state = old_state


def test_api_bad_show_returns_400(tmp_path):
    old_path, old_state = service.path, service.state
    try:
        service.path = tmp_path / 'bad.json'
        service.state = new_game()
        response = TestClient(app).post('/shows/book', json={
            'name': 'Invalid', 'segments': [{'kind': 'match', 'title': 'Bad',
                                            'wrestler_ids': ['steel', 'storm'], 'duration': 12}]})
        assert response.status_code == 400
    finally:
        service.path, service.state = old_path, old_state
