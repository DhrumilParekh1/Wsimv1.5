"""Stateful storytelling: maturity, escalation ceiling, repetition and payoff risk."""
from __future__ import annotations
from .models import clamp


def evaluate_direction(story, direction: str, quality: float) -> dict:
    if not story:
        return dict(hype=0., trust=0., coherence=0., relevance=0., escalation=0., note='Unattached segment')
    history = story.history
    weeks = max(1, len({h.get('week') for h in history}) + 1)
    previous = [h.get('direction') for h in history]
    repeated = 0
    for value in reversed(previous):
        if value != direction: break
        repeated += 1
    level = getattr(story, 'escalation_level', 0.)
    if direction != 'escalate': level=max(0,level-.6)
    good = clamp((quality - 50) / 25, -1, 1)
    hype=trust=coherence=relevance=0.
    note=''
    if direction == 'advance':
        hype = .7 + good*.55 - max(0, repeated-2)*1.45
        coherence = .5 if repeated < 3 else -1.8*(repeated-1)
        note='Development advances' if repeated < 3 else 'Fans feel the story has stalled'
    elif direction == 'slow_burn':
        patience = max(0, weeks-5)*.65 + max(0, repeated-1)*1.7
        hype = .55 + good*.45 - patience
        trust = -max(0, patience-1)*.65
        coherence = .65 - patience*.8
        note='Tension grows gradually' if patience < 2 else 'The payoff is being delayed too long'
    elif direction == 'escalate':
        ceiling = max(0,level-2)*2.0 + max(0,repeated-1)*1.9
        hype = 2.0 + good - ceiling
        trust = -max(0,ceiling-2)*.75
        coherence = -max(0,ceiling-1)*1.0
        level = clamp(level + 1.35,0,10)
        note='Stakes rise' if ceiling < 2 else 'Escalation fatigue is setting in'
    elif direction == 'swerve':
        setup = story.coherence >= 68 and weeks >= 3 and repeated == 0
        hype = (1.7 + good) if setup else (-2.1 + good - repeated*1.2)
        trust = .35 if setup else -1.9-repeated
        coherence = .4 if setup else -4.5
        note='A well-foreshadowed twist' if setup else 'A twist feels unearned'
    elif direction == 'resolve':
        readiness = min(1, weeks / 6) * .40 + min(1,len(history)/5)*.25 + min(1,story.fan_investment/85)*.20 + min(1,story.coherence/80)*.15
        early = max(0,.8-readiness)
        hype = -1.7-early*9 + good*1.5
        trust = (2.4 + good) if early < .12 else -early*9
        coherence = 1.4 if early < .12 else -early*10
        relevance = -early*2.6
        note='The payoff feels earned' if early < .12 else 'The feud ends before fans are invested'
    return dict(hype=round(hype,2),trust=round(trust,2),coherence=round(coherence,2),
                relevance=round(relevance,2),escalation=round(level,2),note=note,
                weeks=weeks,repeat=repeated)
