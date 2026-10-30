"""Persistent inaugural championship tournaments and direct multi-person crowning.

Booker manually schedules the named bracket matches. Winners are selected before
booking, then the simulator records results and only awards the vacant belt
after the final match has really been simulated. All methods share title rules.
"""
from __future__ import annotations
from .models import Segment, clamp
from .championships import ensure_championships

DIRECT={"triple_threat":3,"fatal_four_way":4}
METHODS=("single_elimination","triple_threat","fatal_four_way","battle_royale")

def _round(name,index,participants,match_format="singles"):
    return {"id":f"{name}-m{index}","participants":list(participants),
            "match_format":match_format,"winner_id":None,"status":"ready" if participants else "waiting",
            "show_id":None,"week":None}

def create_tournament(state,belt_id,entrant_ids,method="single_elimination",name=None):
    belts=ensure_championships(state)
    belt=belts.get(belt_id)
    if not belt or belt["company_id"]!=state.player_company_id:
        raise ValueError("Unknown championship")
    if belt.get("holder_id"):
        raise ValueError("Inaugural tournament requires a vacant championship")
    if method not in METHODS:
        raise ValueError("Unknown championship competition format")
    if any(t["belt_id"]==belt_id and t["status"]=="active" for t in state.tournaments.values()):
        raise ValueError("An active championship competition already exists for this title")
    entrants=list(entrant_ids)
    n=len(entrants)
    if n!=len(set(entrants)):
        raise ValueError("Championship entrants must all be different")
    if method=="single_elimination" and n not in (4,8):
        raise ValueError("Elimination brackets require exactly 4 or 8 wrestlers")
    if method in DIRECT and n!=DIRECT[method]:
        raise ValueError(f"{method} requires exactly {DIRECT[method]} wrestlers")
    if method=="battle_royale" and not 4<=n<=20:
        raise ValueError("Battle royale championship requires 4–20 wrestlers")
    for wid in entrants:
        w=state.wrestlers.get(wid)
        if not w or w.company_id!=state.player_company_id or w.division!=belt["division"]:
            raise ValueError("All entrants must be active roster wrestlers from the championship's division")
        if w.injury or w.availability<25:
            raise ValueError(f"{w.name} is unavailable to compete")
    tid=state.generate_id("tournament")
    rounds=[]
    if method=="single_elimination":
        remaining=n; cursor=0
        while remaining>=2:
            rounds.append([_round(tid,len(rounds)*10+i,
                                   entrants[i*2:i*2+2] if len(rounds)==0 else [])
                           for i in range(remaining//2)])
            remaining//=2
    else:
        rounds=[[_round(tid,0,entrants,method)]]
    tour={"id":tid,"name":(name or f"Inaugural {belt['name']}").strip()[:90],
          "belt_id":belt_id,"division":belt["division"],"method":method,
          "entrant_ids":entrants,"rounds":rounds,
          "status":"active","winner_id":None,
          "created_week":state.week,"created_year":state.year,
          "completed_week":None}
    state.tournaments[tid]=tour
    state.news.append(f"{tour['name']}: inaugural championship competition announced.")
    return tour

def pending_matches(state):
    return [{"tournament_id":t["id"],"tournament_name":t["name"],"belt_id":t["belt_id"],
             "round":r+1,**m}
            for t in state.tournaments.values() if t["status"]=="active"
            for r,round_matches in enumerate(t["rounds"])
            for m in round_matches if m["status"]=="ready"]

def _locate(state,segment):
    tour=state.tournaments.get(segment.tournament_id)
    if not tour or tour["status"]!="active":
        raise ValueError("Unknown or completed championship competition")
    for round_index,round_matches in enumerate(tour["rounds"]):
        for match_index,m in enumerate(round_matches):
            if m["id"]==segment.tournament_match_id:
                return tour,round_index,match_index,m
    raise ValueError("Unknown tournament fixture")

def validate_tournament_segment(state,segment,used=None):
    if not segment.tournament_id:
        return
    tour,round_index,match_index,m=_locate(state,segment)
    if m["status"]!="ready":
        raise ValueError("That tournament fixture is not ready to book")
    if segment.kind!="match" or segment.match_format!=m["match_format"]:
        raise ValueError("Booked match format must match tournament fixture")
    if set(segment.wrestler_ids)!=set(m["participants"]) or len(segment.wrestler_ids)!=len(m["participants"]):
        raise ValueError("Booked match participants must match the tournament bracket")
    if segment.championship_id:
        raise ValueError("Tournament titles are awarded automatically after the final; leave match title unset")
    if segment.planned_winner_id not in m["participants"]:
        raise ValueError("Tournament winner must be one of the eligible entrants")
    if used is not None:
        key=(segment.tournament_id,segment.tournament_match_id)
        if key in used:raise ValueError("Duplicate tournament fixture on show card")
        used.add(key)

def _inaugural_champion(state,tour,segment,outcome):
    belt=ensure_championships(state)[tour["belt_id"]]
    if belt.get("holder_id"):
        raise ValueError("The inaugural title is no longer vacant")
    wid=segment.planned_winner_id
    belt["holder_id"]=wid
    belt["defenses"]=0
    belt["prestige"]=round(clamp(belt.get("prestige",50)+(outcome["crowd"]-65)/48,15,100),2)
    belt["lineage"].append({"year":state.year,"week":state.week,"winner_id":wid,
                            "previous_holder_id":None,"change":True,
                            "match_title":segment.title,"tournament_id":tour["id"]})
    belt["lineage"]=belt["lineage"][-120:]
    wrestler=state.wrestlers[wid]
    for key,delta in (("momentum",.65),("popularity",.55),("relevance",1)):
        wrestler.attributes[key]=clamp(wrestler.attributes[key]+delta,0,25)
    outcome["championship"]={"belt_id":belt["id"],"belt_name":belt["name"],
                             "winner_id":wid,"new_champion":True,"prestige":belt["prestige"],
                             "inaugural":True,"tournament_id":tour["id"]}
    state.news.append(f"{wrestler.name} is crowned inaugural {belt['name']} champion.")
    return outcome["championship"]

def record_result(state,segment,outcome,show_id):
    """Advance exactly once, after the booked fixture has been simulated."""
    if not segment.tournament_id:return None
    tour,r,m_index,fixture=_locate(state,segment)
    if fixture["status"]!="ready":
        raise ValueError("Tournament fixture already resolved")
    winner=segment.planned_winner_id
    if winner not in fixture["participants"] or winner!=outcome.get("winner"):
        raise ValueError("Tournament finish differs from the booked winner")
    fixture.update({"status":"complete","winner_id":winner,"show_id":show_id,
                    "week":state.week})
    if r+1<len(tour["rounds"]):
        next_fixture=tour["rounds"][r+1][m_index//2]
        if winner in next_fixture["participants"]:
            raise ValueError("Duplicate bracket advancement")
        next_fixture["participants"].append(winner)
        if len(next_fixture["participants"])==2:
            next_fixture["status"]="ready"
        state.news.append(f"{state.wrestlers[winner].name} advances in {tour['name']}.")
    else:
        tour["winner_id"]=winner
        tour["status"]="complete"
        tour["completed_week"]=state.week
        _inaugural_champion(state,tour,segment,outcome)
    outcome["tournament"]={"id":tour["id"],"fixture":fixture["id"],"winner_id":winner,
                           "round":r+1,"complete":tour["status"]=="complete"}
    return outcome["tournament"]
