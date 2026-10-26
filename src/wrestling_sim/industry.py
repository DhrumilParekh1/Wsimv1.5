"""The living promotion economy: prestige, recruitment, enforceable promises and growth.

All decisions are made by rules and reproducible RNG. Ollama only narrates the facts.
"""
from __future__ import annotations
import math
import random
from .models import clamp
from .ratings import rating_breakdown

TIERS = ('jobber', 'lower_mid_card', 'mid_card', 'upper_mid_card', 'main_event')
TIER_SCREEN = {'jobber':.20, 'lower_mid_card':.35, 'mid_card':.50,
               'upper_mid_card':.70, 'main_event':.90}


def company_prestige(state, company_id: str) -> dict:
    c=state.companies[company_id]
    other=[v.viewership for k,v in state.companies.items() if k != company_id]
    comparable=sorted(other)[len(other)//2] if other else max(c.viewership,1)
    relative=clamp(50 + 22*math.log(max(1000,c.viewership)/max(1000,comparable)),5,100)
    related=[s for s in state.storylines.values() if s.stage!='resolved' and any(
        state.wrestlers.get(w) and state.wrestlers[w].company_id==company_id for w in s.wrestler_ids)]
    hype=sum(s.hype for s in related)/len(related) if related else clamp(c.popularity,0,100)
    stars=sorted([rating_breakdown(w)['commercial'] for w in state.wrestlers.values()
        if w.company_id==company_id],reverse=True)
    star=sum(stars[:5])/max(1,len(stars[:5])) if stars else 20
    historic=clamp(getattr(c,'prestige_history',45),0,100)
    raw=.25*relative+.20*c.fan_trust+.20*hype+.15*c.sponsor_interest+.10*star+.10*historic
    return {'score':round(clamp(raw),2),'relative_viewership':round(relative,2),
            'hype':round(hype,2),'fan_trust':round(c.fan_trust,2),
            'sponsor_interest':round(c.sponsor_interest,2),
            'star_power':round(star,2),'history':round(historic,2)}


def update_prestige_history(state):
    for cid,c in state.companies.items():
        current=company_prestige(state,cid)['score']
        c.prestige_history=round(clamp(.97*c.prestige_history+.03*current),3)


def wrestler_willingness(state, wrestler, target_company_id: str, salary_weekly: int,
                         role: str='mid_card', promises: list | None=None) -> dict:
    if role not in TIERS: raise ValueError('Unknown negotiated card role')
    target=state.companies[target_company_id]
    prestige=company_prestige(state,target_company_id)['score']
    old=company_prestige(state,wrestler.company_id)['score'] if wrestler.company_id in state.companies else 45
    old_tier=TIERS.index(wrestler.card_tier)
    role_gain=TIERS.index(role)-old_tier
    pay=clamp(50+35*math.log(max(1,salary_weekly)/max(350,wrestler.salary_weekly or 800)))
    role_score=clamp(52+role_gain*18)
    mood=clamp(100-wrestler.morale*4 + (20 if wrestler.wants_release else 0))
    fit=clamp(50+(target.fan_trust-50)*.25 +(wrestler.owner_relationship*4-50)*.15)
    opportunity=clamp(55+(prestige-old)*.65+role_gain*9)
    development=clamp(35+target.fan_trust*.35)
    base=.20*prestige+.20*pay+.20*role_score+.15*fit+.15*mood+.10*development
    # Preference shaping rather than excluding weaker promotions.
    if wrestler.personality=='ambitious': base+=.13*(opportunity-prestige)+role_gain*2
    if wrestler.personality=='independent': base+=3 if promises and 'creative_freedom' in promises else -1
    if wrestler.personality=='cooperative': base+=3 if target.fan_trust>60 else 0
    if wrestler.attributes['loyalty']>19 and wrestler.company_id not in (None,target_company_id): base-=9
    base+=min(8,len(promises or [])*1.8)
    chance=clamp(.09 + (base-45)*.011,.06,.93)
    return dict(interest=round(clamp(base),1),acceptance_probability=round(chance,3),
                destination_prestige=prestige,current_prestige=old,offered_role=role,
                financial_offer_score=round(pay,1))


def declare_interest(state, wrestler_id: str, public: bool=False):
    w=state.wrestlers.get(wrestler_id)
    if not w or w.company_id==state.player_company_id: raise ValueError('Choose an external wrestler')
    from .world import prospect_discovered
    if not prospect_discovered(state,wrestler_id): raise ValueError('Discover this wrestler through scouting first')
    key=f'{state.year}:{state.week}:{wrestler_id}:{"public" if public else "private"}'
    if any(x['key']==key for x in state.recruitment_interest): raise ValueError('Already approached this wrestler this week')
    interest=wrestler_willingness(state,w,state.player_company_id,max(w.salary_weekly,800))
    reaction=clamp(interest['interest']+(-4 if w.company_id and public else 2),0,100)
    record=dict(key=key,year=state.year,week=state.week,wrestler_id=w.id,
                public=public,interest=round(reaction,1),company_id=w.company_id,
                status='pending',due_ordinal=state.year*52+state.week+1,
                message=(f'Public interest in {w.name} draws attention from {state.companies[w.company_id].name}.'
                    if public and w.company_id else f'Your representatives discreetly contacted {w.name}.'))
    state.recruitment_interest.append(record)
    if public:
        state.player_company.sponsor_interest=clamp(state.player_company.sponsor_interest+.15)
        state.news.append(record['message'])
        # Public announcements carry immediate, engine-grounded fan reaction.
        from .social import generate_transfer_reaction
        generate_transfer_reaction(state,w,record)
    return record


def process_recruitment_enquiries(state):
    """Deliver the actual scouting/recruitment response on the following week."""
    updates=[]
    ordinal=state.year*52+state.week
    for inquiry in state.recruitment_interest:
        if inquiry.get('status','pending')!='pending' or inquiry.get('due_ordinal',inquiry['year']*52+inquiry['week']+1)>ordinal:
            continue
        w=state.wrestlers.get(inquiry['wrestler_id'])
        if not w:
            inquiry['status']='closed';continue
        from .world import scout_reports
        reports=[r for r in state.scouting_reports if r['wrestler_id']==w.id]
        report=reports[-1] if reports else None
        inquiry['status']='reported'
        inquiry['result']={'interest':inquiry['interest'],
                           'salary_expectation':max(500,round(w.salary_weekly*(1.1 if w.company_id else 1.0))),
                           'contract_weeks':w.contract_weeks,
                           'confidence':report['confidence'] if report else None,
                           'scout_note':report['note'] if report else 'No detailed scouting information yet',
                           'can_negotiate_precontract':w.company_id is not None and w.contract_weeks<=12}
        updates.append(f'Recruitment report received: {w.name} — estimated interest {inquiry["interest"]:.0f}/100. Review Talent Market inbox.')
    return updates


def acknowledge_recruitment_report(state, key: str):
    inquiry=next((x for x in state.recruitment_interest if x['key']==key and x.get('status')=='reported'),None)
    if inquiry is None:raise ValueError('No outstanding recruitment report for that enquiry')
    inquiry['status']='reviewed'
    return {'status':'reviewed','wrestler_id':inquiry['wrestler_id'], 'message':'Recruitment report acknowledged; interest can still be pursued.'}


def negotiate_future_contract(state, wrestler_id: str, salary_weekly: int, weeks: int,
                              promised_role: str='mid_card', promises: list | None=None,
                              signing_bonus: int=0):
    w=state.wrestlers.get(wrestler_id)
    if not w or w.company_id in (None,state.player_company_id):
        raise ValueError('Future contracts target wrestlers under rival contracts')
    if w.contract_weeks>12: raise ValueError('Pre-contract talks open with 12 or fewer weeks remaining')
    if not 4<=weeks<=156 or salary_weekly<=0 or signing_bonus<0: raise ValueError('Invalid offer terms')
    if promised_role not in TIERS: raise ValueError('Unknown promised role')
    if any(x['wrestler_id']==w.id and x['status']=='signed' for x in state.precontracts):
        raise ValueError('A future deal has already been signed')
    score=wrestler_willingness(state,w,state.player_company_id,salary_weekly,promised_role,promises)
    rng=random.Random(f'precontract:{state.seed}:{state.year}:{state.week}:{w.id}:{salary_weekly}:{weeks}:{promised_role}')
    chance=score['acceptance_probability']
    # A future transfer doesn't evade the current exclusive contract.
    accepted=rng.random()<chance
    deal=dict(id=state.generate_id('precontract'),wrestler_id=w.id,old_company_id=w.company_id,
              destination=state.player_company_id,salary_weekly=salary_weekly,
              weeks=weeks,signing_bonus=signing_bonus,role=promised_role,
              promises=list(promises or []),accepted=accepted,status='signed' if accepted else 'rejected',
              accepted_week=state.week,probability=chance)
    state.precontracts.append(deal)
    return deal


def lodge_promise(state, wrestler_id: str, kind: str, target, deadline_weeks: int=8, origin='contract'):
    if kind not in ('tier','appearances','championship_opportunity','promotion','creative_freedom','coaching'):
        raise ValueError('Unknown contract promise type')
    if kind=='tier' and target not in TIERS: raise ValueError('Invalid promised card tier')
    if not 1<=deadline_weeks<=104: raise ValueError('Promise deadline must be 1–104 weeks')
    ordinal=state.year*52+state.week
    entry=dict(id=state.generate_id('promise'),wrestler_id=wrestler_id,kind=kind,
        target=target,due_ordinal=ordinal+deadline_weeks,created_ordinal=ordinal,
        origin=origin,status='pending',progress=0)
    state.contract_promises.append(entry)
    return entry


def update_promises(state, show=None):
    ordinal=state.year*52+state.week
    news=[]
    for promise in state.contract_promises:
        if promise['status']!='pending': continue
        w=state.wrestlers.get(promise['wrestler_id'])
        if not w:continue
        kind=promise['kind']; present=bool(show and any(w.id in s.wrestler_ids for s in show.segments))
        achieved=False
        if kind=='tier': achieved=TIERS.index(w.card_tier)>=TIERS.index(promise['target'])
        elif kind=='appearances':
            promise['progress']+=1 if present else 0
            achieved=promise['progress']>=int(promise['target'])
        elif kind=='championship_opportunity': achieved=bool(show and any(s.championship_id and w.id in s.wrestler_ids for s in show.segments))
        elif kind=='promotion': achieved=bool(show and any(s.promotion_budget and s.promotion_budget>=int(promise['target']) and w.id in s.wrestler_ids for s in show.segments))
        elif kind=='creative_freedom': achieved=bool(show and any(s.storyline_id and w.id in s.wrestler_ids for s in show.segments))
        elif kind=='coaching': achieved=w.id in state.coach_assignments
        if achieved:
            promise['status']='fulfilled';w.morale=clamp(w.morale+.8,0,25)
            w.owner_relationship=clamp(w.owner_relationship+.45,0,25)
            news.append(f'{w.name} appreciates your fulfilled {kind.replace("_"," ")} promise.')
        elif ordinal>=promise['due_ordinal']:
            promise['status']='broken';w.morale=clamp(w.morale-2.5,0,25)
            w.owner_relationship=clamp(w.owner_relationship-1.8,0,25)
            if w.morale<7:w.wants_release=True
            news.append(f'{w.name} is unhappy: the promised {kind.replace("_"," ")} was not delivered.')
    if news:
        state.news.extend(news)
        from .memories import add_memory
        for item in news: add_memory(state,'contract_promise',item,intensity=78)
    return news


def process_precontracts(state):
    notes=[]
    for deal in state.precontracts:
        if deal['status']!='signed':continue
        w=state.wrestlers.get(deal['wrestler_id'])
        if not w or w.contract_weeks>0:continue
        company=state.companies[deal['destination']]
        if company.money<deal['signing_bonus']:
            deal['status']='failed_financing';notes.append(f'{w.name} future contract fell through for lack of funds.')
            continue
        if sum(v.company_id==company.id for v in state.wrestlers.values())>=company.roster_limit:
            deal['status']='failed_roster';notes.append(f'{w.name} future deal could not be registered: roster full.')
            continue
        old=w.company_id
        w.company_id=company.id;w.salary_weekly=deal['salary_weekly'];w.contract_weeks=deal['weeks']
        w.card_tier=deal['role'];company.money-=deal['signing_bonus']
        deal['status']='completed'
        for kind in deal['promises']:
            if kind=='championship_opportunity':lodge_promise(state,w.id,kind,True,12)
            elif kind=='promotion':lodge_promise(state,w.id,kind,5000,8)
            elif kind=='coaching':lodge_promise(state,w.id,kind,True,8)
            elif kind=='creative_freedom':lodge_promise(state,w.id,kind,True,6)
        star_movement(state,w,old,company.id)
        notes.append(f'{w.name} joins {company.name} after their previous contract expires.')
    state.news.extend(notes)
    return notes


def star_movement(state,w,old_company_id,new_company_id):
    market=rating_breakdown(w)['commercial']/100
    for cid,sign in ((old_company_id,-1),(new_company_id,1)):
        if cid not in state.companies:continue
        c=state.companies[cid]
        # Signing publicity is temporary; historical prestige adjusts slowly.
        c.viewership=max(1000,round(c.viewership*(1+sign*.065*market)))
        c.sponsor_interest=clamp(c.sponsor_interest+sign*1.2*market)
        c.popularity=clamp(c.popularity+sign*1.0*market)


def weekly_morale(state):
    notes=[]
    for w in state.wrestlers.values():
        if not w.company_id:continue
        satisfaction=w.morale/25
        if w.company_id==state.player_company_id and w.morale<=5 and not w.wants_release:
            rng=random.Random(f'morale:{state.seed}:{state.year}:{state.week}:{w.id}')
            chance=clamp(.1+(5-w.morale)*.04+(25-w.attributes['professionalism'])*.008,0,.65)
            if rng.random()<chance:
                w.wants_release=True;notes.append(f'{w.name} formally requests a transfer after continued dissatisfaction.')
        # Morale reversion toward a modestly neutral baseline prevents permanent spirals.
        w.morale=round(clamp(w.morale+(0.06 if satisfaction<.6 else -.025),0,25),3)
    return notes


def expansion_quote(state,kind: str)->dict:
    c=state.player_company
    prestige=company_prestige(state,c.id)['score']
    if kind=='extra_ppv':
        cost=60000+20000*max(0,len(c.ppv_weeks)-3)
        ready=prestige>=28 and c.fan_trust>=40 and c.viewership>=35000
    elif kind=='more_hours':
        cost=95000+60000*max(0,(c.show_minutes-120)//30)
        ready=prestige>=38 and c.viewership>=60000
    else:raise ValueError('Unknown expansion type')
    return dict(kind=kind,cost=cost,cash=c.money,prestige=prestige,ready=ready,
                affordable=c.money>=cost*1.7,viewership=c.viewership)


def expand_company(state,kind: str):
    quote=expansion_quote(state,kind)
    if not quote['ready']:raise ValueError('Your audience and prestige do not justify this expansion yet')
    if not quote['affordable']:raise ValueError('Insufficient financial reserves for expansion')
    c=state.player_company
    if kind=='more_hours':
        if c.show_minutes>=180:raise ValueError('Maximum weekly runtime is 180 minutes')
        c.show_minutes+=30
    else:
        if len(c.ppv_weeks)>=8:raise ValueError('Maximum eight PPVs per year')
        targets=[6,11,23,29,40,46,49]
        unused=[w for w in targets if w not in c.ppv_weeks and w>state.week]
        if not unused:raise ValueError('No remaining PPV date this year')
        c.ppv_weeks=sorted(c.ppv_weeks+[unused[0]])
    c.money-=quote['cost']
    state.news.append(f'{c.name} invests ${quote["cost"]:,} into {kind.replace("_"," ")}.')
    return dict(**quote,new_show_minutes=c.show_minutes,ppv_weeks=c.ppv_weeks)
