"""Branching, persistent 2-step creative episodes for each active storyline.

Decisions influence the persistent simulation. Each storyline can only run one
creative episode per week. Finishing one creates a specific, trackable promise
for the next card, which is rewarded or penalized through the show engine.
"""
from __future__ import annotations
import random
from statistics import mean
from .models import GameState, clamp

OPENINGS = {
    'mind_games': {
        'label': 'Build through mind games',
        'hint': 'Stronger coherence, slower rise in hype',
        'narrative': '{a} proposes weeks of calculated mind games. {b} will need to respond with something personal.',
        'hype': -.4, 'coherence': 2.1, 'fan_investment': 1.0,
    },
    'challenge': {
        'label': 'Make a public challenge',
        'hint': 'Higher hype; pressure to deliver',
        'narrative': '{a} wants to call out {b} in front of the audience. Everybody will expect an answer.',
        'hype': 2.4, 'coherence': .7, 'fan_investment': 1.5,
    },
    'shock': {
        'label': 'Make it personal',
        'hint': 'Big short-term buzz, greater storytelling risk',
        'narrative': '{a} pitches a shocking escalation involving {b}. The creative room debates whether it is too soon.',
        'hype': 3.6, 'coherence': -1.6, 'fan_investment': .6,
    },
}
BEATS = {
    'mind_games': [
        {'id': 'promo', 'label': 'Book a cutting promo', 'hint': 'Promise a verbal chapter in the next two cards'},
        {'id': 'confrontation', 'label': 'Plan a controlled confrontation', 'hint': 'Give the opponents a face-to-face scene'},
    ],
    'challenge': [
        {'id': 'confrontation', 'label': 'Book a face-to-face challenge', 'hint': 'Deliver the confrontation your fans expect'},
        {'id': 'match', 'label': 'Promise a decisive match', 'hint': 'Set up an encounter within the deadline'},
    ],
    'shock': [
        {'id': 'betrayal', 'label': 'Build to a betrayal', 'hint': 'A high-risk twist requiring on-screen payoff'},
        {'id': 'backstage', 'label': 'Show backstage fallout', 'hint': 'Less spectacle, more psychological buildup'},
    ],
}


def _scene_key(state: GameState, storyline_id: str) -> str:
    return f'scene-{state.year}-{state.week}-{storyline_id}'


def _node(state: GameState, scene: dict) -> dict:
    from .management import creative_head, advise_openings
    head = creative_head(state)
    story = state.storylines[scene['storyline_id']]
    people = [state.wrestlers[wid].name for wid in story.wrestler_ids[:2]]
    a, b = people
    if scene['step'] == 0:
        intro = (f'Your head writer has called a creative meeting about “{story.title}.” '
                 f'{a} and {b} have a storyline with {story.hype:.0f}/100 hype and '
                 f'{story.coherence:.0f}/100 narrative coherence. How should it advance?')
        options = advise_openings(state, story, OPENINGS)
        intro = f"{head['name']} (Creative {head['skill']}/25) advises you. " + intro
        title = 'What direction should the rivalry take?'
    elif scene['step'] == 1:
        first = scene['choices'][0]
        intro = (scene['last_narrative'] + ' Now the creative team needs a concrete follow-up. '
                 'The promise will be remembered by the simulation: missing it has consequences.')
        options = BEATS[first]
        title = 'What will you promise the audience?'
    else:
        intro = scene.get('last_narrative', '')
        options = []
        title = 'Creative meeting complete'
    return {'id': scene['id'], 'storyline_id': story.id, 'storyline_title': story.title,
            'title': title, 'narrative': intro, 'step': scene['step'], 'status': scene['status'],
            'options': options, 'choices': list(scene['choices']),
            'result': scene.get('result'), 'history': list(scene.get('history', [])),
            'creative_head': head['name'], 'creative_skill': head['skill']}


def scene_overview(state: GameState) -> list[dict]:
    scenes = []
    for story in state.storylines.values():
        if story.stage == 'resolved':
            continue
        key = _scene_key(state, story.id)
        if key in state.scenes:
            scenes.append(_node(state, state.scenes[key]))
        else:
            scenes.append({'id': key, 'storyline_id': story.id, 'storyline_title': story.title,
                           'title': 'Your next creative meeting',
                           'narrative': f'Decide how to develop “{story.title}” this week.',
                           'step': -1, 'status': 'not_started', 'options': [], 'choices': [],
                           'result': None, 'history': []})
    return scenes


def start_scene(state: GameState, storyline_id: str) -> dict:
    story = state.storylines.get(storyline_id)
    if not story or story.stage == 'resolved':
        raise ValueError('An active storyline is required to start a creative scene')
    if any(state.wrestlers.get(wid) is None or state.wrestlers[wid].company_id != state.player_company_id
           for wid in story.wrestler_ids):
        raise ValueError('The storyline must involve wrestlers on your roster')
    key = _scene_key(state, storyline_id)
    if key in state.scenes:
        raise ValueError('A creative meeting has already started for this story this week')
    scene = {'id': key, 'storyline_id': storyline_id, 'step': 0,
             'status': 'in_progress', 'choices': [], 'history': [], 'last_narrative': ''}
    state.scenes[key] = scene
    return _node(state, scene)


def choose_scene(state: GameState, scene_id: str, option_id: str) -> dict:
    scene = state.scenes.get(scene_id)
    if not scene:
        raise ValueError('Unknown creative scene; start a meeting first')
    if scene_id != _scene_key(state, scene['storyline_id']):
        raise ValueError('This creative scene belongs to an earlier week')
    if scene['status'] != 'in_progress':
        raise ValueError('This creative meeting is already complete')
    story = state.storylines[scene['storyline_id']]
    if story.stage == 'resolved':
        raise ValueError('The storyline is already resolved')
    node = _node(state, scene)
    if option_id not in {opt['id'] for opt in node['options']}:
        raise ValueError('Invalid creative scene option')
    rng = random.Random(f'{state.seed}:{scene_id}:{scene["step"]}:{option_id}')
    variance = rng.triangular(-.6, .6, 0)
    effects = {}
    if scene['step'] == 0:
        # Real performer skills influence creative viability. Choices matter more
        # than noise; a well-established story can still reject a premature turn.
        performers = [state.wrestlers[wid] for wid in story.wrestler_ids]
        if option_id == 'mind_games':
            calibre = mean((w.attributes['mic_skills'] + w.attributes['character_work']) * 2 for w in performers)
        elif option_id == 'challenge':
            calibre = mean((w.attributes['charisma'] + w.attributes['presence']) * 2 for w in performers)
        else:
            calibre = mean(4 * (.45 * w.attributes['character_work'] + .35 * w.attributes['heel']
                                + .20 * w.attributes['fan_connection']) for w in performers)
        from .management import creative_head
        aptitude_effect = clamp((calibre - 72) / 15, -2.0, 2.0)
        aptitude_effect += (creative_head(state)['skill'] - 15) * .12
        if option_id == 'shock' and story.coherence < 55:
            aptitude_effect -= 1.5
        opening = OPENINGS[option_id]
        for name in ('hype', 'coherence', 'fan_investment'):
            previous = getattr(story, name)
            new_value = clamp(previous + opening[name] + aptitude_effect * {'hype': .65, 'coherence': .55, 'fan_investment': .5}[name] + variance * .4)
            setattr(story, name, round(new_value, 3))
            effects[name] = round(new_value - previous, 2)
        a, b = [state.wrestlers[wid].name for wid in story.wrestler_ids[:2]]
        narrative = opening['narrative'].format(a=a, b=b)
    else:
        # Promise remains live until fulfilled by an appropriate show segment.
        # One planned beat per storyline: replacing a previous unfulfilled plan
        # is a conscious creative reversal, costing storyline coherence.
        if story.planned_beat and not story.planned_beat.get('fulfilled'):
            story.coherence = clamp(story.coherence - 2.0)
            effects['coherence'] = -2.0
        ordinal = (state.year - 2026) * 52 + state.week
        story.planned_beat = {'kind': option_id, 'wrestler_ids': list(story.wrestler_ids[:2]),
                              'due_ordinal': ordinal + 1,
                              'origin_scene': scene_id, 'fulfilled': False}
        story.fan_investment = clamp(story.fan_investment + .5)
        effects['fan_investment'] = .5
        narrative = (f'You commit to a {option_id.replace("_", " ")} segment for “{story.title}”. '
                     'Deliver it this week or next to reward fans for following the story.')
    scene['choices'].append(option_id)
    scene['history'].append({'week': state.week, 'option_id': option_id,
                             'narrative': narrative, 'effects': effects})
    scene['last_narrative'] = narrative
    scene['step'] += 1
    if scene['step'] == 2:
        scene['status'] = 'complete'
        # Resolve the corresponding creative Inbox request only by finishing
        # the room conversation, not by choosing a shortcut on the dashboard.
        state.decisions[f'{state.year}-{state.week}-creative'] = 'creative_room'
        scene['result'] = {'kind': story.planned_beat['kind'],
                           'due_ordinal': story.planned_beat['due_ordinal']}
    state.activity_log.append({'type': 'creative_scene', 'year': state.year,
                               'week': state.week, 'storyline_id': story.id,
                               'scene_id': scene_id, 'option_id': option_id,
                               'narrative': narrative, 'effects': effects})
    state.news.append(narrative)
    response = _node(state, scene)
    response['choice_result'] = {'narrative': narrative, 'effects': effects}
    return response
