"""V1.2 integration tests for the new cross-system management mechanics.

These test deterministic game-state consequences, not fictional narrative wording.
"""
import pytest
from fastapi.testclient import TestClient
from wrestling_sim.starter import new_game
from wrestling_sim.industry import (
    company_prestige, wrestler_willingness, negotiate_future_contract,
    lodge_promise, update_promises, expansion_quote, expand_company, star_movement,
)
from wrestling_sim.marketing import purchase_campaign, campaign_visibility
from wrestling_sim.world import scout_reports, calendar
from wrestling_sim.development import personality_fit, coaching_effectiveness
from wrestling_sim.models import Segment
from wrestling_sim.fan_interest import fan_context, fan_outcome
from wrestling_sim.storage import save_game, load_game
from wrestling_sim.transfer_market import resolve_rival_bid
from wrestling_sim import api
from wrestling_sim.service import GameService


def test_starter_has_three_ppvs_and_physical_traits():
    s=new_game()
    assert s.player_company.show_minutes==120
    assert s.player_company.ppv_weeks==[17,35,52]
    assert [e['week'] for e in calendar(s,52) if e['is_ppv']]==[17,35,52]
    for w in s.wrestlers.values():
        assert 140<w.height_cm<230
        assert 45<w.weight_kg<180
        assert len(w.traits)>0


def test_prestige_responds_to_relative_viewership():
    s=new_game()
    first=company_prestige(s,s.player_company_id)['score']
    s.player_company.viewership *= 4
    higher=company_prestige(s,s.player_company_id)['score']
    assert higher>first
    assert 0<=higher<=100


def test_lower_prestige_does_not_preclude_offer():
    s=new_game()
    w=s.wrestlers['thorn']
    assert w.company_id != s.player_company_id
    offer=wrestler_willingness(s,w,s.player_company_id,30000,'main_event', ['promotion'])
    assert offer['acceptance_probability']>0
    assert offer['acceptance_probability']<1


def test_precontract_requires_expiry_window_and_does_not_transfer_immediately():
    s=new_game(34)
    w=s.wrestlers['storm']
    assert w.company_id not in (None,s.player_company_id)
    original=w.company_id
    w.contract_weeks=30
    with pytest.raises(ValueError,match='12'):
        negotiate_future_contract(s,w.id,50000,52)
    w.contract_weeks=9
    result=negotiate_future_contract(s,w.id,50000,52,'main_event')
    assert result['status'] in ('signed','rejected')
    assert w.company_id==original


def test_promises_affect_morale_and_capture_failure():
    s=new_game()
    w=s.wrestlers['steel']
    initial=w.morale
    p=lodge_promise(s,w.id,'championship_opportunity',True,1)
    s.week=2
    news=update_promises(s)
    assert p['status']=='broken'
    assert w.morale<initial
    assert any('unhappy' in n for n in news)


def test_promise_fulfilled_by_booked_show():
    s=new_game()
    w=s.wrestlers['steel']
    p=lodge_promise(s,w.id,'appearances',1,3)
    show=type('ShowStub',(),{'segments':[Segment('promo',[w.id],10,'Opening address')]})()
    update_promises(s,show)
    assert p['status']=='fulfilled'


def test_campaigns_are_paid_once_with_affordability():
    s=new_game()
    before=s.player_company.money
    purchase_campaign(s,'weekly',10000)
    assert s.player_company.money==before-10000
    assert campaign_visibility(s)>0
    with pytest.raises(ValueError,match='already'):
        purchase_campaign(s,'weekly',1000)
    with pytest.raises(ValueError,match='exceeds'):
        purchase_campaign(s,'ppv',s.player_company.money+1)


def test_expansion_is_conditional_and_changes_schedule():
    s=new_game()
    s.player_company.money=5_000_000
    s.player_company.viewership=2_500_000
    s.player_company.fan_trust=95
    s.player_company.sponsor_interest=95
    assert expansion_quote(s,'extra_ppv')['ready']
    quote=expand_company(s,'extra_ppv')
    assert len(quote['ppv_weeks'])==4
    assert len(s.player_company.ppv_weeks)==4
    s.player_company.viewership=2_500_000
    if expansion_quote(s,'more_hours')['ready']:
        expand_company(s,'more_hours')
        assert s.player_company.show_minutes==150


def test_scout_reports_progress_and_have_salary_uncertainty():
    s=new_game()
    first=scout_reports(s,'scout_local')
    assert all('scouted_market_value' in r and 'contract_weeks_estimate' in r for r in first)
    assert all(r['confidence']<=100 for r in first)
    s.week=2
    second=scout_reports(s,'scout_local')
    assert second
    assert len(s.scouting_reports)==len(first)+len(second)


def test_personality_and_workload_change_coaching_effectiveness():
    s=new_game()
    coach=s.coaches['coach_tech']
    w=s.wrestlers['steel']
    assert personality_fit('demanding','ambitious')>personality_fit('demanding','volatile')
    baseline=coaching_effectiveness(s,coach,w)
    for wid in list(s.wrestlers)[:6]:s.coach_assignments[wid]=coach['id']
    overloaded=coaching_effectiveness(s,coach,w)
    assert overloaded<baseline


def test_repeated_rivalry_fatigue_lowers_anticipation():
    s=new_game()
    story=s.storylines['steel-phoenix']
    seg=Segment('match',['steel','phoenix'],25,'Veteran vs Prodigy',storyline_id=story.id,planned_winner_id='steel')
    first=fan_context(s,seg,story)
    story.fatigue=24
    later=fan_context(s,seg,story)
    assert later['anticipation']<first['anticipation']
    assert fan_outcome(later,56,55,'medium')['satisfaction']<=fan_outcome(first,56,55,'medium')['satisfaction']


def test_rival_bid_cannot_automatically_transfer():
    s=new_game()
    bid={'id':'offer-12','wrestler_id':'steel','buyer_id':'rival','seller_id':s.player_company_id,
        'fee':250000,'salary_weekly':10000,'contract_weeks':52,'status':'pending'}
    s.transfer_offers.append(bid)
    assert s.wrestlers['steel'].company_id==s.player_company_id
    resolve_rival_bid(s,'offer-12','reject')
    assert s.wrestlers['steel'].company_id==s.player_company_id
    assert bid['status']=='rejected'


def test_star_movement_has_business_consequences():
    s=new_game()
    before=s.player_company.viewership
    star_movement(s,s.wrestlers['phoenix'],None,s.player_company_id)
    assert s.player_company.viewership>before


def test_new_fields_roundtrip(tmp_path):
    s=new_game()
    s.campaigns.append({'key':'2026:1:weekly','year':2026,'week':1,'scope':'weekly','amount':1000})
    s.contract_promises.append({'id':'x','wrestler_id':'steel','kind':'tier','target':'main_event','status':'pending'})
    file=tmp_path/'save.json';save_game(s,file)
    restored=load_game(file)
    assert restored.wrestlers['steel'].height_cm==s.wrestlers['steel'].height_cm
    assert restored.wrestlers['steel'].traits==s.wrestlers['steel'].traits
    assert restored.player_company.ppv_weeks==[17,35,52]
    assert restored.campaigns==s.campaigns
    assert restored.contract_promises==s.contract_promises


def test_api_exposes_new_industry_state(monkeypatch,tmp_path):
    monkeypatch.setattr(api,'service',GameService(tmp_path/'api-state.json'))
    client=TestClient(api.app)
    result=client.get('/ui/state')
    assert result.status_code==200,result.text
    data=result.json()
    assert 'prestige' in data['company']
    assert 'expansion' in data
    assert 'precontracts' in data
    assert 'contract_promises' in data
    assert 'traits' in data['wrestlers'][0]


def test_renewal_does_not_trigger_publicity_as_new_signing(monkeypatch):
    # A renewal must never count as a new star joining the company.
    from wrestling_sim.game import offer_contract
    from wrestling_sim import industry
    s=new_game(55)
    w=s.wrestlers['steel']
    called=[]
    monkeypatch.setattr(industry,'star_movement',lambda *args: called.append(args))
    offer_contract(s,w.id,100000,52,promised_role='main_event')
    assert not called


def test_calendar_ppv_week17_triggers_broadcast_bonus():
    from wrestling_sim.game import book_show, simulate_show
    s=new_game(42)
    s.week=17
    card=[
        Segment('confrontation',['steel','phoenix'],10,'The Challenge',storyline_id='steel-phoenix'),
        Segment('match',['steel','phoenix'],25,'Steel vs Phoenix',storyline_id='steel-phoenix',planned_winner_id='steel'),
        Segment('match',['vale','collins'],25,'Vale vs Collins',storyline_id='vale-collins',planned_winner_id='vale'),
        Segment('promo',['knox'],25,'Knox Speech'),
        Segment('promo',['cruz'],25,'Nova Speech'),
    ]
    show=book_show(s,'Spring Championship',card)
    result=simulate_show(s,show.id)
    assert result['event_type']=='PPV'
    assert result['finances']['ppv_bonus']>0


def test_api_recruitment_and_campaign(monkeypatch,tmp_path):
    monkeypatch.setattr(api,'service',GameService(tmp_path/'api-v12.json'))
    client=TestClient(api.app)
    c=client.post('/ui/company/campaign',json={'scope':'weekly','amount':2500})
    assert c.status_code==200,c.text
    e=client.post('/ui/recruit/interest',json={'wrestler_id':'storm','public':False})
    assert e.status_code==200,e.text
    assert client.get('/ui/state').json()['campaigns'][0]['amount']==2500
