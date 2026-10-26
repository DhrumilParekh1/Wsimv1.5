"""Persistent rival companies, staff hiring, scouting, coaching, schedule and weekly trends.

Every event is deterministic for a fixed campaign seed and week. The authoring
layer displays the results, never decides them. All names are fictional.
"""
from __future__ import annotations
import random
from dataclasses import asdict
from statistics import mean
from .models import GameState, clamp
from .ratings import rating_breakdown

COACH_MARKET = {
 'coach_fitness': dict(id='coach_fitness', name='Elena Torres', specialty='fitness', skill=20, salary_weekly=1300, signing_fee=2800, personality='supportive', relationship_bias=2, company_id=None),
 'coach_tech': dict(id='coach_tech', name='Kenji Mori', specialty='technical', skill=23, salary_weekly=2300, signing_fee=5200, personality='demanding', relationship_bias=-1, company_id=None),
 'coach_promo': dict(id='coach_promo', name='Maya Cole', specialty='promo', skill=21, salary_weekly=1700, signing_fee=3500, personality='supportive', relationship_bias=3, company_id=None),
 'coach_veteran': dict(id='coach_veteran', name='Graham Price', specialty='technical', skill=14, salary_weekly=550, signing_fee=0, personality='pragmatic', relationship_bias=1, company_id='player'),
 'coach_rival': dict(id='coach_rival', name='Diego Ortiz', specialty='promo', skill=24, salary_weekly=3600, signing_fee=13000, personality='demanding', relationship_bias=-2, company_id='rival'),
}
SCOUT_MARKET = {
 'scout_local': dict(id='scout_local', name='Avery Bennett', skill=13, coverage='regional', salary_weekly=500, signing_fee=0, company_id='player'),
 'scout_national': dict(id='scout_national', name='Samir Khan', skill=20, coverage='national', salary_weekly=1700, signing_fee=4500, company_id=None),
 'scout_global': dict(id='scout_global', name='Yuki Nakamura', skill=24, coverage='global', salary_weekly=3200, signing_fee=12000, company_id=None),
}
TRAINING_STATS={'fitness':('stamina','athleticism','agility'), 'technical':('technique','workrate','selling','sequences'), 'promo':('mic_skills','charisma','character_work','presence')}


def bootstrap_world(state: GameState) -> None:
    if not state.coaches:
        state.coaches = {k: dict(v) for k, v in COACH_MARKET.items()}
    if not state.scouts:
        state.scouts = {k: dict(v) for k, v in SCOUT_MARKET.items()}
    for scout in state.scouts.values():
        skill=scout['skill']
        scout.setdefault('judgement_current',skill)
        scout.setdefault('judgement_potential',max(1,min(25,skill+(1 if scout['coverage']=='global' else -1))))
        scout.setdefault('industry_knowledge',skill)
        scout.setdefault('network',max(1,min(25,skill+1)))
        scout.setdefault('contract_intelligence',max(1,skill-2))
    # Stable, pre-existing wrestler/coach relationships (good and poor fits).
    for wrestler in state.wrestlers.values():
        for coach_id,coach in state.coaches.items():
            rng=random.Random(f'prior-rapport:{state.seed}:{wrestler.id}:{coach_id}')
            wrestler.relationships.setdefault(coach_id,round(rng.uniform(5,21),2))
            coach.setdefault('relationships',{}).setdefault(wrestler.id,
                round(rng.uniform(5,21),2))
            coach.setdefault('management_relationship',15.0 if coach['company_id']=='player' else 12.5)
    if not state.weekly_metrics:
        record_metrics(state, 'initial')
    if not state.world_news:
        add_world_news(state, 'industry', 'The wrestling world enters a new era in 2026.',
                       'Titan Wrestling Alliance enters the season as the established favourite.', 'rival')


def add_world_news(state, category, headline, summary, company_id=None):
    item = dict(year=state.year, week=state.week, category=category,
                headline=headline, summary=summary, company_id=company_id)
    state.world_news.append(item)
    state.world_news[:] = state.world_news[-150:]
    return item


def record_metrics(state: GameState, phase='show') -> dict:
    c = state.player_company
    record = dict(year=state.year, week=state.week, phase=phase, money=c.money,
                  viewership=int(c.viewership), popularity=round(c.popularity,2), fan_trust=round(c.fan_trust,2),
                  sponsor_interest=round(c.sponsor_interest,2),
                  roster_size=sum(w.company_id==state.player_company_id for w in state.wrestlers.values()))
    # One authoritative end-of-week snapshot, replacing the initial snapshot after the show.
    for i, older in enumerate(state.weekly_metrics):
        if older['year']==state.year and older['week']==state.week:
            state.weekly_metrics[i]=record
            break
    else:
        state.weekly_metrics.append(record)
    return record


def calendar(state: GameState, horizon=16) -> list[dict]:
    """Three starter PPVs a year, expandable by investment; preserve historic shows."""
    events=[]
    c=state.player_company
    ppv_names=['First Light','Summer Clash','Final Reckoning','Rising Tide','Nightfall','Crossroads','Break Point','Summit']
    past=[(s.result.get('year',state.year),s.week) for s in state.shows.values() if s.simulated and s.result]
    first=min([year*52+week for year,week in past]+[state.year*52+state.week])
    last=state.year*52+state.week+horizon
    for ordinal in range(first,last+1):
        year=(ordinal-1)//52; week=(ordinal-1)%52+1
        if year<2026:continue
        ppv=week in c.ppv_weeks
        ppv_index=c.ppv_weeks.index(week) if ppv else 0
        name=f'Aurora: {ppv_names[ppv_index%len(ppv_names)]}' if ppv else f'Aurora Weekly · W{week}'
        show=next((s for s in state.shows.values() if s.week==week and s.result and s.result.get('year')==year),None)
        pending=next((s for s in state.shows.values() if s.week==week and not s.simulated and year==state.year),None)
        if show or pending:name=(show or pending).name
        future=[(p-week)%52 for p in c.ppv_weeks]
        events.append(dict(year=year,week=week,is_ppv=ppv,type='PPV' if ppv else 'Weekly',name=name,
            status='completed' if show else 'booked' if pending else 'upcoming',
            show_id=(show or pending).id if (show or pending) else None,
            build_advice='Build a satisfying payoff with an appropriate match finish.' if ppv else
                         'Develop both divisions and protect coherence for the next PPV.',
            weeks_to_ppv=min(future) if future else 52))
    return events


def staff_market(state, kind):
    staff = state.coaches if kind=='coach' else state.scouts
    return list(staff.values())


def hire_staff(state: GameState, kind: str, staff_id: str):
    if kind not in ('coach','scout'): raise ValueError('Unknown staff category')
    data=state.coaches if kind=='coach' else state.scouts
    member=data.get(staff_id)
    if not member: raise ValueError('Unknown staff member')
    if member['company_id']==state.player_company_id: raise ValueError('Staff member already employed')
    fee=member['signing_fee']*(2 if member['company_id'] and member['company_id']!=state.player_company_id else 1)
    if fee>state.player_company.money: raise ValueError('Insufficient funds for signing or buyout')
    state.player_company.money-=fee
    member['company_id']=state.player_company_id
    add_world_news(state,'staff',f'{member["name"]} joins Aurora',f'{kind.capitalize()} hired for ${fee:,}.',state.player_company_id)
    return dict(name=member['name'],kind=kind,fee=fee)


def assign_coach(state: GameState, coach_id: str, wrestler_id: str) -> dict:
    coach=state.coaches.get(coach_id)
    w=state.wrestlers.get(wrestler_id)
    if not coach or coach['company_id']!=state.player_company_id: raise ValueError('Hire this coach first')
    if not w or w.company_id!=state.player_company_id: raise ValueError('Select one of your wrestlers')
    if w.fatigue>22: raise ValueError('Wrestler is too fatigued to start training')
    key=f'training-{state.year}-{state.week}-{wrestler_id}'
    if key in state.assignments: raise ValueError('Only one coaching proposal per wrestler per week')
    # Capacity and personality compatibility influence both willingness and progress.
    # One coach per wrestler, multiple trainees per coach, limited to four.
    if sum(c==coach_id for wid,c in state.coach_assignments.items() if wid!=wrestler_id)>=4:
        raise ValueError('Coach already has four trainees')
    rng=random.Random(f'coach:{state.seed}:{state.year}:{state.week}:{coach_id}:{wrestler_id}')
    existing_relation=w.relationships.get(coach_id,12.5)
    coach_relation=coach.get('relationships',{}).get(wrestler_id,12.5)
    staff_rapport=coach.get('management_relationship',12.5)
    from .development import personality_fit
    compatibility=personality_fit(coach['personality'],w.personality)
    willingness=clamp((compatibility-50)*.0025 + .18 + w.owner_relationship*.009 + existing_relation*.009 + coach_relation*.007 + staff_rapport*.004 +
                      w.attributes['professionalism']*.006 + coach['relationship_bias']*.014 -
                      (.16 if w.personality=='independent' else 0) + rng.uniform(-.06,.06),.08,.97)
    accepted=rng.random()<willingness
    state.assignments[key]={'wrestler_id':wrestler_id,'coach_id':coach_id,'accepted':accepted}
    if accepted:
        state.coach_assignments[wrestler_id]=coach_id
        w.relationships[coach_id]=clamp(existing_relation+.35,0,25)
        coach['relationships'][w.id]=clamp(coach_relation+.25,0,25)
        narrative=f'{w.name} agrees to train with {coach["name"]} ({coach["specialty"]}).'
    else:
        w.owner_relationship=clamp(w.owner_relationship-.20,0,25)
        coach['management_relationship']=clamp(staff_rapport-.15,0,25)
        narrative=f'{w.name} declines coaching with {coach["name"]}; the partnership did not feel right.'
    state.news.append(narrative)
    return dict(accepted=accepted, chance=round(willingness,3), narrative=narrative)


def scout_reports(state: GameState, scout_id: str):
    scout=state.scouts.get(scout_id)
    if not scout or scout['company_id']!=state.player_company_id: raise ValueError('Hire this scout first')
    # Once/week per scout; reports are informative estimates, not perfect ratings.
    if any(r['year']==state.year and r['week']==state.week and r['scout_id']==scout_id for r in state.scouting_reports):
        raise ValueError('Scout has already submitted a report this week')
    known = {r['wrestler_id'] for r in state.scouting_reports}
    coverage_rank = {'known':0,'regional':1,'national':2,'global':3}
    tier = {'regional':1,'national':2,'global':3}[scout['coverage']]
    targets=[w for w in state.wrestlers.values()
             if w.company_id != state.player_company_id and coverage_rank[w.discovery_tier] <= tier]
    # Prefer finding unfamiliar independent prospects, then refine reports on known talent.
    targets.sort(key=lambda w: (w.id in known, w.discovery_tier=='known', w.company_id is not None, w.id))
    if not targets:raise ValueError('No wrestlers within scouting coverage')
    rng=random.Random(f'report:{state.seed}:{state.year}:{state.week}:{scout_id}')
    unseen=[w for w in targets if w.id not in known]
    seen=[w for w in targets if w.id in known]
    rng.shuffle(unseen);rng.shuffle(seen)
    targets=unseen+seen
    reports=[]
    for w in targets[:min(3,1+scout['skill']//9)]:
        actual=rating_breakdown(w)
        past=sum(r['wrestler_id']==w.id and r['scout_id']==scout_id for r in state.scouting_reports)
        observation=min(1, .50+.10*past)
        current_error=(25-scout['judgement_current'])*.55/observation
        potential_error=(25-scout['judgement_potential'])*.7/observation
        estimate=round(clamp(actual['current_ability']+rng.uniform(-current_error,current_error)),1)
        potential=round(clamp(actual['potential_ability']+rng.uniform(-potential_error,potential_error)),1)
        entry=dict(year=state.year,week=state.week,scout_id=scout_id,scout_name=scout['name'],
                   wrestler_id=w.id, name=w.name, division=w.division, current_estimate=estimate,
                   potential_estimate=potential,
                   confidence=round(clamp(scout['skill']/25*100+past*5)),
                   observations=past+1,ca_uncertainty=round(current_error,1),
                   pa_uncertainty=round(potential_error,1),
                   scouted_market_value=round(__import__('wrestling_sim.front_office',fromlist=['monetary_value']).monetary_value(w,state)*
                            (1+rng.uniform(-.5,.5)*(25-scout['contract_intelligence'])/25)),
                   contract_weeks_estimate=max(0,w.contract_weeks+rng.randint(-max(1,25-scout['contract_intelligence']),max(1,25-scout['contract_intelligence']))),
                   coverage=scout['coverage'], company_id=w.company_id,
                   note=('Rival contract: monitor expiry.' if w.company_id else
                         'Free agent: contract talks available.'),
                   recommendation=('Priority target' if potential>77 else 'Monitor development'))
        reports.append(entry)
    state.scouting_reports.extend(reports)
    return reports


def progress_coaches(state: GameState, rng: random.Random) -> list[str]:
    messages=[]
    for wrestler_id,coach_id in list(state.coach_assignments.items()):
        w=state.wrestlers.get(wrestler_id)
        coach=state.coaches.get(coach_id)
        if not w or w.company_id!=state.player_company_id or not coach or coach['company_id']!=state.player_company_id:
            state.coach_assignments.pop(wrestler_id,None);continue
        if w.fatigue>21: continue
        from .development import coaching_effectiveness
        effectiveness=coaching_effectiveness(state,coach,w)
        relationship=w.relationships.get(coach_id,12.5)
        stat=rng.choice(TRAINING_STATS[coach['specialty']])
        growth=(.018+.11*effectiveness/100)*w.growth_aptitude
        growth*=clamp((25-w.attributes[stat])/10,.08,1)
        growth*=clamp((25-w.fatigue)/25,.1,1)
        growth*=rng.uniform(.82,1.14)
        w.attributes[stat]=round(clamp(w.attributes[stat]+growth,0,25),3)
        w.fatigue=clamp(w.fatigue+.10,0,25)
        w.relationships[coach_id]=round(clamp(relationship+rng.uniform(-.10,.12),0,25),3)
        if effectiveness<42 and rng.random()<.10:
            w.morale=clamp(w.morale-.13,0,25)
        if rng.random()<.07: messages.append(f'{coach["name"]} reports steady progress in {w.name}\'s {stat.replace("_"," ")}.')
    return messages


def simulate_competitors(state: GameState) -> list[str]:
    """NPC promotions book fictional cards, affect the market and pursue talent."""
    messages=[]
    for rival in [c for c in state.companies.values() if c.id!=state.player_company_id]:
        roster=[w for w in state.wrestlers.values() if w.company_id==rival.id]
        rng=random.Random(f'competitor:{state.seed}:{state.year}:{state.week}:{rival.id}')
        card=[]
        for division in ('men','women'):
            division_roster=[w for w in roster if w.division==division and w.availability>=25]
            if len(division_roster)>=2:
                a,b=rng.sample(division_roster,2)
                ability=mean((rating_breakdown(w)['match'] for w in (a,b)))
                crowd_pull=mean((w.attributes['popularity']*4 for w in (a,b)))
                rating=round(clamp(ability*.70+crowd_pull*.20+rival.popularity*.10+rng.triangular(-6,6)),2)
                winner=max((a,b),key=lambda w:w.attributes['momentum']+rng.uniform(-4,4))
                winner.attributes['momentum']=clamp(winner.attributes['momentum']+.10,0,25)
                a.fatigue=clamp(a.fatigue+.65,0,25);b.fatigue=clamp(b.fatigue+.65,0,25)
                card.append(dict(kind='match',division=division,
                                 title=f'{a.name} vs {b.name}',participant_ids=[a.id,b.id],
                                 winner_id=winner.id,rating=rating,duration=21))
            elif division_roster:
                performer=division_roster[0]
                rating=round(clamp(rating_breakdown(performer)['promo']*.74 +
                                   rival.popularity*.26 +rng.triangular(-6,6)),2)
                card.append(dict(kind='promo',division=division,
                                 title=f'{performer.name} Addresses the Audience',
                                 participant_ids=[performer.id],winner_id=None,rating=rating,duration=9))
        if roster:
            featured=max(roster,key=lambda w:w.attributes['popularity'])
            promo_quality=round(clamp(rating_breakdown(featured)['promo']*.80 +rival.popularity*.20+rng.uniform(-6,6)),2)
            card.append(dict(kind='promo',division=featured.division,
                             title=f'{featured.name}: A Statement to the Roster',
                             participant_ids=[featured.id],winner_id=None,rating=promo_quality,duration=8))
        quality=round(sum(x['rating']*x['duration'] for x in card)/max(1,sum(x['duration'] for x in card)),2) if card else 37
        crowd=round(clamp(quality*.66+rival.popularity*.34+rng.uniform(-4,4)),2)
        delta=round((crowd-58)/24,2)
        rival.popularity=round(clamp(rival.popularity+delta),2)
        # Rival audience reach is a comparable count, not a 0–100 popularity index.
        viewer_growth=clamp((crowd-59)/440+(rival.fan_trust-50)/3000,-.095,.095)
        rival.viewership=max(1000,round(rival.viewership*(1+viewer_growth)))
        rival.sponsor_interest=round(clamp(rival.sponsor_interest+(quality-60)/38),2)
        attendance=int(rival.venue_capacity * clamp(.17+rival.popularity/120+(crowd-50)/230,.15,.99))
        net=attendance*rival.ticket_price + int(quality*85) - rival.weekly_fixed_costs - sum(w.salary_weekly for w in roster)
        rival.money+=net
        headline=f'{rival.name} weekly show scores {quality:.0f}/100'
        detail=f'Crowd reaction {crowd:.0f}/100, {attendance:,} attendance, {rival.viewership:,} viewers.'
        if card:detail+=f' Main event: {card[0]["title"]}.'
        add_world_news(state,'rival_show',headline,detail,rival.id)
        state.rival_history.append(dict(year=state.year,week=state.week,company_id=rival.id,
                         show_name=f'{rival.name} — Week {state.week}',card=card,
                         quality=quality,crowd=crowd,attendance=attendance,net=net,
                         viewership=rival.viewership,popularity=rival.popularity))
        if state.week%3==0:
            candidates=[w for w in state.wrestlers.values() if w.company_id is None]
            candidates.sort(key=lambda w: rating_breakdown(w)['potential_ability'],reverse=True)
            if candidates and len(roster)<rival.roster_limit:
                prospect=candidates[0] if rng.random()<.55 else rng.choice(candidates)
                salary=int(450+rating_breakdown(prospect)['market_value']*29)
                if rival.money>salary*8:
                    prospect.company_id=rival.id; prospect.salary_weekly=salary; prospect.contract_weeks=52
                    rival.money-=salary*2
                    news=f'{rival.name} signs {prospect.name} to a 52-week deal.'
                    add_world_news(state,'transfer',news,'The free-agent market is tightening.',rival.id)
                    messages.append(news)
        if state.week%4==0:
            targets=[w for w in state.wrestlers.values() if w.company_id==state.player_company_id and w.contract_weeks<=6]
            if targets:
                w=max(targets,key=lambda t:rating_breakdown(t)['market_value'])
                news=f'{rival.name} monitoring {w.name} ahead of contract expiry.'
                add_world_news(state,'rumour',news,'Renewal talks could become more expensive.',rival.id)
                messages.append(news)
    state.rival_history[:]=state.rival_history[-300:]
    return messages


def weekly_staff_cost(state):
    return sum(x['salary_weekly'] for data in (state.scouts,state.coaches) for x in data.values()
               if x['company_id']==state.player_company_id)


def prospect_discovered(state: GameState, wrestler_id: str) -> bool:
    w=state.wrestlers.get(wrestler_id)
    return bool(w and (w.discovery_tier=='known' or
                any(r['wrestler_id']==wrestler_id for r in state.scouting_reports)))
