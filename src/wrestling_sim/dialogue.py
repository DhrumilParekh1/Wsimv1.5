"""Multi-step, player-directed wrestler conversations and contract negotiation rooms.

Dialogue choices have real state effects; the narrative describes deterministic
seeded simulation outcomes. Never expose supposed 'true' private dispositions.
"""
from __future__ import annotations
import random
from .models import GameState, clamp
from .ratings import rating_breakdown

TOPICS={
 'booking': ('My place on the card', 'I want to understand where I fit in your creative plans.'),
 'morale': ('Locker-room concerns', 'There are things backstage that I need to talk about.'),
 'contract': ('My future with the company', 'I would like to know what you have planned for my contract.'),
 'dispute': ('A disagreement', 'Something with another wrestler has been bothering me.'),
}
CHOICES={
 'booking': [('promise','Promise a featured match','Boost morale, but the commitment must be delivered.'),('explain','Explain the long-term plan','May reassure a patient professional.'),('challenge','Ask them to prove themselves','Appeals to ambitious wrestlers, but risks friction.')],
 'morale': [('listen','Listen and acknowledge the concern','Often improves the relationship.'),('compromise','Offer a workload compromise','An attentive response; some may want more.'),('boundary','Lay down firm expectations','Risk of conflict, especially with independent personalities.')],
 'contract': [('reassure','Offer verbal reassurance','A small trust-building step.'),('negotiate','Invite them into formal talks','Open the contract room after this meeting.'),('defer','Ask them to wait','May lead to frustration as expiry approaches.')],
 'dispute': [('mediate','Offer to mediate','Improves trust when done well.'),('side','Take their side','Strengthens rapport but may increase backstage tension.'),('distance','Tell them to handle it professionally','Avoids direct involvement, but can seem dismissive.')],
}


def begin_meeting(state: GameState, wrestler_id: str, topic: str, concern_id: str | None = None) -> dict:
    w=state.wrestlers.get(wrestler_id)
    if not w or w.company_id!=state.player_company_id:raise ValueError('Meetings require your signed talent')
    if topic not in TOPICS: raise ValueError('Unknown conversation topic')
    key=f'{state.year}-{state.week}-{wrestler_id}'
    if key in state.dialogue_sessions:raise ValueError('You have already met this wrestler this week')
    if concern_id:
        concern=next((c for c in state.talent_concerns if c['id']==concern_id and c['wrestler_id']==wrestler_id and c['status']=='open'),None)
        if concern is None: raise ValueError('This concern is no longer open')
    title,intro=TOPICS[topic]
    opening=f'In your private office, {w.name} sits down. “{intro}”'
    session=dict(id=key,wrestler_id=wrestler_id,topic=topic,step=0,status='active',title=title,
                 lines=[dict(speaker=w.name,text=intro)],effects={},option=None,concern_id=concern_id)
    state.dialogue_sessions[key]=session
    return meeting_view(state,session)


def meeting_view(state, session):
    w=state.wrestlers[session['wrestler_id']]
    return {**session,'wrestler_name':w.name,'portrait_id':w.id,'personality':w.personality,
            'morale':round(w.morale,2),'owner_relationship':round(w.owner_relationship,2),
            'options':([dict(id=i,label=l,hint=h) for i,l,h in CHOICES[session['topic']]] if session['step']==0 else
                       [{'id':'support','label':'End positively','hint':'Finish with mutual respect.'},
                        {'id':'firm','label':'Set firm expectations','hint':'Emphasise accountability.'}] if session['status']=='active' else [])}


def answer_meeting(state, session_id: str, choice_id: str):
    s=state.dialogue_sessions.get(session_id)
    if not s or s['status']!='active':raise ValueError('Meeting is closed')
    if s['step']>1:raise ValueError('Meeting is already complete')
    valid={x['id'] for x in meeting_view(state,s)['options']}
    if choice_id not in valid:raise ValueError('Invalid dialogue choice')
    w=state.wrestlers[s['wrestler_id']]
    from .memories import relevant_memories,add_memory
    memories = relevant_memories(state,[w.id],limit=4)
    unresolved = sum(1 for m in memories if m['type']=='broken_promise')
    rng=random.Random(f'meeting:{state.seed}:{session_id}:{s["step"]}:{choice_id}')
    rapport=(w.owner_relationship + w.morale + w.attributes['professionalism'])/75
    modifier={'ambitious':-.05,'cooperative':.13,'independent':-.10,'volatile':-.20,'balanced':0}[w.personality]
    fit={'challenge':(.16 if w.personality=='ambitious' else -.1),'boundary':(-.1 if w.personality in ('independent','volatile') else 0),
         'explain':(.12 if w.personality=='cooperative' else 0),'compromise':.12,'listen':.12,'promise':.10,'reassure':.10,'defer':-.18,
         'negotiate':.07,'mediate':.11,'side':.06,'distance':-.10,'support':.13,'firm':-.06}.get(choice_id,0)
    chance=clamp(.21+rapport*.65+modifier+fit-.055*min(3,unresolved),.05,.96)
    accepted=rng.random()<chance
    base={'promise':(1.0,1.0),'explain':(.5,.8),'challenge':(.15,-.45),
          'listen':(.55,1.0),'compromise':(.6,.8),'boundary':(-.2,-.8),
          'reassure':(.45,.65),'negotiate':(.3,.5),'defer':(-.7,-.55),
          'mediate':(.35,.85),'side':(.6,.35),'distance':(-.5,-.65),
          'support':(.2,.4),'firm':(.0,-.15)}[choice_id]
    morale_delta,relation_delta=(base if accepted else (-abs(base[0])*.8-.15,-abs(base[1])*.8-.25))
    w.morale=round(clamp(w.morale+morale_delta,0,25),3)
    w.owner_relationship=round(clamp(w.owner_relationship+relation_delta,0,25),3)
    if choice_id=='promise' and accepted:
        state.assignments[f'push-{state.year}-{state.week}-{w.id}']=dict(wrestler_id=w.id,due_week=state.week+2,fulfilled=False)
    if choice_id=='negotiate':s['open_contract']=True
    spoken=(f'{w.name} seems reassured and agrees to the direction.' if accepted else
            f'{w.name} remains unconvinced. The conversation has become more tense.')
    s['lines'] += [dict(speaker='You',text=next(x[1] for x in (CHOICES[s['topic']] if s['step']==0 else [('support','End positively',''),('firm','Set firm expectations','')]) if x[0]==choice_id)),
                   dict(speaker=w.name,text=spoken)]
    s['effects'][f'step_{s["step"]}']=dict(morale=round(morale_delta,2),relationship=round(relation_delta,2),accepted=accepted)
    if s['step']==0:s['opening_choice']=choice_id
    s['step']+=1
    if s['step']>=2:
        s['status']='complete'
        if s.get('concern_id'):
            from .front_office import answer_concern
            first=s.get('opening_choice','explain')
            choice='promise' if first=='promise' else 'firm' if first=='challenge' else 'explain'
            s['concern_result']=answer_concern(state,s['concern_id'],choice)
        add_memory(state,'owner_meeting',f'{w.name} discussed {s["topic"]} with the owner; {spoken}',
                   [w.id],intensity=60,relationship_effect=relation_delta)
        state.interactions.append(dict(year=state.year,week=state.week,wrestler_id=w.id,topic=s['topic'],
                                       narrative=spoken,morale_delta=morale_delta,owner_relationship_delta=relation_delta))
        state.news.append(f'Private meeting with {w.name}: {spoken}')
    return meeting_view(state,s)


def begin_contract(state: GameState, wrestler_id: str):
    w=state.wrestlers.get(wrestler_id)
    if not w or w.company_id not in (None,state.player_company_id): raise ValueError('This wrestler has an exclusive rival contract')
    from .world import prospect_discovered
    if w.company_id is None and not prospect_discovered(state,wrestler_id):
        raise ValueError('You must scout this independent wrestler before opening contract talks')
    if any(x['wrestler_id']==wrestler_id and x.get('year')==state.year and x.get('week')==state.week for x in state.contract_sessions.values()):
        raise ValueError('You already negotiated with this wrestler this week; wait for the next week')
    expected=int(450+rating_breakdown(w)['market_value']*27+w.attributes['ambition']*15)
    if w.company_id==state.player_company_id: expected=max(expected,int(w.salary_weekly*1.04))
    key=state.generate_id('negotiation')
    session=dict(id=key,wrestler_id=wrestler_id,year=state.year,week=state.week,status='active',round=0,asking_salary=expected,
                 requested_weeks=52,opening_ask=expected,history=[],counter_offer=None)
    state.contract_sessions[key]=session
    return contract_view(state,session)


def contract_view(state, session):
    w=state.wrestlers[session['wrestler_id']]
    return {**session,'wrestler_name':w.name,'personality':w.personality,'owner_relationship':w.owner_relationship,
            'morale':w.morale,'current_salary':w.salary_weekly,'contract_weeks':w.contract_weeks,
            'free_agent':w.company_id is None}


def answer_contract(state: GameState, session_id: str, action: str,
                    salary: int=0, weeks: int=52, bonus: int=0) -> dict:
    s=state.contract_sessions.get(session_id)
    if not s or s['status']!='active':raise ValueError('Negotiation is closed')
    w=state.wrestlers[s['wrestler_id']]
    if action=='walk':
        from .memories import add_memory
        add_memory(state,'contract_breakdown',f'Talks with {w.name} ended without agreement.',[w.id],intensity=72,relationship_effect=-1)
        s['status']='walked_away';s['history'].append(dict(actor='owner',text='You end negotiations for now.'))
        return contract_view(state,s)
    if action not in ('offer','compromise'):raise ValueError('Choose offer, compromise or walk')
    if not 4<=weeks<=156 or salary<=0 or bonus<0:raise ValueError('Invalid contract terms')
    if bonus>state.player_company.money:raise ValueError('Insufficient cash for a signing bonus')
    if w.company_id is None and sum(x.company_id==state.player_company_id for x in state.wrestlers.values())>=state.player_company.roster_limit:
        raise ValueError('Roster is full')
    if s['round']>=3:raise ValueError('Too many offers this negotiation')
    rng=random.Random(f'contract-room:{state.seed}:{state.year}:{state.week}:{session_id}:{s["round"]}:{salary}:{weeks}:{bonus}:{action}')
    expected=s['asking_salary']
    effective=salary+bonus/max(weeks,1)
    rapport=w.owner_relationship/25
    personality={'ambitious':-.10,'cooperative':.09,'independent':-.03,'volatile':-.13,'balanced':0}[w.personality]
    willingness=clamp(.20+(effective/expected-.75)*1.10+rapport*.16+personality +
                      (.08 if action=='compromise' else 0) + rng.uniform(-.035,.035),.03,.97)
    # Once the wrestler states explicit salary/term demands, meeting them closes
    # the deal; the asking price must not drift upward after an accepted counter.
    outstanding=s.get('counter_offer')
    meets_counter=(outstanding is not None and salary>=outstanding['salary_weekly']
                   and weeks>=outstanding['weeks']
                   and bonus>=outstanding['signing_bonus'])
    accepted=meets_counter or rng.random()<willingness
    s['round']+=1
    s['history'].append(dict(actor='owner',text=f'Offer: ${salary:,}/week for {weeks} weeks, bonus ${bonus:,}.'+(' Proposed compromise.' if action=='compromise' else '')))
    if accepted:
        state.player_company.money-=bonus
        w.company_id=state.player_company_id;w.salary_weekly=salary;w.contract_weeks=weeks
        w.morale=clamp(w.morale+.45,0,25);w.owner_relationship=clamp(w.owner_relationship+.6,0,25)
        s['status']='signed';reply=f'{w.name} agrees. We have a deal.'
        from .memories import add_memory
        add_memory(state,'contract_signed',f'{w.name} agreed to a {weeks}-week contract.',[w.id],intensity=75,relationship_effect=1)
        from .world import add_world_news
        add_world_news(state,'signing',f'Aurora signs {w.name}',f'{weeks}-week contract agreed.',state.player_company_id)
    else:
        counter=max(salary+100,int(max(expected,salary)*(.92 if action=='compromise' else .98)))
        s['asking_salary']=counter
        s['counter_offer']=dict(salary_weekly=counter,weeks=weeks,signing_bonus=bonus)
        reply=f'{w.name} counters at ${counter:,}/week.'
        if s['round']>=3: s['status']='rejected';reply=f'{w.name} walks away after the final offer.'
        w.owner_relationship=clamp(w.owner_relationship-.15,0,25)
    s['history'].append(dict(actor=w.name,text=reply))
    return {**contract_view(state,s),'last_chance':round(willingness,3),'accepted':accepted}
