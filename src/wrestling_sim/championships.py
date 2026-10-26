"""Promotion championships: persistent lineage, division restrictions and commercial prestige."""
from __future__ import annotations
from .models import GameState, Segment, clamp

BELTS = (
    ('men_world','APW World Championship','men', 92),
    ('men_intercontinental','APW Intercontinental Championship','men', 73),
    ('women_world','APW Women’s World Championship','women', 87),
)

def ensure_championships(state:GameState) -> dict:
    for belt_id,name,division,prestige in BELTS:
        if belt_id not in state.championships:
            state.championships[belt_id]={'id':belt_id,'name':name,'division':division,
                'company_id':state.player_company_id,'holder_id':None,
                'prestige':prestige,'defenses':0,'lineage':[]}
    return state.championships

def check_title_match(state:GameState, segment:Segment) -> None:
    if not segment.championship_id: return
    belt=ensure_championships(state).get(segment.championship_id)
    if not belt or belt['company_id']!=state.player_company_id:
        raise ValueError('Invalid championship')
    if any(state.wrestlers[w].division!=belt['division'] for w in segment.wrestler_ids):
        raise ValueError('Title match cannot mix divisions')
    if belt['holder_id'] and belt['holder_id'] not in segment.wrestler_ids:
        raise ValueError('The defending champion must be in the match')
    if not segment.planned_winner_id or segment.finish_type not in ('clean','flash_pin','interference'):
        raise ValueError('Title matches require a named winner and eligible finish')

def settle_title_match(state:GameState, segment:Segment, outcome:dict, week:int):
    if not segment.championship_id: return None
    belt=ensure_championships(state)[segment.championship_id]
    old=belt['holder_id']; new=segment.planned_winner_id
    # Prestige is earned with well-received championship bouts and can decay.
    belt['prestige']=round(clamp(belt['prestige']+(outcome['crowd']-65)/48,15,100),2)
    changed=old!=new
    if changed:
        belt['holder_id']=new
        belt['defenses']=0
    else: belt['defenses']+=1
    belt['lineage'].append({'week':week,'winner_id':new,'previous_holder_id':old,'change':changed,
                            'match_title':segment.title})
    belt['lineage']=belt['lineage'][-120:]
    winner=state.wrestlers[new]
    winner.attributes['relevance']=clamp(winner.attributes['relevance']+(1.0 if changed else .16),0,25)
    winner.attributes['popularity']=clamp(winner.attributes['popularity']+(.55 if changed else .08),0,25)
    winner.attributes['momentum']=clamp(winner.attributes['momentum']+(.65 if changed else .16),0,25)
    result={'belt_id':belt['id'],'belt_name':belt['name'],'winner_id':new,'new_champion':changed,
            'prestige':belt['prestige']}
    outcome['championship']=result
    return result
