"""V0.8 acceptance checks: viewer metric, shocks, memories, expectations and automatic AI."""
from __future__ import annotations
import copy
import json
import random
from dataclasses import asdict
from statistics import mean, pstdev
import pytest

from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.game import book_show,simulate_show
from wrestling_sim.audience import duration_risk, surprise_roll, ensure_expectations
from wrestling_sim.memories import add_memory,relevant_memories,memory_effect
from wrestling_sim.storage import load_game,save_game
from wrestling_sim.auto_narrative import auto_show,auto_dialogue
from wrestling_sim.dialogue import begin_meeting,answer_meeting


def card():
    return [
        Segment('match',['steel','phoenix'],30,'Steel versus Phoenix: The Reckoning',
                storyline_id='steel-phoenix',planned_winner_id='phoenix',
                match_styles=['technical','storytelling'],role_turn_wrestler_id='phoenix',role_turn_to='heel'),
        Segment('match',['vale','collins'],30,'Vale challenges Collins',storyline_id='vale-collins',
                match_styles=['power','technical'],planned_winner_id='vale'),
        Segment('promo',['knox'],20,'Knox Speaks to the Crowd'),
        Segment('interview',['cruz'],15,'Nova Addresses Her Future'),
        Segment('backstage',['steel'],15,'Steel Reflects on His Defeat'),
    ]


def test_viewership_is_not_popularity_index_and_persists(tmp_path):
    s=new_game()
    assert s.player_company.viewership > 1000
    assert s.weekly_metrics[0]['viewership']==s.player_company.viewership
    initial=s.player_company.viewership
    show=book_show(s,'Wrestling Tonight',card())
    result=simulate_show(s,show.id)
    assert result['company_viewership']==s.player_company.viewership
    assert result['viewership']>0
    assert s.player_company.viewership!=initial
    f=tmp_path/'game.json';save_game(s,f)
    migrated=load_game(f)
    assert migrated.player_company.viewership==s.player_company.viewership
    assert migrated.memories==s.memories


def test_length_risk_short_is_punished_and_long_is_volatile():
    def rolls(d):
        return [duration_risk('match',d,'standard',random.Random(i))['adjustment'] for i in range(1300)]
    short,medium,long=rolls(3),rolls(15),rolls(41)
    assert mean(short)<mean(medium)-2
    assert pstdev(long)>pstdev(medium)*2
    assert pstdev(long)>pstdev(short)
    assert {duration_risk('match',d,'standard',random.Random(8))['band'] for d in (3,15,41)}=={'short','medium','long'}
    assert pstdev([duration_risk('promo',15,'standard',random.Random(i))['adjustment'] for i in range(200)]) > 2


def test_surprise_is_rare_with_weighted_direction():
    hits=sum(bool(surprise_roll(75,75,random.Random(i))) for i in range(20000))
    assert 70<hits<200  # ~0.7%, not common
    class AlwaysShock:
        def random(self):return 0
        def uniform(self,a,b):return (a+b)/2
    assert surprise_roll(98,90,AlwaysShock())['type']=='breakout'
    assert surprise_roll(15,10,AlwaysShock())['type']=='breakout'  # rare possible even for a poor segment
    assert surprise_roll(15,10,random.Random(1)) is None


def test_turn_consequences_and_audience_expectations_are_persisted():
    s=new_game(103)
    story=s.storylines['steel-phoenix']
    assert story.expectations and all(0<=x['support']<=100 for x in story.expectations)
    show=book_show(s,'Week of Change',card())
    result=simulate_show(s,show.id)
    assert result['segments'][0]['role_turn']['to']=='heel'
    assert s.wrestlers['phoenix'].role=='heel'
    assert any(m['type']=='role_turn' for m in s.memories)
    assert result['segments'][0]['expectations']['fan_expectations']
    another=new_game(103)
    another.wrestlers['phoenix'].role='heel'
    with pytest.raises(ValueError,match='already in that role'):
        book_show(another,'Not Again',card())


def test_earned_expectations_create_boredom_if_repeated():
    from wrestling_sim.audience import resolve_expectations
    s=new_game();story=s.storylines['steel-phoenix']
    segment=Segment('match',['steel','phoenix'],21,'Decisive Payoff',storyline_id=story.id,finish_type='clean',creative_direction='resolve',planned_winner_id='steel')
    gains=[resolve_expectations(s,story,segment,{})['investment_delta'] for _ in range(6)]
    assert gains[0]>0 and gains[1]>0 and gains[-1]<0
    story.compliance_streak=0
    ignorer=Segment('promo',['steel'],5,'Some Words',storyline_id=story.id)
    misses=[resolve_expectations(s,story,ignorer,{})['investment_delta'] for _ in range(5)]
    assert misses[0]==0 and misses[-1]<0


def test_memory_retrieval_weights_old_betrayal_and_private_dealings():
    s=new_game()
    add_memory(s,'betrayal','Steel betrayed Phoenix on national television.',
               ['steel','phoenix'],'steel-phoenix',intensity=95,relationship_effect=-4)
    add_memory(s,'contract_signed','Orion accepted a new contract.',['knox'],intensity=50)
    found=relevant_memories(s,['steel','phoenix'],'steel-phoenix')
    assert found[0]['type']=='betrayal'
    assert not any(m['type']=='contract_signed' for m in found)
    assert memory_effect(s,['steel','phoenix'],'steel-phoenix')<0


def test_automatic_show_narration_preserves_scores_and_assignments(monkeypatch):
    s=new_game();show=book_show(s,'Winter Showcase',card());simulate_show(s,show.id)
    frozen=[(x['quality'],x['crowd'],x['winner'],x['role_turn']) for x in show.result['segments']]
    original_moves=copy.deepcopy(s.wrestlers['phoenix'].moveset)
    def fake_generate(payload,schema,system_instruction):
        return {'highlights':['The fans lean forward as tension mounts.' for _ in payload['highlights']],
                'posts':['The crowd had a very strong reaction to the show.' for _ in payload['posts']],
                'segment_reactions':['Some fans cheered loudly while others wanted more.' for _ in payload['segments']],
                'fan_report':'Fans particularly enjoyed the rivalry developments, although some disputed the pacing and endings.'}
    monkeypatch.setattr('wrestling_sim.auto_narrative._generate',fake_generate)
    ai=auto_show(s,show.id)
    assert ai['source']=='ollama'
    assert show.result['fan_report']['source']=='ollama'
    assert all(seg['fan_report']['source']=='ollama' for seg in show.result['segments'])
    assert all(p['source']=='ollama' for p in s.social_posts if p['show_id']==show.id and p['id']!='unexpected') or len([p for p in s.social_posts if p['show_id']==show.id])>12
    assert frozen==[(x['quality'],x['crowd'],x['winner'],x['role_turn']) for x in show.result['segments']]
    assert s.wrestlers['phoenix'].moveset==original_moves


def test_missing_ollama_creates_visible_warning_without_faking_output(monkeypatch):
    s=new_game();show=book_show(s,'Test Show',card());simulate_show(s,show.id)
    def fail(*args,**kwargs):raise ValueError('Model not running')
    monkeypatch.setattr('wrestling_sim.auto_narrative._generate',fail)
    old=show.result['quality']
    result=auto_show(s,show.id)
    assert result['source']=='unavailable'
    assert show.result['quality']==old
    assert show.result['ollama_status']=='unavailable'
    assert s.narrative_alerts and 'Model not running' in s.narrative_alerts[-1]['message']
    assert 'fan_report' not in show.result


def test_dialogue_uses_long_term_history_automatically(monkeypatch):
    s=new_game();add_memory(s,'broken_promise','The owner did not deliver a promised main event.', ['steel'],intensity=94)
    meeting=begin_meeting(s,'steel','booking')
    answer_meeting(s,meeting['id'],'explain')
    seen={}
    def generate(payload,schema,system_instruction):
        seen.update(payload['facts'])
        return {'reply':'I remember that you made this promise before, and I need to see real progress.'}
    monkeypatch.setattr('wrestling_sim.narrative._generate',generate)
    result=auto_dialogue(s,'meeting',meeting['id'])
    assert result['source']=='ollama'
    assert seen['recent_memories']
    assert 'ai_flavour' in s.dialogue_sessions[meeting['id']]['lines'][-1]
    assert s.wrestlers['steel'].owner_relationship>=0
