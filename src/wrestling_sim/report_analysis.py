"""Deterministic readable verdicts; Ollama can narrate, never interpret scores freely."""
from __future__ import annotations


def analyze_segment(segment):
    quality=float(segment['quality']);crowd=float(segment['crowd'])
    audience=segment.get('audience') or {};engine=segment.get('match_engine') or {}
    expected=float(audience.get('expected_quality',50));satisfaction=float(audience.get('satisfaction',crowd))
    gap=satisfaction-expected
    if gap<=-18: verdict='Significantly below fan expectations'
    elif gap<=-7:verdict='Below fan expectations'
    elif gap>=12:verdict='Exceeded fan expectations'
    elif gap>=4:verdict='A positive surprise'
    else:verdict='Close to fan expectations'
    positives=[];concerns=[]
    if segment['kind']=='match':
        execution=float((segment.get('match_details') or {}).get('ring_execution',0))
        stamina=float(engine.get('stamina_readiness',50))
        finish=float(engine.get('finish_satisfaction',50))
        if execution>=65:positives.append('Competent in-ring execution')
        elif execution<48:concerns.append('In-ring execution lacked consistency')
        if finish>=67:positives.append('Finish was reasonably well received')
        elif finish<48:concerns.append('The finish disappointed fans')
        if stamina<50:concerns.append('Low stamina limited sustained performance')
        elif stamina>=75:positives.append('Energy was sustained throughout')
    if gap<-10:concerns.append(f'Fan satisfaction was {abs(gap):.1f} points below expectations')
    if gap>9:positives.append('Audience satisfaction surpassed the buildup')
    if audience.get('fatigue',0)>=12:concerns.append('Recent repetition reduced interest')
    if not positives:positives.append('The segment contributed to the ongoing show narrative' if crowd>=45 else 'Some storyline context remains')
    if not concerns and quality<60:concerns.append('Overall execution fell short of a strong rating')
    conclusion=(f'{verdict}. {"; ".join(positives[:2])}. '
                + ('Concerns: '+ '; '.join(concerns[:2])+'.' if concerns else 'Fans responded favourably.'))
    return {'verdict':verdict,'satisfaction_gap':round(gap,1),'positives':positives[:3],
            'concerns':concerns[:3], 'conclusion':conclusion,
            'sentiment':'positive' if crowd>=70 and gap>=-6 else 'negative' if crowd<43 or gap<-22 else 'mixed',
            'quality':quality,'crowd':crowd,'satisfaction':satisfaction,'expected_quality':expected}


def consistent_ai_reaction(text: str, analysis: dict) -> bool:
    """Conservatively reject obvious hype contradictions, preserving canonical prose."""
    if not isinstance(text,str) or not text.strip():return False
    tone=text.lower()
    exaggerated=('for the ages','best ever','flawless','masterpiece','instant classic',
                'greatest match','perfect match','absolutely incredible','stole the show',
                'this is it, folks','greatest promo','for the ages','everyone went wild',
                'crowd erupted with joy','everyone was thrilled','fans absolutely loved')
    if analysis['sentiment']!='positive' and any(phrase in tone for phrase in exaggerated):
        return False
    if analysis['sentiment']=='negative' and 'everyone loved' in tone:return False
    return True
