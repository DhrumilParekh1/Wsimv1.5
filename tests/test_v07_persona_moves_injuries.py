"""V0.7 regression tests for movesets, recovery, and Ollama's text-only boundary."""
from __future__ import annotations
from dataclasses import asdict
import json
import random
import pytest
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.simulation import simulate_segment
from wrestling_sim.game import book_show, simulate_show
from wrestling_sim.movesets import validate_moveset
from wrestling_sim.injuries import injury_probability, roll_injury, advance_recovery
from wrestling_sim.storage import load_game
from wrestling_sim.dialogue import begin_meeting,answer_meeting,begin_contract,answer_contract
from wrestling_sim.narrative import enhance_dialogue, enhance_highlights


def test_moves_are_from_each_wrestlers_assigned_library():
    state=new_game(132)
    segment=Segment('match',['steel','phoenix'],24,'A Technical Match',
                    match_styles=['technical','high_flying'], planned_winner_id='phoenix')
    outcome=simulate_segment(state,segment,random.Random(2),0)
    assert outcome['highlights']==outcome['match_engine']['highlights']
    assert outcome['highlights'][-1]['move'] in [m['name'] for m in state.wrestlers['phoenix'].moveset]
    for beat in outcome['highlights']:
        if beat['move']:
            assert beat['move'] in {m['name'] for m in state.wrestlers[beat['performer_id']].moveset}


def test_promos_backstage_and_interviews_generate_multiple_chronological_beats():
    state=new_game()
    for kind in ('promo','backstage','interview','confrontation','betrayal','return','contract_signing'):
        s=Segment(kind,['steel','phoenix'],8,f'{kind} scene',storyline_id='steel-phoenix')
        result=simulate_segment(state,s,random.Random(3),0)
        assert len(result['highlights'])>=2
        assert [x['minute'] for x in result['highlights']]==sorted(x['minute'] for x in result['highlights'])
        assert all(x['performer_id'] in s.wrestler_ids for x in result['highlights'])


def test_injury_risk_is_bounded_and_responds_to_load_and_proneness():
    s=new_game(); w=s.wrestlers['steel']
    standard=Segment('match',['steel','phoenix'],15,'Standard',planned_winner_id='steel')
    intense=Segment('match',['steel','phoenix'],45,'Extreme',stipulation='extreme',intensity='high',planned_winner_id='steel')
    w.attributes['injury_proneness']=0
    low=injury_probability(w,standard)
    w.attributes['injury_proneness']=25
    high=injury_probability(w,intense)
    assert 0<low<high<=.10
    assert injury_probability(w,Segment('promo',['steel'],5,'Speech'))==0
    assert injury_probability(w,Segment('promo',['steel'],5,'Brawl',promo_brawl=True))<high


class FixedRNG:
    def __init__(self,choice):self.choice=choice
    def random(self):return next(self.choice)
    def randint(self,low,high):return high


def test_short_and_long_injury_bands_and_complete_weekly_recovery(monkeypatch):
    state=new_game();w=state.wrestlers['steel']
    segment=Segment('match',['steel','phoenix'],30,'Main Event',planned_winner_id='steel')
    monkeypatch.setattr('wrestling_sim.injuries.injury_probability',lambda w,s:.99)
    first=roll_injury(state,w,segment,FixedRNG(iter([0,.20])))
    assert first['severity']=='short' and first['weeks_remaining']==3
    assert w.injury_history[-1]['weeks_remaining']==3
    with pytest.raises(ValueError,match='injured'):
        book_show(state,'An Ineligible Card',[Segment('match',['steel','phoenix'],40,'Main',planned_winner_id='steel')]+[
            Segment('match',['vale','collins'],40,'Women',storyline_id='vale-collins',planned_winner_id='vale'),
            Segment('promo',['knox'],25,'Promo')])
    for _ in range(2):
        assert advance_recovery(state)==[]
    assert w.injury['weeks_remaining']==1
    assert advance_recovery(state) and w.injury is None
    second=roll_injury(state,w,segment,FixedRNG(iter([0,.99])))
    assert second['severity']=='long' and second['weeks_remaining']==52


def test_legacy_save_migrates_new_fields_without_changing_old_ratings(tmp_path):
    state=new_game();from wrestling_sim.ratings import rating_breakdown
    before=rating_breakdown(state.wrestlers['steel'])['current_ability']
    data=asdict(state)
    for w in data['wrestlers'].values():
        w['attributes'].pop('injury_proneness')
        w.pop('moveset');w.pop('injury');w.pop('injury_history')
    filename=tmp_path/'legacy-v06.json'
    filename.write_text(json.dumps(data),encoding='utf-8')
    restored=load_game(filename)
    w=restored.wrestlers['steel']
    assert w.attributes['injury_proneness']==9.0
    assert w.moveset and w.injury is None
    assert rating_breakdown(w)['current_ability']==before


def test_move_list_validation_rejects_invalid_data():
    with pytest.raises(ValueError):validate_moveset([{'name':'test','style':'technical','finisher':False}])
    with pytest.raises(ValueError):validate_moveset([{'name':'test','style':'fictional','finisher':False}]*3)


def test_ollama_meeting_voice_keeps_original_effects(monkeypatch):
    s=new_game();meeting=begin_meeting(s,'vale','booking')
    answer_meeting(s,meeting['id'],'explain')
    previous=asdict(s.wrestlers['vale'])
    original=s.dialogue_sessions[meeting['id']]['lines'][-1]['text']
    def fake(payload,schema,system_instruction):
        assert payload['facts']['personality']=='independent'
        return {'reply':'I hear what you are saying, but I still need to make my own path.'}
    monkeypatch.setattr('wrestling_sim.narrative._generate',fake)
    result=enhance_dialogue(s,'meeting',meeting['id'])
    assert result['immutable_outcome']
    assert asdict(s.wrestlers['vale'])==previous
    assert s.dialogue_sessions[meeting['id']]['lines'][-1]['text']==original
    assert s.dialogue_sessions[meeting['id']]['lines'][-1]['ai_flavour']==result['text']


def test_ollama_contract_voice_cannot_change_terms(monkeypatch):
    s=new_game();session=begin_contract(s,'steel')
    result=answer_contract(s,session['id'],'offer',salary=1,weeks=52)
    assert result['history'][-1]['actor']=='Marcus Steel'
    before=(s.contract_sessions[session['id']]['asking_salary'],
            s.wrestlers['steel'].owner_relationship,s.player_company.money)
    monkeypatch.setattr('wrestling_sim.narrative._generate',lambda p,sc,system_instruction:{'reply':'That is not a proposal I can accept right now.'})
    answer=enhance_dialogue(s,'contract',session['id'])
    assert answer['immutable_outcome']
    assert before==(s.contract_sessions[session['id']]['asking_salary'],
                    s.wrestlers['steel'].owner_relationship,s.player_company.money)


def test_ollama_highlight_atmosphere_never_changes_beats_and_is_all_or_nothing(monkeypatch):
    s=new_game();segments=[Segment('match',['steel','phoenix'],40,'Main Event',
                                    match_styles=['technical','storytelling'],planned_winner_id='phoenix',
                                    storyline_id='steel-phoenix'),
                           Segment('promo',['steel','phoenix'],20,'Confrontation',storyline_id='steel-phoenix'),
                           Segment('match',['vale','collins'],40,'Women Main Event',storyline_id='vale-collins',planned_winner_id='vale')]
    sh=book_show(s,'Weekly',segments)
    simulate_show(s,sh.id)
    score=s.shows[sh.id].result['quality'];initial_cash=s.player_company.money
    original=[[(b['minute'],b['text'],b['move']) for b in seg['highlights']] for seg in sh.result['segments']]
    monkeypatch.setattr('wrestling_sim.narrative._generate',lambda p,sc,system_instruction:
                        {'reactions':['The crowd feels the tension growing with each exchange.']*len(p['canonical_highlights'])})
    for index in range(3):
        answer=enhance_highlights(s,sh.id,index)
        assert answer['immutable_outcome']
    assert score==sh.result['quality'] and s.player_company.money==initial_cash
    assert original==[[(b['minute'],b['text'],b['move']) for b in seg['highlights']] for seg in sh.result['segments']]
    assert enhance_highlights(s,sh.id,0)['generated']==0
    # Failed validation does not partially modify highlights.
    sh.result['segments'][0]['highlights'][0].pop('ai_flavour')
    monkeypatch.setattr('wrestling_sim.narrative._generate',lambda p,sc,system_instruction:
                        {'reactions':['An invented suplex knocks someone unconscious.']*len(p['canonical_highlights'])})
    with pytest.raises(ValueError):enhance_highlights(s,sh.id,0)
    assert 'ai_flavour' not in sh.result['segments'][0]['highlights'][0]


def test_api_movesets_injuries_and_ollama_endpoints(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from wrestling_sim.api import app,service
    old_state,old_path=service.state,service.path
    try:
        service.state=new_game(); service.path=tmp_path/'api.json'
        c=TestClient(app)
        first=c.get('/ui/state')
        assert first.status_code==200
        assert first.json()['wrestlers'][0]['moveset']
        assert 'injury_reports' in first.json()
        edits=[{'name':'Headlock counter','style':'technical','finisher':False},
               {'name':'Arm drag','style':'technical','finisher':False},
               {'name':'Signature clasp','style':'storytelling','finisher':True}]
        assert c.put('/wrestlers/steel/moveset',json={'moves':edits}).status_code==200
        assert c.get('/wrestlers/steel').json()['moveset']==edits
        assert c.put('/wrestlers/storm/moveset',json={'moves':edits}).status_code==400
        meet=c.post('/ui/meetings/start',json={'wrestler_id':'steel','topic':'booking'}).json()
        monkeypatch.setattr('wrestling_sim.narrative._generate',lambda payload,schema,system_instruction:
                            {'reply':'I have heard the direction, and I want to know where it leads.'})
        voice=c.post('/ui/ollama/dialogue',json={'kind':'meeting','session_id':meet['id']})
        assert voice.status_code==200 and voice.json()['immutable_outcome']
        card=[Segment('match',['steel','phoenix'],40,'Men Main',storyline_id='steel-phoenix',planned_winner_id='phoenix'),
              Segment('match',['vale','collins'],40,'Women Main',storyline_id='vale-collins',planned_winner_id='vale'),
              Segment('promo',['knox'],20,'Knox speaks')]
        event=c.post('/shows/book',json={'name':'An Episode','segments':[asdict(s) for s in card]})
        assert event.status_code==200
        show_id=event.json()['id']
        assert c.post(f'/shows/{show_id}/simulate').status_code==200
        monkeypatch.setattr('wrestling_sim.narrative._generate',lambda payload,schema,system_instruction:
                            {'reactions':['The audience waits for the next beat with mounting anticipation.']*len(payload['canonical_highlights'])})
        enhanced=c.post('/ui/ollama/highlights',json={'show_id':show_id,'segment_index':2})
        assert enhanced.status_code==200 and enhanced.json()['generated']>=2
    finally:
        service.state=old_state;service.path=old_path
