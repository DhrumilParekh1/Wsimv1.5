"""Regression tests for real promotional money, creative maturity and AI isolation."""
from __future__ import annotations
import copy
import time
from pathlib import Path
from wrestling_sim.models import Segment
from wrestling_sim.starter import new_game
from wrestling_sim.creative_logic import evaluate_direction
from wrestling_sim.game import book_show, simulate_show
from wrestling_sim.marketing import marketing_impact,segment_spend
from wrestling_sim.press_and_incidents import ensure_incidents,answer_incident
from wrestling_sim.efficient_narrative import auto_show_fast
from wrestling_sim.narration_jobs import queue,status
from wrestling_sim.service import GameService
from test_v09_titles_promotion_rng_ai import sample_card


def test_creative_direction_matters_to_hype_and_relevance():
    s=new_game();story=s.storylines['steel-phoenix'];story.history.clear()
    rushed=evaluate_direction(story,'resolve',65)
    assert rushed['trust']<0 and rushed['relevance']<0
    story.history=[{'week':i,'direction':'advance'} for i in range(1,9)]
    story.fan_investment=90;story.coherence=90
    mature=evaluate_direction(story,'resolve',75)
    assert mature['trust']>rushed['trust']
    story.history=[{'week':i,'direction':'escalate'} for i in range(1,6)]
    story.escalation_level=7
    stale=evaluate_direction(story,'escalate',70)
    assert stale['hype']<0 and stale['trust']<0


def test_advertising_dollars_affordability_and_diminishing_returns():
    s=new_game()
    a=Segment('match',['steel','phoenix'],20,'Test A',planned_winner_id='steel',promotion_budget=10000)
    b=Segment('match',['steel','phoenix'],20,'Test B',planned_winner_id='steel',promotion_budget=100000)
    assert segment_spend(a)==10000 and segment_spend(b)==100000
    assert 0<marketing_impact(s,a)<marketing_impact(s,b)
    assert marketing_impact(s,b)<10*marketing_impact(s,a)
    s.player_company.money=100
    items=sample_card()
    items[0].promotion_budget=1000
    for x in items[1:]:x.promotion_budget=0
    import pytest
    with pytest.raises(ValueError,match='Insufficient funds'):
        book_show(s,'Too Expensive',items)


def test_event_director_prevents_same_wrestler_weekly_collision():
    s=new_game();s.incidents=[]
    incidents=ensure_incidents(s)
    assert len(incidents)==2
    ids=[wid for incident in incidents for wid in incident['wrestler_ids']]
    assert len(ids)==len(set(ids))
    answer_incident(s,incidents[0]['id'],'mediate')
    assert s.incidents[0]['status']=='resolved'
    assert s.incidents[0]['resolution']['decision']
    assert s.incidents[0]['result']


def test_compact_ollama_requests_keep_score_immutable(monkeypatch):
    s=new_game();show=book_show(s,'Test',sample_card());simulate_show(s,show.id)
    score=copy.deepcopy([(x['quality'],x['crowd'],x['winner']) for x in show.result['segments']])
    types=[]
    def fake_generate(payload,schema,system_instruction=None):
        fields=schema['properties'];types.append(tuple(fields))
        if 'report' in fields:return {'report':'The crowd enjoyed several developments, although the pacing of some segments divided fans.'}
        if 'posts' in fields:return {'posts':['A fascinating show with plenty to discuss after the ending.' for _ in payload['posts']]}
        if 'commentary' in fields:return {'commentary':['A dramatic moment held the attention of the entire audience.' for _ in payload['segments']],
                                          'reactions':['Fans reacted strongly and debated the segment afterwards.' for _ in payload['segments']]}
        raise ValueError('Unknown request')
    monkeypatch.setattr('wrestling_sim.efficient_narrative._generate',fake_generate)
    result=auto_show_fast(s,show.id)
    assert result['source']=='ollama'
    assert len(types)>2
    assert score==[(x['quality'],x['crowd'],x['winner']) for x in show.result['segments']]
    assert show.result['fan_report']['source']=='ollama'


def test_async_narration_saves_game_without_waiting_for_model(tmp_path,monkeypatch):
    import wrestling_sim.narration_jobs as jobs
    import threading
    service=GameService(tmp_path/'game.json')
    show=book_show(service.state,'Show',sample_card())
    simulate_show(service.state,show.id)
    service.save()
    event=threading.Event()
    def fake_auto(state,show_id,progress):
        progress('Generating fan posts')
        event.wait(timeout=3)
        state.shows[show_id].result['fan_report']={'text':'The local audience was enthusiastic about this show.','source':'ollama'}
        return {'source':'ollama'}
    monkeypatch.setattr(jobs,'auto_show_fast',fake_auto)
    start=time.monotonic();queued=queue(service,show.id)
    assert time.monotonic()-start <1.0
    assert queued['status'] in ('queued','running')
    assert (tmp_path/'game.json').exists()
    event.set()
    for _ in range(100):
        if status(show.id,service)['status']=='completed':break
        time.sleep(.02)
    assert status(show.id,service)['status']=='completed'
    assert service.state.shows[show.id].result['fan_report']['source']=='ollama'
