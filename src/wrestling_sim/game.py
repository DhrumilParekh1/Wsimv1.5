"""Game orchestration: book, resolve, spend, negotiate, advance world."""
from __future__ import annotations
import random
from dataclasses import asdict
from statistics import mean
from .models import GameState, Segment, Show, Storyline, clamp
from .progression import after_appearance, progress_week
from .ratings import rating_breakdown
from .simulation import simulate_segment


def create_storyline(state: GameState, title: str, wrestler_ids: list[str]) -> Storyline:
    if len(set(wrestler_ids)) < 2:
        raise ValueError("Storylines need at least two distinct wrestlers")
    if not title.strip():
        raise ValueError("Storyline title is required")
    if any(wid not in state.wrestlers or state.wrestlers[wid].company_id != state.player_company_id
           for wid in wrestler_ids):
        raise ValueError("Storyline participants must belong to your roster")
    divisions = {state.wrestlers[wid].division for wid in wrestler_ids}
    if len(divisions) != 1:
        raise ValueError("A storyline must use one division: men or women")
    storyline = Storyline(id=state.generate_id("story"), title=title.strip(), wrestler_ids=wrestler_ids)
    state.storylines[storyline.id] = storyline
    from .audience import ensure_expectations
    ensure_expectations(state,storyline)
    return storyline


def book_show(state: GameState, name: str, segments: list[Segment], duration: int = 120) -> Show:
    if not name.strip():
        raise ValueError("Show title is required")
    if duration != state.player_company.show_minutes:
        raise ValueError(f"Current weekly broadcast is {state.player_company.show_minutes} minutes")
    if not segments or len(segments) > 12:
        raise ValueError("Book 1..12 segments per show")
    total_minutes = sum(s.duration for s in segments)
    if not duration-20 <= total_minutes <= duration:
        raise ValueError(f"You must book {duration-20}–{duration} minutes (currently {total_minutes}).")
    if any(show.week == state.week and not show.simulated for show in state.shows.values()):
        raise ValueError("Complete your existing booked show before booking another")
    if any(show.week == state.week and show.simulated for show in state.shows.values()):
        raise ValueError("Starter engine supports one event per week")
    from .championships import check_title_match
    from .marketing import segment_spend
    estimated_marketing=sum(segment_spend(s) for s in segments)
    if estimated_marketing > state.player_company.money:
        raise ValueError('Insufficient funds for planned advertising/promotion')
    match_appearances = set()
    storyline_slots: dict[str, int] = {}
    featured_divisions: set[str] = set()
    for segment in segments:
        for wid in segment.wrestler_ids:
            wrestler = state.wrestlers.get(wid)
            if not wrestler or wrestler.company_id != state.player_company_id:
                raise ValueError(f"{wid}: wrestler is not on your active roster")
            if wrestler.injury:
                raise ValueError(f'{wrestler.name} is injured ({wrestler.injury["weeks_remaining"]} weeks remaining) and cannot be booked')
            if wrestler.availability < 25:
                raise ValueError(f"{wid}: wrestler is unavailable to perform")
            if wrestler.wants_release and wrestler.morale <= 4:
                consent_rng=random.Random(f'booking-consent:{state.seed}:{state.year}:{state.week}:{wid}')
                chance=clamp(.05+(4-wrestler.morale)*.052 +
                    max(0,16-wrestler.attributes['professionalism'])*.012,0,.45)
                if consent_rng.random()<chance:
                    raise ValueError(f'{wrestler.name} refuses this booking due to a severe contract dispute; resolve their concerns.')
        divisions = {state.wrestlers[wid].division for wid in segment.wrestler_ids}
        if len(divisions) > 1:
            raise ValueError("Segments cannot mix the men's and women's divisions")
        if segment.role_turn_wrestler_id and not segment.storyline_id:
            raise ValueError('Role turns must be attached to a storyline')
        if segment.role_turn_wrestler_id and state.wrestlers[segment.role_turn_wrestler_id].role == segment.role_turn_to:
            raise ValueError('The wrestler is already in that role')
        if segment.storyline_id:
            # Audit explicit deviations from the locked creative room strategy.
            scene=state.scenes.get(f'scene-{state.year}-{state.week}-{segment.storyline_id}')
            if scene and scene.get('status')=='complete' and scene.get('choices'):
                locked={'mind_games':'slow_burn','challenge':'escalate','shock':'swerve'}.get(scene['choices'][0])
                if locked and segment.creative_direction!=locked:
                    state.activity_log.append({'type':'creative_override','year':state.year,'week':state.week,
                        'storyline_id':segment.storyline_id,'locked':locked,
                        'booked':segment.creative_direction,'segment':segment.title})
            storyline_slots[segment.storyline_id] = storyline_slots.get(segment.storyline_id, 0) + 1
            if storyline_slots[segment.storyline_id] > 2:
                raise ValueError("An active storyline may occupy at most two card slots")
            featured_divisions.update(divisions)
            storyline = state.storylines.get(segment.storyline_id)
            if not storyline:
                raise ValueError(f"Unknown storyline: {segment.storyline_id}")
            if not set(segment.wrestler_ids).issubset(storyline.wrestler_ids):
                raise ValueError("Segment wrestlers must belong to the attached storyline")
        check_title_match(state,segment)
        if segment.kind == "match":
            if match_appearances.intersection(segment.wrestler_ids):
                raise ValueError("A wrestler can only participate in one match per show")
            match_appearances.update(segment.wrestler_ids)
    custom=any(c.get('type')=='company_foundation' for c in state.campaigns)
    if custom:
        represented={state.wrestlers[segment.wrestler_ids[0]].division
                     for segment in segments if segment.wrestler_ids}
        if represented!={'men','women'}:
            raise ValueError("The weekly broadcast must feature both divisions.")
    elif featured_divisions != {"men", "women"}:
        raise ValueError("Every weekly show needs at least one men's and one women's storyline segment")
    show = Show(id=state.generate_id("show"), name=name.strip(), week=state.week,
                duration=duration, segments=segments)
    state.shows[show.id] = show
    return show


def _finance_event(state: GameState, avg_crowd: float, avg_quality: float,
                   duration: int) -> dict[str, int]:
    c = state.player_company
    attendance_factor = clamp(.15 + c.popularity / 120 + (avg_crowd - 50) / 220, .18, 1)
    attendance = int(c.venue_capacity * attendance_factor)
    tickets = attendance * c.ticket_price
    streaming = int(800 + c.viewership * .026 + avg_quality * 35)
    sponsors = max(0, int(c.sponsor_interest * 90 + (avg_crowd - 60) * 25))
    merchandise = int(attendance * 8 * c.fan_trust / 100)
    production = int(4500 + duration * 55)
    net = tickets + streaming + sponsors + merchandise - production
    c.money += net
    return {"attendance": attendance, "tickets": tickets, "streaming": streaming,
            "sponsors": sponsors, "merchandise": merchandise,
            "production": production, "event_net": net}


def simulate_show(state: GameState, show_id: str) -> dict:
    show = state.shows.get(show_id)
    if not show:
        raise ValueError("Unknown show")
    if show.simulated:
        raise ValueError("Show already simulated")
    if show.week != state.week:
        raise ValueError("Cannot simulate a show from an earlier week")
    rng = random.Random(f"{state.seed}:{state.year}:{state.week}:{show.id}")
    crowd_fatigue = 0.0
    results = []
    from .championships import settle_title_match,ensure_championships
    ensure_championships(state)
    from .memories import add_memory
    from .audience import evaluate_turn,resolve_expectations
    for segment in show.segments:
        outcome = simulate_segment(state, segment, rng, crowd_fatigue)
        results.append(outcome)
        if segment.championship_id:
            title_result=settle_title_match(state,segment,outcome,state.week)
            if title_result:
                outcome['hype_delta']+=min(4,title_result['prestige']*.035)
                state.news.append(f"{title_result['belt_name']}: {state.wrestlers[title_result['winner_id']].name} " +
                                  ('wins the championship!' if title_result['new_champion'] else 'retains the title.'))
        storyline = state.storylines.get(segment.storyline_id) if segment.storyline_id else None
        if segment.role_turn_wrestler_id:
            outcome['role_turn'] = evaluate_turn(state,storyline,segment,rng)
            if outcome['role_turn']:
                outcome['crowd'] = clamp(.86*outcome['crowd']+.14*outcome['role_turn']['crowd_reaction'])
                turn=outcome['role_turn']
                add_memory(state,'role_turn',f"{turn['wrestler_name']} turned {turn['to']} during {segment.title}.",
                           segment.wrestler_ids,segment.storyline_id,85,trust_effect=(turn['success']-60)/20)
        if outcome['surprise']:
            shock=outcome['surprise']
            for wid in segment.wrestler_ids:
                wrestler=state.wrestlers[wid]
                for attr in ('popularity','momentum','relevance'):
                    wrestler.attributes[attr]=clamp(wrestler.attributes[attr]+shock['fame_delta'],0,25)
            add_memory(state,shock['type'],shock['headline']+f' during {segment.title}.',
                       segment.wrestler_ids,segment.storyline_id,96,trust_effect=shock['fame_delta'])
            state.news.append(shock['headline']+f' — {segment.title}.')
        if storyline:
            outcome['expectations']=resolve_expectations(state,storyline,segment,outcome)
        if storyline:
            creative=outcome.get('creative_impact') or {}
            storyline.escalation_level = creative.get('escalation',storyline.escalation_level)
            storyline.hype = clamp(storyline.hype + outcome["hype_delta"])
            storyline.fan_investment = clamp(storyline.fan_investment + outcome["hype_delta"] * .45)
            storyline.coherence = clamp(storyline.coherence + (outcome["quality"] - 60) / 30
                                        + (outcome['match_engine']['coherence_modifier'] if outcome['match_engine'] else 0))
            if outcome['planned_beat_delivered']:
                storyline.planned_beat['fulfilled'] = True
                storyline.coherence = clamp(storyline.coherence + 2.5)
                state.news.append(f'Creative promise delivered: {storyline.title} advanced through a {segment.kind}.')
            storyline.coherence = clamp(storyline.coherence + creative.get('coherence',0))
            if creative.get('relevance',0):
                for wid in segment.wrestler_ids:
                    performer=state.wrestlers[wid]
                    performer.attributes['relevance']=clamp(performer.attributes['relevance']+creative['relevance'],0,25)
            if segment.creative_direction == "resolve":
                storyline.stage = "resolved"
            storyline.last_seen_week = state.week
            recent=sum(h.get('week',-100)>=state.week-5 for h in storyline.history)
            storyline.fatigue=clamp(storyline.fatigue+max(0,recent-1)*.8+(.5 if segment.creative_direction=='slow_burn' else -.2),0,35)
            storyline.anticipation=clamp(storyline.hype*.6+storyline.fan_investment*.4-storyline.fatigue*.5)
            if segment.kind=='betrayal':
                add_memory(state,'betrayal',f'{segment.title}: a betrayal reshaped {storyline.title}.',
                           segment.wrestler_ids,storyline.id,91,relationship_effect=-3.5)
            if outcome['planned_beat_delivered']:
                add_memory(state,'promise_delivered',f'The creative promise in {storyline.title} was delivered via {segment.title}.',
                           segment.wrestler_ids,storyline.id,63,trust_effect=2)
            if segment.creative_direction == 'resolve':
                add_memory(state,'payoff',f'{storyline.title} reached a booked resolution in {segment.title}.',
                           segment.wrestler_ids,storyline.id,75,trust_effect=(outcome['crowd']-50)/12)
            storyline.history.append({"week": state.week, "show_id": show.id, "kind": segment.kind,
                                      "direction": segment.creative_direction,
                                      "quality": outcome["quality"], "crowd": outcome["crowd"],
                                      "creative_note":creative.get('note',''),
                                      "finish":segment.finish_type if segment.kind=='match' else None})
        from .front_office import after_pair_segment
        after_pair_segment(state,segment.wrestler_ids,outcome['quality'],segment.kind)
        if len(segment.wrestler_ids) == 2:
            left, right = (state.wrestlers[x] for x in segment.wrestler_ids)
            effect = .14 if outcome['quality'] >= 70 else -.12
            if segment.kind == 'betrayal': effect -= .8
            left.relationships[right.id] = clamp(left.relationships.get(right.id, 0) + effect, -25, 25)
            right.relationships[left.id] = clamp(right.relationships.get(left.id, 0) + effect, -25, 25)
        for wid in segment.wrestler_ids:
            after_appearance(state.wrestlers[wid], segment.kind, outcome["crowd"],
                             outcome["quality"], segment.duration, rng,
                             intensity=segment.intensity, stipulation=segment.stipulation,
                             promo_brawl=segment.promo_brawl)
        # Medical availability is computed after performance, not by the prose model.
        from .injuries import roll_injury
        for wid in segment.wrestler_ids:
            injury=roll_injury(state,state.wrestlers[wid],segment,rng)
            if injury:
                outcome['injuries'].append(injury)
                outcome['highlights'].append({'minute':segment.duration,'text':injury['description'],
                                              'performer_id':wid,'move':None,'is_medical':True})
        if segment.planned_winner_id:
            winner = state.wrestlers[segment.planned_winner_id]
            winner.attributes["momentum"] = clamp(winner.attributes["momentum"] + .28, 0, 25)
            for wid in segment.wrestler_ids:
                if wid != segment.planned_winner_id:
                    loser = state.wrestlers[wid]
                    # Losing is less harmful when a match's crowd reception is strong.
                    loser.morale = clamp(loser.morale - (.42 if outcome["crowd"] < 65 else .11), 0, 25)
                    # A protected main-event star accepts occasional meaningful losses,
                    # but losing convincingly to a jobber without established context
                    # strains their morale, owner relationship and fan confidence.
                    tier_order=('jobber','lower_mid_card','mid_card','upper_mid_card','main_event')
                    gap=tier_order.index(loser.card_tier)-tier_order.index(winner.card_tier)
                    if gap >= 3:
                        mitigation=1.0 if storyline and storyline.hype>78 and outcome['crowd']>77 else .35
                        loser.morale=clamp(loser.morale-.9*(1-mitigation),0,25)
                        loser.owner_relationship=clamp(loser.owner_relationship-.65*(1-mitigation),0,25)
                        if mitigation<.5:
                            from .front_office import queue_problem
                            queue_problem(state,loser.id,'protection',
                                f'{loser.name} questions losing to {winner.name} without a convincing buildup.')
                            outcome['crowd']=clamp(outcome['crowd']-2.0)
        crowd_fatigue = clamp(crowd_fatigue + segment.duration * .06 - (2 if segment.kind == "backstage" else 0), 0, 20)
    for key, assignment in list(state.assignments.items()):
        if key.startswith('press-promise-') and not assignment.get('fulfilled'):
            if any(assignment['wrestler_id'] in seg.wrestler_ids for seg in show.segments):
                assignment['fulfilled'] = True
                state.wrestlers[assignment['wrestler_id']].owner_relationship = clamp(
                    state.wrestlers[assignment['wrestler_id']].owner_relationship+.4,0,25)
        if key.startswith('push-') and not assignment.get('fulfilled'):
            if any(assignment['wrestler_id'] in seg.wrestler_ids for seg in show.segments):
                assignment['fulfilled'] = True
                state.wrestlers[assignment['wrestler_id']].morale = clamp(state.wrestlers[assignment['wrestler_id']].morale + .8, 0, 25)
    total_minutes = sum(segment.duration for segment in show.segments)
    avg_quality = sum(result["quality"] * result["duration"] for result in results) / total_minutes
    avg_crowd = sum(result["crowd"] * result["duration"] for result in results) / total_minutes
    # Advertising costs actual money; high effort can widen reach without improving wrestling skill.
    from .marketing import segment_spend, marketing_impact
    promotion_cost=sum(segment_spend(s) for s in show.segments)
    finances = _finance_event(state, avg_crowd, avg_quality, show.duration)
    finances['promotion_spend']=promotion_cost
    finances['event_net']-=promotion_cost
    state.player_company.money-=promotion_cost
    title_bouts=[s for s in show.segments if s.championship_id]
    if title_bouts:
        prestige=sum(state.championships[s.championship_id]['prestige'] for s in title_bouts)/len(title_bouts)
        uplift=int(finances['streaming']*(.08+len(title_bouts)*.035)*prestige/100)
        finances['title_interest_revenue']=uplift
        finances['event_net']+=uplift
        state.player_company.money+=uplift
    else: finances['title_interest_revenue']=0
    from .sponsors import settle_show_sponsors
    settle_show_sponsors(state, finances, avg_crowd, avg_quality)
    company = state.player_company
    trust_change = sum(result["fan_trust_delta"] for result in results) / max(1, len(results))
    company.fan_trust = clamp(company.fan_trust + trust_change)
    # Reach is a real viewership count, subject to gradual changes and rare viral spikes.
    trust_influence=(company.fan_trust-50)/3000
    promo_visibility=sum(marketing_impact(state,s)*s.duration for s in show.segments)/total_minutes
    belt_boost=.0045*len(title_bouts)
    weekly_growth=clamp((avg_crowd-59)/440+trust_influence+promo_visibility*.004+belt_boost,-.095,.095)
    shocks=[x['surprise'] for x in results if x.get('surprise')]
    if shocks:
        weekly_growth+=sum(x['fame_delta']*.014 for x in shocks)
    company.viewership=max(1000,round(company.viewership*(1+weekly_growth)))
    # Preserve internal legacy popularity for old AI promotion formulas/save compatibility.
    company.popularity = clamp(company.popularity + weekly_growth*18)
    company.sponsor_interest = clamp(company.sponsor_interest + (avg_quality - 65) / 22)
    report = {"show_id": show.id, "name": show.name, "year": state.year,
              "week": state.week, "quality": round(avg_quality, 2),
              "crowd": round(avg_crowd, 2), "segments": results,
              "finances": finances, "viewership":company.viewership, "company_fan_trust": round(company.fan_trust, 2),
              "company_viewership": company.viewership,
              "company_sponsor_interest": round(company.sponsor_interest, 2)}
    if state.week in company.ppv_weeks:
        # Purchased PPV slots rather than automatic monthly events.
        bonus=int(finances['streaming']*.65+finances['sponsors']*.18)
        ppv_cost=7500
        delta=bonus-ppv_cost
        state.player_company.money+=delta
        finances['ppv_bonus']=bonus
        finances['ppv_extra_production']=ppv_cost
        finances['event_net']+=delta
        report['event_type']='PPV'
    else:
        report['event_type']='Weekly'
    from .industry import update_promises, update_prestige_history
    update_promises(state, show)
    update_prestige_history(state)
    from .world import record_metrics, add_world_news
    record_metrics(state, 'show')
    add_world_news(state,'player_show',f'{show.name}: {avg_quality:.1f}/100',
                   f'{finances["attendance"]:,} fans attended. Crowd response {avg_crowd:.1f}.',state.player_company_id)
    show.result = report
    show.simulated = True
    state.financial_history.append({"year": state.year, "week": state.week,
                                    "reason": "event", **finances})
    state.news.append(f"{show.name} drew {finances['attendance']:,} fans; crowd reaction {avg_crowd:.1f}/100.")
    from .social import generate_fan_posts
    generate_fan_posts(state, show, report)
    return report


def offer_contract(state: GameState, wrestler_id: str, salary_weekly: int,
                   weeks: int, signing_bonus: int = 0,
                   promised_role: str | None=None, promises: list[str] | None=None) -> dict:
    wrestler = state.wrestlers.get(wrestler_id)
    if not wrestler:
        raise ValueError("Unknown wrestler")
    if wrestler.company_id not in (None, state.player_company_id):
        raise ValueError("Wrestler is under an exclusive rival-company contract")
    if not (4 <= weeks <= 156):
        raise ValueError("Contract length must be 4..156 weeks")
    if salary_weekly <= 0 or signing_bonus < 0:
        raise ValueError("Contract salary must be positive and bonus nonnegative")
    from .world import prospect_discovered
    if wrestler.company_id is None and not prospect_discovered(state, wrestler_id):
        raise ValueError('This independent prospect needs a scouting report before contract talks')
    company = state.player_company
    already_employed = wrestler.company_id == state.player_company_id
    if not already_employed and sum(w.company_id == state.player_company_id for w in state.wrestlers.values()) >= company.roster_limit:
        raise ValueError("Roster is full")
    if signing_bonus > company.money:
        raise ValueError("Not enough funds for signing bonus")
    from .front_office import monetary_value
    market = rating_breakdown(wrestler)["market_value"]
    wage_from_value = monetary_value(wrestler,state) / 52 / 13
    expected = int(0.55*(450 + market * 27 + wrestler.attributes["ambition"] * 15) + 0.45*wage_from_value)
    if already_employed:
        expected = max(expected, int(wrestler.salary_weekly * 1.04))
    # Deterministic per-offer seed: changing offer amounts changes the draw.
    rng = random.Random(f"contract:{state.seed}:{state.year}:{state.week}:{wrestler_id}:{salary_weekly}:{weeks}:{signing_bonus}")
    ratio = (salary_weekly + signing_bonus / weeks) / expected
    from .industry import wrestler_willingness, TIERS
    if promised_role and promised_role not in TIERS: raise ValueError('Unknown promised card status')
    base = clamp(.48 + 1.18 * (ratio - 1) + (wrestler.morale - 12.5) / 80, .03, .98)
    interest=wrestler_willingness(state,wrestler,state.player_company_id,salary_weekly,
        promised_role or wrestler.card_tier,promises)
    odds=clamp(.65*base+.35*interest['acceptance_probability'],.03,.98)
    accepted = rng.random() < odds
    if accepted:
        from .industry import star_movement
        old_company=wrestler.company_id
        company.money -= signing_bonus
        wrestler.company_id = state.player_company_id
        wrestler.contract_weeks = weeks
        wrestler.salary_weekly = salary_weekly
        wrestler.attributes["loyalty"] = clamp(wrestler.attributes["loyalty"] + .4, 0, 25)
        if old_company != state.player_company_id:
            star_movement(state,wrestler,old_company,state.player_company_id)
        from .industry import lodge_promise
        if promised_role and promised_role!=wrestler.card_tier:
            lodge_promise(state,wrestler.id,'tier',promised_role,8)
        for kind in (promises or []):
            if kind=='championship_opportunity':lodge_promise(state,wrestler.id,kind,True,12)
            elif kind=='promotion':lodge_promise(state,wrestler.id,kind,5000,8)
            elif kind=='coaching':lodge_promise(state,wrestler.id,kind,True,8)
            elif kind=='creative_freedom':lodge_promise(state,wrestler.id,kind,True,6)
        state.news.append(f"{wrestler.name} signed a {weeks}-week deal for ${salary_weekly:,}/week.")
    else:
        wrestler.morale = clamp(wrestler.morale - (.2 if already_employed else 0), 0, 25)
        state.news.append(f"{wrestler.name} declined a contract offer.")
    return {"wrestler_id": wrestler_id, "accepted": accepted,
            "salary_offered": salary_weekly, "signing_bonus": signing_bonus,
            "contract_weeks": weeks, "estimated_expected_salary": expected,
            "acceptance_probability": round(odds, 3)}


def inbox_blockers(state: GameState) -> list[dict]:
    """Blocking obligations are computed from saved state, never trusted from the browser."""
    from .decisions import available_decisions
    from .management import media_opportunity, creative_tasks
    from .front_office import concerns
    from .press_and_incidents import pending_incidents
    from .press_and_incidents import conference
    press = conference(state)
    if press and not press['completed']:
        remaining = sum(q['answer'] is None for q in press['questions'])
        issues = [{'kind':'press','id':press['id'],
                   'title':f'Weekly press conference: {remaining} questions unanswered'}]
    else:
        issues = []
    issues += [{'kind':'talent','id':i['id'],'title':i['title']} for i in concerns(state)]
    issues += [{'kind':'incident','id':i['id'],'title':i['title']} for i in pending_incidents(state)]
    issues += [{'kind': 'decision', 'id': e['id'], 'title': e['title']}
              for e in available_decisions(state)]
    opp = media_opportunity(state)
    if opp['id'] not in state.assignments:
        issues.append({'kind': 'media', 'id': opp['id'], 'title': opp['title']})
    for bid in state.transfer_offers:
        if bid.get('status')=='pending':
            issues.append({'kind':'rival_offer','id':bid['id'],'title':bid['message']})
    issues += [{'kind':'recruitment','id':e['key'],'title':f"Recruitment report received: {state.wrestlers[e['wrestler_id']].name}"} for e in state.recruitment_interest if e.get('status')=='reported' and e['wrestler_id'] in state.wrestlers]
    for task in creative_tasks(state):
        issues.append({'kind':'creative', 'id':task['id'], 'title':task['title']})
    from .sponsors import sponsor_offers
    for offer in sponsor_offers(state):
        issues.append({'kind':'sponsor', 'id':offer['id'], 'title':offer['name']})
    return issues


def advance_week(state: GameState) -> dict:
    if not any(show.week == state.week and show.simulated for show in state.shows.values()):
        raise ValueError(f"You must book and simulate a completed {state.player_company.show_minutes-20}–{state.player_company.show_minutes} minute show before advancing the week")
    # The press conference is mandatory even when the Inbox UI is bypassed.
    from .press_and_incidents import conference
    weekly_press = conference(state)
    if weekly_press and not weekly_press['completed']:
        remaining = sum(q['answer'] is None for q in weekly_press['questions'])
        raise ValueError(f'Complete the Press Conference before advancing ({remaining} questions remaining)')
    blockers = inbox_blockers(state)
    if blockers:
        raise ValueError('Resolve every Inbox item before advancing: ' + ', '.join(item['title'] for item in blockers[:5]))
    rng = random.Random(f"progress:{state.seed}:{state.year}:{state.week}")
    from .front_office import weekly_playtime
    weekly_playtime(state,state.year,state.week)
    from .management import creative_head
    from .world import bootstrap_world, weekly_staff_cost, progress_coaches, simulate_competitors
    bootstrap_world(state)
    staff_salary = creative_head(state)["salary_weekly"] + weekly_staff_cost(state)
    salaries = staff_salary + sum(w.salary_weekly for w in state.wrestlers.values()
                   if w.company_id == state.player_company_id)
    fixed_cost = state.player_company.weekly_fixed_costs
    state.player_company.money -= salaries + fixed_cost
    state.financial_history.append({"year": state.year, "week": state.week,
                                    "reason": "weekly_upkeep", "salaries": salaries,
                                    "fixed_costs": fixed_cost, "net": -salaries - fixed_cost})
    # Rolling four-week cash-flow signal for sustained, unsustainable spending.
    recent=state.financial_history[-4:]
    cash_flows=[item.get('net',0) for item in recent if isinstance(item.get('net'),(int,float))]
    if len(cash_flows)>=3:
        avg=sum(cash_flows)/len(cash_flows)
        if avg<0 and state.player_company.money < max(1,-avg)*8:
            state.player_company.sponsor_interest=clamp(state.player_company.sponsor_interest-.3)
            state.news.append('Financial warning: projected cash reserves are under eight weeks at recent net spending.')
    messages = progress_week(state, rng)
    from .injuries import advance_recovery
    messages.extend(advance_recovery(state))
    # All non-player promotions advance independently and pay their own salaries.
    messages.extend(progress_coaches(state, rng))
    # Progress approved mentorships as actual saved weekly arrangements.
    for arrangement in state.mentorships:
        if arrangement.get('status')!='active':continue
        student=state.wrestlers.get(arrangement['student_id'])
        mentor=state.wrestlers.get(arrangement['mentor_id'])
        if student and mentor and student.company_id==mentor.company_id==state.player_company_id:
            affinity=student.relationships.get(mentor.id,12.5)
            improvement=.012 + .025*affinity/25
            student.attributes['technique']=clamp(student.attributes['technique']+improvement,0,25)
            student.attributes['sequences']=clamp(student.attributes['sequences']+improvement*.65,0,25)
        arrangement['weeks_remaining']-=1
        if arrangement['weeks_remaining']<=0:
            arrangement['status']='completed'
            messages.append(f"Mentorship concluded for {student.name if student else 'a wrestler'}.")

    # Multi-week consequences for resolved incidents, keyed to the actual week.
    for incident in state.incidents:
        follow=incident.get('follow_up')
        if not follow or follow.get('remaining_weeks',0)<=0:continue
        current=(state.year,state.week)
        if follow.get('last_processed')==list(current):continue
        follow['last_processed']=list(current)
        direction=1 if follow.get('positive') else -1
        for wid in follow.get('wrestler_ids',[]):
            worker=state.wrestlers.get(wid)
            if worker and worker.company_id==state.player_company_id:
                worker.owner_relationship=clamp(worker.owner_relationship+direction*.12,0,25)
                worker.morale=clamp(worker.morale+direction*.10,0,25)
        follow['remaining_weeks']-=1
        if follow['remaining_weeks']==0:
            messages.append('Backstage follow-up concluded: '+incident['title'])
    messages.extend(simulate_competitors(state))
    from .industry import weekly_morale, update_promises, process_precontracts, update_prestige_history
    from .transfer_market import competitor_offers
    messages.extend(update_promises(state))
    messages.extend(weekly_morale(state))
    messages.extend(x['message'] for x in competitor_offers(state))
    messages.extend(process_precontracts(state))
    update_prestige_history(state)
    for storyline in state.storylines.values():
        plan = storyline.planned_beat
        ordinal = (state.year - 2026) * 52 + state.week
        if storyline.stage != 'resolved' and plan and not plan.get('fulfilled') and ordinal >= plan.get('due_ordinal', 10**9):
            storyline.coherence = clamp(storyline.coherence - 4.0)
            storyline.hype = clamp(storyline.hype - 2.0)
            state.player_company.fan_trust = clamp(state.player_company.fan_trust - .5)
            from .memories import add_memory
            add_memory(state,'broken_promise',f'Unfulfilled promise: {plan["kind"]} in {storyline.title} never happened.',
                       plan.get('wrestler_ids',storyline.wrestler_ids),storyline.id,87,trust_effect=-4,relationship_effect=-1.5)
            state.news.append(f'Fans lose patience: your promised {plan["kind"]} for {storyline.title} did not happen.')
            storyline.planned_beat = {}
        if storyline.stage != "resolved" and (storyline.last_seen_week is None or storyline.last_seen_week < state.week - 1):
            storyline.hype = clamp(storyline.hype - .9)
        storyline.fatigue=clamp(storyline.fatigue-1.3,0,35)
    for key, assignment in list(state.assignments.items()):
        if key.startswith('press-promise-') and not assignment.get('fulfilled') and assignment.get('due_week',99999) <= state.week:
            w=state.wrestlers[assignment['wrestler_id']]
            w.owner_relationship=clamp(w.owner_relationship-1.6,0,25)
            state.player_company.fan_trust=clamp(state.player_company.fan_trust-.9)
            assignment['fulfilled']=True
            messages.append(f'{w.name} questions your unfulfilled public promise.')
        if key.startswith('push-') and not assignment.get('fulfilled') and assignment['due_week'] <= state.week:
            wrestler = state.wrestlers[assignment['wrestler_id']]
            wrestler.morale = clamp(wrestler.morale - 1.4, 0, 25)
            wrestler.owner_relationship = clamp(wrestler.owner_relationship - 1.2, 0, 25)
            from .memories import add_memory
            add_memory(state,'broken_promise',f'{wrestler.name} was promised a booking opportunity that did not arrive.',
                       [wrestler.id],intensity=90,relationship_effect=-3.0)
            messages.append(f'{wrestler.name} is unhappy that their promised push did not arrive.')
            assignment['fulfilled'] = True
    state.week += 1
    if state.week > 52:
        state.year += 1
        state.week = 1
    from .industry import process_recruitment_enquiries
    messages.extend(process_recruitment_enquiries(state))
    from .press_and_incidents import ensure_incidents
    ensure_incidents(state)
    if state.player_company.money < 0:
        messages.append("Warning: your company is operating with negative cash reserves.")
    state.news.extend(messages)
    return {"year": state.year, "week": state.week, "payroll": salaries,
            "fixed_costs": fixed_cost, "remaining_cash": state.player_company.money,
            "events": messages}


def brief_state(state: GameState) -> dict:
    roster = sorted((w for w in state.wrestlers.values() if w.company_id == state.player_company_id),
                    key=lambda w: rating_breakdown(w)["current_ability"], reverse=True)
    return {"year": state.year, "week": state.week,
            "promotion": asdict(state.player_company),
            "roster": [{"id": w.id, "name": w.name, "role": w.role,
                        "age": w.age, "contract_weeks": w.contract_weeks,
                        "division": w.division, "energy": round(100-4*w.fatigue,1),
                        "owner_relationship": round(w.owner_relationship,1),
                        **rating_breakdown(w)} for w in roster],
            "storylines": [asdict(s) for s in state.storylines.values()],
            "recent_news": state.news[-8:]}
