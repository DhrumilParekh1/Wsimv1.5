"""Audience anticipation, satisfaction, repetition and accountability.
Every score is grounded in game state, not generated fan prose.
"""
from __future__ import annotations
from .models import clamp
TIERS={'jobber':0,'lower_mid_card':1,'mid_card':2,'upper_mid_card':3,'main_event':4}


def stake_level(state,segment,story=None):
    wrestlers=[state.wrestlers[w] for w in segment.wrestler_ids]
    top=max(TIERS[w.card_tier] for w in wrestlers)
    status=round(clamp(27+top*13+(8 if segment.championship_id else 0)+((story.hype-50)*.18 if story else 0)))
    return {'score':status,'tier':('lower_card' if status<45 else 'mid_card' if status<68 else 'upper_card' if status<82 else 'main_event')}


def rivalry_repetition(state,segment,story):
    ids=frozenset(segment.wrestler_ids)
    recent=0;hist=0
    for show in state.shows.values():
        if not show.simulated or show.result is None:continue
        for seg in show.segments:
            if frozenset(seg.wrestler_ids)==ids:
                hist+=1
                if abs((state.year-show.result.get('year',state.year))*52+state.week-show.week)<=8:
                    recent+=1
    # Repeated versions of the same feud are less novel but old histories eventually become valuable.
    fatigue=clamp(max(0,recent-1)*5+max(0,hist-4)*.7 + (story.fatigue if story else 0),0,35)
    return {'recent_encounters':recent,'historical_encounters':hist,'fatigue':round(fatigue,1)}


def fan_context(state,segment,story):
    stakes=stake_level(state,segment,story)
    repeat=rivalry_repetition(state,segment,story)
    core=(story.hype*.46+story.fan_investment*.36+story.coherence*.18) if story else 42
    hype_bonus=(stakes['score']-50)*.23
    participants=[state.wrestlers[w] for w in segment.wrestler_ids]
    traits={t for w in participants for t in w.traits}
    distinctive=3.5 if len(participants)==2 and 'small_underdog' in traits and ('big_man' in traits or 'giant' in traits) else 0
    anticipation=clamp(core+hype_bonus-repeat['fatigue']*.60+distinctive)
    # High-profile rivalries have greater exposure and therefore expectations.
    expected_quality=clamp(48+stakes['score']*.28+anticipation*.13)
    return {**stakes,**repeat,'anticipation':round(anticipation,2),
            'expected_quality':round(expected_quality,2)}


def fan_outcome(context,quality,raw_crowd,duration_band):
    expectation_gap=quality-context['expected_quality']
    fatigue_penalty=context['fatigue']*.22
    satisfaction=clamp(.69*raw_crowd+.31*(50+expectation_gap)-fatigue_penalty)
    # Short segments and long high-stakes disasters disappoint disproportionately.
    if duration_band=='short' and context['anticipation']>65:satisfaction=clamp(satisfaction-3)
    trust=clamp((satisfaction-62)/24 - max(0,context['anticipation']-quality)*.017,-5,5)
    return {'satisfaction':round(satisfaction,2),'expectation_gap':round(expectation_gap,2),
            'accountability_trust':round(trust,3),'fatigue_penalty':round(fatigue_penalty,2)}
