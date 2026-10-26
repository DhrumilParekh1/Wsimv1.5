"""Small, independent Ollama requests so failure in one feature doesn't void others.

Facts and match execution are immutable; AI supplies only validated atmosphere.
"""
from __future__ import annotations
from .narrative import _generate, _clean_fan_post
from .auto_narrative import _alert
from .memories import relevant_memories
from .report_analysis import analyze_segment, consistent_ai_reaction


def auto_show_fast(state, show_id: str, progress=None):
    show = state.shows[show_id]
    report = show.result
    if not report:
        raise ValueError('Show must be simulated before narration')
    posts=[p for p in state.social_posts if p['show_id']==show_id]
    results=[]
    errors=[]

    def stage(label):
        if progress: progress(label)

    def attempt(label, operation):
        try:
            count=operation()
            results.append(label)
            return count
        except (ValueError, TypeError, KeyError, OSError) as exc:
            errors.append((label,str(exc)))
            _alert(state, f'{show_id} {label}', exc)
            return 0

    def report_text():
        schema={'type':'object','properties':{'report':{'type':'string','minLength':35,'maxLength':550}},'required':['report'],'additionalProperties':False}
        facts={'show':show.name,'crowd':round(report['crowd'],1),
               'segments':[{'title':s['title'],'kind':s['kind'],'crowd':round(s['crowd'],1),
                           'winner':state.wrestlers[s['winner']].name if s.get('winner') else None,
                           'verdict':(s.get('analysis') or analyze_segment(s))['verdict'],
                           'strengths':(s.get('analysis') or analyze_segment(s))['positives'],
                           'concerns':(s.get('analysis') or analyze_segment(s))['concerns']}
                          for s in report['segments']]}
        obj=_generate({'task':'Write 3 concise sentences strictly reflecting the supplied verdicts, weaknesses, expectations and scores. If fans were dissatisfied, say so explicitly. Do not call a mixed or poor match amazing or an instant classic. Preserve every fixed outcome.','facts':facts},schema)
        text=obj.get('report','')
        if not isinstance(text,str) or not 35<=len(text.strip())<=550 or '<' in text:
            raise ValueError('Invalid fan report response')
        report['fan_report']={'text':text.strip(),'source':'ollama',
               'summary':{kind:sum(p['sentiment']==kind for p in posts) for kind in ('positive','mixed','negative')}}
        return 1

    def fan_posts():
        changed=0
        for offset in range(0,min(len(posts),12),4):
            batch=posts[offset:offset+4]
            schema={'type':'object','properties':{'posts':{'type':'array','minItems':len(batch),'maxItems':len(batch),
                 'items':{'type':'string','minLength':8,'maxLength':190}}},'required':['posts'],'additionalProperties':False}
            obj=_generate({'task':'Rewrite fan microblogs with different natural voices, preserving each assigned sentiment and all match results.',
                 'posts':[{'title':p['segment'],'sentiment':p['sentiment'],'text':p['text'],
                           'verdict':next((x.get('analysis',{}).get('verdict') for x in report['segments'] if x['title']==p['segment']),None)} for p in batch]},schema)
            texts=obj.get('posts',[])
            if len(texts)!=len(batch) or any(not isinstance(t,str) or not 8<=len(t.strip())<=190 or '<' in t for t in texts):
                raise ValueError('Invalid fan posts response')
            seen={p['text'].strip().casefold() for p in posts[:offset] if p.get('source')=='ollama'}
            for post,text in zip(batch,texts):
                try:
                    clean=_clean_fan_post(text,post['sentiment'])
                except ValueError:
                    continue
                match=next((seg for seg in report['segments'] if seg['title']==post['segment']),None)
                analysis=(match.get('analysis') or analyze_segment(match)) if match else {'sentiment':post['sentiment']}
                # Never publish near-identical AI reactions within the same show.
                # Keep the original deterministic post when a rewrite is repeated.
                normalized=' '.join(clean.casefold().split())
                if normalized in seen:
                    continue
                if consistent_ai_reaction(clean,analysis):
                    seen.add(normalized)
                    post['text']=clean;post['source']='ollama';changed+=1
        return changed

    def segment_text():
        count=0
        # For each segment, only one representative move/beat needs prose expansion;
        # the canonical simulator has already generated the remaining timed highlights.
        for offset in range(0,len(report['segments']),3):
            batch=report['segments'][offset:offset+3]
            facts=[]
            for seg in batch:
                beat=seg.get('highlights',[{}])[0] if seg.get('highlights') else {'text':seg['narrative']}
                facts.append({'name':seg['title'],'kind':seg['kind'],'crowd':round(seg['crowd'],1),
                    'highlight':beat.get('text',seg['narrative']),
                    'canonical_fan_verdict':(seg.get('analysis') or analyze_segment(seg)),
                    'memories':[m['description'] for m in relevant_memories(state,seg['participants'],limit=2)], 'traits':{state.wrestlers[w].name:state.wrestlers[w].traits[:4] for w in seg['participants']},
                    'personality':{state.wrestlers[w].name:state.wrestlers[w].personality for w in seg['participants']},
                    'alignment':{state.wrestlers[w].name:state.wrestlers[w].role for w in seg['participants']},
                    'direction':next((card.creative_direction for card in show.segments if card.title==seg['title']),'advance'),
                    'audience':seg.get('audience',{})})
            schema={'type':'object','properties':{
                 'commentary':{'type':'array','minItems':len(batch),'maxItems':len(batch),
                               'items':{'type':'string','minLength':15,'maxLength':190}},
                 'reactions':{'type':'array','minItems':len(batch),'maxItems':len(batch),
                               'items':{'type':'string','minLength':15,'maxLength':210}}},
                 'required':['commentary','reactions'],'additionalProperties':False}
            obj=_generate({'task':'For each fixed segment write one atmospheric line and one POST-EVENT fan reaction that agrees with the canonical fan verdict. A below-expectations, mixed or disappointing segment MUST NOT be celebrated as a classic. Reflect the supplied wrestler traits and personalities only when relevant. No new moves, wrestlers, winners or injuries.',
                    'segments':facts},schema)
            lines=obj.get('commentary',[]); reactions=obj.get('reactions',[])
            if len(lines)!=len(batch) or len(reactions)!=len(batch):
                raise ValueError('Segment narration count mismatch')
            # All validate before mutation. Reject any invented canonical move names.
            known={m['name'].lower() for w in state.wrestlers.values() for m in w.moveset}
            for seg,line,reaction in zip(batch,lines,reactions):
                if not isinstance(line,str) or not isinstance(reaction,str) or not 15<=len(line.strip())<=190 or not 15<=len(reaction.strip())<=210 or '<' in (line+reaction):
                    raise ValueError('Invalid short segment narrative')
                original=seg.get('highlights',[{}])[0].get('text','') if seg.get('highlights') else ''
                if any(name in line.lower() and name not in original.lower() for name in known):
                    raise ValueError('New or unsupported move in Ollama commentary')
            for seg,line,reaction in zip(batch,lines,reactions):
                analysis=seg.get('analysis') or analyze_segment(seg)
                if consistent_ai_reaction(line,analysis) and seg.get('highlights'):
                    seg['highlights'][0]['ai_flavour']=line.strip()
                if consistent_ai_reaction(reaction,analysis):
                    seg['fan_report']={'text':reaction.strip(),'source':'ollama'}
                count+=1
        return count

    def promo_dialogue():
        scenes=[seg for seg in report['segments'] if seg['kind']!='match']
        count=0
        for offset in range(0,len(scenes),2):
            batch=scenes[offset:offset+2]
            facts=[]
            for seg in batch:
                participants=[state.wrestlers[wid] for wid in seg['participants']]
                story=next((s for s in state.storylines.values() if all(w.id in s.wrestler_ids for w in participants)),None)
                facts.append({'segment':seg['title'],'type':seg['kind'],
                    'performers':[{'name':w.name,'role':w.role,'personality':w.personality,
                                   'traits':w.traits[:5], 'mic_skills':w.attributes['mic_skills']}
                                  for w in participants],
                    'fixed_beats':[b['text'] for b in seg.get('highlights',[])[:3]],
                    'history':[m['description'] for m in relevant_memories(state,seg['participants'],limit=3)],
                    'storyline':story.title if story else 'None',
                    'verdict':(seg.get('analysis') or analyze_segment(seg))['verdict'],
                    'fixed_outcome':seg['narrative']})
            schema={'type':'object','properties':{'scenes':{'type':'array','minItems':len(batch),'maxItems':len(batch),
                'items':{'type':'string','minLength':40,'maxLength':700}}},
                'required':['scenes'],'additionalProperties':False}
            obj=_generate({'task':'Write a short FICTIONAL on-screen dialogue scene for each non-match segment. '
                'Use actual performer names as dialogue speaker labels (Name: dialogue). Make their lines distinct based on '
                'the supplied traits, alignments, personalities and previous history. Follow the fixed story beats. '
                'Do NOT invent new wrestlers, match winners, injuries, turns, betrayals, signed contracts, title changes or promises. '
                'Never add outcomes beyond the fixed facts; leave the storyline unresolved unless stated. '
                'Write 2-4 meaningful short lines per scene, newline-separated in each string.', 'segments':facts},schema)
            lines=obj.get('scenes')
            if not isinstance(lines,list) or len(lines)!=len(batch):
                raise ValueError('Ollama promo dialogue count mismatch')
            for seg,line in zip(batch,lines):
                if not isinstance(line,str) or not 40<=len(line.strip())<=700 or '<' in line or 'http' in line.lower():
                    raise ValueError('Invalid promo dialogue')
                if not any(state.wrestlers[wid].name.lower() in line.lower() for wid in seg['participants']):
                    raise ValueError('Dialogue does not contain an assigned wrestler')
                forbidden=('signed the contract','became champion','suffered an injury','is hospitalized',
                           'announces their retirement')
                if any(phrase in line.lower() for phrase in forbidden):
                    raise ValueError('Ollama invented a canonical event')
            for seg,line in zip(batch,lines):
                seg['promo_dialogue']=line.strip()
                count+=1
        return count

    stage('Writing the audience report')
    attempt('fan_report',report_text)
    stage('Generating fan social reactions')
    attempt('fan_posts',fan_posts)
    stage('Enhancing match and promo highlights')
    attempt('segments',segment_text)
    stage('Writing character-aware promos and backstage dialogue')
    attempt('promo_dialogue',promo_dialogue)
    expected=4 if any(s['kind']!='match' for s in report['segments']) else 3
    report['ollama_status']='generated' if len(results)==expected else 'partial_generated' if results else 'unavailable'
    return {'source':'ollama' if all(k in results for k in ('fan_report','fan_posts','segments')) else 'partial' if results else 'unavailable',
            'generated':results,'errors':errors}
