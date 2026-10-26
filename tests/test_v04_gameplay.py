"""Version 0.4 acceptance tests: new mandatory booking and management rules."""
from dataclasses import asdict
import json
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.game import book_show, simulate_show, advance_week, create_storyline
from wrestling_sim.management import (creative_head, staff_market, sign_creative_head,
                                       media_opportunity, assign_media, interact_wrestler,
                                       creative_tasks)
from wrestling_sim.storage import save_game, load_game
from wrestling_sim.scenes import start_scene, choose_scene
from wrestling_sim.api import app, service


def full_card():
    """110 minutes, with exactly two segments for each division's active storyline."""
    return [
        Segment('match',['steel','phoenix'],20,'Men main event','steel-phoenix',
                planned_winner_id='phoenix',stipulation='extreme',intensity='high'),
        Segment('match',['vale','collins'],20,'Women main event','vale-collins',planned_winner_id='collins'),
        Segment('promo',['steel','phoenix'],15,'Men promo','steel-phoenix'),
        Segment('confrontation',['vale','collins'],15,'Women promo','vale-collins',promo_brawl=True),
        Segment('interview',['knox'],10,'Knox interview'),
        Segment('interview',['cruz'],10,'Cruz interview'),
        Segment('backstage',['steel'],10,'Backstage talk'),
        Segment('return',['phoenix'],10,'Star return'),
    ]


def test_every_week_requires_full_show():
    s=new_game()
    with pytest.raises(ValueError,match='100–120'):
        book_show(s,'Tiny',[Segment('match',['steel','phoenix'],8,'Small','steel-phoenix',planned_winner_id='steel')])
    with pytest.raises(ValueError, match='must book and simulate'):
        advance_week(s)
    booked=book_show(s,'First Light',full_card())
    with pytest.raises(ValueError, match='must book and simulate'):
        advance_week(s)
    report=simulate_show(s,booked.id)
    assert len(report['segments'])==8
    resolve_inbox_for_test(s)
    assert advance_week(s)['week']==2
    with pytest.raises(ValueError,match='must book and simulate'):
        advance_week(s)


def test_division_rules_and_required_storylines():
    s=new_game()
    assert s.wrestlers['steel'].division=='men'
    assert s.wrestlers['vale'].division=='women'
    with pytest.raises(ValueError,match='one division'):
        create_storyline(s,'Mixed',['steel','vale'])
    mixed=full_card();mixed[0]=Segment('match',['steel','vale'],20,'Mixed','steel-phoenix',planned_winner_id='steel')
    with pytest.raises(ValueError,match='cannot mix'):
        book_show(s,'Mixed',mixed)
    missing=full_card();missing[1]=Segment('interview',['knox'],20,'Knox extra')
    missing[3]=Segment('interview',['steel'],15,'Steel extra')
    with pytest.raises(ValueError,match='women'):
        book_show(s,'All men storyline',missing)


def test_two_slots_per_story():
    s=new_game();card=full_card();card[-1]=Segment('promo',['steel','phoenix'],10,'Too many','steel-phoenix')
    with pytest.raises(ValueError,match='at most two'):
        book_show(s,'Overstuffed',card)


def test_highlights_duration_and_energy():
    s=new_game();initial=s.wrestlers['steel'].fatigue
    show=book_show(s,'Energetic',full_card());report=simulate_show(s,show.id)
    events=report['segments'][0]['match_engine']['highlights']
    assert events[0]['minute']>=1 and events[-1]['minute']==20
    assert all(events[i]['minute']<=events[i+1]['minute'] for i in range(len(events)-1))
    assert 'Alex Phoenix' in events[-1]['text']
    assert s.wrestlers['steel'].fatigue>initial
    assert s.wrestlers['vale'].fatigue>initial
    previous=s.wrestlers['steel'].fatigue
    resolve_inbox_for_test(s)
    advance_week(s)
    assert s.wrestlers['steel'].fatigue<previous
    assert 0<=s.wrestlers['steel'].fatigue<=25


def test_stipulations_cost_extra_energy():
    a,b=new_game(1),new_game(1)
    card_a=full_card();card_a[0].stipulation='standard';card_a[0].intensity='measured'
    book_show(a,'A',card_a);simulate_show(a,next(iter(a.shows)))
    book_show(b,'B',full_card());simulate_show(b,next(iter(b.shows)))
    assert b.wrestlers['steel'].fatigue>a.wrestlers['steel'].fatigue


def test_promo_brawl_costs_energy():
    a,b=new_game(9),new_game(9)
    card_a=full_card();card_a[3].promo_brawl=False
    book_show(a,'A',card_a);simulate_show(a,next(iter(a.shows)))
    book_show(b,'B',full_card());simulate_show(b,next(iter(b.shows)))
    assert b.wrestlers['collins'].fatigue>a.wrestlers['collins'].fatigue


def test_staff_market_and_advice():
    s=new_game();old=s.player_company.money
    assert creative_head(s)['skill']==13
    cost=next(h['buyout'] for h in staff_market(s) if h['id']=='vega')
    response=sign_creative_head(s,'vega')
    assert response['skill']==23 and old-s.player_company.money==cost
    scene=start_scene(s,'steel-phoenix')
    assert scene['creative_head']=='Casey Vega'
    assert sum(opt.get('recommended',False) for opt in scene['options'])==1
    with pytest.raises(ValueError,match='already'):
        sign_creative_head(s,'vega')


def test_creative_room_inbox_task():
    s=new_game();scene=start_scene(s,'vale-collins')
    choose_scene(s,scene['id'],'mind_games');choose_scene(s,scene['id'],'promo')
    tasks=creative_tasks(s)
    assert len(tasks)==1 and tasks[0]['kind']=='promo'
    # The suggested segment can be part of a standard show and fulfills the promise.
    card=full_card();card[3]=Segment('promo',['vale','collins'],15,'Promised promo','vale-collins')
    book_show(s,'Promises',card);report=simulate_show(s,next(iter(s.shows)))
    assert any(seg['planned_beat_delivered'] for seg in report['segments'])
    assert creative_tasks(s)==[]


def test_media_assignment_one_per_week_and_stamina():
    s=new_game();w=s.wrestlers['steel'];before=w.fatigue
    result=assign_media(s,'steel')
    assert isinstance(result['accepted'],bool)
    if result['accepted']:
        assert w.fatigue>before
    else: assert w.fatigue==before
    with pytest.raises(ValueError,match='already'):
        assign_media(s,'phoenix')


def test_wrestler_interactions_and_disputes():
    s=new_game();before=s.wrestlers['steel'].owner_relationship
    response=interact_wrestler(s,'steel','listen')
    assert response['wrestler_id']=='steel'
    assert s.wrestlers['steel'].owner_relationship!=before
    with pytest.raises(ValueError,match='already'):
        interact_wrestler(s,'steel','push')
    s.week=3
    from wrestling_sim.decisions import available_decisions, choose_option
    dispute=next(e for e in available_decisions(s) if e['kind']=='dispute')
    resolved=choose_option(s,dispute['id'],'mediate')
    assert resolved['effects']['wrestler_relationship']>0


def test_save_migration_v03(tmp_path):
    s=new_game();p=tmp_path/'save.json';save_game(s,p)
    data=json.loads(p.read_text())
    del data['creative_head_id'];del data['assignments'];del data['interactions'];del data['storylines']['vale-collins']
    for w in data['wrestlers'].values():
        w.pop('division');w.pop('personality');w.pop('owner_relationship')
    p.write_text(json.dumps(data))
    migrated=load_game(p)
    assert migrated.wrestlers['vale'].division=='women'
    assert 'vale-collins' in migrated.storylines
    assert migrated.creative_head_id=='morgan'
    assert asdict(load_game(p))==asdict(migrated)


def test_http_and_frontend_state(tmp_path):
    old_state,old_path=service.state,service.path
    try:
        service.state=new_game();service.path=tmp_path/'live.json'
        client=TestClient(app)
        snapshot=client.get('/ui/state').json()
        assert snapshot['staff']['skill']==13
        assert snapshot['media']['energy_cost']==8
        assert len(snapshot['storylines'])==2
        assert snapshot['wrestlers'][0]['division']=='men'
        assert client.post('/weeks/advance').status_code==400
        assert client.post('/ui/staff/hire',json={'head_id':'brook'}).status_code==200
        assert client.post('/ui/wrestlers/interact',json={'wrestler_id':'steel','topic':'listen'}).status_code==200
        assert client.post('/ui/media/assign',json={'wrestler_id':'steel'}).status_code==200
        bad=client.post('/shows/book',json={'name':'Short','segments':[asdict(full_card()[0])]})
        assert bad.status_code==400
        posted=client.post('/shows/book',json={'name':'Full show','duration':120,'segments':[asdict(x) for x in full_card()]})
        assert posted.status_code==200,posted.text
        played=client.post(f"/shows/{posted.json()['id']}/simulate")
        assert played.status_code==200,played.text
        assert len(played.json()['segments'][0]['match_engine']['highlights'])>=4
        resolve_inbox_for_test(service.state)
        assert client.post('/weeks/advance').status_code==200
        assert client.get('/').status_code==200
    finally:
        service.state,service.path=old_state,old_path


def resolve_inbox_for_test(state):
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
