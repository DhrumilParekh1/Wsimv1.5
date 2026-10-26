"""V1.0 persistent card expectations, wrestler chemistry and monetary market valuation.
All state mutations are deterministic for the same seed, week and choice.
"""
from __future__ import annotations
import random
from statistics import mean
from .models import GameState, clamp
from .ratings import rating_breakdown

TIERS = ('jobber', 'lower_mid_card', 'mid_card', 'upper_mid_card', 'main_event')
EXPECTED_APPEARANCES = {'jobber': 0.20, 'lower_mid_card': 0.35, 'mid_card': 0.50,
                        'upper_mid_card': 0.70, 'main_event': 0.90}


def monetary_value(w, state=None):
    """Indicative acquisition/earning value (USD), not a guaranteed transfer price.
    A performer with zero current salary (free agent) is still valuable.
    """
    r = rating_breakdown(w)
    ann_salary = 52 * max(w.salary_weekly, 600 + 36 * r['current_ability'])
    market = r['market_value'] / 100
    draw = (r['commercial'] / 100) ** 1.55
    projected_revenue = 275000 * draw * (0.55 + market)
    audience_multiplier = 1 + max(0, r['demand'] - 50) / 95
    potential_premium = max(0, r['potential_ability'] - r['current_ability']) * 6800
    contract_premium = min(1.5, w.contract_weeks / 52) * ann_salary * .22
    unavailability_discount = .78 if w.injury else 1.0
    value = ((ann_salary * (1.1 + 2.7 * market)) + projected_revenue * audience_multiplier
             + potential_premium + contract_premium) * unavailability_discount
    return int(round(max(25000, value) / 1000) * 1000)


def pair_key(a, b):
    return ':'.join(sorted((a, b)))


def pair_chemistry(state, a, b):
    if a == b: return 50.0
    key = pair_key(a, b)
    if key in state.chemistry: return float(state.chemistry[key]['score'])
    wa, wb = state.wrestlers[a], state.wrestlers[b]
    relationship = (wa.relationships.get(b, 12.5) + wb.relationships.get(a, 12.5)) / 2
    history = sum(1 for story in state.storylines.values() if a in story.wrestler_ids and b in story.wrestler_ids)
    ring_fit = 100 - abs(wa.attributes['workrate'] - wb.attributes['workrate']) * 2.5
    character_fit = 100 - abs(wa.attributes['character_work'] - wb.attributes['character_work']) * 2.5
    familiarity = min(100, history * 14 + (wa.attributes['experience'] + wb.attributes['experience']) * .9)
    # Five separate influences; never overwhelmingly determined by one.
    score = clamp(.27 * relationship * 4 + .24 * ring_fit + .17 * character_fit +
                  .17 * familiarity + .15 * 65, 0, 100)
    state.chemistry[key] = {'score': round(score, 2), 'appearances': 0,
                             'recent_quality': [], 'history': []}
    return round(score, 2)


def after_pair_segment(state, ids, quality, kind):
    for i, a in enumerate(ids):
        for b in ids[i+1:]:
            old = pair_chemistry(state, a, b)
            key = pair_key(a, b)
            entry = state.chemistry[key]
            pair_rel = (state.wrestlers[a].relationships.get(b, 12.5) +
                        state.wrestlers[b].relationships.get(a, 12.5))/2 * 4
            rng = random.Random(f'chem:{state.seed}:{state.year}:{state.week}:{a}:{b}:{entry["appearances"]}')
            delta = .13 * (quality - 65) / 10 + .10 * (pair_rel - 50)/20 + rng.triangular(-.22,.22,0)
            # A betrayal may lower real relationship while producing great on-screen chemistry.
            entry['score'] = round(clamp(old + delta, 0, 100), 2)
            entry['appearances'] += 1
            entry['recent_quality'] = (entry['recent_quality'] + [round(quality,1)])[-6:]
            entry['history'] = (entry['history'] + [{'week':state.week,'kind':kind,'delta':round(delta,2)}])[-20:]


def set_tier(state, wrestler_id, tier):
    w = state.wrestlers.get(wrestler_id)
    if not w or w.company_id != state.player_company_id:
        raise ValueError('Only your own wrestler may have their roster tier changed')
    if tier not in TIERS: raise ValueError('Unknown roster tier')
    old = w.card_tier
    if old == tier: return {'wrestler_id':w.id,'card_tier':tier,'change':'unchanged'}
    downgrade = TIERS.index(tier) < TIERS.index(old)
    distance = abs(TIERS.index(tier) - TIERS.index(old))
    if downgrade:
        w.morale = clamp(w.morale - .7 * distance,0,25)
        w.owner_relationship = clamp(w.owner_relationship - .6 * distance,0,25)
        queue_problem(state,w.id,'status',f'{w.name} challenges the decision to move from {old.replace("_"," ")} to {tier.replace("_"," ")}.', urgency=distance)
    else:
        w.morale = clamp(w.morale + .5 * distance,0,25)
        w.owner_relationship = clamp(w.owner_relationship + .2,0,25)
    w.card_tier=tier
    return {'wrestler_id':w.id,'card_tier':tier,'previous_tier':old,'change':'demotion' if downgrade else 'promotion'}


def queue_problem(state,wid,kind,description,urgency=1):
    key=f'{state.year}-{state.week}-{kind}-{wid}'
    if any(e['id']==key for e in state.talent_concerns): return
    state.talent_concerns.append({'id':key,'wrestler_id':wid,'kind':kind,'title':description,
                                  'year':state.year,'week':state.week,'urgency':urgency,
                                  'status':'open','outcome':None})


def concerns(state):
    return [x for x in state.talent_concerns if x['status']=='open' and
            state.wrestlers.get(x['wrestler_id']) and state.wrestlers[x['wrestler_id']].company_id==state.player_company_id]


def answer_concern(state, concern_id, choice):
    issue = next((i for i in concerns(state) if i['id']==concern_id),None)
    if not issue: raise ValueError('Concern is unavailable or already resolved')
    if choice not in ('promise','explain','firm'): raise ValueError('Choose promise, explain or firm')
    w=state.wrestlers[issue['wrestler_id']]
    rng=random.Random(f'issue:{state.seed}:{concern_id}:{choice}')
    receptiveness=(w.morale + w.owner_relationship + w.attributes['professionalism'])/75
    personality={'ambitious':-.14,'cooperative':.14,'independent':-.04,'volatile':-.20,'balanced':0}[w.personality]
    odds=clamp(.36 + .35*receptiveness + personality + {'promise':.13,'explain':0,'firm':-.22}[choice],.05,.93)
    accepted=rng.random()<odds
    mod=({'promise':1.1,'explain':.45,'firm':-.4}[choice]) if accepted else -({'promise':.8,'explain':.55,'firm':1.3}[choice])
    w.owner_relationship=clamp(w.owner_relationship+mod,0,25)
    w.morale=clamp(w.morale+mod*.7,0,25)
    if choice=='promise':
        state.assignments[f'playing-time-{w.id}-{state.year}-{state.week}']={
            'wrestler_id':w.id,'due_ordinal':(state.year-2026)*52+state.week+3,
            'expected_shows': max(1,round(EXPECTED_APPEARANCES[w.card_tier]*3)),
            'start_count':sum(1 for x in state.talent_appearances.get(w.id,[]) if x['booked']),
            'fulfilled':False}
    issue['status']='resolved';issue['outcome']=choice
    state.news.append(f'Private meeting with {w.name}: {"understood the explanation" if accepted else "left dissatisfied"}.')
    from .memories import add_memory
    add_memory(state,'booking_concern',f'{w.name} raised a {issue["kind"]} concern; you chose {choice}.',
               [w.id],intensity=65,relationship_effect=round(mod,2))
    return {'accepted':accepted,'relationship_change':round(mod,2),'wrestler_id':w.id,
            'narrative':f'{w.name} {"accepts" if accepted else "questions"} your {choice} response.'}


def weekly_playtime(state, year, week):
    for w in state.wrestlers.values():
        if w.company_id != state.player_company_id: continue
        appeared = any(s.week==week and s.simulated and
                       s.result and s.result.get('year',year)==year and
                       any(w.id in seg.wrestler_ids for seg in s.segments)
                       for s in state.shows.values())
        recent=state.talent_appearances.setdefault(w.id,[])
        losses=sum(1 for sh in state.shows.values() if sh.week==week and sh.simulated and
                   sh.result and sh.result.get('year',year)==year for seg in sh.segments
                   if seg.kind=='match' and w.id in seg.wrestler_ids and seg.planned_winner_id!=w.id)
        recent.append({'year':year,'week':week,'booked':appeared,'losses':losses})
        state.talent_appearances[w.id]=recent[-12:]
        # Grace period: evaluate only after three shows have accumulated.
        if len(recent)>=3 and not w.injury:
            recent_window=recent[-4:]
            observed=sum(x['booked'] for x in recent_window)/len(recent_window)
            expected=EXPECTED_APPEARANCES[w.card_tier]
            if w.card_tier=='main_event' and sum(x.get('losses',0) for x in recent_window)>=2:
                queue_problem(state,w.id,'protection',f'{w.name} is concerned about being protected as a main-event star after recent losses.')
                w.morale=clamp(w.morale-.25,0,25)
            if observed+0.16<expected:
                w.morale=clamp(w.morale-.22,0,25)
                queue_problem(state,w.id,'playing_time',f'{w.name} expects a {w.card_tier.replace("_"," ")} role and more appearances ({sum(x["booked"] for x in recent_window)}/{len(recent_window)} recent shows).')
        for key,a in state.assignments.items():
            if not key.startswith('playing-time-') or a.get('fulfilled') or a['wrestler_id']!=w.id:continue
            ordinal=(year-2026)*52+week
            if ordinal>=a['due_ordinal']:
                count=sum(1 for x in state.talent_appearances[w.id] if
                          (x['year']-2026)*52+x['week'] > a['due_ordinal']-3 and x['booked'])
                success=count>=a['expected_shows']
                w.owner_relationship=clamp(w.owner_relationship+(1.2 if success else -2),0,25)
                w.morale=clamp(w.morale+(.7 if success else -1.4),0,25)
                a['fulfilled']=True
                state.news.append(f'{w.name}: {"playing-time commitment kept" if success else "playing-time promise broken"}.')
