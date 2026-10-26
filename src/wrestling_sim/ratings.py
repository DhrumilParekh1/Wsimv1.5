"""0..25 skills -> 0..100 category, CA, PA, and MV ratings.

PA is a projected ceiling, NOT a promise; MV is a relative score, NOT dollars.
"""
from __future__ import annotations
from .models import Wrestler, clamp
from .weights import (
    MATCH_WEIGHTS, PROMO_WEIGHTS, COMMERCIAL_WEIGHTS, BACKSTAGE_WEIGHTS,
    CURRENT_ABILITY_WEIGHTS, MARKET_VALUE_WEIGHTS,
)


def attribute_value(wrestler: Wrestler, key: str) -> float:
    if key == "role_fit":
        return wrestler.attributes[wrestler.role]
    if key == "controversy_safety":
        return 25 - wrestler.attributes["controversy_risk"]
    return wrestler.attributes[key]


def weighted_category(wrestler: Wrestler, weights: dict[str, float]) -> float:
    return round(4 * sum(weight * attribute_value(wrestler, key) for key, weight in weights.items()), 2)


def rating_breakdown(wrestler: Wrestler) -> dict[str, float]:
    match = weighted_category(wrestler, MATCH_WEIGHTS)
    promo = weighted_category(wrestler, PROMO_WEIGHTS)
    commercial = weighted_category(wrestler, COMMERCIAL_WEIGHTS)
    backstage = weighted_category(wrestler, BACKSTAGE_WEIGHTS)
    categories = {"match": match, "promo": promo, "commercial": commercial, "backstage": backstage}
    ca = sum(categories[key] * weight for key, weight in CURRENT_ABILITY_WEIGHTS.items())
    pa = ca + (100 - ca) * wrestler.growth_aptitude * wrestler.development_runway
    demand = 4 * sum(wrestler.attributes[key] for key in ("popularity", "relevance", "momentum")) / 3
    market_inputs = {
        "commercial": commercial, "current_ability": ca, "potential_ability": pa,
        "demand": demand, "availability": 0 if wrestler.injury else wrestler.availability,
    }
    market = sum(market_inputs[key] * weight for key, weight in MARKET_VALUE_WEIGHTS.items())
    return {**categories, "current_ability": round(clamp(ca), 2),
            "potential_ability": round(clamp(pa), 2), "demand": round(demand, 2),
            "market_value": round(clamp(market), 2)}
