"""HTTP API for future web/desktop frontend. Run: uvicorn wrestling_sim.api:app --reload"""
from __future__ import annotations
import os
from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field
from .game import advance_week, book_show, brief_state, create_storyline, offer_contract, simulate_show, inbox_blockers
from .models import Segment
from .world import bootstrap_world, calendar, hire_staff, assign_coach, scout_reports
from .dialogue import begin_meeting, answer_meeting, begin_contract, answer_contract
from .ratings import rating_breakdown
from .service import GameService
from .decisions import available_decisions, choose_option
from .scenes import scene_overview, start_scene, choose_scene
from .management import (creative_head, staff_market, sign_creative_head,
                         media_opportunity, assign_media, interact_wrestler, creative_tasks, decline_media, cancel_creative_commitment)
from .sponsors import sponsor_offers, respond_sponsor, terminate_sponsor
from .auto_narrative import auto_show, auto_dialogue
from .narrative import config as ollama_config, status as ollama_status, rewrite_social, segment_recap, enhance_dialogue, enhance_highlights

app = FastAPI(title="Fictional Wrestling Promotion Simulator API", version="1.3.0")
service = GameService(os.getenv('WRESTLING_SIM_SAVE', 'saves/game.db'))


class ChoiceRequest(BaseModel):
    event_id: str
    option_id: str


class StartSceneRequest(BaseModel):
    storyline_id: str


class SceneChoiceRequest(BaseModel):
    scene_id: str
    option_id: str


class StaffRequest(BaseModel):
    head_id: str

class MediaRequest(BaseModel):
    wrestler_id: str

class InteractionRequest(BaseModel):
    wrestler_id: str
    topic: str


class HireRequest(BaseModel):
    kind: str
    staff_id: str

class CoachAssignment(BaseModel):
    coach_id: str
    wrestler_id: str

class ScoutRequest(BaseModel):
    scout_id: str

class StartMeeting(BaseModel):
    wrestler_id: str
    topic: str
    concern_id: str | None = None

class AnswerMeeting(BaseModel):
    session_id: str
    choice_id: str

class RecruitmentAcknowledgement(BaseModel):
    key: str

class StartNegotiation(BaseModel):
    wrestler_id: str

class AnswerNegotiation(BaseModel):
    session_id: str
    action: str
    salary: int = 0
    weeks: int = 52
    bonus: int = 0

class SponsorReply(BaseModel):
    offer_id: str
    action: str
    counter_amount: int = 0

class CreativeCancel(BaseModel):
    storyline_id: str

class VoiceRequest(BaseModel):
    kind: str
    session_id: str

class HighlightsRequest(BaseModel):
    show_id: str
    segment_index: int = Field(ge=0)

class CardTierUpdate(BaseModel):
    tier: str

class MoveDefinition(BaseModel):
    name: str
    style: str
    finisher: bool = False
    signature: bool = False

class MovesetUpdate(BaseModel):
    moves: list[MoveDefinition]

class SegmentRecap(BaseModel):
    show_id: str
    segment_index: int = Field(ge=0)

class SocialRewrite(BaseModel):
    show_id: str

class NewGameRequest(BaseModel):
    seed: int = 2026


class StorylineRequest(BaseModel):
    title: str
    wrestler_ids: list[str]


class SegmentRequest(BaseModel):
    kind: str
    wrestler_ids: list[str]
    duration: int
    title: str
    storyline_id: str | None = None
    booking_quality: float = Field(default=17, ge=0, le=25)  # legacy saves
    promotion_effort: float | None = Field(default=None, ge=0, le=25)
    promotion_budget: int | None = Field(default=None, ge=0, le=100000000)
    championship_id: str | None = None
    planned_winner_id: str | None = None
    creative_direction: str = "advance"
    match_style: str = "balanced"
    finish_type: str = "clean"
    stipulation: str = "standard"
    intensity: str = "standard"
    promo_brawl: bool = False
    match_styles: list[str] = Field(default_factory=list)
    role_turn_wrestler_id: str | None = None
    role_turn_to: str | None = None


class BookShowRequest(BaseModel):
    name: str
    duration: int = 120
    segments: list[SegmentRequest]


class ContractRequest(BaseModel):
    wrestler_id: str
    salary_weekly: int
    weeks: int
    signing_bonus: int = 0
    promised_role: str | None = None
    promises: list[str] = Field(default_factory=list)


def perform(action, after=None):
    with service.lock:
        try:
            result = action(service.state)
            if after is not None:
                ai_result = after(service.state,result)
                if isinstance(result,dict) and ai_result:
                    result['narrative_generation'] = ai_result
            service.save()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


class TalentConcernReply(BaseModel):
    concern_id: str
    choice: str

class IncidentReply(BaseModel):
    incident_id: str
    choice: str

class PressReply(BaseModel):
    question_id: str
    choice: str

class BuyoutRequest(BaseModel):
    wrestler_id: str
    proposed_fee: int
    salary_weekly: int
    weeks: int = 52


class InterestRequest(BaseModel):
    wrestler_id: str
    public: bool = False

class PrecontractRequest(BaseModel):
    wrestler_id: str
    salary_weekly: int = Field(ge=1)
    weeks: int = Field(default=52, ge=4, le=156)
    promised_role: str = 'mid_card'
    promises: list[str] = Field(default_factory=list)
    signing_bonus: int = Field(default=0, ge=0)

class PromiseRequest(BaseModel):
    wrestler_id: str
    kind: str
    target: str | int | bool
    deadline_weeks: int = Field(default=8, ge=1, le=104)

class RivalBidRequest(BaseModel):
    offer_id: str
    decision: str

class ExpansionRequest(BaseModel):
    kind: str

class CampaignRequest(BaseModel):
    scope: str
    amount: int = Field(ge=1)

@app.post('/ui/recruit/interest')
def ui_recruit_interest(req: InterestRequest):
    from .industry import declare_interest
    return perform(lambda s:declare_interest(s,req.wrestler_id,req.public))

@app.post('/ui/recruit/acknowledge')
def ui_recruit_acknowledge(req: RecruitmentAcknowledgement):
    from .industry import acknowledge_recruitment_report
    return perform(lambda s:acknowledge_recruitment_report(s,req.key))

@app.post('/ui/recruit/precontract')
def ui_recruit_precontract(req: PrecontractRequest):
    from .industry import negotiate_future_contract
    return perform(lambda s:negotiate_future_contract(s,req.wrestler_id,req.salary_weekly,
            req.weeks,req.promised_role,req.promises,req.signing_bonus))

@app.post('/ui/recruit/promise')
def ui_recruit_promise(req: PromiseRequest):
    from .industry import lodge_promise
    def action(s):
        wrestler=s.wrestlers.get(req.wrestler_id)
        if not wrestler or wrestler.company_id != s.player_company_id:
            raise ValueError('Promises can only be made to your contracted wrestlers')
        return lodge_promise(s,req.wrestler_id,req.kind,req.target,req.deadline_weeks)
    return perform(action)

@app.post('/ui/recruit/rival-offer')
def ui_rival_offer(req: RivalBidRequest):
    from .transfer_market import resolve_rival_bid
    return perform(lambda s:resolve_rival_bid(s,req.offer_id,req.decision))

@app.post('/ui/company/campaign')
def ui_company_campaign(req: CampaignRequest):
    from .marketing import purchase_campaign
    return perform(lambda s:purchase_campaign(s,req.scope,req.amount))

@app.post('/ui/company/expand')
def ui_expand(req: ExpansionRequest):
    from .industry import expand_company
    return perform(lambda s:expand_company(s,req.kind))

@app.post('/ui/talent/resolve')
def ui_talent_resolve(req: TalentConcernReply):
    from .front_office import answer_concern
    return perform(lambda s:answer_concern(s,req.concern_id,req.choice))

@app.post('/ui/incidents/resolve')
def ui_incident_resolve(req: IncidentReply):
    from .press_and_incidents import answer_incident
    return perform(lambda s:answer_incident(s,req.incident_id,req.choice))

@app.post('/ui/press/answer')
def ui_press_answer(req: PressReply):
    from .press_and_incidents import answer_press
    return perform(lambda s:answer_press(s,req.question_id,req.choice))

@app.post('/ui/talent/buyout')
def ui_buyout(req: BuyoutRequest):
    from .front_office import monetary_value
    import random
    from .models import clamp
    def action(s):
        w=s.wrestlers.get(req.wrestler_id)
        if not w or w.company_id in (None,s.player_company_id):
            raise ValueError('Buyout requires an active rival contract')
        if req.weeks<4 or req.weeks>156 or req.salary_weekly<=0 or req.proposed_fee<=0:
            raise ValueError('Invalid transfer offer')
        if s.player_company.money < req.proposed_fee + req.salary_weekly*4:
            raise ValueError('Insufficient cash to fund the buyout and opening payroll')
        if sum(x.company_id==s.player_company_id for x in s.wrestlers.values())>=s.player_company.roster_limit:
            raise ValueError('Roster is full')
        vendor=s.companies[w.company_id]
        value=monetary_value(w,s)
        rng=random.Random(f'buyout:{s.seed}:{s.year}:{s.week}:{w.id}:{req.proposed_fee}:{req.salary_weekly}')
        vendor_odds=clamp(.18 + .72*(req.proposed_fee / max(1,value)-.8),.02,.95)
        player_odds=clamp(.25+.65*(req.salary_weekly/max(w.salary_weekly*1.2,500)-.85)
                          +(w.attributes['ambition']-12.5)/100,.03,.96)
        vendor_accept=rng.random()<vendor_odds
        talent_accept=rng.random()<player_odds
        accepted=vendor_accept and talent_accept
        if accepted:
            s.player_company.money-=req.proposed_fee
            vendor.money+=req.proposed_fee
            w.company_id=s.player_company_id;w.salary_weekly=req.salary_weekly;w.contract_weeks=req.weeks
            s.news.append(f'{w.name} joined Aurora after a negotiated transfer worth ${req.proposed_fee:,}.')
        return {'accepted':accepted,'seller_accepted':vendor_accept,'wrestler_accepted':talent_accept,
                'market_value_dollars':value,'proposed_fee':req.proposed_fee}
    return perform(action)

@app.get('/health')
def health():
    return {"status": "ok", "version": app.version}


@app.post('/game/new')
def game_new(request: NewGameRequest):
    service.reset(request.seed)
    return brief_state(service.state)


@app.get('/game')
def game_brief():
    return brief_state(service.state)


@app.get('/game/full')
def game_full():
    return asdict(service.state)


@app.get('/wrestlers')
def wrestlers():
    return [{"id": w.id, "name": w.name, "company_id": w.company_id,
             "role": w.role, **rating_breakdown(w)} for w in service.state.wrestlers.values()]


@app.get('/wrestlers/{wrestler_id}')
def wrestler_detail(wrestler_id: str):
    wrestler = service.state.wrestlers.get(wrestler_id)
    if not wrestler:
        raise HTTPException(status_code=404, detail="Unknown wrestler")
    return {**asdict(wrestler), "ratings": rating_breakdown(wrestler)}


@app.put('/wrestlers/{wrestler_id}/moveset')
def update_moveset(wrestler_id: str, update: MovesetUpdate):
    from .movesets import validate_moveset
    def action(state):
        w=state.wrestlers.get(wrestler_id)
        if not w or w.company_id!=state.player_company_id:
            raise ValueError('Only your own roster can have edited movesets')
        moves=[m.model_dump(exclude_unset=True) for m in update.moves]
        validate_moveset(moves)
        w.moveset=moves
        return {'wrestler_id':w.id,'moveset':moves}
    return perform(action)

@app.post('/wrestlers/{wrestler_id}/tier')
def set_card_tier(wrestler_id:str, request: CardTierUpdate):
    from .models import clamp
    def action(state):
        person=state.wrestlers.get(wrestler_id)
        if not person or person.company_id!=state.player_company_id:
            raise ValueError('Unknown active roster wrestler')
        if request.tier not in ('main_event','upper_mid_card','mid_card','lower_mid_card','jobber'):
            raise ValueError('Unknown card tier')
        from .front_office import set_tier
        return set_tier(state,wrestler_id,request.tier)
    return perform(action)

@app.get('/storylines')
def storylines():
    return {id: asdict(story) for id, story in service.state.storylines.items()}


@app.post('/storylines')
def storylines_create(request: StorylineRequest):
    return perform(lambda s: asdict(create_storyline(s, request.title, request.wrestler_ids)))


@app.post('/shows/book')
def shows_book(request: BookShowRequest):
    return perform(lambda s: asdict(book_show(s, request.name,
                   [Segment(**seg.model_dump()) for seg in request.segments], request.duration)))


@app.post('/shows/{show_id}/simulate')
def shows_simulate(show_id: str):
    # Save numerical simulation before starting any slow Ollama work.
    result = perform(lambda s: simulate_show(s, show_id))
    from .narration_jobs import queue
    result['narrative_generation'] = queue(service, show_id)
    return result

@app.get('/shows/{show_id}/narration-status')
def shows_narration_status(show_id: str):
    from .narration_jobs import status
    return status(show_id, service)


@app.get('/shows/{show_id}')
def shows_get(show_id: str):
    show = service.state.shows.get(show_id)
    if not show:
        raise HTTPException(status_code=404, detail='Unknown show')
    return asdict(show)


@app.post('/contracts/offer')
def contract_offer(request: ContractRequest):
    return perform(lambda s: offer_contract(s, request.wrestler_id, request.salary_weekly,
                                           request.weeks, request.signing_bonus,
                                           request.promised_role, request.promises))


@app.post('/weeks/advance')
def weeks_advance():
    return perform(advance_week)


# The browser frontend is packaged with Python. No npm or Node.js is required.
WEB_DIR = Path(__file__).resolve().parent / 'web'
app.mount('/assets', StaticFiles(directory=WEB_DIR / 'assets'), name='assets')


@app.get('/', include_in_schema=False)
def homepage():
    return FileResponse(WEB_DIR / 'index.html')


@app.get('/ui/state')
def ui_state():
    with service.lock:
        state = service.state
        bootstrap_world(state)
        return {
            'year': state.year, 'week': state.week,
            'company': {**asdict(state.player_company), 'prestige': __import__('wrestling_sim.industry',fromlist=['company_prestige']).company_prestige(state,state.player_company_id)},
            'company_prestige': {cid:__import__('wrestling_sim.industry',fromlist=['company_prestige']).company_prestige(state,cid) for cid in state.companies},
            'campaigns': state.campaigns[-12:],
            'recruitment_interest': state.recruitment_interest[-30:],
            'precontracts': state.precontracts[-20:],
            'contract_promises': state.contract_promises[-40:],
            'transfer_offers': [o for o in state.transfer_offers if o.get('status')=='pending'],
            'expansion': {kind:__import__('wrestling_sim.industry',fromlist=['expansion_quote']).expansion_quote(state,kind) for kind in ('extra_ppv','more_hours')},
            'companies': [asdict(c) for c in state.companies.values()],
            'wrestlers': [{**asdict(w), 'ratings': {**rating_breakdown(w), 'market_dollars':__import__('wrestling_sim.front_office',fromlist=['monetary_value']).monetary_value(w,state)}}
                          for w in state.wrestlers.values()],
            'storylines': [asdict(s) for s in state.storylines.values()],
            'championships': list(__import__('wrestling_sim.championships',fromlist=['ensure_championships']).ensure_championships(state).values()),
            'shows': [asdict(s) for s in state.shows.values()],
            'finance': state.financial_history[-24:],
            'news': state.news[-25:],
            'decisions': available_decisions(state),
            'scenes': scene_overview(state),
            'activity': state.activity_log[-30:],
            'staff': creative_head(state),
            'staff_market': staff_market(state),
            'creative_tasks': creative_tasks(state),
            'media': media_opportunity(state) if media_opportunity(state)['id'] not in state.assignments else None,
            'interactions': state.interactions[-25:],
            'calendar': calendar(state),
            'weekly_metrics': state.weekly_metrics[-55:],
            'world_news': state.world_news[-70:],
            'rival_history': state.rival_history[-60:],
            'coaches': list(state.coaches.values()),
            'scouts': list(state.scouts.values()),
            'coach_assignments': state.coach_assignments,
            'scouting_reports': state.scouting_reports[-40:],
            'dialogue_sessions': list(state.dialogue_sessions.values()),
            'contract_sessions': list(state.contract_sessions.values()),
            'sponsor_offers': sponsor_offers(state),
            'sponsor_deals': list(state.sponsor_deals.values()),
            'social_posts': state.social_posts[-120:],
            'memories':state.memories[-120:],
            'narrative_alerts':state.narrative_alerts[-8:],
            'chemistry': state.chemistry,
            'talent_concerns': __import__('wrestling_sim.front_office',fromlist=['concerns']).concerns(state),
            'incidents': __import__('wrestling_sim.press_and_incidents',fromlist=['pending_incidents']).pending_incidents(state),
            'recent_incidents': [i for i in state.incidents if i.get('status')=='resolved'][-12:],
            'press_conference': __import__('wrestling_sim.press_and_incidents',fromlist=['conference']).conference(state),
            'inbox_blockers': inbox_blockers(state),
            'injury_reports': [{'id':w.id,'name':w.name,**w.injury} for w in state.wrestlers.values()
                               if w.company_id==state.player_company_id and w.injury],
            'ollama': {'enabled': True, 'automatic': True, 'model': ollama_config()['model']},
        }


@app.post('/ui/choices')
def ui_choose(request: ChoiceRequest):
    # The creative Inbox item is navigation-only. The creative room handles its resolution.
    if request.event_id.endswith('-creative'):
        raise HTTPException(status_code=400,detail='Open the Creative Room to decide the storyline direction')
    return perform(lambda s: choose_option(s, request.event_id, request.option_id))


@app.post('/ui/scenes/start')
def ui_start_scene(request: StartSceneRequest):
    return perform(lambda s: start_scene(s, request.storyline_id))


@app.post('/ui/scenes/choose')
def ui_choose_scene(request: SceneChoiceRequest):
    return perform(lambda s: choose_scene(s, request.scene_id, request.option_id))


@app.post('/ui/staff/hire')
def ui_hire_staff(request: StaffRequest):
    return perform(lambda s: sign_creative_head(s, request.head_id))


@app.post('/ui/media/assign')
def ui_assign_media(request: MediaRequest):
    return perform(lambda s: assign_media(s, request.wrestler_id))


@app.post('/ui/wrestlers/interact')
def ui_interact_wrestler(request: InteractionRequest):
    return perform(lambda s: interact_wrestler(s, request.wrestler_id, request.topic))


@app.post('/ui/management/hire')
def ui_hire_specialist(request: HireRequest):
    return perform(lambda s: hire_staff(s, request.kind, request.staff_id))

@app.post('/ui/management/coach')
def ui_assign_coach(request: CoachAssignment):
    return perform(lambda s: assign_coach(s, request.coach_id, request.wrestler_id))

@app.post('/ui/management/scout')
def ui_scout_report(request: ScoutRequest):
    return perform(lambda s: scout_reports(s, request.scout_id))

@app.post('/ui/meetings/start')
def ui_begin_meeting(request: StartMeeting):
    return perform(lambda s: begin_meeting(s, request.wrestler_id, request.topic, request.concern_id), lambda s,r: auto_dialogue(s,'meeting',r['id']))

@app.post('/ui/meetings/choose')
def ui_answer_meeting(request: AnswerMeeting):
    return perform(lambda s: answer_meeting(s, request.session_id, request.choice_id), lambda s,r: auto_dialogue(s,'meeting',request.session_id))

@app.post('/ui/negotiations/start')
def ui_begin_negotiation(request: StartNegotiation):
    return perform(lambda s: begin_contract(s, request.wrestler_id))

@app.post('/ui/negotiations/choose')
def ui_answer_negotiation(request: AnswerNegotiation):
    return perform(lambda s: answer_contract(s, request.session_id, request.action, request.salary,
                                              request.weeks, request.bonus), lambda s,r: auto_dialogue(s,'contract',request.session_id) if request.action != 'walk' else None)


@app.post('/ui/media/decline')
def ui_decline_media():
    return perform(decline_media)

@app.get('/ui/ollama/status')
def ui_ollama_status():
    return ollama_status()

@app.post('/ui/social/rewrite')
def ui_rewrite_social(request: SocialRewrite):
    # Long-running local LLM generation occurs outside the state lock.
    # Save state only after the text passes structural validation.
    with service.lock:
        try:
            result = rewrite_social(service.state, request.show_id)
            service.save()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

class SponsorTermination(BaseModel):
    deal_id: str

@app.post('/ui/sponsors/terminate')
def ui_sponsor_terminate(request: SponsorTermination):
    return perform(lambda s: terminate_sponsor(s,request.deal_id))

@app.post('/ui/sponsors/reply')
def ui_sponsor_reply(request: SponsorReply):
    return perform(lambda s: respond_sponsor(s, request.offer_id, request.action, request.counter_amount))


@app.post('/ui/creative/cancel')
def ui_cancel_creative(request: CreativeCancel):
    return perform(lambda s: cancel_creative_commitment(s, request.storyline_id))


@app.post('/ui/ollama/dialogue')
def ui_ollama_dialogue(request: VoiceRequest):
    with service.lock:
        try:
            result=enhance_dialogue(service.state,request.kind,request.session_id)
            service.save()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.post('/ui/ollama/highlights')
def ui_ollama_highlights(request: HighlightsRequest):
    with service.lock:
        try:
            result=enhance_highlights(service.state,request.show_id,request.segment_index)
            service.save()
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.post('/ui/ollama/recap')
def ui_ollama_recap(request: SegmentRecap):
    with service.lock:
        try:
            return segment_recap(service.state, request.show_id, request.segment_index)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
