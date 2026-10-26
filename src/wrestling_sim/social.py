"""Deterministic fictional fan reactions driven by actual simulated outcomes."""
from __future__ import annotations
import random
from .models import GameState, Show

HANDLES = ['@RingSideRae', '@CrowdPulse', '@WrestlingNerd', '@TurnbuckleTea',
           '@PromoWatch', '@TopRopeTalk', '@GrappleFan', '@MatchNight']


def generate_fan_posts(state: GameState, show: Show, report: dict) -> list[dict]:
    rng = random.Random(f'fans:{state.seed}:{state.year}:{state.week}:{show.id}')
    posts = []
    for index, segment in enumerate(report['segments']):
        score = segment['crowd']
        # Align social verdict with expectation gap, not crowd rating alone.
        from .report_analysis import analyze_segment
        sentiment = (segment.get('analysis') or analyze_segment(segment))['sentiment']
        templates = {
            'positive': [f"{segment['title']} delivered tonight. The timing was excellent!",
                         f"That {segment['kind'].replace('_',' ')} had the crowd invested from the opening."],
            'mixed': [f"Not everything in {segment['title']} clicked, but I can see the idea.",
                      f"Interesting choices tonight. I'm undecided about {segment['title']}."],
            'negative':[f"{segment['title']} didn't connect with me. Hoping next week feels stronger.",
                        f"The pacing of {segment['title']} needs another look."]}
        for count in range(2):
            text = templates[sentiment][count]
            posts.append({'id':f'{show.id}-{index}-{count}', 'show_id':show.id,
                          'week':state.week, 'year':state.year, 'handle':rng.choice(HANDLES),
                          'text':text, 'sentiment':sentiment, 'crowd':round(score,1),
                          'segment':segment['title'], 'source':'simulation'})
    overall = report['crowd']
    general = ('Fans are buzzing about the whole show!' if overall>=75 else
               'A few strong moments; curious where the stories go next.' if overall >= 50 else
               'This week was uneven. Hope the promotion comes back stronger.')
    posts.append({'id':f'{show.id}-overall','show_id':show.id, 'week':state.week,'year':state.year,
                  'handle':'@CrowdPulse','text':general,'sentiment':('positive' if overall>=75 else 'mixed' if overall>=50 else 'negative'),
                  'crowd':round(overall,1),'segment':show.name,'source':'simulation'})
    state.social_posts.extend(posts)
    state.social_posts = state.social_posts[-350:]
    return posts


def generate_transfer_reaction(state, wrestler, inquiry):
    """Public interest creates grounded social chatter immediately, not a signing claim."""
    company = state.player_company
    excitement = min(95, max(20, round(wrestler.attributes['relevance']*2.4+
                      wrestler.attributes['popularity']*1.2+company.fan_trust*.2)))
    sentiment = 'positive' if excitement>=65 else 'mixed'
    line=(f'Rumours that {company.name} wants {wrestler.name} are exciting, but no deal exists.'
          if sentiment=='positive' else
          f'{company.name} is reportedly interested in {wrestler.name}. Can they afford a deal?')
    state.social_posts.append({'id':f'transfer-{inquiry["key"]}','show_id':f'transfer-{state.year}-{state.week}',
        'week':state.week,'year':state.year,'handle':'@GrappleFan','text':line,'sentiment':sentiment,
        'crowd':excitement,'segment':f'Transfer interest: {wrestler.name}','source':'simulation'})
    state.social_posts=state.social_posts[-350:]
