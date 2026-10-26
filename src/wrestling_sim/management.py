"""Creative staff, media appearances, and wrestler-owner interactions.

All entries are fictional. Stable pseudo-random outcomes make reloading reproducible.
"""
from __future__ import annotations
import random
from .models import GameState, clamp

CREATIVE_MARKET = {
    'morgan': {'id':'morgan', 'name':'Morgan Reed', 'skill':13, 'salary_weekly':600, 'signing_fee':0, 'company_id':'player', 'specialty':'balanced'},
    'sato': {'id':'sato', 'name':'Hana Sato', 'skill':21, 'salary_weekly':2600, 'signing_fee':18000, 'company_id':None, 'specialty':'long-form stories'},
    'brook': {'id':'brook', 'name':'Elliot Brook', 'skill':18, 'salary_weekly':1500, 'signing_fee':8000, 'company_id':None, 'specialty':'character building'},
    'vega': {'id':'vega', 'name':'Casey Vega', 'skill':23, 'salary_weekly':4500, 'signing_fee':38000, 'company_id':'rival', 'specialty':'main-event drama'},
}


def creative_head(state: GameState) -> dict:
    return CREATIVE_MARKET.get(state.creative_head_id, CREATIVE_MARKET['morgan'])


def staff_market(state: GameState) -> list[dict]:
    return [{**head, 'employed': key == state.creative_head_id,
             'buyout': int(head['signing_fee'] * (2 if head['company_id'] == 'rival' else 1))}
            for key, head in CREATIVE_MARKET.items()]


def sign_creative_head(state: GameState, head_id: str) -> dict:
    head = CREATIVE_MARKET.get(head_id)
    if not head:
        raise ValueError('Unknown creative head')
    if head_id == state.creative_head_id:
        raise ValueError('This creative head already works for you')
    cost = head['signing_fee'] * (2 if head['company_id'] == 'rival' else 1)
    if state.player_company.money < cost:
        raise ValueError('Not enough cash to sign or buy out this creative head')
    state.player_company.money -= cost
    state.creative_head_id = head_id
    state.news.append(f"{head['name']} joins as head of creative. Signing and buyout costs: ${cost:,}.")
    return {'staff': head['name'], 'skill': head['skill'], 'fee': cost}


def advise_openings(state: GameState, story, openings: dict) -> list[dict]:
    head = creative_head(state)
    # Skill improves the chance of ranking a sensible recommendation, never guarantees success.
    rng = random.Random(f"advice:{state.seed}:{state.year}:{state.week}:{story.id}:{head['id']}")
    evaluation = {}
    for key, opening in openings.items():
        fit = (.40 * story.coherence + .32 * story.fan_investment + .28 * story.hype) / 100
        if key == 'mind_games': fit += (65 - story.coherence) / 200
        elif key == 'challenge': fit += (story.hype - 45) / 230
        else: fit += (story.coherence - 65) / 250
        # Less skilled writers introduce significantly more noise in analysis.
        evaluation[key] = fit + rng.uniform(-1, 1) * (26-head['skill']) / 35
    best = max(evaluation, key=evaluation.get)
    return [{'id':key, 'label':val['label'], 'hint':val['hint'],
             'recommended':key == best,
             'advice':f"{head['name']} {'recommends this route' if key == best else 'sees this as an alternative'}"}
            for key,val in openings.items()]


def media_opportunity(state: GameState) -> dict:
    return {'id': f"media-{state.year}-{state.week}", 'title': 'Regional media appearance',
            'description':'A fictional partner wants a wrestler for a regional interview and promotional campaign.',
            'energy_cost': 8, 'reward': 1800 + int(state.player_company.sponsor_interest * 12)}


def assign_media(state: GameState, wrestler_id: str) -> dict:
    opp = media_opportunity(state)
    if opp['id'] in state.assignments:
        raise ValueError('This media opportunity has already been resolved this week')
    w = state.wrestlers.get(wrestler_id)
    if not w or w.company_id != state.player_company_id:
        raise ValueError('Select a wrestler on your own roster')
    if w.fatigue > 22 or w.availability < 25:
        raise ValueError('This wrestler is too exhausted or unavailable')
    rng = random.Random(f"media:{state.seed}:{state.year}:{state.week}:{wrestler_id}")
    willingness = clamp(.12 + .016*w.owner_relationship + .012*w.attributes['professionalism']
                        + .009*w.attributes['loyalty'] - .008*w.fatigue
                        + (.10 if w.personality == 'cooperative' else -.12 if w.personality == 'independent' else 0), .10, .97)
    accepted = rng.random() < willingness
    if accepted:
        w.fatigue = clamp(w.fatigue + 2.0, 0, 25)  # 8% energy cost
        delta = 0.35 + .8 * w.attributes['promotion'] / 25
        state.player_company.sponsor_interest = clamp(state.player_company.sponsor_interest + delta)
        state.player_company.money += opp['reward']
        state.financial_history.append({'year':state.year,'week':state.week,'reason':'media_promotion','net':opp['reward'],'media':opp['reward']})
        w.attributes['relevance'] = clamp(w.attributes['relevance'] + .16, 0, 25)
        narrative = f"{w.name} represented your promotion in a media appearance, earning ${opp['reward']:,}."
    else:
        w.owner_relationship = clamp(w.owner_relationship - .4, 0, 25)
        narrative = f"{w.name} declined the media appearance. Their schedule and relationship with management influenced the answer."
    result = {'opportunity_id':opp['id'], 'wrestler_id':w.id, 'accepted':accepted,
              'chance':round(willingness, 3), 'narrative':narrative, 'energy_delta':-8 if accepted else 0}
    state.assignments[opp['id']] = result
    state.news.append(narrative)
    state.activity_log.append({'type':'media', **result})
    return result


INTERACTIONS = {'listen':'Their concerns', 'push':'A bigger push',
                'contract':'Contract expectations', 'boundary':'Firm expectations'}


def interact_wrestler(state: GameState, wrestler_id: str, topic: str) -> dict:
    w = state.wrestlers.get(wrestler_id)
    if not w or w.company_id != state.player_company_id:
        raise ValueError('You may only meet with your own wrestlers')
    if topic not in INTERACTIONS:
        raise ValueError('Unknown conversation topic')
    # One interaction per wrestler per week, so choices have consequences.
    if any(it['year']==state.year and it['week']==state.week and it['wrestler_id']==w.id
           for it in state.interactions):
        raise ValueError('You have already met this wrestler this week')
    rng = random.Random(f"interaction:{state.seed}:{state.year}:{state.week}:{w.id}:{topic}")
    rapport = (w.owner_relationship + w.attributes['professionalism'] + w.morale) / 3
    response = clamp(.20 + rapport / 35 + rng.uniform(-.14, .14)
                     + (.09 if w.personality == 'cooperative' else -.12 if w.personality == 'volatile' else 0), .1, .96)
    receptive = rng.random() < response
    morale_effect, relation_effect = {
        'listen': (.45, .9), 'push': (1.15,.65),
        'contract': (.32, .28), 'boundary': (-.55,-.65)
    }[topic]
    if not receptive:
        morale_effect *= -.65
        relation_effect *= -.6
    w.morale = clamp(w.morale + morale_effect, 0, 25)
    w.owner_relationship = clamp(w.owner_relationship + relation_effect, 0, 25)
    if topic == 'push' and receptive:
        state.assignments[f"push-{state.year}-{state.week}-{w.id}"] = {'wrestler_id':w.id, 'due_week':state.week+2,'fulfilled':False}
    if topic == 'contract':
        narrative = f"{w.name} discussed pay and contract security. {'The conversation was constructive.' if receptive else 'No agreement was reached.'}"
    else:
        narrative = f"You spoke with {w.name} about {INTERACTIONS[topic].lower()}. {'They responded positively.' if receptive else 'They remain unconvinced.'}"
    result = {'wrestler_id':w.id,'topic':topic,'year':state.year,'week':state.week,
              'receptive':receptive,'narrative':narrative,'morale_delta':round(morale_effect,2),
              'owner_relationship_delta':round(relation_effect,2)}
    state.interactions.append(result)
    state.news.append(narrative)
    return result


def creative_tasks(state: GameState) -> list[dict]:
    """Structured commitments, shared by the inbox, booker and simulator."""
    tasks=[]
    for story in state.storylines.values():
        plan=story.planned_beat
        if story.stage=='resolved' or not plan or plan.get('fulfilled'):continue
        kind=plan['kind']
        expected_ids = plan.get('wrestler_ids', story.wrestler_ids[:2])
        names=[state.wrestlers[wid].name for wid in expected_ids]
        title={'match':f'{names[0]} vs {names[1]} — The Showdown',
               'promo':f'{names[0]} Sends a Message',
               'confrontation':f'{names[0]} Confronts {names[1]}',
               'betrayal':f'Trust Broken: {names[0]} and {names[1]}',
               'backstage':f'Tension Behind the Curtain'}.get(kind,f'{story.title}: New Chapter')
        tasks.append(dict(id=story.id,storyline_id=story.id,storyline_title=story.title,
                          title=title,kind=kind,wrestler_ids=expected_ids,
                          performer_names=names,division=state.wrestlers[expected_ids[0]].division,
                          duration=18 if kind=='match' else 8,
                          deadline_ordinal=plan.get('due_ordinal'),
                          description=f'Creative promise: {kind.replace("_"," ")} involving {" & ".join(names)}. Deliver by the deadline.',
                          status='booked' if any(seg.storyline_id==story.id and seg.kind==kind
                             and set(seg.wrestler_ids)==set(expected_ids)
                             for show in state.shows.values() if show.week==state.week for seg in show.segments) else 'pending'))
    return tasks


def decline_media(state: GameState) -> dict:
    opp = media_opportunity(state)
    if opp['id'] in state.assignments:
        raise ValueError('Media request already resolved')
    result = {'opportunity_id': opp['id'], 'accepted': False, 'declined_by_owner': True,
              'narrative': 'You declined the media appearance this week.'}
    state.assignments[opp['id']] = result
    state.news.append(result['narrative'])
    return result


def cancel_creative_commitment(state: GameState, storyline_id: str) -> dict:
    storyline = state.storylines.get(storyline_id)
    if not storyline or not storyline.planned_beat or storyline.planned_beat.get('fulfilled'):
        raise ValueError('There is no pending creative promise for this storyline')
    storyline.planned_beat = {}
    storyline.coherence = clamp(storyline.coherence - 4)
    storyline.hype = clamp(storyline.hype - 2)
    state.player_company.fan_trust = clamp(state.player_company.fan_trust - 1.0)
    note = f'You cancelled the planned segment for {storyline.title}. Fans lost some trust.'
    state.news.append(note)
    return {'cancelled': True, 'narrative': note}
