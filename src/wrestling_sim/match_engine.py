"""V0.3 match psychology engine; pure calculation, no mutation of game state.

Professional wrestling outcomes are BOOKED. Randomness changes reception, not
secretly the winner. Changing weights here doesn't affect historical save files.
"""
from __future__ import annotations
from statistics import mean
import random
from .models import GameState, Segment, clamp

# Edit these presets to rebalance styles. Each style totals 1.0, while
# two/three-style blends still use 65/35 and 55/30/15 respectively.
STYLE_WEIGHTS = {
    'balanced': {'workrate':.15,'technique':.13,'moves':.12,'sequences':.14,'selling':.13,
                 'athleticism':.12,'agility':.09,'stamina':.08,'determination':.04},
    'technical': {'technique':.26,'workrate':.20,'sequences':.18,'selling':.14,
                  'moves':.10,'stamina':.07,'determination':.05},
    'high_flying': {'agility':.24,'athleticism':.22,'moves':.20,'sequences':.15,
                    'flair':.09,'selling':.05,'stamina':.05},
    'power': {'athleticism':.25,'moves':.22,'presence':.16,'stamina':.15,
              'selling':.12,'determination':.10},
    'brawl': {'determination':.22,'selling':.18,'presence':.17,'stamina':.15,
              'moves':.14,'character_work':.09,'workrate':.05},
    'storytelling': {'character_work':.16,'sequences':.16,'moves':.13,'flair':.10,
                     'athleticism':.07,'agility':.06,'selling':.16,
                     'technique':.10,'determination':.06},
}

FINISH_EFFECTS = {
    "clean": {"crowd": 1.1, "hype": .2, "trust": .25, "coherence": .7},
    "flash_pin": {"crowd": -.4, "hype": 1.0, "trust": -.3, "coherence": -.4},
    "interference": {"crowd": 2.3, "hype": 2.0, "trust": -1.2, "coherence": -1.5},
    "disqualification": {"crowd": -6.0, "hype": 1.3, "trust": -2.0, "coherence": -2.3},
    "time_limit_draw": {"crowd": -1.5, "hype": 1.0, "trust": -.8, "coherence": -.6},
}
INTENSITY_LOAD = {"measured": .78, "standard": 1.0, "high": 1.35}


def match_profile(state: GameState, segment: Segment, story) -> dict:
    wrestlers = [state.wrestlers[wid] for wid in segment.wrestler_ids]
    means = lambda key: mean(w.attributes[key] * 4 for w in wrestlers)
    styles = segment.match_styles or [segment.match_style]
    blend = [0.55, 0.30, 0.15] if len(styles) == 3 else [0.65, 0.35] if len(styles) == 2 else [1.0]
    divisor = sum(blend)
    combined = {key: sum(STYLE_WEIGHTS[name].get(key, 0) * share / divisor
                         for name, share in zip(styles, blend)) for key in {k for name in styles for k in STYLE_WEIGHTS[name]}}
    style_fit = mean(4 * sum(w.attributes[key] * weight for key, weight in combined.items()) for w in wrestlers)
    # Styles change which attributes dominate; combo synergy reflects pace/psychology/stamina.
    contrast = len(styles) - 1
    synergy = (2.2 if 'storytelling' in styles and 'technical' in styles else 0) + (1.5 if 'high_flying' in styles and 'power' in styles else 0)
    if 'high_flying' in styles and 'brawl' in styles: synergy -= 1.2
    style_fit = clamp(style_fit + synergy - .65 * contrast)
    psychology = .29 * means("selling") + .24 * means("sequences") + .25 * means("experience") + .22 * means("character_work")
    # The player's selected match style and stipulation both affect the rating.
    if segment.stipulation == "no_disqualification":
        stip_fit = .40 * means("selling") + .34 * means("presence") + .26 * means("character_work")
    elif segment.stipulation == "submission":
        stip_fit = .48 * means("technique") + .28 * means("selling") + .24 * means("stamina")
    elif segment.stipulation in ("cage", "extreme"):
        stip_fit = .32 * means("stamina") + .32 * means("selling") + .36 * means("presence")
    elif segment.stipulation == "ironman":
        stip_fit = .40 * means("stamina") + .35 * means("workrate") + .25 * means("technique")
    else:
        stip_fit = 76.0
    exhaustion = mean(w.fatigue for w in wrestlers)
    stamina = means("stamina")
    workload = segment.duration * INTENSITY_LOAD[segment.intensity]
    stamina_readiness = clamp(100 - max(0, workload - 10) * 1.12 + (stamina - 75) * .22 - exhaustion * .68)
    if segment.planned_winner_id:
        winner = state.wrestlers[segment.planned_winner_id]
        competitors=[w for w in wrestlers if w.id != winner.id]
        opposition=mean(w.attributes['momentum'] for w in competitors)
        credibility = clamp(76 + (winner.attributes['momentum'] - opposition) * 1.4
                            + ((story.hype - 50) * .16 if story else 0))
    else:
        credibility = 72.0
    fx = FINISH_EFFECTS[segment.finish_type]
    historic=[h for h in (story.history[-6:] if story else []) if h.get('finish')==segment.finish_type]
    repetition=len(historic)
    high_stakes=bool(segment.championship_id or (story and story.hype>77))
    tier={'jobber':0,'lower_mid_card':1,'mid_card':2,'upper_mid_card':3,'main_event':4}
    loser_protection=0
    if segment.planned_winner_id:
        other=[w for w in wrestlers if w.id!=segment.planned_winner_id]
        loser_protection=max(tier[w.card_tier] for w in other)
    # The match's technical quality and its ending satisfaction are separate.
    satisfaction=credibility*.40+psychology*.24+style_fit*.20+stamina_readiness*.16
    satisfaction+= {'clean':6,'flash_pin':-1,'interference':-5,'disqualification':-15,'time_limit_draw':-9}[segment.finish_type]
    satisfaction-=repetition*(6 if segment.finish_type!='clean' else 1.5)
    if high_stakes and segment.finish_type in ('disqualification','interference'): satisfaction-=11
    if segment.finish_type in ('interference','disqualification','flash_pin'):
        satisfaction+=loser_protection*1.4
    satisfaction=clamp(satisfaction)
    # Bounded scoring. Even a strong stipulation cannot rescue poor performers.
    execution = clamp((style_fit - 72) * .12 + (psychology - 75) * .09 +
                      (stamina_readiness - 75) * .085 + (stip_fit - 75) * .060 +
                      (credibility - 75) * .04, -11, 11)
    if segment.finish_type == 'time_limit_draw' and segment.duration < 10:
        execution -= 2.0
    if segment.stipulation == 'ironman' and segment.duration < 20:
        execution -= 3.5
    if segment.intensity == 'high' and stamina_readiness < 65:
        execution -= 2.0
    execution = clamp(execution, -12, 12)
    # Distinctive finish wording, no invented match results or injuries.
    winner_name = state.wrestlers[segment.planned_winner_id].name if segment.planned_winner_id else None
    if segment.finish_type == 'time_limit_draw':
        ending = 'The bell sounds at the time limit with neither competitor declared the winner.'
    elif segment.finish_type == 'interference':
        ending = f'An outside distraction shapes the decisive moment. {winner_name} is awarded the win.'
    elif segment.finish_type == 'disqualification':
        ending = f'The official ends the contest by disqualification. {winner_name} wins on the ruling.'
    elif segment.finish_type == 'flash_pin':
        ending = f'{winner_name} takes a sudden, surprising victory.'
    elif winner_name:
        ending = f'{winner_name} wins decisively after the final exchange.'
    else:
        ending = 'The two competitors deliver the planned finish without a designated victor.'
    openings = {
        'balanced': 'Both competitors mix holds, counters and moments of spectacle.',
        'technical': 'The match begins with careful holds and technical counters.',
        'high_flying': 'The pace rises quickly as agile sequences draw attention.',
        'power': 'The competitors rely on power and imposing ring presence.',
        'brawl': 'A heated, physical contest keeps the pace unpredictable.',
        'storytelling': 'Every counter and pause refers back to the rivalry between them.',
    }
    middle = ('The pacing remains controlled, keeping the audience focused.' if segment.intensity == 'measured'
              else 'The middle portion builds to a series of well-timed reversals.' if segment.intensity == 'standard'
              else 'The high tempo pushes the performers to sustain the audience energy.')
    # Purely flavour variance: all outcome variance is in the regular simulation RNG.
    return {
        'style': segment.match_style, 'styles': styles, 'style_weights': {k:round(v,3) for k,v in combined.items()}, 'stipulation': segment.stipulation,
        'finish': segment.finish_type, 'intensity': segment.intensity,
        'style_fit': round(style_fit, 2), 'psychology': round(psychology, 2),
        'stamina_readiness': round(stamina_readiness, 2),
        'finish_satisfaction': round(satisfaction,2), 'finish_repetition':repetition,
        'stipulation_fit': round(stip_fit, 2), 'finish_credibility': round(credibility, 2),
        'execution_modifier': round(execution, 2),
        'crowd_modifier': fx['crowd']+(satisfaction-70)*.20, 'hype_modifier': fx['hype'],
        'trust_modifier': fx['trust'], 'coherence_modifier': fx['coherence'],
        'beats': [f"The match blends {', '.join(s.replace('_', ' ') for s in styles)}. " + openings[styles[0]], middle, ending],
    }

for _style, _weights in STYLE_WEIGHTS.items():
    assert abs(sum(_weights.values()) - 1) < 1e-9, f"Invalid {_style} style weights"


def generate_highlights(state: GameState, segment: Segment, rng: random.Random) -> list[dict]:
    """Chronological fictional beats, drawing moves ONLY from an actor's assigned moveset."""
    if segment.match_format=="battle_royale":
        from .battle_royale import royale_highlights
        return royale_highlights(state,segment,rng)["highlights"]
    if segment.match_format!="singles":
        from .multi_match_engine import multi_highlights
        return multi_highlights(state,segment,rng)["highlights"]
    a,b=(state.wrestlers[x] for x in segment.wrestler_ids)
    styles=set(segment.match_styles or [segment.match_style])
    count=min(9,max(3,segment.duration//3))
    highlights=[]
    for i in range(count):
        minute=max(1,round(segment.duration*(i+1)/(count+1)))
        actor,partner=(a,b) if i%2==0 else (b,a)
        compatible=[m for m in actor.moveset if m['style'] in styles and not m['finisher']]
        pool=compatible or [m for m in actor.moveset if not m['finisher']] or actor.moveset
        selected=rng.choice(pool)
        move=selected['name']
        # Action probabilities respect the same attribute profile as match scoring.
        blended=match_profile(state,segment,state.storylines.get(segment.storyline_id))['style_weights']
        execution=sum(actor.attributes[attr]*weight for attr,weight in blended.items())
        # Individual move selection remains restricted to the assigned moveset.
        penalty=actor.fatigue*.28+(minute/segment.duration)*max(0,segment.duration-16)*.10
        # Each exchange has its OWN chance and RNG roll, rather than relying
        # on one arbitrary modifier applied to the finished match.
        chance=clamp(.19+execution*.027-(penalty*.01)
                    - (2.0 if 'high_flying' in styles and selected['style']=='high_flying' else 0)*.015,
                    .15,.92)
        roll=rng.random()
        success=roll<chance
        if success:
            line=f'{actor.name} lands {move}; {partner.name} regroups and responds.'
        else:
            line=f'{actor.name} attempts {move}, but {partner.name} counters.'
        highlights.append({'minute':minute,'text':line,'performer_id':actor.id,'move':move,
                           'successful':success,'success_chance':round(chance,4),
                           'rng_roll':round(roll,4), 'action_delta':round((int(success)-chance)*14,3)})
    winner=state.wrestlers.get(segment.planned_winner_id) if segment.planned_winner_id else None
    if segment.finish_type=='time_limit_draw':
        ending='The bell sounds at the time limit; no winner is declared.'
        move=None
    elif winner and segment.finish_type=='clean':
        finisher=next((m['name'] for m in winner.moveset if m['finisher']),winner.moveset[-1]['name'])
        move=finisher
        ending=f'{winner.name} finishes with {finisher} and scores the booked victory.'
    elif winner:
        move=None
        ending=f'{winner.name} is declared the winner via {segment.finish_type.replace("_"," ")}.'
    else:
        move=None
        ending='The contest reaches its planned conclusion without a named winner.'
    # Two additional event rolls determine how cleanly the intended finish is executed.
    finishing_skill=winner.attributes['sequences'] if winner else 12.5
    for offset in (2,1):
        minute=max(1,segment.duration-offset)
        roll=rng.random()
        chance=clamp(.42+finishing_skill*.016-(winner.fatigue*.008 if winner else 0),.15,.92)
        success=roll<chance
        line=(f'The closing exchange is timed precisely by {winner.name}.' if success else
              f'The finishing sequence briefly loses rhythm before {winner.name} recovers.') if winner else ending
        highlights.append({'minute':minute,'text':line,
            'performer_id':winner.id if winner else None,'move':None,'successful':success,
            'success_chance':round(chance,4),'rng_roll':round(roll,4),'action_delta':round((int(success)-chance)*5,2)})
    highlights.sort(key=lambda b:b['minute'])
    highlights.append({'minute':segment.duration,'text':ending,
                       'performer_id':winner.id if winner else None,'move':move,'is_finish':True})
    return highlights
