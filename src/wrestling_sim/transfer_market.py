"""Two-way regulated recruitment: no wrestler changes employer without agreement.

AI competitors may bid; the human controls accept/reject. Pre-contracts honor expiry.
"""
from __future__ import annotations
import random
from .models import clamp
from .industry import wrestler_willingness, star_movement
from .front_office import monetary_value


def competitor_offers(state):
    rng=random.Random(f'poaching:{state.seed}:{state.year}:{state.week}')
    active=[w for w in state.wrestlers.values() if w.company_id==state.player_company_id]
    if not active:return []
    offers=[]
    if state.week%3!=0:return []  # proposals every few weeks, not constant spam
    rival_ids=[c.id for c in state.companies.values() if c.id!=state.player_company_id]
    if not rival_ids:return []
    willing=sorted(active,key=lambda w:((25-w.morale)*3+w.attributes['popularity']+w.attributes['ambition']),reverse=True)
    target=willing[0] if rng.random()<.65 else rng.choice(active)
    rival=state.companies[rng.choice(rival_ids)]
    if rival.money < 80000:return []
    amount=max(10000,round(monetary_value(target,state)*(0.55+rng.uniform(0,.55)),-3))
    amount=min(amount,round(rival.money*.40))
    pay=round(max(target.salary_weekly,800)*(1.05+rng.uniform(0,.60)))
    if target.contract_weeks==0:return []
    offer=dict(id=state.generate_id('rival-bid'),wrestler_id=target.id,buyer_id=rival.id,
        seller_id=state.player_company_id,fee=amount,salary_weekly=pay,contract_weeks=52,
        status='pending',year=state.year,week=state.week,
        message=f'{rival.name} bids ${amount:,} for {target.name} (currently {target.contract_weeks} weeks under contract).')
    state.transfer_offers.append(offer)
    offers.append(offer)
    return offers


def resolve_rival_bid(state,offer_id:str,decision:str):
    bid=next((x for x in state.transfer_offers if x['id']==offer_id and x['status']=='pending'),None)
    if not bid:raise ValueError('Offer unavailable or already resolved')
    if decision not in ('accept','reject','counter'):raise ValueError('Choose accept, reject or counter')
    buyer=state.companies[bid['buyer_id']];w=state.wrestlers[bid['wrestler_id']]
    if w.company_id!=state.player_company_id:raise ValueError('The wrestler is no longer contracted to you')
    if decision=='reject':
        bid['status']='rejected';w.morale=clamp(w.morale-(.45 if w.wants_release else .1),0,25)
        return dict(status='rejected',message=f'You rejected {buyer.name}’s offer for {w.name}.')
    if decision=='counter':
        bid['status']='countered'
        return dict(status='countered',message=f'You asked {buyer.name} to return with a stronger offer.')
    if buyer.money<bid['fee']:raise ValueError('Rival cannot currently afford this fee')
    desire=wrestler_willingness(state,w,buyer.id,bid['salary_weekly'],w.card_tier)
    rng=random.Random(f'bid-answer:{state.seed}:{bid["id"]}')
    agrees=rng.random()<desire['acceptance_probability']
    if not agrees:
        bid['status']='wrestler_declined'
        return dict(status='wrestler_declined',message=f'{w.name} declined the proposed rival contract despite your approval.')
    bid['status']='completed'
    buyer.money-=bid['fee'];state.player_company.money+=bid['fee']
    old=w.company_id;w.company_id=buyer.id;w.salary_weekly=bid['salary_weekly'];w.contract_weeks=bid['contract_weeks']
    w.wants_release=False
    star_movement(state,w,old,buyer.id)
    state.news.append(f'{w.name} transferred to {buyer.name} for ${bid["fee"]:,}.')
    return dict(status='completed',message=state.news[-1])
