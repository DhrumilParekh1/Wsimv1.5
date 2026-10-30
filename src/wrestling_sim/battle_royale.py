"""Battle royale elimination simulation; outcome booked, execution emergent.

Every elimination uses the active survivors' stamina, positioning and opponent
attributes; the selected winner survives and the logged final elimination is
always valid. No real-world outcomes are inferred.
"""
from __future__ import annotations
import random
from .models import clamp

def royale_highlights(state,segment,rng:random.Random):
    ids=list(segment.wrestler_ids)
    if not 4<=len(ids)<=20:raise ValueError("Battle royale requires 4–20 wrestlers")
    if segment.planned_winner_id not in ids:raise ValueError("Battle royale needs a booked winner")
    winner=segment.planned_winner_id
    active=list(ids)
    endurance={wid:clamp(100-state.wrestlers[wid].fatigue*.4) for wid in ids}
    positioning={wid:rng.random() for wid in ids}
    eliminated=[]
    events=[]
    attempt=0
    while len(active)>1:
        attempt+=1
        # Elimination selection is probabilistic but excludes the booked winner.
        # More exhausted wrestlers and wrestlers at the ropes are more vulnerable.
        threatened=[wid for wid in active if wid!=winner]
        # Optional player-directed late eliminations: finish non-featured
        # entrants first, then preserve the requested spotlight exit order.
        special=[wid for wid in segment.featured_eliminations if wid in threatened]
        ordinary=[wid for wid in threatened if wid not in special]
        if ordinary:threatened=ordinary
        elif special:threatened=special[:1]
        weights=[.2+(100-endurance[wid])*.025+positioning[wid]*1.3 for wid in threatened]
        target=rng.choices(threatened,weights=weights,k=1)[0]
        opponents=[wid for wid in active if wid!=target]
        attacker=rng.choice(opponents)
        target_w=state.wrestlers[target]
        attack_w=state.wrestlers[attacker]
        # Attack / defence attributes in 0..1; stamina and risk modify resistance.
        offence=(attack_w.attributes["athleticism"]*.32+
                 attack_w.attributes["moves"]*.28+
                 attack_w.attributes["presence"]*.18+
                 attack_w.attributes["stamina"]*.22)/25
        defence=(target_w.attributes["athleticism"]*.24+
                 target_w.attributes["determination"]*.28+
                 target_w.attributes["stamina"]*.28+
                 target_w.attributes["sequences"]*.20)/25
        exposure=positioning[target]
        fatigue=(100-endurance[target])/100
        chance=clamp(.15+.35*offence+.25*exposure+.15*fatigue-.30*defence,.04,.90)
        roll=rng.random()
        eliminated_now=roll<chance or attempt>len(ids)*18
        # The last two always resolve to the booked survivor in bounded time.
        end_min=segment.duration*(len(eliminated)+1)/(len(ids)-1)
        minute=max(1,min(segment.duration-1,round(end_min)))
        if eliminated_now:
            active.remove(target)
            eliminated.append({"wrestler_id":target,"by_id":attacker,"minute":minute,
                               "chance":round(chance,4),"roll":round(roll,4)})
            text=f"{attack_w.name} eliminates {target_w.name}; {len(active)} competitors remain."
            positioning.pop(target)
        else:
            text=f"{target_w.name} survives an elimination attempt from {attack_w.name}."
            positioning[target]=min(1.,positioning[target]+.12)
        endurance[target]=max(0.,endurance[target]-5)
        endurance[attacker]=max(0.,endurance[attacker]-3)
        events.append({"minute":minute,"text":text,"performer_id":attacker,
                       "target_id":target,"action":"elimination",
                       "successful":eliminated_now,"success_chance":round(chance,4),
                       "rng_roll":round(roll,4),
                       "action_delta":round((int(eliminated_now)-chance)*5,2),
                       "eliminated_id":target if eliminated_now else None})
    final=state.wrestlers[winner]
    events.append({"minute":segment.duration,"text":f"{final.name} is the last wrestler remaining and wins the battle royale.",
                   "performer_id":winner,"is_finish":True})
    return {"highlights":events,"eliminations":eliminated,"survivor_id":winner,
            "format":"battle_royale","endurance":{wid:round(v,2) for wid,v in endurance.items()},
            "interaction_quality":round(clamp(48+sum(1 for x in events if x.get("successful"))*2),2)}
