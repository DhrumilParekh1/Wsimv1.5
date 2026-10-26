"""Ollama runs automatically on narrative moments; no player opt-in buttons.

Every state change is committed by the Python simulation first. Failure to
connect to a local model is reported visibly, NEVER passed off as AI output.
"""
from __future__ import annotations
from .models import GameState
from .memories import relevant_memories
from .narrative import _generate, _safe_flavour, enhance_dialogue


def _alert(state, context: str, error: Exception):
    state.narrative_alerts.append({'year':state.year,'week':state.week,
        'context':context, 'message': f'Ollama narrative unavailable: {error}'})
    state.narrative_alerts[:] = state.narrative_alerts[-25:]


def auto_dialogue(state: GameState, kind: str, session_id: str):
    try:
        return enhance_dialogue(state,kind,session_id)
    except (ValueError,TypeError,KeyError) as exc:
        _alert(state,f'{kind} {session_id}',exc)
        return {'source':'unavailable','error':str(exc)}


def auto_show(state: GameState, show_id: str):
    """One bounded Ollama batch for highlights/fan reactions/report after simulation.

    Factual highlights always exist, including in error/offline conditions;
    AI authored material never changes score, assigned moves or sentiments.
    """
    show=state.shows[show_id]
    report=show.result
    beats=[]
    for index,seg in enumerate(report['segments']):
        for hi,beat in enumerate(seg.get('highlights',[])[:2]):
            beats.append((index,hi,seg,beat))
    posts=[p for p in state.social_posts if p['show_id']==show_id][:12]
    payload={
      'task':'Rewrite each existing highlight with exactly ONE concise atmospheric sentence (8 to 16 words) per entry, grounded in the fixed fact. '
             'You MAY repeat the exact named moves in each fact but may not invent NEW moves, performers, finishes, injuries or outcomes. '
             'Also draft one distinct fictional fan post for each provided fixed sentiment; then a brief neutral fan report '
             'describing positives/negatives. Include exactly one post-segment fan analysis per segment, '
             'grounded in its reaction and length; especially matches. Output JSON in order. No invented numeric claims.',
      'show':show.name,'quality':round(report['quality'],1),'crowd':round(report['crowd'],1),
      'segments':[{'title':seg['title'], 'kind':seg['kind'], 'quality':seg['quality'],
                    'crowd':seg['crowd'], 'duration_risk':seg.get('duration_risk'),
                    'surprise':seg.get('surprise')} for seg in report['segments']],
      'highlights':[{'segment':s['title'],'kind':s['kind'],'fact':b['text'],
                     'performers':[state.wrestlers[i].name for i in s['participants']],
                     'prior_history':[m['description'] for m in relevant_memories(state,s['participants'],limit=2)]}
                    for _,_,s,b in beats],
      'posts':[{'segment':p['segment'],'sentiment':p['sentiment'],'baseline':p['text']} for p in posts],
      'injuries':[i['description'] for s in report['segments'] for i in s['injuries']],
      'shocks':[s['surprise']['headline'] for s in report['segments'] if s.get('surprise')],
    }
    schema={'type':'object','properties':{
       'highlights':{'type':'array','minItems':len(beats),'maxItems':len(beats),'items':{'type':'string','minLength':8,'maxLength':200}},
       'posts':{'type':'array','minItems':len(posts),'maxItems':len(posts),'items':{'type':'string','minLength':8,'maxLength':200}},
       'segment_reactions':{'type':'array','minItems':len(report['segments']),'maxItems':len(report['segments']), 'items':{'type':'string','minLength':15,'maxLength':240}},
       'fan_report':{'type':'string','minLength':35,'maxLength':600}},
       'required':['highlights','posts','segment_reactions','fan_report'],'additionalProperties':False}
    try:
        generated=_generate(payload,schema, 'You are a wrestling broadcast writer and fictional audience reporter. '
           'Every supplied fact has already happened in the game. Preserve all match moves verbatim when referring to them. '
           'Preserve fan sentiment and NEVER invent a win, injury, role turn, move or statistic.')
        lines=generated.get('highlights');tweets=generated.get('posts');fan=generated.get('fan_report')
        reactions=generated.get('segment_reactions')
        if not isinstance(lines,list) or len(lines)!=len(beats) or not isinstance(tweets,list) or len(tweets)!=len(posts) or not isinstance(reactions,list) or len(reactions)!=len(report['segments']):
            raise ValueError('Ollama returned the wrong number of highlights/posts')
        # Content is additional commentary, never a replacement for simulator facts.
        # Require exact canonical move string whenever an AI sentence names a move;
        # do not let the model introduce a different known wrestling maneuver.
        move_names={m['name'].lower() for w in state.wrestlers.values() for m in w.moveset}
        cleaned=[]
        for (_,_,seg,beat),line in zip(beats,lines):
            if not isinstance(line,str) or not 8<=len(line.strip())<=200:
                raise ValueError('Invalid AI commentary line')
            allowed = {m['name'].lower() for wid in seg['participants'] for m in state.wrestlers[wid].moveset}
            used = [m for m in move_names if m in line.lower()]
            if any(m not in allowed or m not in beat['text'].lower() for m in used):
                raise ValueError('AI invented a move that was not in the canonical highlight')
            if '<script' in line.lower() or 'http://' in line.lower() or 'https://' in line.lower():
                raise ValueError('Unsafe model response')
            cleaned.append(line.strip())
        cleaned_posts=[t.strip() if isinstance(t,str) and 8<=len(t.strip())<=200 and '<script' not in t.lower() and 'http://' not in t.lower() and 'https://' not in t.lower() else '' for t in tweets]
        if any(not t for t in cleaned_posts): raise ValueError('Invalid generated fan post')
        if not isinstance(fan,str) or not 35<=len(fan.strip())<=600 or '<script' in fan.lower():
            raise ValueError('Invalid fan report')
        if any(not isinstance(t,str) or not 15<=len(t.strip())<=240 or '<script' in t.lower() for t in reactions):
            raise ValueError('Invalid post-match fan reactions')
        # Mutate only after every field validates.
        for (_,_,_,beat),line in zip(beats,cleaned): beat['ai_flavour']=line
        for post,line in zip(posts,cleaned_posts):
            post['text']=line;post['source']='ollama'
        for seg,reaction in zip(report['segments'],reactions):
            seg['fan_report']={'text':reaction.strip(),'source':'ollama'}
        report['fan_report']={'text':fan.strip(),'source':'ollama',
           'summary':{'positive':sum(p['sentiment']=='positive' for p in posts),
                      'mixed':sum(p['sentiment']=='mixed' for p in posts),
                      'negative':sum(p['sentiment']=='negative' for p in posts)}}
        report['ollama_status']='generated'
        return {'source':'ollama','highlights':len(beats),'posts':len(posts)}
    except (ValueError,TypeError,KeyError) as exc:
        # A connection failure is different from a malformed generation. Do not
        # make additional model calls through an unrelated fallback generator.
        if any(word in str(exc).lower() for word in ('model not running', 'connection refused',
                'ollama is disabled', 'ollama is unavailable', 'timed out', 'connection error')):
            _alert(state,f'show {show_id} batch',exc)
            report['ollama_status']='unavailable'
            return {'source':'unavailable','error':str(exc)}
        # The full response is a demanding schema for small local models.
        # A bad highlight should NOT suppress fan reporting or fan social.
        _alert(state,f'show {show_id} batch',exc)
        report['ollama_status']='partial'
        successes=[]
        try:
            from .narrative import rewrite_social
            result=rewrite_social(state,show_id)
            successes.append('posts') if result.get('updated') else None
        except (ValueError,TypeError,KeyError) as post_exc:
            _alert(state,f'show {show_id} posts',post_exc)
        try:
            compact={'show':show.name,'crowd':round(report['crowd'],1),
              'segments':[{'title':x['title'],'kind':x['kind'],'crowd':x['crowd'],
                'duration':x['duration'],'winner':state.wrestlers[x['winner']].name if x.get('winner') else None}
                for x in report['segments']]}
            schema={'type':'object','properties':{'report':{'type':'string','minLength':35,'maxLength':700}},
                    'required':['report'],'additionalProperties':False}
            result=_generate({'task':'Write an objective fictional fan report in 3-5 sentences from these fixed outcomes. '
                              'Identify crowd positives and concerns. Do not invent stats or results.',
                              'facts':compact},schema)
            fan=result.get('report')
            if not isinstance(fan,str) or not 35<=len(fan.strip())<=700 or '<script' in fan.lower() or 'http://' in fan.lower():
                raise ValueError('Invalid standalone fan report')
            report['fan_report']={'text':fan.strip(),'source':'ollama',
                'summary':{'positive':sum(p['sentiment']=='positive' for p in posts),
                           'mixed':sum(p['sentiment']=='mixed' for p in posts),
                           'negative':sum(p['sentiment']=='negative' for p in posts)}}
            successes.append('fan_report')
        except (ValueError,TypeError,KeyError) as fan_exc:
            _alert(state,f'show {show_id} fan report',fan_exc)
        # Do not label factual fallback material as AI-authored.
        if successes: report['ollama_status']='partial_generated'
        else: report['ollama_status']='unavailable'
        return {'source':'partial' if successes else 'unavailable',
                'generated':successes,'batch_error':str(exc)}
