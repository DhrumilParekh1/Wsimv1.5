"""Acceptance checks for the V1.6 persistent-management additions."""
from wrestling_sim.starter import new_game
from wrestling_sim.dialogue import begin_meeting, answer_meeting
from wrestling_sim.press_and_incidents import pending_incidents, answer_incident
from wrestling_sim.models import Segment
from wrestling_sim.game import book_show
from wrestling_sim.scenes import start_scene,choose_scene


def test_three_round_meeting_preserves_chosen_path():
    state=new_game()
    meeting=begin_meeting(state,'steel','booking')
    answer_meeting(state,meeting['id'],'explain')
    second=answer_meeting(state,meeting['id'],'compromise')
    assert second['status']=='active'
    assert second['step']==2
    completed=answer_meeting(state,meeting['id'],'support')
    assert completed['status']=='complete'
    assert [item['choice'] for item in completed['decisions']]==['explain','compromise','support']


def test_incident_creates_persistent_follow_up():
    state=new_game()
    event=pending_incidents(state)[0]
    answer_incident(state,event['id'],event['options'][0]['id'])
    assert event['follow_up']['remaining_weeks']>=2
    assert event['follow_up']['wrestler_ids']==event['wrestler_ids']


def test_locked_creative_direction_produces_audit_entry():
    state=new_game()
    scene=start_scene(state,'steel-phoenix')
    choose_scene(state,scene['id'],'mind_games')
    choose_scene(state,scene['id'],'promo')
    card=[
        Segment('match',['steel','phoenix'],30,'Men match','steel-phoenix',planned_winner_id='phoenix',creative_direction='escalate'),
        Segment('match',['vale','collins'],30,'Women match','vale-collins',planned_winner_id='vale'),
        Segment('promo',['steel','phoenix'],20,'Promised promo','steel-phoenix'),
        Segment('promo',['knox'],20,'Opening words'),
    ]
    book_show(state,'Creative deviation',card)
    assert any(x['type']=='creative_override' and x['locked']=='slow_burn'
               for x in state.activity_log)
