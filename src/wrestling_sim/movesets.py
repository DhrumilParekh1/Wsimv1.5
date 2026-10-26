"""A move belongs to its performer; narrative models may not add moves to this registry.

Move text is fictional, non-graphic, and descriptive rather than instructional.
"""
from __future__ import annotations

# Each wrestler gets an intentionally small, readable signature library.
# Styles are booker-facing categories and provide weighted selection for highlights.
PRESET = {
    'power': ['shoulder tackle', 'spinebuster', 'power slam', 'running clothesline', 'powerbomb'],
    'technical': ['wristlock counter', 'arm drag', 'suplex', 'mat reversal', 'submission hold'],
    'high_flying': ['springboard crossbody', 'dropkick', 'top-rope splash', 'hurricanrana', 'running moonsault'],
    'brawl': ['clothesline', 'corner exchange', 'running knee', 'swinging neckbreaker', 'ring apron counter'],
    'storytelling': ['headlock reversal', 'small package', 'signature counter', 'dramatic near fall', 'comeback clothesline'],
}
SIGNATURE_STYLES = {
    'steel': ('power','storytelling'), 'phoenix': ('high_flying','technical'),
    'vale': ('storytelling','brawl'), 'cruz': ('technical','high_flying'),
    'collins': ('technical','storytelling'), 'knox': ('power','brawl'),
    'storm': ('power','storytelling'), 'haze': ('high_flying','technical'),
    'ryder': ('storytelling','brawl'), 'sora': ('technical','high_flying'),
    'mizuki': ('high_flying','brawl'), 'arden': ('brawl','storytelling'),
    'lyra': ('storytelling','technical'), 'orbit': ('high_flying','technical'),
    'crowe': ('brawl','storytelling'), 'eden': ('storytelling','technical'),
    'pike': ('technical','power'), 'talia': ('technical','high_flying'),
    'thorn': ('power','technical'), 'aria': ('storytelling','brawl'),
    'solis': ('high_flying','technical'), 'hart': ('technical','storytelling'),
    'blaze': ('brawl','storytelling'), 'finn': ('technical','power'),
}


def default_moveset(wrestler_id: str, attributes: dict | None = None) -> list[dict]:
    """Preset by identity for starter cast, by best capabilities for custom talent."""
    if wrestler_id in SIGNATURE_STYLES:
        styles = SIGNATURE_STYLES[wrestler_id]
    else:
        a = attributes or {}
        scores = {
            'power': a.get('athleticism', 15)+a.get('presence', 15),
            'technical': a.get('technique', 15)+a.get('workrate', 15),
            'high_flying': a.get('agility', 15)+a.get('moves', 15),
            'brawl': a.get('presence', 15)+a.get('selling', 15),
            'storytelling': a.get('character_work', 15)+a.get('experience', 15),
        }
        styles = tuple(sorted(scores, key=lambda k: (-scores[k],k))[:2])
    # Four foundations + exactly one finisher; signatures are supplementary, not
    # separate scoring multipliers. Distinct wrestlers retain individual styles.
    primary, secondary = styles
    base = [dict(name=name, style=primary, finisher=False) for name in PRESET[primary][:3]]
    base.append(dict(name=PRESET[secondary][0], style=secondary, finisher=False))
    base.append(dict(name=PRESET[primary][-1], style=primary, finisher=True))
    signatures = [dict(name=name, style=secondary, finisher=False, signature=True)
                  for name in PRESET[secondary][1:3] if name not in {m['name'] for m in base}]
    return base + signatures


def validate_moveset(moveset: list[dict]) -> None:
    if not isinstance(moveset,list) or not 3<=len(moveset)<=8:
        raise ValueError('Wrestler movesets allow 3–8 moves (five core including a finisher, plus signatures)')
    if len({m.get('name') for m in moveset if isinstance(m,dict)}) != len(moveset):
        raise ValueError('Duplicate moves in wrestler moveset')
    if sum(bool(m.get('finisher')) for m in moveset if isinstance(m,dict)) != 1:
        raise ValueError('Exactly one finisher is required')
    if sum(bool(m.get('signature')) for m in moveset if isinstance(m,dict)) > 3:
        raise ValueError('At most three flair moves are allowed')
    for move in moveset:
        if (not isinstance(move,dict) or not isinstance(move.get('name'),str)
            or not 2<=len(move['name'])<=65 or move.get('style') not in PRESET
            or not isinstance(move.get('finisher'),bool)):
            raise ValueError('Invalid move definition')
