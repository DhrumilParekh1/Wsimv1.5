"""Create a player-owned promotion competing with the four established companies.

Apply to an unsimulated real-name starting campaign. Draft picks are fictional
game transfers, not an assertion of real wrestler availability.
"""
from __future__ import annotations
import copy
from .models import Company, Storyline

TIERS={
    "indie":{"money":75000,"popularity":8,"fan_trust":45,
             "sponsor_interest":12,"weekly_fixed_costs":650,
             "venue_capacity":160,"ticket_price":15,"roster_limit":8,
             "show_minutes":45,"picks":1},
    "startup":{"money":400000,"popularity":22,"fan_trust":48,
               "sponsor_interest":28,"weekly_fixed_costs":2200,
               "venue_capacity":600,"ticket_price":25,"roster_limit":14,
               "show_minutes":60,"picks":2},
    "juggernaut":{"money":2500000,"popularity":45,"fan_trust":55,
                  "sponsor_interest":60,"weekly_fixed_costs":7000,
                  "venue_capacity":2500,"ticket_price":42,"roster_limit":24,
                  "show_minutes":90,"picks":3},
}

def is_custom_company(state):
    return any(c.get("type")=="company_foundation" for c in state.campaigns)

def is_eligible_for_company_creation(state):
    return (not is_custom_company(state) and state.year==2026 and state.week==1
            and not state.shows
            and state.player_company.name=="WWE"
            and any(w.id.startswith("rw_") for w in state.wrestlers.values()))

def create_company(state, name: str, tier: str, men: list[str], women: list[str]):
    if not is_eligible_for_company_creation(state):
        raise ValueError("Company setup requires a new, unplayed real-world campaign.")
    if tier not in TIERS:
        raise ValueError("Choose indie, startup, or juggernaut.")
    name=name.strip()
    if not 3<=len(name)<=55 or any(ch in "<>{}" for ch in name):
        raise ValueError("Company name must be 3–55 readable characters.")
    if name.casefold() in {c.name.casefold() for c in state.companies.values()}:
        raise ValueError("Choose a distinct company name.")
    count=TIERS[tier]["picks"]
    if len(men)!=count or len(women)!=count:
        raise ValueError(f"{tier} requires {count} men's and {count} women's draft picks.")
    picks=list(men)+list(women)
    if len(picks)!=len(set(picks)):
        raise ValueError("Draft picks must be different wrestlers.")
    for wid,division in [(wid,"men") for wid in men]+[(wid,"women") for wid in women]:
        w=state.wrestlers.get(wid)
        if not w or w.division!=division:
            raise ValueError("Draft pick unavailable or from an incorrect division.")
        if w.injury or w.age<18:
            raise ValueError("Drafted talent must be available and eligible.")
    new=copy.deepcopy(state)
    old=new.companies.pop("player")
    old.id="wwe"
    new.companies["wwe"]=old
    for wrestler in new.wrestlers.values():
        if wrestler.company_id=="player":
            wrestler.company_id="wwe"
    config=TIERS[tier]
    new.companies["player"]=Company(
        id="player",name=name,
        money=config["money"],popularity=config["popularity"],
        fan_trust=config["fan_trust"],sponsor_interest=config["sponsor_interest"],
        weekly_fixed_costs=config["weekly_fixed_costs"],
        venue_capacity=config["venue_capacity"],ticket_price=config["ticket_price"],
        roster_limit=config["roster_limit"],show_minutes=config["show_minutes"])
    # None of these are real employment or contract changes: all transfer
    # mechanics are fictional starts to a single-player sandbox scenario.
    for wid in picks:
        w=new.wrestlers[wid]
        w.company_id="player"
        w.salary_weekly=800 if tier=="indie" else 1800 if tier=="startup" else 4200
        w.contract_weeks=52
        w.morale=17
        w.owner_relationship=15
    new.storylines={}
    from .audience import ensure_expectations
    if count>=2:
        for division,selected in (("men",men),("women",women)):
            sid="founding-"+division
            new.storylines[sid]=Storyline(id=sid,title=f"{name}: {division.title()} Opening Rivalry",
                                         wrestler_ids=selected[:2],hype=30,
                                         fan_investment=35,coherence=65)
            ensure_expectations(new,new.storylines[sid])
    for cid,belt in new.championships.items():
        belt["company_id"]="player"
        belt["name"]=f"{name} "+("Women's World Championship" if cid=="women_world" else
                                   "Intercontinental Championship" if cid=="men_intercontinental" else
                                   "World Championship")
        belt["holder_id"]=None
        belt["lineage"]=[]
        belt["defenses"]=0
    new.talent_concerns=[]
    new.incidents=[]
    new.press_conferences={}
    new.scenes={}
    new.social_posts=[]
    new.chemistry={}
    new.shows={}
    new.assignments={}
    new.recruitment_interest=[]
    new.news=[f"{name} has entered the wrestling industry as a {tier} company. Draft complete."]
    new.activity_log.append({"type":"company_foundation","tier":tier,
                             "name":name,"men":list(men),"women":list(women),
                             "starting_cash":config["money"]})
    new.campaigns.append({"type":"company_foundation","tier":tier,
                          "name":name,"draft_picks":picks,"year":new.year,"week":new.week})
    for coach in new.coaches.values():
        if coach.get("company_id")=="player":coach["company_id"]="wwe"
    for scout in new.scouts.values():
        if scout.get("company_id")=="player":scout["company_id"]="wwe"
    from .world import bootstrap_world,record_metrics
    from .press_and_incidents import ensure_incidents
    new.weekly_metrics=[]
    bootstrap_world(new)
    ensure_incidents(new)
    return new
