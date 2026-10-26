"""V0.9 acceptance coverage: titles, positions, promotion investment, action RNG, AI isolation."""
import copy
import json
from pathlib import Path
import pytest
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.game import book_show,simulate_show
from wrestling_sim.storage import save_game,load_game
from wrestling_sim.auto_narrative import auto_show


def sample_card(promo=12, defend=True):
    return [
      Segment('match',['steel','phoenix'],25,'Steel Faces Phoenix',storyline_id='steel-phoenix',
              planned_winner_id='steel',match_styles=['technical','storytelling'],
              promotion_effort=promo,championship_id='men_world' if defend else None),
      Segment('match',['vale','collins'],25,'Vale Faces Collins',storyline_id='vale-collins',
              planned_winner_id='collins',match_styles=['balanced','power'],promotion_effort=promo),
      Segment('confrontation',['steel','phoenix'],15,'The Challenge',storyline_id='steel-phoenix',
              promotion_effort=promo),
      Segment('interview',['cruz'],15,'Cruz on the Future',promotion_effort=promo),
      Segment('backstage',['collins'],20,'Behind the Curtain',promotion_effort=promo),
    ]


def test_three_titles_and_persisted_roster_tiers(tmp_path):
    s=new_game()
    assert set(s.championships)=={'men_world','men_intercontinental','women_world'}
    assert s.championships['women_world']['holder_id']=='vale'
    assert s.wrestlers['steel'].card_tier=='main_event'
    s.wrestlers['phoenix'].card_tier='mid_card'
    f=tmp_path/'save.json';save_game(s,f)
    restored=load_game(f)
    assert restored.championships==s.championships
    assert restored.wrestlers['phoenix'].card_tier=='mid_card'


def test_title_defense_and_change_impacts_relevance_and_revenue():
    s=new_game(seed=44)
    before=s.wrestlers['steel'].attributes['relevance']
    show=book_show(s,'Title Night',sample_card())
    result=simulate_show(s,show.id)
    belt=s.championships['men_world']
    assert belt['holder_id']=='steel' and belt['defenses']==1
    assert s.wrestlers['steel'].attributes['relevance']>before
    assert result['segments'][0]['championship']['belt_name']==belt['name']
    assert result['finances']['title_interest_revenue']>0
    assert result['finances']['promotion_spend']>0


def test_title_match_must_feature_champion():
    s=new_game()
    card=sample_card()
    card[0].wrestler_ids=['phoenix','knox'];card[0].storyline_id=None
    with pytest.raises(ValueError,match='champion'):
        book_show(s,'Invalid championship',card)


def test_title_transition_updates_lineage():
    s=new_game()
    card=sample_card();card[0].planned_winner_id='phoenix'
    show=book_show(s,'The Upset',card);simulate_show(s,show.id)
    belt=s.championships['men_world']
    assert belt['holder_id']=='phoenix'
    assert belt['lineage'][-1]['previous_holder_id']=='steel'
    assert belt['lineage'][-1]['change'] is True


def test_promotion_spend_does_not_improve_actual_match_skill():
    low=new_game(11);high=new_game(11)
    lowcard=sample_card(2,False);highcard=sample_card(25,False)
    r0=simulate_show(low,book_show(low,'A',lowcard).id)
    r1=simulate_show(high,book_show(high,'A',highcard).id)
    # Same skill/style/stamina but bigger advertising input.
    assert r0['segments'][0]['match_engine']['style_fit']==r1['segments'][0]['match_engine']['style_fit']
    assert r1['finances']['promotion_spend']>r0['finances']['promotion_spend']
    assert r1['segments'][0]['promotion_visibility']>r0['segments'][0]['promotion_visibility']


def test_action_rng_is_per_attempt_and_reproducible():
    a=new_game(77);b=new_game(77)
    s1=book_show(a,'Wrestling',sample_card());s2=book_show(b,'Wrestling',sample_card())
    r1=simulate_show(a,s1.id);r2=simulate_show(b,s2.id)
    assert r1['segments'][0]['action_rng']==r2['segments'][0]['action_rng']
    assert r1['segments'][0]['quality']==r2['segments'][0]['quality']
    for result in r1['segments']:
        for action in result['highlights']:
            if 'successful' in action:
                assert 0 <= action['rng_roll'] < 1
                assert 0 < action['success_chance'] < 1
                assert action['successful']==(action['rng_roll']<action['success_chance'])
        assert result['action_rng']['attempts']>=2


def test_ollama_partial_failure_recovers_fan_report_without_mutating_results(monkeypatch):
    s=new_game();show=book_show(s,'Show',sample_card());simulate_show(s,show.id)
    baseline=[(r['quality'],r['crowd'],r['winner']) for r in show.result['segments']]
    def generate(payload,schema,system_instruction=None):
        if 'highlights' in schema['properties']:
            raise ValueError('The large structured response was incomplete')
        if 'report' in schema['properties']:
            return {'report':'The audience welcomed the strong moments, but some fans questioned pacing and the main-event finish.'}
        raise ValueError('Unexpected call')
    monkeypatch.setattr('wrestling_sim.auto_narrative._generate',generate)
    monkeypatch.setattr('wrestling_sim.narrative._generate',generate)
    result=auto_show(s,show.id)
    assert result['source']=='partial'
    assert 'fan_report' in result['generated']
    assert show.result['fan_report']['source']=='ollama'
    assert baseline==[(r['quality'],r['crowd'],r['winner']) for r in show.result['segments']]
