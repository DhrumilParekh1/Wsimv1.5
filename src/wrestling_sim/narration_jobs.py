"""Narration jobs run outside the game lock; numerical results are saved first."""
from __future__ import annotations
import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from .efficient_narrative import auto_show_fast

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='ringside-ollama')
_jobs = {}
_guard = threading.RLock()


def status(show_id, service=None):
    key=(service,show_id) if service is not None else show_id
    with _guard:
        return dict(_jobs.get(key, {'status': 'not_started', 'stage': 'Not queued'}))


def queue(service, show_id):
    with service.lock:
        original_state=service.state
        snapshot = copy.deepcopy(original_state)
        key=(service,show_id)
    with _guard:
        previous=_jobs.get(key, {})
        if previous.get('status') in ('queued','running','completed'):
            return dict(previous)
        _jobs[key]={'status':'queued','stage':'Waiting for local Ollama', 'show_id':show_id}

    def worker():
        with _guard:
            _jobs[key].update(status='running',stage='Generating highlights and audience reports')
        try:
            def progress(label):
                with _guard:
                    _jobs[key]['stage']=label
            generated=auto_show_fast(snapshot,show_id,progress)
            with service.lock:
                live=service.state
                if live is not original_state or show_id not in live.shows:
                    raise RuntimeError('Campaign changed; discarded obsolete narration')
                source=snapshot.shows[show_id].result
                target=live.shows[show_id].result
                for report_key in ('ollama_status','fan_report'):
                    if report_key in source: target[report_key]=copy.deepcopy(source[report_key])
                for source_segment,target_segment in zip(source['segments'],target['segments']):
                    for field in ('fan_report','promo_dialogue'):
                        if field in source_segment: target_segment[field]=copy.deepcopy(source_segment[field])
                    for a,b in zip(source_segment.get('highlights',[]),target_segment.get('highlights',[])):
                        if a.get('ai_flavour'): b['ai_flavour']=a['ai_flavour']
                changed={post['id']:post for post in snapshot.social_posts if post.get('show_id')==show_id}
                for post in live.social_posts:
                    if post['id'] in changed and changed[post['id']].get('source')=='ollama':
                        post['text']=changed[post['id']]['text'];post['source']='ollama'
                live.narrative_alerts.extend(x for x in snapshot.narrative_alerts if x not in live.narrative_alerts)
                service.save()
            with _guard:
                _jobs[key].update(status='completed',stage='Narrative processing finished',result=generated)
        except Exception as exc:
            with _guard:
                _jobs[key].update(status='failed',stage='Ollama narration failed; simulation is saved',error=str(exc)[:240])
    _pool.submit(worker)
    return status(show_id,service)
