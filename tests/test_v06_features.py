"""Acceptance tests for V0.6 gameplay and optional language-model boundary."""
import json
from dataclasses import asdict
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.starter import new_game
from wrestling_sim.models import Segment
from wrestling_sim.match_engine import match_profile
from wrestling_sim.game import book_show, simulate_show, advance_week, inbox_blockers
from wrestling_sim.management import decline_media, cancel_creative_commitment
from wrestling_sim.decisions import available_decisions, choose_option
from wrestling_sim.sponsors import sponsor_offers, respond_sponsor
from wrestling_sim.social import generate_fan_posts
from wrestling_sim.narrative import rewrite_social
from wrestling_sim.scenes import start_scene, choose_scene
from wrestling_sim.api import app, service
from wrestling_sim.storage import save_game, load_game


def complete_pending(state):
    from wrestling_sim.press_and_incidents import conference,answer_press
    session=conference(state)
    for question in session['questions']:
        if question['answer'] is None:
            answer_press(state,question['id'],'candid')
    for d in list(available_decisions(state)):
        choose_option(state,d['id'],d['options'][0]['id'])
    decline_media(state)
    for offer in sponsor_offers(state):
        respond_sponsor(state,offer['id'],'reject')
    from wrestling_sim.press_and_incidents import pending_incidents,answer_incident
    for issue in list(pending_incidents(state)):
        answer_incident(state,issue['id'],'support')
    from wrestling_sim.front_office import concerns,answer_concern
    for issue in list(concerns(state)):
        answer_concern(state,issue['id'],'explain')


def full_show():
    return [Segment('match',['steel','phoenix'],35,'Steel vs Phoenix','steel-phoenix',planned_winner_id='phoenix',match_styles=['technical','storytelling','high_flying']),
            Segment('match',['vale','collins'],32,'Vale vs Collins','vale-collins',planned_winner_id='vale',match_styles=['high_flying','technical']),
            Segment('promo',['knox'],20,'Knox speaks'),Segment('interview',['cruz'],20,'Nova interview')]


def test_style_combos_validate_and_change_rating():
    s=new_game()
    with pytest.raises(ValueError,match='2 or 3'):
        Segment('match',['steel','phoenix'],20,'x',match_styles=['technical'],planned_winner_id='steel')
    with pytest.raises(ValueError,match='2 or 3'):
        Segment('match',['steel','phoenix'],20,'x',match_styles=['technical','technical'],planned_winner_id='steel')
    one=Segment('match',['steel','phoenix'],20,'x',match_styles=['technical','storytelling'],planned_winner_id='steel')
    two=Segment('match',['steel','phoenix'],20,'x',match_styles=['high_flying','power'],planned_winner_id='steel')
    p1,p2=match_profile(s,one,None),match_profile(s,two,None)
    assert p1['style_fit']!=p2['style_fit']
    assert p1['style_weights']!=p2['style_weights']
    assert abs(sum(p1['style_weights'].values())-1)<.01


def test_inbox_blockers_server_enforced_and_can_clear():
    s=new_game()
    show=book_show(s,'Show',full_show());simulate_show(s,show.id)
    with pytest.raises(ValueError,match='Press Conference'):
        advance_week(s)
    complete_pending(s)
    assert not inbox_blockers(s)
    assert advance_week(s)['week']==2


def test_creative_commitment_can_cancel_at_a_cost():
    s=new_game();scene=start_scene(s,'steel-phoenix')
    choose_scene(s,scene['id'],'challenge');choose_scene(s,scene['id'],'confrontation')
    assert any(x['kind']=='creative' for x in inbox_blockers(s))
    original=s.player_company.fan_trust
    cancel_creative_commitment(s,'steel-phoenix')
    assert s.player_company.fan_trust == original-1
    assert not any(x['kind']=='creative' for x in inbox_blockers(s))


def test_sponsors_payout_avoids_duplicate_and_retains_history():
    s=new_game();offer=sponsor_offers(s)[0]
    accepted=respond_sponsor(s,offer['id'],'accept')
    assert accepted['accepted']
    with pytest.raises(ValueError):respond_sponsor(s,offer['id'],'accept')
    show=book_show(s,'Show',full_show());r=simulate_show(s,show.id)
    assert r['finances']['contract_sponsors']>0
    assert r['finances']['sponsors']>=r['finances']['contract_sponsors']
    assert len(s.social_posts)>5
    assert all(p['show_id']==show.id for p in s.social_posts)
    assert all(p['source']=='simulation' for p in s.social_posts)


def test_optional_ollama_only_changes_text(monkeypatch):
    s=new_game();show=book_show(s,'Show',full_show());simulate_show(s,show.id)
    original=[(p['crowd'],p['sentiment']) for p in s.social_posts]
    def fake(payload,schema):
        return {'posts':['My own short review of this fictional show!']*len(payload['posts'])}
    monkeypatch.setattr('wrestling_sim.narrative._generate',fake)
    result=rewrite_social(s,show.id)
    assert result['updated']>0
    assert [(p['crowd'],p['sentiment']) for p in s.social_posts]==original
    assert s.social_posts[0]['source']=='ollama'
    assert rewrite_social(s,show.id)['updated']==0 or len(s.social_posts)>12


def test_v05_saves_receive_new_state_and_legacy_style(tmp_path):
    s=new_game();old=Segment('match',['steel','phoenix'],22,'Old-fashioned',planned_winner_id='steel')
    s.shows['old']=__import__('wrestling_sim.models',fromlist=['Show']).Show('old','Legacy',1,[old])
    path=tmp_path/'game.json';save_game(s,path)
    data=json.loads(path.read_text());
    for field in ('sponsor_deals','sponsor_responses','social_posts'):data.pop(field,None)
    for segment in data['shows']['old']['segments']:segment.pop('match_styles',None)
    path.write_text(json.dumps(data))
    loaded=load_game(path)
    assert loaded.sponsor_deals=={}
    assert loaded.shows['old'].segments[0].match_styles==[]


def test_api_sponsor_social_and_styles(tmp_path):
    previous,old_path=service.state,service.path
    try:
        service.state=new_game();service.path=tmp_path/'api.json'
        c=TestClient(app)
        assert c.get('/ui/state').json()['inbox_blockers']
        assert c.get('/ui/ollama/status').status_code==200
        bad=c.post('/shows/book',json={'name':'X','segments':[asdict(x) for x in full_show()[:1]]})
        assert bad.status_code==400
        o=c.get('/ui/state').json()['sponsor_offers'][0]
        r=c.post('/ui/sponsors/reply',json={'offer_id':o['id'],'action':'reject'})
        assert r.status_code==200
        assert c.post('/ui/media/decline').status_code==200
        booked=c.post('/shows/book',json={'name':'Show','segments':[asdict(x) for x in full_show()]})
        assert booked.status_code==200,booked.text
        result=c.post('/shows/'+booked.json()['id']+'/simulate')
        assert result.status_code==200,result.text
        assert c.get('/ui/state').json()['social_posts']
        assert c.post('/weeks/advance').status_code==400
    finally:service.state=previous;service.path=old_path


def test_ollama_recap_is_display_only(monkeypatch):
    from wrestling_sim.narrative import segment_recap
    s=new_game();show=book_show(s,'Wrestling Night',full_show());simulate_show(s,show.id)
    before=asdict(s)
    monkeypatch.setattr('wrestling_sim.narrative._generate',lambda payload,schema: {'recap':'A lively performance builds to its already-booked finish, with every exchange engaging the arena.'})
    res=segment_recap(s,show.id,0)
    assert res['immutable_outcome'] and res['source']=='ollama'
    assert before==asdict(s)
