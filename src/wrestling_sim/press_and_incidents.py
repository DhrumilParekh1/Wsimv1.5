"""Deterministic, data-driven press conferences and random backstage/world events.
144+ question variants and 240+ incident variants; each is an actual choice with effects.
"""
from __future__ import annotations
import random
from .models import GameState, clamp

PRESS_TOPICS = [
 ('future', 'What is the long-term plan for {name} after recent events?'),
 ('future', 'Can {name} remain a central figure as the roster evolves?'),
 ('booking', 'Why have you been giving {name} so much television time?'),
 ('booking', 'Is {name} being overlooked by your creative direction?'),
 ('titles', 'Does {name} deserve a championship opportunity?'),
 ('titles', 'How will you protect the prestige of the championships?'),
 ('rivals', 'Can your promotion compete with {rival} for viewers?'),
 ('rivals', 'Are you worried {rival} will approach your biggest names?'),
 ('business', 'What is your plan to increase weekly television viewership?'),
 ('business', 'Are your sponsorship deals enough to support your ambitions?'),
 ('adversity', 'How do you recover after an underwhelming main event?'),
 ('adversity', 'What would you say to fans frustrated by recent booking?'),
 ('locker_room', 'Are you concerned about tension behind the scenes?'),
 ('locker_room', 'How will you maintain trust with the locker room?'),
 ('creative', 'Would you ever change the current alignment of {name}?'),
 ('creative', 'How do you balance surprises against audience expectations?'),
 ('future', 'Could {name} be a cornerstone of the promotion next year?'),
 ('business', 'Would you prioritize profitability over expanding the roster?'),
]
PRESS_FRAMES = [
 'At the weekly media briefing, a journalist asks: {question}',
 'Following a difficult show, a reporter presses you: {question}',
 'At a sponsor-sponsored media event, a question is raised: {question}',
 'An independent wrestling publication asks: {question}',
 'At the pre-show press conference, a journalist asks: {question}',
 'After a viral online debate, you are asked: {question}',
 'A regional broadcaster wants clarification: {question}',
 'During a live fan Q&A, a moderator asks: {question}',
 'During a post-show media scrum, a correspondent asks: {question}',
 'At an international press event, a journalist asks: {question}',
 'During a televised industry roundtable, a host asks: {question}',
 'Inside an open training session, an interviewer asks: {question}',
]
# 18 x 12 = 216 question templates, instantiated with actual wrestlers/rival companies.
PRESS_CHOICES = [
 {'id':'back','label':'Publicly back your wrestler','hint':'Higher loyalty; risks overpromising'},
 {'id':'candid','label':'Give an honest, measured answer','hint':'Fan trust and credibility'},
 {'id':'deflect','label':'Keep your plans private','hint':'Protect flexibility, may disappoint fans'},
 {'id':'challenge','label':'Set an ambitious public target','hint':'Major hype potential; makes a promise'},
 {'id':'neutral','label':'Stay neutral and avoid commitments','hint':'Minimal immediate effect on fans or talent'},
]

INCIDENT_TEMPLATES = [
 ('friendship','{a} and {b} formed an unexpected friendship during training.'),
 ('argument','{a} and {b} had a disagreement about match preparation.'),
 ('mentoring','{a} offered to mentor {b} ahead of the next show.'),
 ('creative','{a} is unhappy with how {b} is featured in the storyline.'),
 ('workout','{a} volunteered for extra conditioning after a difficult appearance.'),
 ('media','{a} was praised by a local journalist for a candid interview.'),
 ('lateness','{a} arrived late to a production meeting.'),
 ('chemistry','{a} and {b} impressed producers during a rehearsal.'),
 ('rehearsal','{a} struggled in a rehearsal with {b}.'),
 ('rumour','A journalist is spreading an unverified story about {a}.'),
 ('community','{a} was invited to represent the promotion at a charity event.'),
 ('sponsor','A potential brand partner is interested in featuring {a}.'),
 ('jealousy','{a} reportedly resents the attention {b} has received.'),
 ('coach','{a} disagrees with the coaching plan provided by management.'),
 ('fan','Fan interest in {a} is climbing after an unexpected online clip.'),
 ('slump','{a} admits to struggling with motivation after several quiet weeks.'),
 ('teamwork','{a} publicly congratulated {b} on a strong match.'),
 ('contract','{a} has privately asked about the long-term direction of the company.'),
 ('equipment','A production equipment problem threatens the next appearance by {a}.'),
 ('scheduling','A travel scheduling conflict may affect {a} and {b}.'),
 ('social','An online disagreement between supporters of {a} and {b} is attracting attention.'),
 ('opportunity','A streaming platform requested a special appearance by {a}.'),
 ('leadership','{a} stepped in to help settle a disagreement involving {b}.'),
 ('celebration','{a} and {b} celebrated a personal career milestone together.'),
 ('scuffle','A disagreement between {a} and {b} turned into a brief backstage scuffle.'),
]
INCIDENT_FRAMES = [
 '{description}', 'Your head writer reports: {description}',
 'A locker-room source tells you: {description}', 'The production team flags this: {description}',
 'An agent contacts you: {description}', 'The morning briefing notes: {description}',
 'A backstage message arrives: {description}', 'Your manager privately informs you: {description}',
 'A regional reporter mentions: {description}', 'A staff member requests your attention: {description}',
]
# 24 x 10 = 240 incident templates, with variable wrestlers and seeded intensity.
# Incident-specific decisions. The ids are persistent save-game values.
OPTION_SETS = {
 'mentoring': [('approve','Approve the mentorship'),('trial','Arrange a two-week trial'),('coach','Involve the coaching department'),('decline','Decline respectfully')],
 'friendship': [('encourage','Encourage their partnership'),('acknowledge','Congratulate them'),('leave','Let the friendship develop naturally')],
 'celebration': [('celebrate','Recognise their milestone'),('private','Congratulate them privately'),('leave','Let them enjoy the moment')],
 'teamwork': [('praise','Praise the teamwork'),('build','Explore future collaboration'),('leave','Leave the arrangement alone')],
 'chemistry': [('praise','Praise their chemistry'),('rehearse','Schedule more joint practice'),('leave','Keep preparations unchanged')],
 'leadership': [('recognise','Recognise their leadership'),('responsibility','Give them more responsibility'),('leave','Keep the current setup')],
 'argument': [('listen','Hear both sides separately'),('mediate','Arrange mediation'),('warn','Issue a conduct warning'),('delegate','Ask management to investigate')],
 'scuffle': [('separate','Separate the wrestlers and investigate'),('mediate','Hold a mediated meeting'),('discipline','Take disciplinary action'),('delegate','Refer it to senior staff')],
 'jealousy': [('listen','Discuss their concerns privately'),('clarify','Clarify booking opportunities'),('mediate','Arrange a joint meeting'),('delegate','Ask the creative head to review')],
 'creative': [('review','Review storyline roles'),('promise','Offer a specific future opportunity'),('explain','Explain the current creative plan'),('delegate','Refer to the creative head')],
 'rehearsal': [('practice','Schedule extra rehearsal'),('coach','Assign technical support'),('reduce','Reduce the segment complexity'),('leave','Proceed without changes')],
 'workout': [('approve','Approve additional training'),('recover','Recommend a recovery session'),('coach','Request a fitness assessment'),('leave','Maintain the current plan')],
 'coach': [('review','Review the coaching assignment'),('mediate','Discuss expectations with both'),('switch','Offer a different coach'),('leave','Keep the plan unchanged')],
 'lateness': [('listen','Ask for an explanation'),('warn','Give a formal warning'),('excuse','Excuse this incident'),('delegate','Let staff review the matter')],
 'slump': [('support','Offer personal support'),('rest','Offer a lighter schedule'),('coach','Arrange a coaching session'),('challenge','Set an achievable performance target')],
 'contract': [('meet','Arrange a contract meeting'),('review','Promise a contract review'),('explain','Explain the current contract'),('leave','Maintain the existing terms')],
 'media': [('promote','Feature the wrestler in publicity'),('praise','Acknowledge the positive coverage'),('leave','Avoid extra publicity')],
 'fan': [('promote','Build a campaign around the attention'),('observe','Wait to see if interest lasts'),('feature','Increase their on-screen exposure')],
 'social': [('respond','Publish a balanced response'),('ignore','Avoid amplifying the dispute'),('engage','Ask both wrestlers to address fans')],
 'community': [('approve','Approve the appearance'),('schedule','Find a suitable date'),('decline','Decline the invitation')],
 'opportunity': [('accept','Accept the appearance'),('negotiate','Negotiate better terms'),('decline','Decline the offer')],
 'sponsor': [('pitch','Prepare a sponsorship proposal'),('enquire','Request the partner’s terms'),('decline','Do not pursue this deal')],
 'rumour': [('investigate','Investigate the rumour'),('statement','Release a factual statement'),('ignore','Do not amplify unverified claims')],
 'equipment': [('repair','Fund an urgent repair'),('adapt','Change the production plan'),('delegate','Ask production staff to resolve it')],
 'scheduling': [('reschedule','Adjust the travel schedule'),('delegate','Ask logistics to find a solution'),('adapt','Modify the planned appearance')],
}
LEGACY_OPTIONS = [('support','Offer support and practical help'),('mediate','Bring everyone together'),('discipline','Establish clear professional standards'),('delegate','Ask your staff to handle it')]
def incident_options(kind):
    return [{'id':k,'label':v} for k,v in OPTION_SETS.get(kind,LEGACY_OPTIONS)]


def _rng(state, marker):return random.Random(f'v1:{state.seed}:{state.year}:{state.week}:{marker}')


def ensure_incidents(state):
    current=[i for i in state.incidents if i['year']==state.year and i['week']==state.week]
    if len(current)>=2:return current
    roster=[w for w in state.wrestlers.values() if w.company_id==state.player_company_id]
    if not roster:return []
    rng=_rng(state,'incidents')
    used={wid for incident in current for wid in incident.get('wrestler_ids',[])}
    recent=[i for i in state.incidents if (state.year-i['year'])*52+state.week-i['week']<=3]
    hostile={'argument','creative','jealousy','scuffle','rumour','lateness','slump'}
    for index in range(len(current),2):
        eligible=[w for w in roster if w.id not in used]
        if not eligible: eligible=roster
        a=rng.choice(eligible)
        available=[w for w in roster if w.id!=a.id and w.id not in used]
        if not available: available=[w for w in roster if w.id!=a.id]
        b=rng.choice(available or [a])
        recent_types={i['kind'] for i in recent if a.id in i.get('wrestler_ids',[])}
        types=[]
        for kind,body in INCIDENT_TEMPLATES:
            if kind in recent_types: continue
            if kind in hostile and a.personality=='cooperative': continue
            if kind in ('argument','scuffle','jealousy') and a.relationships.get(b.id,12.5)>18: continue
            weight=3 if kind in ('mentoring','friendship','media','community','workout','teamwork','celebration') else 1
            if kind in hostile and a.personality=='volatile': weight+=2
            types.extend([(kind,body)]*weight)
        if not types:types=[('media',INCIDENT_TEMPLATES[5][1])]
        kind,body=rng.choice(types)
        description=body.format(a=a.name,b=b.name)
        frame=rng.choice(INCIDENT_FRAMES)
        involved=[a.id] if kind in {'workout','media','lateness','rumour','community','sponsor','coach','fan','slump','contract','equipment','opportunity'} else [a.id,b.id]
        state.incidents.append({'id':f'incident-{state.year}-{state.week}-{index}', 'year':state.year,
            'week':state.week,'kind':kind,'title':description,'description':frame.format(description=description),
            'wrestler_ids':involved, 'status':'open','choice':None,
            'severity':rng.choice(['minor']*39+['moderate']*17+['major']*3+['critical']),
            'options':incident_options(kind)})
        used.update(involved)
    return [i for i in state.incidents if i['year']==state.year and i['week']==state.week]


def pending_incidents(state):
    ensure_incidents(state)
    return [i for i in state.incidents if i['status']=='open']


def answer_incident(state,incident_id,choice):
    event=next((i for i in pending_incidents(state) if i['id']==incident_id),None)
    if not event:raise ValueError('Incident unavailable or already resolved')
    options=event.get('options') or incident_options(event['kind'])
    if choice not in [o['id'] for o in options] and choice not in ('support','mediate','discipline','delegate'):
        raise ValueError('Unknown incident response')
    if choice not in [o['id'] for o in options]:
        options=incident_options(event['kind'])+[{'id':k,'label':v} for k,v in LEGACY_OPTIONS]
    rng=_rng(state,incident_id+choice)
    primary=state.wrestlers[event['wrestler_ids'][0]]
    secondary=state.wrestlers[event['wrestler_ids'][-1]]
    personality={'cooperative':.13,'ambitious':-.04,'volatile':-.19,'independent':-.09,'balanced':0}[primary.personality]
    chance=clamp(.55 + personality + (primary.owner_relationship-12.5)/110+
                 {'decline':-.15,'discipline':-.13,'warn':-.08,'ignore':-.08,'leave':-.02,'trial':.05,'coach':.07,'approve':.13,'listen':.09,'mediate':.05,'support':.13,'delegate':-.09,'practice':.1,'investigate':.08,'repair':.14,'adapt':.06,'celebrate':.15,'praise':.13,'accept':.11,'recognise':.14}.get(choice,.04),.07,.95)
    success=rng.random()<chance
    magnitude={'minor':.35,'moderate':1.1,'major':2.3,'critical':5.5}[event['severity']]
    direction=1 if success else -1
    primary.owner_relationship=clamp(primary.owner_relationship+direction*magnitude*.65,0,25)
    primary.morale=clamp(primary.morale+direction*magnitude*.7,0,25)
    relationship_change=direction*magnitude*.6
    for a,b in (((primary,secondary),(secondary,primary)) if primary.id!=secondary.id else ()):
        a.relationships[b.id]=clamp(a.relationships.get(b.id,12.5)+relationship_change,0,25)
    from .front_office import pair_chemistry
    if primary.id != secondary.id:
        pair_chemistry(state,primary.id,secondary.id)
        key=':'.join(sorted(event['wrestler_ids']))
        state.chemistry[key]['score']=round(clamp(state.chemistry[key]['score']+direction*magnitude*.35),2)
    cash_impact=-round(magnitude*250) if choice in ('support','repair','practice','celebrate','promote','approve','coach','accept') else 0
    category=event['kind']
    # Different incident families have different simulation consequences.
    if category in ('media','social','fan','community','sponsor','opportunity'):
        primary.attributes['momentum']=clamp(primary.attributes['momentum']+direction*magnitude*.35,0,25)
        primary.attributes['relevance']=clamp(primary.attributes['relevance']+direction*magnitude*.19,0,25)
        state.player_company.sponsor_interest=clamp(state.player_company.sponsor_interest+direction*magnitude*.4)
        if category in ('sponsor','opportunity') and success:
            cash_impact += round(magnitude*1800)
    elif category in ('workout','mentoring','rehearsal','coach','teamwork'):
        attr='stamina' if category=='workout' else 'technique' if category=='rehearsal' else 'professionalism'
        primary.attributes[attr]=clamp(primary.attributes[attr]+direction*magnitude*.13,0,25)
    elif category in ('argument','scuffle','jealousy','rumour','lateness','creative','slump','contract'):
        primary.attributes['loyalty']=clamp(primary.attributes['loyalty']+direction*magnitude*.18,0,25)
        if not success and event['severity'] in ('major','critical'):
            state.player_company.fan_trust=clamp(state.player_company.fan_trust-magnitude*.5)
    elif category in ('equipment','scheduling') and not success:
        cash_impact -= round(magnitude*2800)
    if event['severity']=='critical':
        state.news.append(f'MAJOR BACKSTAGE DEVELOPMENT: {event["title"]}')
    state.player_company.money+=cash_impact
    state.player_company.fan_trust=clamp(state.player_company.fan_trust+direction*magnitude*.25)
    # Decisions have consequences beyond the generic morale roll.
    if category=='mentoring' and success and choice in ('approve','trial','coach') and primary.id!=secondary.id:
        duration=2 if choice=='trial' else 6
        # Saved as an ongoing arrangement; weeks advance separately.
        arrangements=state.mentorships
        arrangements.append({'mentor_id':primary.id,'student_id':secondary.id,
                             'start_week':state.week,'weeks_remaining':duration,
                             'status':'active','type':choice})
        secondary.attributes['technique']=clamp(secondary.attributes['technique']+.05*magnitude,0,25)
    if category in ('mentoring','teamwork','friendship','chemistry') and success and primary.id!=secondary.id:
        primary.relationships[secondary.id]=clamp(primary.relationships.get(secondary.id,12.5)+.3*magnitude,0,25)
        secondary.relationships[primary.id]=clamp(secondary.relationships.get(primary.id,12.5)+.3*magnitude,0,25)
    if category in ('argument','scuffle','jealousy') and choice=='discipline' and not success:
        primary.morale=clamp(primary.morale-.4*magnitude,0,25)
    if category in ('equipment','scheduling') and success and choice in ('repair','reschedule','adapt'):
        state.player_company.fan_trust=clamp(state.player_company.fan_trust+.2*magnitude)
    # Persistent multi-week aftermath: ordinary resolutions fade, serious friction
    # takes longer, and cooperative outcomes can slowly build trust.
    event['follow_up']={'remaining_weeks':3 if event['severity'] in ('major','critical') else 2,
                        'wrestler_ids':list(event['wrestler_ids']),
                        'positive':bool(success), 'last_processed':None,
                        'severity':event['severity']}
    event['status']='resolved';event['choice']=choice;event['successful']=success
    decision=next(o['label'] for o in options if o['id']==choice)
    event['resolution']={'decision':decision,'success':success,'relationship_delta':round(direction*magnitude*.65,2),
        'morale_delta':round(direction*magnitude*.7,2),'cash_change':cash_impact}
    event['result']=f'Management decision: {decision}. ' + (f'{primary.name} accepted the arrangement; practical follow-up was scheduled.' if success else f'{primary.name} had reservations; the issue may require further attention.')
    state.news.append(event['result'])
    from .memories import add_memory
    add_memory(state,'backstage_incident',event['title']+' '+event['result'],event['wrestler_ids'],
               intensity=55 if event['severity']=='minor' else 85,relationship_effect=round(direction*magnitude,2))
    return {'result':event['result'],'success':success,'cash_change':cash_impact,
            'relationship_delta':round(direction*magnitude*.65,2),'chance':round(chance,3), 'severity':event['severity']}


PRESS_TOPIC_CHOICES = {
    'future': ('We see {name} as a cornerstone','{name} must earn their opportunity','No future plans are confirmed','Expect a huge year for {name}'),
    'booking': ('{name} deserves more screen time','We base time on performance','We will not discuss booking privately','We will feature {name} more prominently'),
    'titles': ('{name} has championship-level ability','Championship chances are earned','Title plans stay confidential','A championship opportunity is coming'),
    'rivals': ('Our talent gives us an advantage','Competition makes the industry stronger','We focus on ourselves','We will overtake {rival} soon'),
    'business': ('Our wrestlers will bring in new viewers','Steady investment matters most','We do not discuss business projections','Viewership will grow significantly'),
    'adversity': ('We stand with our wrestlers','We acknowledge the criticism','We won’t discuss internal matters','Our next event will prove the doubters wrong'),
    'locker_room': ('I trust the locker room','We listen and address concerns','Private matters stay private','Our unity will be stronger than ever'),
    'creative': ('We support {name} in every role','A turn must serve the story','No creative plan will be revealed','Fans should expect a huge surprise'),
}


def contextual_press_options(topic,name,rival):
    labels=PRESS_TOPIC_CHOICES.get(topic,PRESS_TOPIC_CHOICES['future'])
    return [{**item,'label':labels[i].format(name=name,rival=rival)} for i,item in enumerate(PRESS_CHOICES)]


def conference(state):
    key=f'{state.year}-{state.week}'
    if key not in state.press_conferences:
        roster=[w for w in state.wrestlers.values() if w.company_id==state.player_company_id]
        if not roster: return None
        rivals=[c for c in state.companies.values() if c.id!=state.player_company_id]
        rng=_rng(state,'press')
        questions=[]
        for index in rng.sample(range(len(PRESS_TOPICS)*len(PRESS_FRAMES)), 3):
            topic,question=PRESS_TOPICS[index//len(PRESS_FRAMES)]
            frame=PRESS_FRAMES[index%len(PRESS_FRAMES)]
            w=rng.choice(roster);r=rng.choice(rivals)
            text=frame.format(question=question.format(name=w.name,rival=r.name))
            questions.append({'id':f'q-{index}', 'text':text,'topic':topic,
                              'wrestler_id':w.id,'options':contextual_press_options(topic,w.name,r.name),'answer':None,'outcome':None})
        state.press_conferences[key]={'id':key,'week':state.week,'year':state.year,
                                      'questions':questions,'completed':False}
    return state.press_conferences[key]


def _reaction(delta,subject):
    """Audience-scale wording, while keeping exact internal numeric changes."""
    if abs(delta)<.13:
        return f"{subject} remained largely unchanged."
    if delta>.85:
        return f"{subject} responded extremely positively."
    if delta>.35:
        return f"{subject} welcomed the response."
    if delta>0:
        return f"{subject} seemed slightly encouraged."
    if delta<-.85:
        return f"{subject} reacted very negatively."
    if delta<-.35:
        return f"{subject} was disappointed by the response."
    return f"{subject} seemed slightly unimpressed."


def answer_press(state,question_id,choice):
    session=conference(state)
    q=next((q for q in session['questions'] if q['id']==question_id),None)
    if not q or q['answer'] is not None:raise ValueError('Question is not awaiting an answer')
    if choice not in [o['id'] for o in PRESS_CHOICES]:raise ValueError('Unknown press answer')
    w=state.wrestlers[q['wrestler_id']]
    rng=_rng(state,question_id+choice)
    consistency={'back':1.0,'candid':.8,'deflect':-.15,'challenge':1.4,'neutral':0}[choice]
    trust_delta=0.0 if choice=='neutral' else consistency*.32+rng.triangular(-.4,.4,0)
    w_delta=0.0 if choice=='neutral' else {'back':.8,'candid':.25,'deflect':-.2,'challenge':.35}[choice]+rng.triangular(-.25,.25,0)
    if w.personality=='volatile' and choice=='deflect':w_delta-=.4
    state.player_company.fan_trust=clamp(state.player_company.fan_trust+trust_delta)
    w.owner_relationship=clamp(w.owner_relationship+w_delta,0,25)
    sponsor_delta=0 if choice=='neutral' else .3 if choice=='candid' else -.15 if choice=='challenge' else .1
    state.player_company.sponsor_interest=clamp(state.player_company.sponsor_interest+sponsor_delta)
    if choice=='challenge':
        from .front_office import queue_problem
        # Publicly committing to the star creates an additional long-term expectation.
        key=f'press-promise-{w.id}-{state.year}-{state.week}-{q["id"]}'
        state.assignments[key]={'wrestler_id':w.id,'due_week':state.week+3,'fulfilled':False,'kind':'press_push'}
    q['answer']=choice
    q['effects']={'fan_trust':round(trust_delta,3),'owner_relationship':round(w_delta,3),'sponsor_interest':round(sponsor_delta,3)}
    q['outcome']=_reaction(trust_delta,"The audience")+" "+_reaction(w_delta,w.name)
    session['completed']=all(item['answer'] is not None for item in session['questions'])
    state.world_news.append({'year':state.year,'week':state.week,'category':'press','headline':f'{state.player_company.name} owner addresses {q["topic"]} questions',
                             'body':q['text']+' '+q['outcome']})
    return {'outcome':q['outcome'],'completed':session['completed']}
