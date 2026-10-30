"""Atomic JSON save/load. Safe for one local single-process game session."""
from __future__ import annotations
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from .models import GameState, Company, Wrestler, Storyline, Show, Segment


def save_game(state: GameState, destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(state), indent=2, ensure_ascii=False)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            file.write(payload)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_game(source: str | Path) -> GameState:
    return restore_game(json.loads(Path(source).read_text(encoding='utf-8')))


def restore_game(data: dict) -> GameState:
    # V0.3 saves contain no roster divisions. Migrate known fictional starter talent;
    # leave new custom characters in the default men's division unless explicitly set.
    for wid in ('vale', 'cruz', 'collins', 'haze', 'orbit'):
        if wid in data.get('wrestlers', {}):
            data['wrestlers'][wid].setdefault('division', 'women')
    if 'vale-collins' not in data.get('storylines', {}) and all(
        wid in data.get('wrestlers', {}) and data['wrestlers'][wid].get('company_id') == data['player_company_id']
        for wid in ('vale','collins')
    ):
        data.setdefault('storylines', {})['vale-collins'] = {
            'id':'vale-collins', 'title':'The Crown and the Challenger',
            'wrestler_ids':['vale','collins'], 'hype':45, 'fan_investment':49, 'coherence':76,
            'stage':'building', 'history':[], 'last_seen_week':None, 'planned_beat':{}
        }
    # V0.7 introduces a non-scoring injury proneness input. Restore legacy saves without
    # discarding a single existing attribute, segment or injury record.
    for raw in data.get('wrestlers',{}).values():
        raw.setdefault('attributes',{}).setdefault('injury_proneness',9.0)
        moves = raw.get('moveset', [])
        if len(moves) > 8:
            from .movesets import default_moveset
            raw['moveset'] = default_moveset(raw.get('id',''), raw.get('attributes',{}))
    # V1.8 import repair: the first real-roster importer accepted source
    # weights in the 40..300 kg range, while Wrestler allows only 45..260.
    # Repair only imported real-name profiles, never arbitrary fictional saves.
    # Preserve the source database; this is a *gameplay placeholder* correction.
    for wid, raw in data.get('wrestlers', {}).items():
        if not wid.startswith(('rw_', 'wd_')):
            continue
        value = raw.get('weight_kg', 90)
        if not isinstance(value, (int, float)) or not 45 <= value <= 260:
            raw['weight_kg'] = 90
            data.setdefault('activity_log', []).append({
                'type': 'real_data_profile_repair',
                'wrestler_id': wid,
                'field': 'weight_kg',
                'original_value': value,
                'replacement_value': 90,
                'reason': 'Unsupported imported weight; substituted a fictional game default.',
            })
            data.setdefault('news', []).append(
                f"Data compatibility repair: {raw.get('name', wid)} has a neutral "
                "in-game weight placeholder; review the source catalogue."
            )
    # Legacy weekly metrics used a 0–100 popularity index; migrate to
    # actual viewers without overwriting any existing recorded values.
    for metric in data.get('weekly_metrics', []):
        if 'viewership' not in metric:
            metric['viewership'] = max(1000,round(25000+metric.get('popularity',36)*4500))
    # V1.0 disallows winnerless NEW bouts; restore legacy booked cards with an
    # awarded winner while leaving historical show result snapshots unchanged.
    for raw_show in data.get('shows', {}).values():
        for card in raw_show.get('segments', []):
            if card.get('kind')=='match' and (not card.get('planned_winner_id') or card.get('finish_type')=='time_limit_draw'):
                card['planned_winner_id'] = card['wrestler_ids'][0]
                if card.get('finish_type')=='time_limit_draw':
                    card['finish_type']='disqualification'
    restored = GameState(
        seed=data['seed'], year=data['year'], week=data['week'],
        player_company_id=data['player_company_id'],
        companies={k: Company(**v) for k, v in data['companies'].items()},
        wrestlers={k: Wrestler(**v) for k, v in data['wrestlers'].items()},
        storylines={k: Storyline(**v) for k, v in data.get('storylines', {}).items()},
        shows={k: Show(**{**v, 'segments': [Segment(**s) for s in v['segments']]})
               for k, v in data.get('shows', {}).items()},
        news=data.get('news', []),
        financial_history=data.get('financial_history', []),
        decisions=data.get('decisions', {}),
        activity_log=data.get('activity_log', []),
        scenes=data.get('scenes', {}),
        creative_head_id=data.get('creative_head_id', 'morgan'),
        assignments=data.get('assignments', {}),
        interactions=data.get('interactions', []),
        coaches=data.get('coaches', {}),
        scouts=data.get('scouts', {}),
        coach_assignments=data.get('coach_assignments', {}),
        scouting_reports=data.get('scouting_reports', []),
        world_news=data.get('world_news', []),
        rival_history=data.get('rival_history', []),
        weekly_metrics=data.get('weekly_metrics', []),
        dialogue_sessions=data.get('dialogue_sessions', {}),
        contract_sessions=data.get('contract_sessions', {}),
        sponsor_deals=data.get('sponsor_deals', {}),
        sponsor_responses=data.get('sponsor_responses', {}),
        social_posts=data.get('social_posts', []),
        memories=data.get('memories', []),
        narrative_alerts=data.get('narrative_alerts', []),
        championships=data.get('championships', {}),
        tournaments=data.get('tournaments', {}),
        chemistry=data.get('chemistry', {}),
        talent_appearances=data.get('talent_appearances', {}),
        talent_concerns=data.get('talent_concerns', []),
        incidents=data.get('incidents', []),
        mentorships=data.get('mentorships', []),
        press_conferences=data.get('press_conferences', {}),
        campaigns=data.get('campaigns', []),
        recruitment_interest=data.get('recruitment_interest', []),
        precontracts=data.get('precontracts', []),
        contract_promises=data.get('contract_promises', []),
        transfer_offers=data.get('transfer_offers', []),
        next_id=data.get('next_id', 1),
    )

    from .press_and_incidents import incident_options
    for incident in restored.incidents:
        if incident.get('status')=='open':
            incident['options']=incident_options(incident.get('kind',''))

    # Restore the extended fictional universe without overwriting existing contracts,
    # stories or player roster decisions from a v0.4 campaign.
    from .starter import new_game
    from .world import bootstrap_world
    blueprint = new_game(restored.seed)
    for company_id in ('circuit', 'royal'):
        restored.companies.setdefault(company_id, blueprint.companies[company_id])
    new_ids = {'sora','mizuki','arden','lyra','pike','talia','thorn','aria',
               'eden','solis','hart','blaze','finn'}
    is_real_universe = any(
        item.get('type') == 'real_roster_provenance'
        for item in data.get('activity_log', [])
    )
    if not is_real_universe:
        # Historical fictional saves still need their legacy starter additions.
        for wrestler_id in new_ids:
            restored.wrestlers.setdefault(wrestler_id, blueprint.wrestlers[wrestler_id])
    bootstrap_world(restored)
    from .championships import ensure_championships
    ensure_championships(restored)
    # Import narrative history when upgrading an older campaign that predates
    # the memory ledger. Do not manufacture an incident that lacks a saved fact.
    if not data.get('memories'):
        historic = []
        for show in sorted(restored.shows.values(), key=lambda e:(e.week,e.id)):
            if not show.simulated or not show.result:
                continue
            for segment, outcome in zip(show.segments,show.result.get('segments',[])):
                if segment.kind not in ('betrayal','return') and not outcome.get('role_turn'):
                    continue
                kind = 'role_turn' if outcome.get('role_turn') else segment.kind
                summary = outcome.get('narrative') or segment.title
                historic.append({'id':f'legacy-{show.id}-{len(historic)}',
                                 'year':show.result.get('year',restored.year), 'week':show.week,
                                 'type':kind,'description':summary[:350],
                                 'wrestler_ids':list(segment.wrestler_ids),
                                 'storyline_id':segment.storyline_id,
                                 'intensity':85 if kind in ('betrayal','role_turn') else 65,
                                 'trust_effect':0,'relationship_effect':-3 if kind=='betrayal' else 0})
        for index, conversation in enumerate(restored.interactions):
            if not conversation.get('wrestler_id'):
                continue
            historic.append({'id':f'legacy-interaction-{index}', 'year':conversation.get('year',restored.year),
                             'week':conversation.get('week',restored.week), 'type':'owner_meeting',
                             'description':str(conversation.get('narrative','Past private meeting.'))[:350],
                             'wrestler_ids':[conversation['wrestler_id']], 'storyline_id':None,
                             'intensity':55,'trust_effect':0,
                             'relationship_effect':float(conversation.get('owner_relationship_delta',0))})
        restored.memories = historic[-700:]
    from .audience import ensure_expectations
    for story in restored.storylines.values():
        ensure_expectations(restored,story)
    from .press_and_incidents import ensure_incidents
    ensure_incidents(restored)
    return restored
