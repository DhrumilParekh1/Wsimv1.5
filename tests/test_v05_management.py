"""V0.5 acceptance suite: dynamic world, management rooms and creative contracts."""
from dataclasses import asdict
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.starter import new_game
from wrestling_sim.world import (calendar,scout_reports,hire_staff,assign_coach,
                                  bootstrap_world,record_metrics,simulate_competitors,
                                  progress_coaches, prospect_discovered)
from wrestling_sim.dialogue import begin_meeting, answer_meeting, begin_contract, answer_contract
from wrestling_sim.game import book_show,simulate_show,advance_week, offer_contract
from wrestling_sim.models import Segment
from wrestling_sim.scenes import start_scene, choose_scene
from wrestling_sim.management import creative_tasks
from wrestling_sim.storage import save_game,load_game
from wrestling_sim.api import app,service
import random


def test_startup_multiple_competitors_and_ppv_schedule():
    s=new_game()
    assert len(s.companies)==4
    assert len(s.rival_history)==0
    events=calendar(s,16)
    assert s.player_company.ppv_weeks==[17,35,52]
    assert [e['week'] for e in events if e['is_ppv']]==[17]
    assert len(s.weekly_metrics)==1
    assert s.weekly_metrics[0]['popularity']==36


def test_independent_wrestlers_require_discovery():
    s=new_game()
    assert not prospect_discovered(s,'hart')
    with pytest.raises(ValueError,match='scout'):
        begin_contract(s,'hart')
    with pytest.raises(ValueError,match='scouting'):
        offer_contract(s,'hart',2000,52)
    result=scout_reports(s,'scout_local')
    assert len(result)>0
    assert all(r['confidence']==52 for r in result)
    assert all(r['wrestler_id'] in s.wrestlers for r in result)
    with pytest.raises(ValueError,match='already'):
        scout_reports(s,'scout_local')
    hire_staff(s,'scout','scout_global')
    elite=scout_reports(s,'scout_global')
    assert len(elite)>0
    assert any(r['name'] for r in elite)
    target=elite[0]['wrestler_id']
    if s.wrestlers[target].company_id is None:
        assert prospect_discovered(s,target)
        assert begin_contract(s,target)['status']=='active'


def test_creative_promise_is_bookable_and_simulates():
    s=new_game()
    scene=start_scene(s,'steel-phoenix')
    choose_scene(s,scene['id'],'challenge')
    choose_scene(s,scene['id'],'confrontation')
    tasks=creative_tasks(s)
    t=tasks[0]
    assert t['kind']=='confrontation'
    assert t['title']=='Marcus Steel Confronts Alex Phoenix'
    assert t['wrestler_ids']==['steel','phoenix']
    assert t['division']=='men'
    card=[
      Segment('confrontation',['steel','phoenix'],8,t['title'],storyline_id='steel-phoenix'),
      Segment('match',['steel','phoenix'],30,'Phoenix vs Steel',storyline_id='steel-phoenix',planned_winner_id='phoenix'),
      Segment('match',['vale','collins'],32,'Ember vs Vega',storyline_id='vale-collins',planned_winner_id='vale'),
      Segment('promo',['cruz'],20,'Nova Addresses the Crowd'),
      Segment('promo',['knox'],20,'Orion Calls Out the World'),
    ]
    show=book_show(s,'Aurora Week One',card)
    report=simulate_show(s,show.id)
    assert report['segments'][0]['planned_beat_delivered']
    assert s.storylines['steel-phoenix'].planned_beat['fulfilled']
    assert s.weekly_metrics[-1]['phase']=='show'
    assert s.weekly_metrics[-1]['week']==1
    assert calendar(s)[0]['status']=='completed'
    resolve_inbox_for_test(s)
    result=advance_week(s)
    assert result['week']==2
    assert len(s.rival_history)==3
    assert any(n['category']=='rival_show' for n in s.world_news)
    assert s.player_company.money != 850000
    assert s.companies['rival'].money != 1500000


def test_staff_assignment_personality_and_growth():
    s=new_game()
    hire_staff(s,'coach','coach_fitness')
    before=s.wrestlers['phoenix'].attributes['stamina']
    result=assign_coach(s,'coach_fitness','phoenix')
    assert isinstance(result['accepted'],bool)
    with pytest.raises(ValueError,match='one coaching proposal'):
        assign_coach(s,'coach_fitness','phoenix')
    if result['accepted']:
        progress_coaches(s,random.Random(2))
        assert s.wrestlers['phoenix'].attributes['stamina']>=before
    assert s.coaches['coach_fitness']['company_id']=='player'
    assert s.player_company.money<850000


def test_meetings_are_multistep_persistent_and_nonrepeatable():
    s=new_game()
    meeting=begin_meeting(s,'steel','booking')
    assert meeting['status']=='active' and len(meeting['options'])==3
    first=answer_meeting(s,meeting['id'],'promise')
    assert first['step']==1 and first['status']=='active'
    done=answer_meeting(s,meeting['id'],'support')
    assert done['status']=='complete'
    assert len(done['lines'])==5
    assert len(s.interactions)==1
    with pytest.raises(ValueError): begin_meeting(s,'steel','morale')


def test_contract_room_counter_walk_and_no_repeat():
    s=new_game()
    session=begin_contract(s,'orbit')
    offer=answer_contract(s,session['id'],'offer',1,52)
    assert offer['round']==1 and not offer['accepted']
    assert offer['counter_offer']['salary_weekly']>1
    final=answer_contract(s,session['id'],'walk')
    assert final['status']=='walked_away'
    with pytest.raises(ValueError,match='already negotiated'):
        begin_contract(s,'orbit')


def test_world_data_survive_saves(tmp_path):
    s=new_game(44)
    scout_reports(s,'scout_local')
    begin_meeting(s,'steel','booking')
    begin_contract(s,'orbit')
    news_len=len(s.world_news)
    file=tmp_path/'state.json'
    save_game(s,file)
    restored=load_game(file)
    assert restored.scouting_reports==s.scouting_reports
    assert restored.dialogue_sessions==s.dialogue_sessions
    assert restored.contract_sessions==s.contract_sessions
    assert restored.world_news==s.world_news
    assert restored.coaches==s.coaches
    assert restored.weekly_metrics==s.weekly_metrics


def test_api_exposes_new_screens_and_endpoints(monkeypatch,tmp_path):
    monkeypatch.setattr(service,'state',new_game(903))
    monkeypatch.setattr(service,'path',tmp_path/'api.json')
    c=TestClient(app)
    data=c.get('/ui/state').json()
    assert len(data['companies'])==4
    for key in ('calendar','weekly_metrics','world_news','rival_history','coaches','scouts',
                'scouting_reports','dialogue_sessions','contract_sessions'):
        assert key in data,key
    r=c.post('/ui/meetings/start',json={'wrestler_id':'steel','topic':'booking'})
    assert r.status_code==200,r.text
    session=r.json()
    assert c.post('/ui/meetings/choose',json={'session_id':session['id'],'choice_id':'explain'}).status_code==200
    assert c.post('/ui/management/scout',json={'scout_id':'scout_local'}).status_code==200
    assert c.post('/ui/management/hire',json={'kind':'coach','staff_id':'coach_promo'}).status_code==200
    assert c.post('/ui/management/coach',json={'coach_id':'coach_promo','wrestler_id':'vale'}).status_code==200
    n=c.post('/ui/negotiations/start',json={'wrestler_id':'orbit'})
    assert n.status_code==200,n.text
    assert c.post('/ui/negotiations/choose',json={'session_id':n.json()['id'],'action':'walk'}).status_code==200


def test_rivals_publish_actual_division_cards():
    s=new_game()
    simulate_competitors(s)
    assert len(s.rival_history)==3
    for result in s.rival_history:
        assert result['show_name'] and result['card']
        assert any(seg['kind']=='match' and seg['division']=='men' for seg in result['card'])
        assert any(seg['kind']=='match' and seg['division']=='women' for seg in result['card'])
        assert all(seg['rating']>=0 and seg['rating']<=100 for seg in result['card'])
        assert any(result['company_id']==c['id'] for c in
                   [{'id':'rival'}, {'id':'circuit'}, {'id':'royal'}])


def test_weekly_show_loop_and_metric_trends_before_first_ppv():
    s=new_game(332)
    for week in range(1,5):
        card=[Segment('confrontation',['steel','phoenix'],10,'The Challenge',storyline_id='steel-phoenix'),
              Segment('match',['steel','phoenix'],25,'Steel vs Phoenix',storyline_id='steel-phoenix',planned_winner_id='steel'),
              Segment('match',['vale','collins'],25,'Vale vs Collins',storyline_id='vale-collins',planned_winner_id='vale'),
              Segment('promo',['knox'],25,'Knox’s Address'),
              Segment('promo',['cruz'],25,'Nova’s Message')]
        show=book_show(s,f'Aurora W{week}',card)
        result=simulate_show(s,show.id)
        assert result['event_type']=='Weekly'
        assert result['finances'].get('ppv_bonus',0)==0
        resolve_inbox_for_test(s) if week<4 else None
        if week<4: advance_week(s)
    assert len(s.weekly_metrics)==4
    assert [r['week'] for r in s.weekly_metrics]==[1,2,3,4]
    assert len(s.rival_history)==9  # three rivals * three advances
    assert sum(e['is_ppv'] and e['status']=='completed' for e in calendar(s))==0


def test_v04_missing_fields_migrate_gracefully(tmp_path):
    import json
    s=new_game()
    payload=asdict(s)
    for field in ('coaches','scouts','coach_assignments','scouting_reports', 'world_news',
                  'rival_history','weekly_metrics','dialogue_sessions','contract_sessions'):
        payload.pop(field)
    for w in payload['wrestlers'].values(): w.pop('discovery_tier',None)
    fn=tmp_path/'legacy.json'
    fn.write_text(json.dumps(payload))
    migrated=load_game(fn)
    assert len(migrated.weekly_metrics)==1
    bootstrap_world(migrated)
    assert len(migrated.coaches)>0 and len(migrated.scouts)>0
    assert len(migrated.weekly_metrics)==1
    assert len(migrated.companies)==4
    assert 'solis' in migrated.wrestlers
    assert migrated.wrestlers['steel'].discovery_tier=='known'
    assert migrated.wrestlers['steel'].relationships['coach_fitness']>0


def test_promised_beat_only_fulfills_with_correct_wrestlers():
    from wrestling_sim.simulation import simulate_segment
    from wrestling_sim.management import creative_tasks
    s = new_game(2026)
    scene = start_scene(s, 'steel-phoenix')
    choose_scene(s, scene['id'], 'mind_games')
    choose_scene(s, scene['id'], 'promo')
    assert s.storylines['steel-phoenix'].planned_beat['wrestler_ids'] == ['steel','phoenix']
    # A one-person promo in the same storyline is NOT the committed two-person beat.
    wrong = Segment('promo', ['steel'], 8, 'Solo message', storyline_id='steel-phoenix')
    assert not simulate_segment(s, wrong, random.Random(1), 0)['planned_beat_delivered']
    correct = Segment('promo', ['steel','phoenix'], 8, 'Face-to-face promo', storyline_id='steel-phoenix')
    assert simulate_segment(s, correct, random.Random(1), 0)['planned_beat_delivered']
    s.shows['test'] = __import__('wrestling_sim.models', fromlist=['Show']).Show('test','Test',s.week,[wrong])
    assert creative_tasks(s)[0]['status'] == 'pending'
    s.shows['test'].segments = [correct]
    assert creative_tasks(s)[0]['status'] == 'booked'


def resolve_inbox_for_test(state):
    from wrestling_sim.press_and_incidents import conference, answer_press
    session=conference(state)
    if session:
        for question in session['questions']:
            if question['answer'] is None:
                answer_press(state,question['id'],'candid')
    """Explicitly respond to weekly mandatory items in legacy progression tests."""
    from wrestling_sim.decisions import available_decisions, choose_option
    from wrestling_sim.management import decline_media, media_opportunity, creative_tasks, cancel_creative_commitment
    from wrestling_sim.sponsors import sponsor_offers, respond_sponsor
    for decision in list(available_decisions(state)):
        choose_option(state, decision['id'], decision['options'][0]['id'])
    if media_opportunity(state)['id'] not in state.assignments:
        decline_media(state)
    for task in creative_tasks(state):
        cancel_creative_commitment(state, task['storyline_id'])
    for offer in sponsor_offers(state):
        respond_sponsor(state, offer['id'], 'reject')
    from wrestling_sim.press_and_incidents import pending_incidents,answer_incident
    for issue in list(pending_incidents(state)):
        answer_incident(state,issue['id'],'support')
    from wrestling_sim.front_office import concerns,answer_concern
    for issue in list(concerns(state)):
        answer_concern(state,issue['id'],'explain')
