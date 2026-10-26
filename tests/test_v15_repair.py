import pytest
from wrestling_sim.starter import new_game
from wrestling_sim.sponsors import terminate_sponsor
from wrestling_sim.narrative import _clean_fan_post
from wrestling_sim.dialogue import begin_contract, answer_contract


def test_clean_social_structured_text():
    v='{"title":"Test", "sentiment":"mixed", "text":"The match was fine, with some good moments."}'
    assert _clean_fan_post(v,'mixed')=='The match was fine, with some good moments.'
    with pytest.raises(ValueError):
        _clean_fan_post('{"title":"Test","sentiment":"negative","text":"Terrible result."}','positive')
    with pytest.raises(ValueError):
        _clean_fan_post('{"title":broken','mixed')


def test_sponsor_cancellation():
    s=new_game()
    s.sponsor_deals['test']={'name':'Test sponsor','weekly_payment':1000,'weeks_left':8,'minimum_crowd':50,'misses':0}
    before=s.player_company.money
    outcome=terminate_sponsor(s,'test')
    assert outcome['fee']==2000
    assert s.player_company.money==before-2000
    assert s.sponsor_deals['test']['weeks_left']==0
    with pytest.raises(ValueError):terminate_sponsor(s,'test')


def test_counter_demand_is_binding():
    s=new_game()
    w=next(x for x in s.wrestlers.values() if x.company_id==s.player_company_id)
    session=begin_contract(s,w.id)
    # Inject an already-quoted counter to ensure meeting it is deterministic.
    saved=s.contract_sessions[session['id']]
    saved['counter_offer']={'salary_weekly':3000,'weeks':52,'signing_bonus':0}
    result=answer_contract(s,session['id'],'offer',salary=3000,weeks=52,bonus=0)
    assert result['status']=='signed'


def test_private_manager_meeting_resolves_concern():
    from wrestling_sim.dialogue import begin_meeting, answer_meeting
    from wrestling_sim.front_office import queue_problem
    s=new_game()
    w=next(x for x in s.wrestlers.values() if x.company_id==s.player_company_id)
    queue_problem(s,w.id,'status',f'{w.name} requests a bigger role')
    concern=next(c for c in s.talent_concerns if c['wrestler_id']==w.id)
    session=begin_meeting(s,w.id,'booking',concern['id'])
    answer_meeting(s,session['id'],'promise')
    result=answer_meeting(s,session['id'],'support')
    assert result['status']=='complete'
    assert concern['status']=='resolved'
    assert result['concern_result']['wrestler_id']==w.id


def test_private_manager_meeting_rejects_wrong_concern():
    from wrestling_sim.dialogue import begin_meeting
    s=new_game()
    w=next(x for x in s.wrestlers.values() if x.company_id==s.player_company_id)
    with pytest.raises(ValueError): begin_meeting(s,w.id,'booking','bad-id')


def test_sponsor_offer_limit_ten():
    from wrestling_sim.sponsors import sponsor_offers
    s=new_game()
    for i in range(10):
        s.sponsor_deals[str(i)]={'weeks_left':3,'name':'Sponsor','weekly_payment':1000}
    assert sponsor_offers(s)==[]
