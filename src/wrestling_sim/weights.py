"""Editable weights and shared rating/segment rules.

All raw skills are 0..25, category/rating outputs 0..100.
Weights sum to 1 within each category; no hidden overall score used to resolve segments.
"""
from __future__ import annotations

PERFORMANCE_ATTRIBUTES = (
    "charisma", "mic_skills", "character_work", "presence", "workrate",
    "technique", "moves", "sequences", "flair", "athleticism", "agility",
    "determination", "selling", "stamina",
)
BACKSTAGE_ATTRIBUTES = (
    "professionalism", "social_media_work", "controversy_risk", "experience",
    "promotion", "loyalty", "ambition", "injury_proneness",
)
AUDIENCE_ATTRIBUTES = ("fan_connection", "popularity", "relevance", "momentum")
ROLE_ATTRIBUTES = ("face", "heel", "tweener")
ALL_ATTRIBUTES = PERFORMANCE_ATTRIBUTES + BACKSTAGE_ATTRIBUTES + AUDIENCE_ATTRIBUTES + ROLE_ATTRIBUTES
ROLES = ROLE_ATTRIBUTES

MATCH_WEIGHTS = {
    "workrate": .14, "technique": .13, "moves": .09, "sequences": .10,
    "athleticism": .10, "agility": .07, "selling": .13, "stamina": .10,
    "flair": .06, "determination": .04, "experience": .04,
}
PROMO_WEIGHTS = {
    "mic_skills": .24, "charisma": .20, "character_work": .19,
    "presence": .15, "flair": .05, "determination": .04,
    "experience": .04, "role_fit": .09,
}
COMMERCIAL_WEIGHTS = {
    "popularity": .22, "fan_connection": .18, "relevance": .16,
    "momentum": .16, "promotion": .10, "social_media_work": .08,
    "presence": .05, "role_fit": .05,
}
BACKSTAGE_WEIGHTS = {
    "professionalism": .30, "loyalty": .18, "ambition": .12,
    "experience": .16, "determination": .14, "controversy_safety": .10,
}
CURRENT_ABILITY_WEIGHTS = {
    "match": .35, "promo": .30, "commercial": .25, "backstage": .10,
}
MARKET_VALUE_WEIGHTS = {
    "commercial": .35, "current_ability": .20, "potential_ability": .15,
    "demand": .15, "availability": .15,
}

# The factors below are used by each segment's own simulation formula, not by CA.
# All factor values are 0..100, before controlled RNG.
SEGMENT_WEIGHTS = {
    "match": {"performers": .50, "story": .13, "chemistry": .12, "booking": .13, "pacing": .12},
    "promo": {"performers": .48, "story": .20, "chemistry": .10, "booking": .14, "pacing": .08},
    "confrontation": {"performers": .43, "story": .23, "chemistry": .13, "booking": .15, "pacing": .06},
    "backstage": {"performers": .36, "story": .30, "chemistry": .12, "booking": .14, "pacing": .08},
    "betrayal": {"performers": .32, "story": .35, "chemistry": .11, "booking": .17, "pacing": .05},
    "interview": {"performers": .54, "story": .18, "chemistry": .08, "booking": .12, "pacing": .08},
    "contract_signing": {"performers": .40, "story": .29, "chemistry": .12, "booking": .14, "pacing": .05},
    "return": {"performers": .40, "story": .31, "chemistry": .06, "booking": .15, "pacing": .08},
}
SEGMENT_DURATION = {
    "match": (6, 25), "promo": (3, 9), "confrontation": (4, 12),
    "backstage": (2, 7), "betrayal": (3, 8), "interview": (2, 6),
    "contract_signing": (5, 12), "return": (3, 8),
}
for key, group in {
    "match": MATCH_WEIGHTS, "promo": PROMO_WEIGHTS, "commercial": COMMERCIAL_WEIGHTS,
    "backstage": BACKSTAGE_WEIGHTS, "current": CURRENT_ABILITY_WEIGHTS,
    "market": MARKET_VALUE_WEIGHTS, **{f"segment:{k}": v for k, v in SEGMENT_WEIGHTS.items()},
}.items():
    assert abs(sum(group.values()) - 1) < 1e-9, f"{key} weights do not total 1"
assert len(set(ALL_ATTRIBUTES)) == 29
