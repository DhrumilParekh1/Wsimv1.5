"""Pure(ish) individual segment simulation; only caller writes persistent state.

Segment quality is NOT CA. Different segments use different attributes.
"""
from __future__ import annotations
import random
from statistics import mean
from .models import GameState, Segment, clamp
from .ratings import rating_breakdown
from .weights import SEGMENT_WEIGHTS, SEGMENT_DURATION
from .match_engine import match_profile


def chemistry(state: GameState, participant_ids: list[str]) -> float:
    """Persistent, multi-factor pair chemistry, updated after every shared segment."""
    if len(participant_ids)<2:return 65.0
    from .front_office import pair_chemistry
    return mean(pair_chemistry(state,a,b) for i,a in enumerate(participant_ids)
                for b in participant_ids[i+1:])


def pacing_score(kind: str, duration: int, fatigue: float) -> float:
    low, high = SEGMENT_DURATION[kind]
    if low <= duration <= high:
        base = 88.0
    elif duration < low:
        base = 88 - 10 * (low - duration)
    else:
        base = 88 - 5 * (duration - high)
    return clamp(base - .5 * fatigue)


def simulate_segment(state: GameState, segment: Segment, rng: random.Random,
                     crowd_fatigue: float) -> dict:
    wrestlers = [state.wrestlers[wid] for wid in segment.wrestler_ids]
    match = segment.kind == "match"
    # A betrayal emphasizes character work and promo delivery rather than in-ring mechanics.
    performer_scores = []
    for wrestler in wrestlers:
        ratings = rating_breakdown(wrestler)
        if match:
            # Match style is a real scoring input, not merely a commentary modifier.
            # 45% of performer execution comes from chosen weighted styles.
            style_profile = match_profile(state, segment, state.storylines.get(segment.storyline_id))
            score = .55 * ratings["match"] + .45 * style_profile['style_fit']
        elif segment.kind == "betrayal":
            score = .70 * ratings["promo"] + .30 * (4 * wrestler.attributes["character_work"])
        elif segment.kind in ("backstage", "contract_signing"):
            score = .80 * ratings["promo"] + .20 * ratings["backstage"]
        else:
            score = ratings["promo"]
        performer_scores.append(score - .38 * wrestler.fatigue + (wrestler.morale-12.5)*.17)
    performer_score = clamp(mean(performer_scores))
    story = state.storylines.get(segment.storyline_id) if segment.storyline_id else None
    if story:
        continuity = .6 * story.coherence + .4 * story.fan_investment
        # The same story repeated every week without development can lose its novelty.
        repeat_count = sum(1 for entry in story.history[-3:] if entry.get("kind") == segment.kind)
        if segment.creative_direction == "slow_burn" and repeat_count >= 2:
            continuity -= 6 * repeat_count
    else:
        continuity = 45.0
    from .memories import memory_effect
    chemistry_score = clamp(chemistry(state, segment.wrestler_ids) + memory_effect(state,segment.wrestler_ids,segment.storyline_id))
    # Creative clarity is inferred from continuity and character execution.
    # Advertising money is an independent crowd/reach factor, NOT wrestling skill.
    booking=clamp(.58*clamp(continuity)+.42*performer_score)
    from .marketing import marketing_impact
    promotion_visibility=marketing_impact(state,segment)
    pacing = pacing_score(segment.kind, segment.duration, crowd_fatigue)
    factors = {"performers": performer_score, "story": clamp(continuity),
               "chemistry": chemistry_score, "booking": booking, "pacing": pacing}
    weights = SEGMENT_WEIGHTS[segment.kind]
    baseline = sum(factors[key] * weight for key, weight in weights.items())
    planned_beat_delivered = bool(story and story.planned_beat and not story.planned_beat.get('fulfilled')
                                  and story.planned_beat.get('kind') == segment.kind
                                  and set(story.planned_beat.get('wrestler_ids', story.wrestler_ids[:2]))
                                      == set(segment.wrestler_ids))
    if planned_beat_delivered:
        baseline += 2.0   # Scene promise fits the booking; storytelling continuity bonus.
    # Most RNG now occurs within each move/promo beat, not as one final mystery roll.
    noise = rng.triangular(-1.0, 1.0, 0)
    match_details = None
    match_modifier = 0.0
    detailed_match = None
    if match:
        detailed_match = match_profile(state, segment, story)
        match_modifier = detailed_match['execution_modifier']
        match_details = {
            'ring_execution': detailed_match['style_fit'],
            'stamina_readiness': detailed_match['stamina_readiness'],
            'finish_credibility': detailed_match['finish_credibility'],
            'execution_modifier': match_modifier,
        }
    if segment.promo_brawl and not match:
        match_modifier += (mean(w.attributes['presence'] + w.attributes['character_work'] for w in wrestlers) - 30) * .15
    from .audience import duration_risk, surprise_roll
    duration = duration_risk(segment.kind,segment.duration,segment.stipulation,rng)
    # Roll every scripted wrestling exchange and spoken beat before rating the segment.
    if detailed_match:
        from .match_engine import generate_highlights
        highlights=generate_highlights(state,segment,rng)
        detailed_match['highlights']=highlights
    else:
        from .highlights import generate_segment_highlights
        highlights=generate_segment_highlights(state,segment,rng)
    actions=[h for h in highlights if 'action_delta' in h]
    action_modifier=sum(h['action_delta'] for h in actions)/max(1,len(actions))
    quality = clamp(baseline + match_modifier + noise + duration['adjustment']+action_modifier)

    from .fan_interest import fan_context, fan_outcome
    context=fan_context(state,segment,story)
    if match:
        crowd_preference = mean((w.attributes["fan_connection"] * 4 for w in wrestlers))
        # Main-event performers draw higher expectations; jobbers can still surprise.
        position_bonus=mean({'main_event':3,'upper_mid_card':1.5,'mid_card':0,
                             'lower_mid_card':-1.2,'jobber':-2.5}.get(w.card_tier,0)
                            for w in wrestlers)
        crowd = .64 * quality + .23 * crowd_preference + .13 * (story.hype if story else 42) + position_bonus
    else:
        crowd = .59 * quality + .23 * mean(w.attributes["fan_connection"] * 4 for w in wrestlers) + .18 * (story.hype if story else 42)
    crowd = clamp(crowd - .38 * crowd_fatigue + rng.triangular(-2, 2, 0)
                  + promotion_visibility + duration['adjustment']*.35
                  + (detailed_match['crowd_modifier'] if detailed_match else 0))

    reactions=fan_outcome(context,quality,crowd,duration['band'])
    crowd=clamp(crowd*.72+reactions['satisfaction']*.28)
    hype_delta = round(clamp((crowd - 52) / 5 + (promotion_visibility / 2.5), -8, 10), 2)
    from .creative_logic import evaluate_direction
    creative_impact=evaluate_direction(story,segment.creative_direction,quality)
    hype_delta += creative_impact['hype']
    if segment.promo_brawl and not match:
        hype_delta += 1.5 if story and story.coherence > 60 else .1
    if detailed_match:
        hype_delta += detailed_match['hype_modifier']
    if planned_beat_delivered:
        hype_delta += .8
    trust_delta = round(clamp((quality - 65) / 17, -3, 3), 2)
    if detailed_match:
        trust_delta += detailed_match['trust_modifier']
    trust_delta += creative_impact['trust'] + reactions['accountability_trust']
    surprise = surprise_roll(quality,crowd,rng)
    if surprise:
        crowd = clamp(crowd + surprise['fame_delta'] * 1.6)
    winner = segment.planned_winner_id if match else None
    summary = {
        "match": f"{wrestlers[0].name} and {wrestlers[-1].name} wrestled a {segment.duration}-minute match.",
        "promo": f"{', '.join(w.name for w in wrestlers)} addressed the audience.",
        "confrontation": f"Tensions escalated between {', '.join(w.name for w in wrestlers)}.",
        "backstage": f"A backstage scene featured {', '.join(w.name for w in wrestlers)}.",
        "betrayal": f"An unexpected betrayal changed the dynamic between {', '.join(w.name for w in wrestlers)}.",
        "interview": f"{', '.join(w.name for w in wrestlers)} took part in an interview.",
        "contract_signing": "An on-screen contract signing raised the stakes.",
        "return": f"{wrestlers[0].name} made a dramatic appearance.",
    }[segment.kind]
    if winner and not match:
        summary += f" Booked winner: {state.wrestlers[winner].name}."
    if detailed_match:
        summary = ' '.join(detailed_match['beats'])
    else:
        nonmatch_highlights=highlights
    if segment.promo_brawl and not match:
        summary += " The verbal exchange breaks into a brief, heated ringside brawl."
    summary += (" The crowd responded enthusiastically." if crowd >= 78 else
                " The crowd was engaged." if crowd >= 60 else
                " The reaction was mixed." if crowd >= 43 else
                " The crowd struggled to connect.")
    result = {
        "title": segment.title, "kind": segment.kind, "duration": segment.duration,
        "participants": segment.wrestler_ids, "winner": winner,
        "quality": round(quality, 2), "crowd": round(crowd, 2),
        "audience": {**context,**reactions},
        "hype_delta": round(hype_delta, 2), "fan_trust_delta": round(trust_delta, 2),
        "rng_adjustment": round(noise, 2),
        "action_rng": {'attempts':len(actions),'successful':sum(bool(a['successful']) for a in actions),
                       'execution_effect':round(action_modifier,2)},
        "promotion_visibility":round(promotion_visibility,2),
        "fan_reaction": ("Fans praised the segment and its pacing." if crowd>=78 else
                         "Fans were engaged, with some divided on the creative direction." if crowd>=60 else
                         "Fans had a mixed response, particularly to the pacing or execution." if crowd>=43 else
                         "The audience was disappointed and wants a stronger follow-up."), "factors": {k: round(v, 2) for k, v in factors.items()},
        "match_details": match_details, "match_engine": detailed_match,
        "highlights": detailed_match["highlights"] if detailed_match else nonmatch_highlights,
        "injuries": [], "duration_risk":duration,"surprise":surprise,"role_turn":None,"expectations":None,
        "planned_beat_delivered": planned_beat_delivered, "narrative": summary,
        "creative_impact": creative_impact,
    }
    from .report_analysis import analyze_segment
    result['analysis'] = analyze_segment(result)
    return result
