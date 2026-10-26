"""Deterministic seeded fiction-only injury events and week-by-week recovery.

Probability values are gameplay knobs, NOT medical forecasts. No detailed injuries are narrated.
"""
from __future__ import annotations
import random
from .models import GameState, Segment, Wrestler, clamp

# Roll severity only on occurrence: most absences last 1–3 weeks; long absences are rare.
SEVERITY_BANDS = (
    ('short', 0.78, (1,3)),
    ('medium', 0.19, (4,12)),
    ('long', 0.03, (13,52)),
)
STIPULATION_RISK = {'standard':1.0,'submission':1.03,'ironman':1.30,
                   'no_disqualification':1.40,'cage':1.80,'extreme':2.20}
INTENSITY_RISK = {'measured':.70,'standard':1.0,'high':1.40}


def injury_probability(w: Wrestler, segment: Segment) -> float:
    """Per-appearance chance, not percentage. Max 10% for extreme combinations."""
    if segment.kind != 'match' and not segment.promo_brawl:
        return 0.0
    base = 0.001 + (w.attributes['injury_proneness'] / 25) * .012
    if segment.kind != 'match':
        return min(.01, base*.22)
    workload = max(.70, min(1.85,segment.duration/16))
    fatigue_factor = 1 + w.fatigue/28
    return min(.10, base * workload * STIPULATION_RISK[segment.stipulation]
               * INTENSITY_RISK[segment.intensity] * fatigue_factor)


def roll_injury(state: GameState, w: Wrestler, segment: Segment, rng:random.Random) -> dict | None:
    if w.injury is not None or rng.random() >= injury_probability(w,segment):
        return None
    pick=rng.random()
    total=0.0
    for name,weight,span in SEVERITY_BANDS:
        total+=weight
        if pick < total:
            severity=name
            weeks=rng.randint(*span)
            break
    else:  # defensive against rounding
        severity, weeks='long', 52
    outcome={'severity':severity,'weeks_remaining':weeks,'original_weeks':weeks,
             'start_week':state.week,'start_year':state.year,
             'description':f'{w.name} is sidelined for approximately {weeks} week(s).'}
    w.injury=outcome
    w.injury_history.append(dict(outcome))
    w.morale=clamp(w.morale-.5 if severity=='short' else w.morale-1,0,25)
    state.news.append(f'Medical update: {outcome["description"]}')
    return dict(wrestler_id=w.id,wrestler_name=w.name,**outcome)


def advance_recovery(state:GameState) -> list[str]:
    news=[]
    for w in state.wrestlers.values():
        if not w.injury:
            continue
        w.injury['weeks_remaining']-=1
        if w.injury['weeks_remaining']<=0:
            w.injury=None
            note=f'{w.name} is cleared to return after their recovery period.'
            state.news.append(note)
            news.append(note)
    return news
