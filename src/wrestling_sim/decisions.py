"""Choice-driven owner-desk events. Decision outcomes persist and change actual game state.

Only fictional characters are used. Outcomes contain modest seeded variance;
choices cannot be re-taken in the same campaign/week.
"""
from __future__ import annotations
import random
from .models import GameState, clamp


def _event_id(state: GameState, topic: str) -> str:
    return f"{state.year}-{state.week}-{topic}"


def available_decisions(state: GameState) -> list[dict]:
    roster = [w for w in state.wrestlers.values() if w.company_id == state.player_company_id]
    if not roster:
        return []
    star = max(roster, key=lambda w: w.attributes['ambition'] + w.attributes['popularity'] * .2)
    story = next((s for s in state.storylines.values() if s.stage != 'resolved'), None)
    events = []
    if story:
        events.append({
            'id': _event_id(state, 'creative'), 'kind': 'creative', 'icon': '🎬',
            'eyebrow': 'CREATIVE MEETING', 'title': 'How long do we keep them waiting?',
            'description': f'Your creative team wants direction for “{story.title}.” The fans are paying attention, but dragging things out could cost you.',
            'involved_ids': story.wrestler_ids[:2],
            'options': [
                {'id': 'slow_burn', 'label': 'Let the tension simmer', 'hint': 'Protect coherence; risk losing momentum'},
                {'id': 'escalate', 'label': 'Raise the stakes now', 'hint': 'Potential hype boost; higher creative risk'},
                {'id': 'reassure', 'label': 'Keep your plans confidential', 'hint': 'Support talent; limited fan impact'},
            ],
            'storyline_id': story.id,
        })
    # A complaint needs a real trigger; ambition alone is not evidence of discontent.
    # Track cooldown through prior resolved decisions, including old saved campaigns.
    eligible = []
    for wrestler in roster:
        previous = [entry for entry in state.activity_log if entry.get('type') == 'decision'
                    and entry.get('event_id','').endswith('-locker_room')
                    and wrestler.name in entry.get('headline','')]
        last = max((entry.get('year', state.year)*52 + entry.get('week', 0) for entry in previous), default=-999)
        now = state.year*52 + state.week
        if now-last < 6:
            continue
        grievances = 0
        if wrestler.morale < 10: grievances += 2
        if wrestler.owner_relationship < 9: grievances += 2
        if wrestler.wants_release: grievances += 2
        if wrestler.attributes['ambition'] >= 21 and wrestler.morale < 14: grievances += 1
        if grievances >= 2:
            eligible.append((grievances, wrestler))
    if eligible:
        eligible.sort(key=lambda entry: (-entry[0], entry[1].id))
        star = eligible[0][1]
        events.append({
            'id': _event_id(state, 'locker_room'), 'kind': 'locker_room', 'icon': '🎙',
            'eyebrow': 'BACKSTAGE', 'title': f'{star.name} wants a word',
            'description': f'{star.name} believes their contributions deserve more attention. They want to know where they stand in your plans.',
            'involved_ids': [star.id],
            'options': [
                {'id': 'promise', 'label': 'Promise a bigger spotlight', 'hint': 'Raises expectations and morale'},
                {'id': 'listen', 'label': 'Listen without making promises', 'hint': 'A measured response'},
                {'id': 'dismiss', 'label': 'Tell them to earn it', 'hint': 'Could test the relationship'},
            ],
            'wrestler_id': star.id,
        })
    if state.week % 3 == 0 and len(roster) >= 2:
        first, second = sorted(roster, key=lambda w: (w.owner_relationship + w.morale, w.id))[:2]
        events.append({
            'id': _event_id(state, 'backstage_dispute'), 'kind': 'dispute', 'icon': '⚡',
            'eyebrow': 'LOCKER ROOM INCIDENT', 'title': f'{first.name} and {second.name} disagree',
            'description': f'{first.name} and {second.name} have differing views on their screen time. Your response could shift locker-room relationships.',
            'involved_ids': [first.id, second.id], 'wrestler_ids': [first.id, second.id],
            'options': [
                {'id':'mediate','label':'Bring them together', 'hint':'May improve cooperation and both relationships'},
                {'id':'side_first','label':f'Back {first.name}', 'hint':'One wrestler may feel supported, the other overlooked'},
                {'id':'ignore','label':'Let them settle it themselves', 'hint':'Avoid management involvement; the dispute may grow'},
            ],
        })
    if state.week % 2 == 0:
        events.append({
            'id': _event_id(state, 'sponsors'), 'kind': 'sponsors', 'icon': '📈',
            'eyebrow': 'BUSINESS', 'title': 'A brand is watching',
            'description': 'A regional partner has noticed your promotion. They have asked whether you want to collaborate on a small campaign.',
            'involved_ids': [],
            'options': [
                {'id': 'campaign', 'label': 'Run the campaign', 'hint': 'Production cost with possible sponsor gains'},
                {'id': 'pitch', 'label': 'Make a careful pitch', 'hint': 'Lower investment and moderate upside'},
                {'id': 'pass', 'label': 'Focus on the next show', 'hint': 'No upfront cost'},
            ],
        })
    return [e for e in events if e['id'] not in state.decisions]


def choose_option(state: GameState, event_id: str, option_id: str) -> dict:
    if event_id in state.decisions:
        raise ValueError('This decision has already been made.')
    event = next((e for e in available_decisions(state) if e['id'] == event_id), None)
    if event is None:
        raise ValueError('This decision is not available this week.')
    if option_id not in {o['id'] for o in event['options']}:
        raise ValueError('Invalid decision option.')
    rng = random.Random(f"choice:{state.seed}:{event_id}:{option_id}")
    variance = rng.triangular(-1.0, 1.0, 0)
    effects = {}
    subject = ''

    def company_change(key: str, amount: float) -> None:
        company = state.player_company
        before = getattr(company, key)
        after = clamp(before + amount)
        setattr(company, key, round(after, 3))
        effects[key] = round(after - before, 2)

    if event['kind'] == 'creative':
        story = state.storylines[event['storyline_id']]
        before = story.hype
        if option_id == 'slow_burn':
            story.coherence = clamp(story.coherence + 1.3 + variance * .3)
            story.hype = clamp(story.hype - 0.3 + variance)
            subject = 'The creative team builds toward a longer payoff. Patience helps the narrative, but the audience may want more.'
        elif option_id == 'escalate':
            story.hype = clamp(story.hype + 2.5 + variance * 2.4)
            story.coherence = clamp(story.coherence - 1.6 + variance * .7)
            subject = 'The next chapter has more urgency. Excitement increases, while storyline coherence may become harder to maintain.'
        else:
            story.coherence = clamp(story.coherence + .8 + variance * .5)
            story.hype = clamp(story.hype + variance * .8)
            for wid in story.wrestler_ids:
                state.wrestlers[wid].morale = clamp(state.wrestlers[wid].morale + .25)
            subject = 'The talent appreciates being kept in the loop. Fans have not seen a major development yet.'
        effects['storyline_hype'] = round(story.hype - before, 2)
    elif event['kind'] == 'locker_room':
        wrestler = state.wrestlers[event['wrestler_id']]
        before = wrestler.morale
        if option_id == 'promise':
            wrestler.morale = clamp(wrestler.morale + 1.0 + variance * .4, 0, 25)
            wrestler.attributes['ambition'] = clamp(wrestler.attributes['ambition'] + .06, 0, 25)
            subject = f'{wrestler.name} leaves encouraged and expects prominent booking in the coming weeks.'
        elif option_id == 'listen':
            wrestler.morale = clamp(wrestler.morale + .4 + variance * .2, 0, 25)
            subject = f'{wrestler.name} appreciates being heard, even without a concrete promise.'
        else:
            wrestler.morale = clamp(wrestler.morale - .9 + variance * .5, 0, 25)
            subject = f'{wrestler.name} is not pleased. Your response may have longer-term consequences.'
        effects['morale'] = round(wrestler.morale - before, 2)
    elif event['kind'] == 'dispute':
        first, second = (state.wrestlers[wid] for wid in event['wrestler_ids'])
        delta = (1.0 + variance*.4) if option_id == 'mediate' else (-1.5 + variance*.3 if option_id == 'ignore' else -1.1 + variance*.4)
        first.relationships[second.id] = clamp(first.relationships.get(second.id, 0)+delta, -25, 25)
        second.relationships[first.id] = clamp(second.relationships.get(first.id, 0)+delta, -25, 25)
        if option_id == 'mediate':
            first.owner_relationship = clamp(first.owner_relationship+.4, 0, 25)
            second.owner_relationship = clamp(second.owner_relationship+.4, 0, 25)
            subject = f'You mediated between {first.name} and {second.name}. Their working relationship improved.'
        elif option_id == 'side_first':
            first.morale = clamp(first.morale+.7, 0, 25)
            second.morale = clamp(second.morale-.8, 0, 25)
            second.owner_relationship = clamp(second.owner_relationship-.7, 0, 25)
            subject = f'You sided with {first.name}. {second.name} is unhappy with the choice.'
        else:
            first.morale = clamp(first.morale-.3, 0, 25)
            second.morale = clamp(second.morale-.3, 0, 25)
            subject = 'Management stayed out of the dispute. Locker-room friction grew.'
        effects['wrestler_relationship'] = round(delta, 2)
    else:
        if option_id == 'campaign':
            state.player_company.money -= 3500
            company_change('sponsor_interest', 1.5 + variance)
            effects['cash'] = -3500
            subject = 'The campaign goes ahead. You spend on marketing and attract some sponsor attention.'
        elif option_id == 'pitch':
            state.player_company.money -= 600
            company_change('sponsor_interest', .65 + variance * .65)
            effects['cash'] = -600
            subject = 'Your measured pitch keeps costs low. The sponsor is cautiously interested.'
        else:
            subject = 'You decline the approach and keep your budget focused on live shows.'
    state.decisions[event_id] = option_id
    result = {'event_id': event_id, 'option_id': option_id, 'year': state.year,
              'week': state.week, 'headline': event['title'], 'narrative': subject,
              'effects': effects}
    state.activity_log.append({'type': 'decision', **result})
    state.news.append(subject)
    return result
