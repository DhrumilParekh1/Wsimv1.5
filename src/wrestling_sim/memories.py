"""Compact, weighted event ledger for simulation and narrative retrieval."""
from __future__ import annotations
from .models import GameState, clamp


def add_memory(state: GameState, event: str, description: str, wrestler_ids=(), storyline_id=None,
               intensity=50, trust_effect=0, relationship_effect=0):
    memory = {'id': state.generate_id('memory'), 'year': state.year, 'week': state.week,
              'type': event, 'description': description[:350], 'wrestler_ids':list(wrestler_ids),
              'storyline_id': storyline_id, 'intensity':round(clamp(intensity),2),
              'trust_effect':float(trust_effect), 'relationship_effect':float(relationship_effect)}
    state.memories.append(memory)
    state.memories[:] = state.memories[-700:]
    return memory


def relevant_memories(state: GameState, wrestler_ids=(), storyline_id=None, limit=5):
    ids = set(wrestler_ids)
    absolute = (state.year-2026)*52 + state.week
    ranked = []
    for m in state.memories:
        overlap = len(ids.intersection(m.get('wrestler_ids',[])))
        direct = bool(storyline_id and m.get('storyline_id')==storyline_id)
        if not overlap and not direct:
            continue
        age = max(0, absolute-((m['year']-2026)*52+m['week']))
        score = m['intensity']*.35 + overlap*24 + (24 if direct else 0) + 25/(1+age/13)
        if m['type'] in ('betrayal','broken_promise','role_turn','contract_breakdown'):
            score += 14
        ranked.append((score,m))
    return [dict(m,relevance_score=round(score,2)) for score,m in sorted(ranked,key=lambda x:x[0],reverse=True)[:limit]]


def memory_effect(state: GameState, wrestler_ids=(), storyline_id=None):
    memories = relevant_memories(state,wrestler_ids,storyline_id,limit=4)
    # Only memories of shared events / same story influence chemistry. Capped and
    # not a direct proxy for historic match quality.
    return clamp(sum((m.get('relationship_effect',0)*.6 + m.get('trust_effect',0)*.3)
                     *m['relevance_score']/110 for m in memories), -6, 6)
