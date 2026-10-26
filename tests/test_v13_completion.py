"""Regression coverage for V1.3 UI/engine fixes and SQLite persistence."""
import tempfile
from pathlib import Path

import pytest
from wrestling_sim.starter import new_game
from wrestling_sim.database import save_database, load_database
from wrestling_sim.service import GameService
from wrestling_sim.industry import declare_interest, process_recruitment_enquiries, acknowledge_recruitment_report
from wrestling_sim.movesets import default_moveset, validate_moveset
from wrestling_sim.match_engine import STYLE_WEIGHTS
from wrestling_sim.report_analysis import analyze_segment, consistent_ai_reaction


def test_db_roundtrip_and_indexes(tmp_path):
    state = new_game(77)
    path=tmp_path/'save.db'
    save_database(state, path)
    assert path.exists()
    restored=load_database(path)
    assert restored.week==state.week and len(restored.wrestlers)==len(state.wrestlers)
    import sqlite3
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM wrestlers').fetchone()[0]==len(state.wrestlers)
        assert db.execute('SELECT count(*) FROM storylines').fetchone()[0]==len(state.storylines)


def test_json_to_sqlite_migration(tmp_path):
    from wrestling_sim.storage import save_game
    state=new_game(41)
    save_game(state,tmp_path/'game.json')
    restored=GameService(tmp_path/'game.db')
    assert restored.state.seed==41
    assert (tmp_path/'game.json').exists()
    assert (tmp_path/'game.db').exists()


@pytest.mark.parametrize('style', list(STYLE_WEIGHTS))
def test_style_weights_normalized(style):
    assert abs(sum(STYLE_WEIGHTS[style].values())-1)<1e-8


def test_moveset_is_compact_and_one_finisher():
    for who in ['vale','phoenix','steel','cruz']:
        moves=default_moveset(who)
        validate_moveset(moves)
        assert len([x for x in moves if not x.get('signature')])==5
        assert sum(bool(x['finisher']) for x in moves)==1
        assert 1<=sum(bool(x.get('signature')) for x in moves)<=3


def test_delayed_recruitment_and_public_posts():
    state=new_game(404)
    from wrestling_sim.world import bootstrap_world
    bootstrap_world(state)
    external=next(w for w in state.wrestlers.values() if w.company_id not in (None,state.player_company_id) and w.discovery_tier in ('known','regional'))
    before=len(state.social_posts)
    interest=declare_interest(state,external.id,public=True)
    assert interest['status']=='pending'
    assert len(state.social_posts)==before+1
    assert not process_recruitment_enquiries(state)
    state.week+=1
    updates=process_recruitment_enquiries(state)
    assert updates and interest['status']=='reported'
    assert interest['result']['contract_weeks']==external.contract_weeks
    acknowledged=acknowledge_recruitment_report(state,interest['key'])
    assert acknowledged['status']=='reviewed'


def test_ollama_mixed_tone_guard():
    segment={'title':'The Showdown','kind':'match','quality':51.6,'crowd':56.6,
        'audience':{'expected_quality':78.,'satisfaction':48.6,'fatigue':0},
        'match_details':{'ring_execution':69.3},
        'match_engine':{'stamina_readiness':43.8,'finish_satisfaction':71.3}}
    info=analyze_segment(segment)
    assert info['satisfaction_gap'] == -29.4
    assert info['sentiment']=='negative'
    assert not consistent_ai_reaction('The match was an instant classic for the ages!',info)
    assert consistent_ai_reaction('There were solid moments, but the match disappointed fans.',info)
