"""Slow skill progression and faster audience/condition fluctuations."""
from __future__ import annotations
import random
from .models import GameState, Wrestler, clamp
from .weights import PERFORMANCE_ATTRIBUTES


def after_appearance(wrestler: Wrestler, kind: str, crowd: float, quality: float,
                     duration: int, rng: random.Random,
                     intensity: str = "standard", stipulation: str = "standard",
                     promo_brawl: bool = False) -> None:
    """Effects happen after a segment so its starting attributes determine its outcome."""
    a = wrestler.attributes
    impression = (crowd - 55) / 25
    a["momentum"] = clamp(a["momentum"] + impression + rng.uniform(-.16, .16), 0, 25)
    a["fan_connection"] = clamp(a["fan_connection"] + impression * .12, 0, 25)
    a["popularity"] = clamp(a["popularity"] + impression * .065, 0, 25)
    a["relevance"] = clamp(a["relevance"] + impression * .13, 0, 25)
    if kind == "match":
        extra = {"standard":1, "no_disqualification":1.30, "submission":1.12,
                 "ironman":1.40, "cage":1.55, "extreme":1.75}[stipulation]
        tempo = {"measured":.78, "standard":1, "high":1.35}[intensity]
        wrestler.fatigue = clamp(wrestler.fatigue + duration * .28 * extra * tempo, 0, 25)
        a["stamina"] = clamp(a["stamina"] + .015 * wrestler.growth_aptitude, 0, 25)
    else:
        wrestler.fatigue = clamp(wrestler.fatigue + duration * (.18 if promo_brawl else .055), 0, 25)
        a[wrestler.role] = clamp(a[wrestler.role] + .025 * wrestler.growth_aptitude, 0, 25)
    wrestler.morale = clamp(wrestler.morale + (quality - 65) / 110, 0, 25)


def progress_week(state: GameState, rng: random.Random) -> list[str]:
    messages = []
    for wrestler in state.wrestlers.values():
        recovery = 4.0 + wrestler.attributes['stamina'] / 7 + wrestler.attributes['professionalism'] / 25
        wrestler.fatigue = clamp(wrestler.fatigue - recovery, 0, 25)
        for skill in PERFORMANCE_ATTRIBUTES:
            old = wrestler.attributes[skill]
            peak_pressure = max(0, wrestler.age - 34) / 16
            physical = skill in ("athleticism", "agility", "stamina")
            learning = .045 * wrestler.growth_aptitude * wrestler.development_runway * (1 - old / 25)
            ageing = (.042 if physical else .012) * peak_pressure
            jitter = rng.uniform(-.017, .017)
            wrestler.attributes[skill] = round(clamp(old + learning - ageing + jitter, 0, 25), 4)
        a = wrestler.attributes
        a["momentum"] = clamp(a["momentum"] * .965 + 12 * .035, 0, 25)
        a["relevance"] = clamp(a["relevance"] - (.045 if wrestler.company_id else .09), 0, 25)
        a["fan_connection"] = clamp(a["fan_connection"] - .008, 0, 25)
        if wrestler.age > 36:
            wrestler.development_runway = max(0, wrestler.development_runway - .0005)
        if wrestler.contract_weeks > 0:
            wrestler.contract_weeks -= 1
            if wrestler.contract_weeks == 0:
                old_company = wrestler.company_id
                wrestler.company_id = None
                wrestler.salary_weekly = 0
                from .industry import star_movement
                star_movement(state,wrestler,old_company,None)
                messages.append(f"{wrestler.name}'s contract with {state.companies[old_company].name} expired.")
    return messages
