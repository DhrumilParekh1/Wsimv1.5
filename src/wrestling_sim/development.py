"""Coach-wrestler compatibility and attribute progression. Stable and auditable."""
from __future__ import annotations
from .models import clamp

FITS={
 'supportive':{'balanced':86,'ambitious':75,'cooperative':96,'independent':73,'volatile':88},
 'demanding':{'balanced':76,'ambitious':93,'cooperative':68,'independent':50,'volatile':42},
 'pragmatic':{'balanced':90,'ambitious':75,'cooperative':86,'independent':94,'volatile':65}}

def personality_fit(coach_personality,wrestler_personality):
    return FITS.get(coach_personality,{}).get(wrestler_personality,70)

def coaching_effectiveness(state,coach,wrestler):
    assigned=sum(cid==coach['id'] for cid in state.coach_assignments.values())
    availability=clamp(100-max(0,assigned-1)*18)
    quality=coach['skill']*4
    compat=personality_fit(coach['personality'],wrestler.personality)
    relationship=(wrestler.relationships.get(coach['id'],12.5)+coach.get('relationships',{}).get(wrestler.id,12.5))*2
    specialty=100 if coach['specialty'] in ('technical','fitness','promo') else 50
    return round(clamp(.40*quality+.20*compat+.15*relationship+.15*availability+.10*specialty),2)
