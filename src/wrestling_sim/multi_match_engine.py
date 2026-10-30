"""Deterministic-seeded interactions for 3- and 4-person booked matches.

Match winners are fixed by the booker. RNG determines quality of cooperation,
counters, interruptions, fatigue, and individual performance—not the result.
"""
from __future__ import annotations
from collections import defaultdict
import random
from .models import clamp
from .match_engine import STYLE_WEIGHTS

def _blend(segment):
    styles=segment.match_styles or [segment.match_style]
    weights=[.55,.30,.15] if len(styles)==3 else [.65,.35] if len(styles)==2 else [1.]
    total=sum(weights)
    return {k:sum(STYLE_WEIGHTS[s].get(k,0)*w/total for s,w in zip(styles,weights))
            for k in {k for s in styles for k in STYLE_WEIGHTS[s]}}

def _score(w,weights):
    return sum(w.attributes[k]*v for k,v in weights.items())/25

def _pick(rng,weights):
    total=sum(max(.001,w) for w in weights)
    roll=rng.random()*total
    for i,weight in enumerate(weights):
        roll-=max(.001,weight)
        if roll<=0:return i
    return len(weights)-1

def multi_highlights(state,segment,rng:random.Random):
    """Simulate individual actions with active/off-ring recovery and pin breaks."""
    ids=segment.wrestler_ids
    if len(ids) not in (3,4):raise ValueError("Multi-person falls require 3 or 4 wrestlers")
    wrestlers=[state.wrestlers[x] for x in ids]
    style=_blend(segment)
    stamina={w.id:100-max(0,w.fatigue)*.35 for w in wrestlers}
    contributions=defaultdict(list)
    events=[]
    count=max(5,min(14,segment.duration//2))
    winner=state.wrestlers[segment.planned_winner_id]
    for i in range(count):
        minute=max(1,round((i+1)*segment.duration/(count+2)))
        # Active actors with sufficient stamina have greater opportunity to act;
        # extra wrestlers can be recovering away from the center of the action.
        active_weights=[max(.05,.25+.65*stamina[w.id]/100 + w.attributes["sequences"]*.008)
                        for w in wrestlers]
        attacker=wrestlers[_pick(rng,active_weights)]
        other=[w for w in wrestlers if w.id!=attacker.id]
        defender=other[_pick(rng,[.6+.4*stamina[w.id]/100 for w in other])]
        act=rng.choices(["exchange","counter","double_team","pin_break","recovery"],
                        weights=[40,22,14,14,10],k=1)[0]
        if act=="double_team":
            allies=[w for w in other if w.id!=defender.id]
            # Existing interpersonal chemistry and alignment affect a temporary
            # alliance, but do not guarantee cooperation or success.
            def alliance_fit(ally):
                bond=(attacker.relationships.get(ally.id,0)+ally.relationships.get(attacker.id,0))/50
                alignment=.18 if attacker.role==ally.role else -.08
                return max(.05,.45+bond*.45+alignment+ally.attributes["character_work"]*.012)
            ally=allies[_pick(rng,[alliance_fit(w) for w in allies])]
            attack=(.33*attacker.attributes["sequences"]+.24*attacker.attributes["moves"]+
                    .20*ally.attributes["character_work"]+.23*ally.attributes["technique"])/25
            defence=(defender.attributes["selling"]+defender.attributes["agility"])/50
            chance=clamp(.38+.38*(attack-defence)+.10*stamina[attacker.id]/100+
                         .12*(alliance_fit(ally)-.5),.10,.88)
            success=rng.random()<chance
            text=(f"{attacker.name} and {ally.name} coordinate against {defender.name}." if success else
                  f"{defender.name} anticipates a double-team from {attacker.name} and {ally.name}.")
            stamina[ally.id]=max(0,stamina[ally.id]-3)
            contributions[ally.id].append(2. if success else -1.)
        elif act=="pin_break":
            attack=(attacker.attributes["agility"]*.3+attacker.attributes["sequences"]*.3+
                    attacker.attributes["determination"]*.25+attacker.attributes["stamina"]*.15)/25
            chance=clamp(.35+.42*(attack-.5)+.08*stamina[attacker.id]/100,.12,.90)
            success=rng.random()<chance
            text=(f"{attacker.name} interrupts {defender.name}'s pin attempt." if success else
                  f"{attacker.name} rushes to stop {defender.name}, but arrives late to the exchange.")
        elif act=="recovery":
            stamina[attacker.id]=min(100,stamina[attacker.id]+11)
            success=True
            chance=1.
            text=f"{attacker.name} takes a moment to recover while the others battle."
        else:
            compatible=[m for m in attacker.moveset if not m.get("finisher") and m.get("style") in (segment.match_styles or [segment.match_style])]
            pool=compatible or [m for m in attacker.moveset if not m.get("finisher")] or attacker.moveset
            move=rng.choice(pool)["name"]
            attack=_score(attacker,style)
            defence=(defender.attributes["technique"]*.4+defender.attributes["selling"]*.3+
                     defender.attributes["agility"]*.3)/25
            chance=clamp(.42+.45*(attack-defence)+.1*(stamina[attacker.id]-stamina[defender.id])/100,.12,.9)
            success=rng.random()<chance
            if act=="counter":
                text=(f"{attacker.name} counters {defender.name} and creates an opening." if success else
                      f"{defender.name} anticipates {attacker.name}'s counter.")
            else:
                text=(f"{attacker.name} connects with {move} on {defender.name}." if success else
                      f"{defender.name} avoids {attacker.name}'s attempt at {move}.")
        stamina[attacker.id]=max(0,stamina[attacker.id]-(3.5 if segment.intensity=="high" else 2.))
        contributions[attacker.id].append(3. if success else -2.)
        events.append({"minute":minute,"text":text,"performer_id":attacker.id,
            "target_id":defender.id,"action":act,"successful":success,
            "success_chance":round(chance,4),
            "action_delta":round((int(success)-chance)*9,3)})
    finisher=next((m["name"] for m in winner.moveset if m.get("finisher")),"the decisive finishing sequence")
    other=[w for w in wrestlers if w.id!=winner.id]
    victim=other[_pick(rng,[1.+w.fatigue*.012 for w in other])]
    if segment.finish_type=="clean":
        ending=f"{winner.name} finishes {victim.name} with {finisher} to claim the booked victory."
    elif segment.finish_type=="flash_pin":
        ending=f"{winner.name} surprises {victim.name} with the decisive pin."
    elif segment.finish_type=="interference":
        ending=f"An outside distraction shifts the finish; {winner.name} defeats {victim.name}."
    else:
        raise ValueError("Multi-person falls allow clean, flash pin or interference finishes")
    events.append({"minute":segment.duration,"text":ending,"performer_id":winner.id,
                   "target_id":victim.id,"is_finish":True})
    performance={wid:round(sum(values)/max(1,len(values)),2) for wid,values in contributions.items()}
    return {"highlights":events,"individual_performance":performance,"endurance":{w:round(v,2) for w,v in stamina.items()},
            "finish_victim_id":victim.id,"format":segment.match_format,
            "interaction_quality":round(55+sum(v for values in contributions.values() for v in values)/max(1,count)*4,2)}
