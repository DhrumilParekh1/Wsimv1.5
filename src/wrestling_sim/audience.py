"""Audience expectation and length-risk models. Nothing here uses AI-produced scores."""
from __future__ import annotations
import random
from .models import GameState, Storyline, Segment, clamp

EXPECTATIONS = {
    'clean_payoff': 'A decisive, credible payoff',
    'slow_build': 'More time for the rivalry to develop',
    'betrayal': 'A surprising betrayal',
    'heel_turn': 'A convincing turn to villain',
    'face_turn': 'A convincing turn to hero',
}


def ensure_expectations(state: GameState, story: Storyline) -> list[dict]:
    if story.expectations:
        return story.expectations
    rng = random.Random(f'fan-expect:{state.seed}:{story.id}')
    fighters = [state.wrestlers[i] for i in story.wrestler_ids if i in state.wrestlers]
    if not fighters:
        return story.expectations
    primary = rng.choice(fighters)
    turn = 'face_turn' if primary.role == 'heel' else 'heel_turn'
    story.expectations = [
        {'id': 'payoff', 'type': 'clean_payoff', 'label': EXPECTATIONS['clean_payoff'], 'support': 55 + rng.randrange(25), 'wrestler_id': None},
        {'id': 'turn', 'type': turn, 'label': f'Fans want {primary.name} to turn {"face" if turn == "face_turn" else "heel"}',
         'support': 30 + rng.randrange(35), 'wrestler_id': primary.id},
        {'id': 'pacing', 'type': 'slow_build', 'label': EXPECTATIONS['slow_build'], 'support': 30 + rng.randrange(30), 'wrestler_id': None},
    ]
    return story.expectations


def duration_risk(kind: str, minutes: int, stipulation: str, rng: random.Random) -> dict:
    """Short = frustration risk; middle = stable; long = upside AND downside.

    Risk is signed and deterministic for the game's seeded RNG stream. Bounds
    are explicit so no one duration is always rewarded or punished.
    """
    match = kind == 'match'
    short = minutes < (7 if match else 3)
    long = minutes > (22 if match else 11)
    if short:
        adjustment = rng.triangular(-16, 4, -5)
        risk_label = 'short: fans may feel short-changed'
    elif long:
        amplitude = min(24, 12 + (minutes - (22 if match else 11)) * .72)
        adjustment = rng.triangular(-amplitude, amplitude, 0)
        risk_label = 'long: high reward and high disappointment risk'
    else:
        adjustment = rng.triangular(-4, 4, 0)
        risk_label = 'medium: stable pacing'
    if match and stipulation in ('extreme', 'cage', 'ironman', 'no_disqualification'):
        adjustment += rng.triangular(-5, 5, 0)
    return {'band': 'short' if short else 'long' if long else 'medium',
            'adjustment': round(adjustment, 3), 'explanation': risk_label}


def surprise_roll(quality: float, crowd: float, rng: random.Random) -> dict | None:
    """Rare and asymmetric breakout/flop events; weighted by performance.

    ~0.7% of segments can produce an unusually large fame swing. Strength and
    direction depend heavily on the underlying crowd and quality, not blind luck.
    """
    if rng.random() >= .007:
        return None
    effective = .5 * quality + .5 * crowd
    chance_breakout = clamp((effective - 40) / 45, .06, .94)
    kind = 'breakout' if rng.random() < chance_breakout else 'flop'
    swing = round(rng.uniform(2.2, 5.0) * (1 if kind == 'breakout' else -1), 2)  # raw wrestler 0–25 fame
    return {'type': kind, 'fame_delta': swing,
            'headline': 'Unexpected breakout moment' if kind == 'breakout' else 'Unexpected audience backlash'}


def evaluate_turn(state: GameState, story: Storyline | None, segment: Segment, rng: random.Random) -> dict | None:
    if not segment.role_turn_wrestler_id:
        return None
    wrestler = state.wrestlers[segment.role_turn_wrestler_id]
    prior = wrestler.role
    target = segment.role_turn_to
    story_fit = story.coherence if story else 42
    proficiency = wrestler.attributes[target] * 4
    groundwork = 14 if story and len(story.history) >= 2 else -12
    dramatic = 5 if segment.kind in ('betrayal', 'confrontation', 'promo') else 0
    momentum = (wrestler.attributes['momentum']-12.5)*.55
    score = clamp(.42*proficiency + .28*story_fit + .16*(wrestler.attributes['character_work']*4)
                  + groundwork + dramatic + momentum + rng.triangular(-6,6,0))
    wrestler.role = target
    aligned = next((x for x in (story.expectations if story else []) if x['type'] == target+'_turn'
                    and x.get('wrestler_id') == wrestler.id), None)
    reaction = clamp(score + (6 if aligned else 0))
    return {'wrestler_id':wrestler.id,'wrestler_name':wrestler.name,'from':prior,'to':target,
            'success':round(score,2),'crowd_reaction':round(reaction,2),'fan_expected':bool(aligned)}


def resolve_expectations(state: GameState, story: Storyline, segment: Segment,
                         outcome: dict) -> dict:
    ensure_expectations(state, story)
    achieved = []
    for exp in story.expectations:
        t = exp['type']
        if t == 'clean_payoff' and segment.kind == 'match' and segment.finish_type == 'clean' and segment.creative_direction == 'resolve':
            achieved.append(exp)
        if t == 'slow_build' and segment.creative_direction == 'slow_burn':
            achieved.append(exp)
        if t == 'betrayal' and segment.kind == 'betrayal':
            achieved.append(exp)
        if t.endswith('_turn') and outcome.get('role_turn') and outcome['role_turn']['to'] == t[:-5] and exp.get('wrestler_id') == outcome['role_turn']['wrestler_id']:
            achieved.append(exp)
    served = sum(e['support'] for e in achieved)/max(1,len(achieved))/100 if achieved else 0
    if achieved:
        story.compliance_streak += 1
        story.ignored_streak = 0
        bonus = 1.8*served - max(0, story.compliance_streak-2)*1.7
    else:
        story.ignored_streak += 1
        story.compliance_streak = 0
        bonus = -max(0, story.ignored_streak-2)*1.5
    story.fan_investment = clamp(story.fan_investment + bonus)
    story.hype = clamp(story.hype + bonus*.6)
    return {'met':[e['label'] for e in achieved], 'investment_delta':round(bonus,2),
            'predictability':story.compliance_streak, 'frustration':story.ignored_streak,
            'fan_expectations':[dict(e) for e in story.expectations]}
