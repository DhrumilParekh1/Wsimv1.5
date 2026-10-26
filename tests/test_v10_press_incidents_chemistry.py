"""Version 1.0 playable-system regression tests."""
from dataclasses import asdict
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.front_office import (pair_chemistry,after_pair_segment, monetary_value,
    set_tier, concerns,answer_concern,weekly_playtime)
from wrestling_sim.press_and_incidents import (PRESS_TOPICS,PRESS_FRAMES,INCIDENT_FRAMES,INCIDENT_TEMPLATES,
    pending_incidents, answer_incident, conference,answer_press)
from wrestling_sim.game import book_show,simulate_show,inbox_blockers,advance_week
from wrestling_sim.storage import save_game,load_game
from wrestling_sim.scenes import start_scene,choose_scene
from wrestling_sim.api import app,service


def test_new_game_has_two_unique_rng_incidents():
    s=new_game();a=pending_incidents(s)
    assert len(a)==2
    assert a[0]['id']!=a[1]['id']
    assert all(e['options'] for e in a)
    assert len(INCIDENT_TEMPLATES)*len(INCIDENT_FRAMES)>=200
    assert len(PRESS_TOPICS)*len(PRESS_FRAMES)>=100
    assert [i['id'] for i in pending_incidents(new_game())]==[i['id'] for i in a]


def test_events_cannot_be_ignored_or_double_answered():
    s=new_game();issue=pending_incidents(s)[0]
    assert any(x['kind']=='incident' for x in inbox_blockers(s))
    answer_incident(s,issue['id'],'support')
    with pytest.raises(ValueError):answer_incident(s,issue['id'],'support')
    assert len(pending_incidents(s))==1


def test_demotions_create_playtime_conversations():
    s=new_game();w=s.wrestlers['steel'];original=w.owner_relationship
    result=set_tier(s,w.id,'jobber')
    assert result['change']=='demotion' and w.owner_relationship<original
    assert len(concerns(s))==1
    concern=concerns(s)[0]
    answer_concern(s,concern['id'],'promise')
    assert not concerns(s)
    assert any(k.startswith('playing-time-') for k in s.assignments)
    with pytest.raises(ValueError): answer_concern(s,concern['id'],'promise')


def test_roster_tier_expected_appearances():
    s=new_game();steel=s.wrestlers['steel']
    for week in [1,2,3,4]:
        weekly_playtime(s,2026,week)
    assert any(x['kind']=='playing_time' for x in concerns(s))
    assert steel.morale<17


def test_pair_chemistry_persists_and_gradually_changes():
    s=new_game();before=pair_chemistry(s,'steel','phoenix')
    assert before==pair_chemistry(s,'phoenix','steel')
    after_pair_segment(s,['steel','phoenix'],95,'match')
    after=pair_chemistry(s,'steel','phoenix')
    assert before!=after and abs(before-after)<1
    assert s.chemistry['phoenix:steel']['appearances']==1


def test_market_value_is_real_money_not_rating():
    s=new_game();w=s.wrestlers['steel']
    amount=monetary_value(w,s)
    assert amount>100000 and amount%1000==0
    w.salary_weekly+=5000
    assert monetary_value(w,s)>amount


def test_press_answers_save_and_create_remembered_promises():
    s=new_game();conf=conference(s)
    assert len(conf['questions'])==3
    assert any(s.wrestlers[q['wrestler_id']].name in q['text'] or q['topic'] in ('rivals','business','adversity','locker_room','creative') for q in conf['questions'])
    for q in conf['questions']:
        answer_press(s,q['id'],'challenge')
    assert conference(s)['completed']
    with pytest.raises(ValueError):answer_press(s,conf['questions'][0]['id'],'candid')
    assert any(k.startswith('press-promise-') for k in s.assignments)


def test_nameless_match_and_draws_rejected():
    with pytest.raises(ValueError,match='named winner'):
        Segment('match',['steel','phoenix'],20,'No decision')
    with pytest.raises(ValueError,match='draw'):
        Segment('match',['steel','phoenix'],20,'Time limit',planned_winner_id='steel',finish_type='time_limit_draw')
    assert Segment('match',['steel','phoenix'],20,'A DQ',planned_winner_id='steel',finish_type='disqualification').planned_winner_id=='steel'


def test_creative_inbox_redirect_completes_only_after_room():
    s=new_game();scene=start_scene(s,'steel-phoenix')
    choose_scene(s,scene['id'],'challenge')
    assert f'{s.year}-{s.week}-creative' not in s.decisions
    choose_scene(s,scene['id'],'match')
    assert s.decisions[f'{s.year}-{s.week}-creative']=='creative_room'


def test_v10_state_survives_save_load(tmp_path):
    s=new_game();set_tier(s,'steel','mid_card');pair_chemistry(s,'steel','phoenix')
    answer_incident(s,pending_incidents(s)[0]['id'],'mediate')
    answer_press(s,conference(s)['questions'][0]['id'],'candid')
    file=tmp_path/'game.json';save_game(s,file)
    restored=load_game(file)
    assert restored.wrestlers['steel'].card_tier=='mid_card'
    assert restored.chemistry==s.chemistry
    assert restored.incidents==s.incidents
    assert restored.press_conferences==s.press_conferences
    assert len(restored.talent_concerns)==1


def test_all_new_api_paths(tmp_path):
    old_state,old_path=service.state,service.path
    try:
        service.state=new_game();service.path=tmp_path/'live.json'
        c=TestClient(app)
        data=c.get('/ui/state').json()
        assert len(data['incidents'])==2
        assert data['wrestlers'][0]['ratings']['market_dollars']>25000
        assert len(data['press_conference']['questions'])==3
        response=c.post('/wrestlers/steel/tier',json={'tier':'jobber'})
        assert response.status_code==200
        assert c.get('/ui/state').json()['talent_concerns']
        concern=c.get('/ui/state').json()['talent_concerns'][0]
        assert c.post('/ui/talent/resolve',json={'concern_id':concern['id'],'choice':'explain'}).status_code==200
        incident=data['incidents'][0]
        assert c.post('/ui/incidents/resolve',json={'incident_id':incident['id'],'choice':'support'}).status_code==200
        question=data['press_conference']['questions'][0]
        assert c.post('/ui/press/answer',json={'question_id':question['id'],'choice':'back'}).status_code==200
        assert c.post('/ui/choices',json={'event_id':'2026-1-creative','option_id':'slow_burn'}).status_code==400
        assert c.post('/ui/talent/buyout',json={'wrestler_id':'steel','proposed_fee':50000,'salary_weekly':3000}).status_code==400
    finally:
        service.state,service.path=old_state,old_path


def test_week_two_seeds_new_inbox_incidents_after_show():
    from wrestling_sim.decisions import available_decisions,choose_option
    from wrestling_sim.management import decline_media
    from wrestling_sim.sponsors import sponsor_offers,respond_sponsor
    s=new_game()
    card=[Segment('match',['steel','phoenix'],30,'Phoenix and Steel',storyline_id='steel-phoenix',planned_winner_id='phoenix'),
          Segment('match',['vale','collins'],30,'Vale and Collins',storyline_id='vale-collins',planned_winner_id='vale'),
          Segment('promo',['knox'],20,'Knox Speaks'),Segment('interview',['cruz'],20,'Cruz Gives an Interview')]
    show=book_show(s,'Week One',card)
    simulate_show(s,show.id)
    for incident in list(pending_incidents(s)):
        answer_incident(s,incident['id'],'support')
    for decision in list(available_decisions(s)):
        choose_option(s,decision['id'],decision['options'][0]['id'])
    decline_media(s)
    for sponsor in sponsor_offers(s):
        respond_sponsor(s,sponsor['id'],'reject')
    assert not inbox_blockers(s)
    result=advance_week(s)
    assert result['week']==2
    assert len(pending_incidents(s))==2
    assert all(i['week']==2 for i in pending_incidents(s))
