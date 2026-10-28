"""Scripted event facts for promos, interviews and backstage scenes.

All factual content is created from state, so optional Ollama cannot invent turns or outcomes.
"""
from __future__ import annotations
import random
from .models import GameState, Segment, clamp

OPENERS = {
    'promo':'addresses the crowd and sets out their argument',
    'confrontation':'interrupts the exchange and questions the other performer',
    'backstage':'speaks privately about the current tension',
    'interview':'answers a pointed question about the rivalry',
    'betrayal':'appears cooperative, but tension is visible',
    'contract_signing':'explains what is at stake in the upcoming contest',
    'return':'steps into view and acknowledges the audience',
}
RESPONSES = {
    'promo':'emphasizes the stakes with a sharp closing line',
    'confrontation':'fires back and refuses to back down',
    'backstage':'offers a guarded response to the challenge',
    'interview':'avoids a direct promise and keeps the audience guessing',
    'betrayal':'breaks the alliance and changes the tone of the story',
    'contract_signing':'puts their name to the on-screen agreement',
    'return':'hints at unfinished business',
}


def generate_segment_highlights(state: GameState, segment: Segment, rng: random.Random) -> list[dict]:
    participants=[state.wrestlers[wid] for wid in segment.wrestler_ids]
    events=[]
    count=max(2,min(4,segment.duration//3+1))
    for i in range(count):
        speaker=participants[i%len(participants)]
        minute=min(segment.duration,max(1,round((i+.5)*segment.duration/count)))
        content=OPENERS[segment.kind] if i==0 else RESPONSES[segment.kind]
        # Solo promos use topic-specific beats, not rivalry creative directions.
        solo_topic=segment.promo_topic if segment.kind=='promo' and not segment.storyline_id else None
        if solo_topic:
            topic_text={
                'self_hype':'promises the crowd a memorable performance',
                'ambitions':'shares their ambitions for the coming season',
                'address_fans':'addresses the supporters and responds to their expectations',
                'recent_win':'reflects on a recent victory',
                'recent_loss':'addresses a recent defeat and vows to improve',
                'open_challenge':'announces an open championship challenge for a future event',
                'title_reign':'reflects on their in-game championship reign',
                'callout':'calls out a potential future opponent'
            }
            if i==0:
                content=topic_text[solo_topic]
            elif segment.promo_interrupt and len(participants)>1 and speaker.id!=participants[0].id:
                content='interrupts the speaker and demands a response'
            else:
                content='develops the selected topic without starting an unrelated rivalry'
        if not solo_topic and segment.creative_direction=='slow_burn' and i>0:
            content='keeps the disagreement unresolved and adds another question'
        if not solo_topic and segment.creative_direction=='resolve' and i==count-1:
            content='offers a clear conclusion to this chapter of the rivalry'
        skill=(.34*speaker.attributes['mic_skills']+.24*speaker.attributes['charisma']+
               .24*speaker.attributes['character_work']+.18*speaker.attributes['presence'])
        chance=clamp(.24+skill/36-speaker.fatigue*.004,.20,.92)
        roll=rng.random()
        success=roll<chance
        if not success: content='struggles to communicate the intended message and loses the crowd briefly'
        text=f'{speaker.name} {content}.'
        if segment.promo_brawl and i==count-1:
            text+=' The argument turns into a brief, heated ringside brawl.'
        events.append(dict(minute=minute,performer_id=speaker.id,move=None,text=text,
                           successful=success,success_chance=round(chance,4),rng_roll=round(roll,4),
                           action_delta=round((int(success)-chance)*13,3)))
    return events
