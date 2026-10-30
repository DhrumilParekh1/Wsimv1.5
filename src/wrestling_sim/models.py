"""Domain entities and game-state serialization-friendly dataclasses."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .weights import ALL_ATTRIBUTES, ROLES, SEGMENT_WEIGHTS


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return min(high, max(low, value))


@dataclass
class Wrestler:
    id: str
    name: str
    age: int
    company_id: str | None
    attributes: dict[str, float]
    role: str = "face"
    growth_aptitude: float = .55
    development_runway: float = .55
    availability: float = 100.0
    morale: float = 17.0
    fatigue: float = 0.0
    salary_weekly: int = 0
    contract_weeks: int = 0
    relationships: dict[str, float] = field(default_factory=dict)
    division: str = "men"
    personality: str = "balanced"
    owner_relationship: float = 15.0
    discovery_tier: str = "known"  # known / regional / national / global
    moveset: list[dict[str, Any]] = field(default_factory=list)
    injury: dict[str, Any] | None = None
    injury_history: list[dict[str, Any]] = field(default_factory=list)
    card_tier: str = "mid_card"  # main_event/upper_mid_card/mid_card/lower_mid_card/jobber
    height_cm: int = 180
    weight_kg: float = 90
    traits: list[str] = field(default_factory=list)
    wants_release: bool = False

    def __post_init__(self) -> None:
        from .movesets import default_moveset, validate_moveset
        if not self.moveset:
            self.moveset = default_moveset(self.id, self.attributes)
        validate_moveset(self.moveset)
        if self.injury is not None:
            if (self.injury.get('severity') not in ('short','medium','long')
                    or not 1 <= self.injury.get('weeks_remaining',0) <= 52):
                raise ValueError('Invalid active injury duration or category')
        if self.discovery_tier not in ("known", "regional", "national", "global"):
            raise ValueError("Unknown scouting discovery tier")
        if self.card_tier not in ("main_event","upper_mid_card","mid_card","lower_mid_card","jobber"):
            raise ValueError('Invalid roster card tier')
        if self.division not in ("men", "women"):
            raise ValueError("Wrestler division must be men or women")
        if not 0 <= self.owner_relationship <= 25:
            raise ValueError("Owner relationship must be rated 0..25")
        if self.personality not in ("balanced", "ambitious", "cooperative", "independent", "volatile"):
            raise ValueError("Unknown wrestler personality")
        if self.role not in ROLES:
            raise ValueError("Role must be face, heel, or tweener")
        if set(self.attributes) != set(ALL_ATTRIBUTES):
            raise ValueError(f"{self.name}: attributes must contain exactly {len(ALL_ATTRIBUTES)} fields")
        if any(not 0 <= value <= 25 for value in self.attributes.values()):
            raise ValueError("All wrestler attributes must be in the 0..25 range")
        if not (0 <= self.growth_aptitude <= 1 and 0 <= self.development_runway <= 1):
            raise ValueError("Growth aptitude and runway must be within 0..1")
        if not 135 <= self.height_cm <= 240 or not 45 <= self.weight_kg <= 260:
            raise ValueError('Invalid wrestler physical profile')
        if len(self.traits)>8 or len(self.traits)!=len(set(self.traits)):
            raise ValueError('Wrestler traits must be unique, maximum eight')
        if self.age < 18:
            raise ValueError("All simulated professional wrestlers must be adults")
        if self.salary_weekly < 0 or self.contract_weeks < 0:
            raise ValueError("Contract values must be nonnegative")
        if self.contract_weeks == 0 and self.company_id:
            raise ValueError("A contracted wrestler needs positive contract weeks")


@dataclass
class Company:
    id: str
    name: str
    money: int
    popularity: float
    fan_trust: float
    sponsor_interest: float
    weekly_fixed_costs: int
    venue_capacity: int
    ticket_price: int
    roster_limit: int
    brand: str = "balanced"
    viewership: int = 0
    prestige_history: float = 50.0
    show_minutes: int = 120
    ppv_weeks: list[int] = field(default_factory=lambda:[17,35,52])

    def __post_init__(self):
        if self.viewership <= 0:
            self.viewership = max(1000, round(25000 + self.popularity * 4500))


@dataclass
class Storyline:
    id: str
    title: str
    wrestler_ids: list[str]
    hype: float = 40
    fan_investment: float = 40
    coherence: float = 65
    stage: str = "building"
    history: list[dict[str, Any]] = field(default_factory=list)
    last_seen_week: int | None = None
    planned_beat: dict[str, Any] = field(default_factory=dict)
    expectations: list[dict[str, Any]] = field(default_factory=list)
    compliance_streak: int = 0
    ignored_streak: int = 0
    escalation_level: float = 0.0
    fatigue: float = 0.0
    anticipation: float = 45.0


@dataclass
class Segment:
    kind: str
    wrestler_ids: list[str]
    duration: int
    title: str
    storyline_id: str | None = None
    booking_quality: float = 17
    planned_winner_id: str | None = None
    creative_direction: str = "advance"
    match_style: str = "balanced"
    finish_type: str = "clean"
    stipulation: str = "standard"
    intensity: str = "standard"
    promo_brawl: bool = False
    promo_topic: str | None = None  # optional solo in-ring promo purpose, distinct from storyline direction
    promo_interrupt: bool = False
    match_styles: list[str] = field(default_factory=list)  # ordered 2–3 style combination; [] loads legacy saves
    role_turn_wrestler_id: str | None = None
    role_turn_to: str | None = None
    promotion_effort: float | None = None  # legacy 0..25 input; existing saves only
    promotion_budget: int | None = None  # cash allocated per segment
    championship_id: str | None = None
    match_format: str = "singles"  # singles/triple_threat/fatal_four_way/battle_royale
    tournament_id: str | None = None
    tournament_match_id: str | None = None
    featured_eliminations: list[str] = field(default_factory=list)  # named late Battle Royale eliminations

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError('Every segment needs a descriptive title')
        if bool(self.role_turn_wrestler_id) != bool(self.role_turn_to):
            raise ValueError('Choose both wrestler and new alignment for a turn')
        if self.role_turn_wrestler_id and (self.role_turn_wrestler_id not in self.wrestler_ids or self.role_turn_to not in ROLES):
            raise ValueError('Role turn must involve a booked wrestler and valid alignment')
        if self.kind not in SEGMENT_WEIGHTS:
            raise ValueError(f"Unknown segment kind: {self.kind}")
        if self.duration < 1 or self.duration > 60:
            raise ValueError("Segment duration must be 1..60 minutes")
        if len(set(self.wrestler_ids)) != len(self.wrestler_ids) or not self.wrestler_ids:
            raise ValueError("Segments need at least one unique participant")
        if self.promo_topic is not None and (self.kind != "promo" or self.promo_topic not in (
            "self_hype","ambitions","address_fans","recent_win","recent_loss",
            "open_challenge","title_reign","callout")):
            raise ValueError("Unknown solo promo topic")
        if self.promo_interrupt and (self.kind!="promo" or len(self.wrestler_ids)!=2):
            raise ValueError("An interrupted promo requires two different wrestlers")
        if self.kind=="confrontation" and len(self.wrestler_ids)<2:
            raise ValueError("A confrontation requires at least two wrestlers")
        formats={"singles":(2,2),"triple_threat":(3,3),
                 "fatal_four_way":(4,4),"battle_royale":(4,20)}
        if self.match_format not in formats:
            raise ValueError("Unknown match format")
        if self.kind != "match" and self.match_format != "singles":
            raise ValueError("Multi-person formats are matches only")
        if self.kind == "match":
            low, high = formats[self.match_format]
            if not low <= len(self.wrestler_ids) <= high:
                raise ValueError(f"{self.match_format} requires {low}–{high} wrestlers")
            if self.match_format != "singles" and self.finish_type not in (
                    ("clean",) if self.match_format=="battle_royale"
                    else ("clean","flash_pin","interference")):
                raise ValueError("Multi-person matches require a compatible finish")
        if self.featured_eliminations:
            if (self.match_format!="battle_royale" or
                len(self.featured_eliminations)!=len(set(self.featured_eliminations)) or
                not set(self.featured_eliminations).issubset(self.wrestler_ids) or
                self.planned_winner_id in self.featured_eliminations):
                raise ValueError("Featured Battle Royale eliminations must be unique, eligible non-winners")
        if bool(self.tournament_id) != bool(self.tournament_match_id):
            raise ValueError("Tournament identifier and match identifier must be supplied together")
        if self.tournament_id and self.kind!="match":
            raise ValueError("Only matches can advance a tournament")
        if self.planned_winner_id and (self.kind != "match" or self.planned_winner_id not in self.wrestler_ids):
            raise ValueError("Booked winner must appear in a match")
        if self.promotion_budget is not None and (self.promotion_budget < 0 or self.promotion_budget > 100000000):
            raise ValueError('Promotion budget must be a nonnegative dollar amount')
        if self.promotion_effort is not None and not 0 <= self.promotion_effort <= 25:
            raise ValueError('Promotion effort must be 0..25')
        if self.championship_id and self.kind != 'match':
            raise ValueError('Championships can only be defended in matches')
        if not 0 <= self.booking_quality <= 25:
            raise ValueError("Booking quality must be within 0..25")
        if self.creative_direction not in ("advance", "slow_burn", "escalate", "resolve", "swerve"):
            raise ValueError("Unrecognized creative direction")
        allowed_styles = ("balanced", "technical", "high_flying", "power", "brawl", "storytelling")
        if self.match_styles and (self.kind != 'match' or not 2 <= len(self.match_styles) <= 3
                                  or len(set(self.match_styles)) != len(self.match_styles)
                                  or any(style not in allowed_styles for style in self.match_styles)):
            raise ValueError('Choose 2 or 3 different valid match styles')
        if self.match_style not in allowed_styles:
            raise ValueError("Unrecognized match style")
        if self.finish_type not in ("clean", "flash_pin", "interference", "disqualification", "time_limit_draw"):
            raise ValueError("Unrecognized match finish")
        if self.stipulation not in ("standard", "no_disqualification", "submission", "ironman", "cage", "extreme"):
            raise ValueError("Unrecognized stipulation")
        if self.intensity not in ("measured", "standard", "high"):
            raise ValueError("Unrecognized match intensity")
        if self.kind == "match":
            if self.finish_type == "time_limit_draw":
                raise ValueError("Time-limit draws are unavailable: book a named winner or a disqualification")
            if not self.planned_winner_id:
                raise ValueError("Every singles match must have a named winner; interference or DQ also requires an awarded winner")
            if self.finish_type == "disqualification" and self.stipulation == "no_disqualification":
                raise ValueError("Disqualification finishes are not allowed in no-disqualification matches")
            if self.finish_type in ("flash_pin", "disqualification") and self.stipulation == "submission":
                raise ValueError("Submission-only matches cannot end with this finish")
            if self.finish_type == "time_limit_draw" and self.stipulation == "ironman":
                raise ValueError("Use a regular finish for an Ironman match")
            if self.finish_type in ("interference", "disqualification", "flash_pin") and not self.planned_winner_id:
                raise ValueError("This finish needs a booked winner")


@dataclass
class Show:
    id: str
    name: str
    week: int
    segments: list[Segment]
    duration: int = 120
    simulated: bool = False
    result: dict[str, Any] | None = None


@dataclass
class GameState:
    seed: int
    year: int
    week: int
    player_company_id: str
    companies: dict[str, Company]
    wrestlers: dict[str, Wrestler]
    storylines: dict[str, Storyline] = field(default_factory=dict)
    shows: dict[str, Show] = field(default_factory=dict)
    news: list[str] = field(default_factory=list)
    financial_history: list[dict[str, Any]] = field(default_factory=list)
    decisions: dict[str, str] = field(default_factory=dict)
    activity_log: list[dict[str, Any]] = field(default_factory=list)
    scenes: dict[str, dict[str, Any]] = field(default_factory=dict)
    creative_head_id: str = "morgan"
    assignments: dict[str, dict[str, Any]] = field(default_factory=dict)
    interactions: list[dict[str, Any]] = field(default_factory=list)
    # V0.5 persistent management systems; older saves receive empty defaults.
    coaches: dict[str, dict[str, Any]] = field(default_factory=dict)
    scouts: dict[str, dict[str, Any]] = field(default_factory=dict)
    coach_assignments: dict[str, str] = field(default_factory=dict)
    scouting_reports: list[dict[str, Any]] = field(default_factory=list)
    world_news: list[dict[str, Any]] = field(default_factory=list)
    rival_history: list[dict[str, Any]] = field(default_factory=list)
    weekly_metrics: list[dict[str, Any]] = field(default_factory=list)
    dialogue_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    contract_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    sponsor_deals: dict[str, dict[str, Any]] = field(default_factory=dict)
    sponsor_responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    social_posts: list[dict[str, Any]] = field(default_factory=list)
    memories: list[dict[str, Any]] = field(default_factory=list)
    narrative_alerts: list[dict[str, Any]] = field(default_factory=list)
    championships: dict[str, dict[str, Any]] = field(default_factory=dict)
    tournaments: dict[str, dict[str, Any]] = field(default_factory=dict)
    chemistry: dict[str, dict[str, Any]] = field(default_factory=dict)
    talent_appearances: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    talent_concerns: list[dict[str, Any]] = field(default_factory=list)
    incidents: list[dict[str, Any]] = field(default_factory=list)
    mentorships: list[dict[str, Any]] = field(default_factory=list)
    press_conferences: dict[str, dict[str, Any]] = field(default_factory=dict)
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    recruitment_interest: list[dict[str, Any]] = field(default_factory=list)
    precontracts: list[dict[str, Any]] = field(default_factory=list)
    contract_promises: list[dict[str, Any]] = field(default_factory=list)
    transfer_offers: list[dict[str, Any]] = field(default_factory=list)
    next_id: int = 1

    @property
    def player_company(self) -> Company:
        return self.companies[self.player_company_id]

    def generate_id(self, prefix: str) -> str:
        result = f"{prefix}-{self.next_id}"
        self.next_id += 1
        return result
